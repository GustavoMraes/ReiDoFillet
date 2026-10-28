from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.tempo import RelogioFixo, para_exibicao
from app.db.transacao import transacao
from app.models import LogAuditoria, Mesa
from app.repositories.auditoria import AuditoriaRepository
from app.schemas.snapshots import MesaSnapshot
from app.services.auditoria import Acao, AuditoriaService


def _auditoria(session: AsyncSession, instante: datetime | None = None) -> AuditoriaService:
    relogio = RelogioFixo(instante or datetime(2026, 10, 25, 23, 15, tzinfo=UTC))
    return AuditoriaService(AuditoriaRepository(session), relogio)


async def _contar(session: AsyncSession, modelo) -> int:
    return (await session.execute(select(func.count()).select_from(modelo))).scalar_one()


async def test_operacao_e_auditoria_sao_gravadas_juntas(session: AsyncSession):
    async with transacao(session):
        mesa = Mesa(numero=10, capacidade=4, localizacao="Salão")
        session.add(mesa)
        await session.flush()
        _auditoria(session).registrar(
            usuario_id=None,
            acao=Acao.CRIAR,
            entidade="Mesa",
            entidade_id=mesa.id,
            antes=None,
            depois=MesaSnapshot.model_validate(mesa),
        )

    assert await _contar(session, Mesa) == 1
    assert await _contar(session, LogAuditoria) == 1


async def test_falha_na_operacao_desfaz_a_auditoria(session: AsyncSession):
    with pytest.raises(RuntimeError):
        async with transacao(session):
            mesa = Mesa(numero=11, capacidade=4, localizacao="Salão")
            session.add(mesa)
            await session.flush()
            _auditoria(session).registrar(
                usuario_id=None,
                acao=Acao.CRIAR,
                entidade="Mesa",
                entidade_id=mesa.id,
                antes=None,
                depois=MesaSnapshot.model_validate(mesa),
            )
            raise RuntimeError("falha na regra de negócio após preparar a auditoria")

    assert await _contar(session, Mesa) == 0
    assert await _contar(session, LogAuditoria) == 0


async def test_falha_na_auditoria_desfaz_a_operacao(session: AsyncSession):
    with pytest.raises(DBAPIError):
        async with transacao(session):
            mesa = Mesa(numero=12, capacidade=4, localizacao="Salão")
            session.add(mesa)
            await session.flush()
            # entidade com mais de 50 caracteres: a gravação da auditoria falha no banco
            _auditoria(session).registrar(
                usuario_id=None, acao=Acao.CRIAR, entidade="X" * 60, entidade_id=mesa.id, antes=None, depois=None
            )

    assert await _contar(session, Mesa) == 0
    assert await _contar(session, LogAuditoria) == 0


async def test_horario_exibido_em_sao_paulo_independente_do_fuso_do_servidor(
    session: AsyncSession, engine: AsyncEngine
):
    async with transacao(session):
        _auditoria(session, datetime(2026, 10, 25, 23, 15, tzinfo=UTC)).registrar(
            usuario_id=None, acao=Acao.CRIAR, entidade="Mesa", entidade_id=1, antes=None, depois=None
        )

    async with engine.connect() as conn:
        await conn.execute(text("SET TIME ZONE 'Asia/Tokyo'"))
        criado_em = (await conn.execute(select(LogAuditoria.criado_em))).scalar_one()

    exibido = para_exibicao(criado_em, "America/Sao_Paulo")
    assert (exibido.hour, exibido.minute) == (20, 15)
