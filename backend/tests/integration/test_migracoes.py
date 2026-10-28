import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import app.models  # noqa: F401
from app.db.base import Base
from tests.integration.conftest import alembic_config


async def test_migracao_corresponde_aos_models(engine: AsyncEngine):
    def comparar(conn):
        return compare_metadata(MigrationContext.configure(conn), Base.metadata)

    async with engine.connect() as conn:
        diferencas = await conn.run_sync(comparar)

    assert diferencas == []


async def test_downgrade_e_upgrade_completos(engine: AsyncEngine, url_teste: str):
    config = alembic_config(url_teste)

    await asyncio.to_thread(command.downgrade, config, "base")
    async with engine.connect() as conn:
        restantes = (
            await conn.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'alembic_version'"))
        ).scalar_one()
    assert restantes == 0

    await asyncio.to_thread(command.upgrade, config, "head")
    async with engine.connect() as conn:
        tabelas = (
            await conn.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'alembic_version'"))
        ).scalar_one()
    assert tabelas == 10


async def _criar_mesa(session: AsyncSession) -> int:
    return (
        await session.execute(
            text("INSERT INTO mesa (numero, capacidade, localizacao) VALUES (1, 4, 'Salão') RETURNING id")
        )
    ).scalar_one()


async def _criar_comanda(session: AsyncSession, mesa_id: int, status: str) -> None:
    await session.execute(
        text("INSERT INTO comanda (mesa_id, status) VALUES (:mesa, :status)"), {"mesa": mesa_id, "status": status}
    )


async def test_mesa_aceita_comanda_ativa_mais_comanda_fechada(session: AsyncSession):
    mesa_id = await _criar_mesa(session)

    await _criar_comanda(session, mesa_id, "FECHADA")
    await _criar_comanda(session, mesa_id, "CANCELADA")
    await _criar_comanda(session, mesa_id, "ABERTA")
    await session.commit()


@pytest.mark.parametrize("segunda", ["ABERTA", "PRE_CONTA"])
async def test_mesa_rejeita_duas_comandas_ativas(session: AsyncSession, segunda: str):
    mesa_id = await _criar_mesa(session)
    await _criar_comanda(session, mesa_id, "ABERTA")
    await session.commit()

    with pytest.raises(IntegrityError):
        await _criar_comanda(session, mesa_id, segunda)
    await session.rollback()


async def _criar_log(session: AsyncSession) -> int:
    log_id = (
        await session.execute(
            text(
                "INSERT INTO log_auditoria (acao, entidade, entidade_id) VALUES ('CRIAR', 'Mesa', '1') RETURNING id"
            )
        )
    ).scalar_one()
    await session.commit()
    return log_id


async def test_auditoria_rejeita_update(session: AsyncSession):
    log_id = await _criar_log(session)

    with pytest.raises(DBAPIError, match="imutáveis"):
        await session.execute(text("UPDATE log_auditoria SET acao = 'X' WHERE id = :id"), {"id": log_id})
    await session.rollback()


async def test_auditoria_rejeita_delete(session: AsyncSession):
    log_id = await _criar_log(session)

    with pytest.raises(DBAPIError, match="imutáveis"):
        await session.execute(text("DELETE FROM log_auditoria WHERE id = :id"), {"id": log_id})
    await session.rollback()
