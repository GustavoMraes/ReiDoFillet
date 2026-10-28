"""Infraestrutura dos testes de integração.

Usam o banco de TEST_DATABASE_URL, que é recriado do zero a cada execução (schema public
apagado e migrações reaplicadas). Sem essa variável, os testes que precisam de banco são pulados.
"""

import asyncio
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from alembic import command
from alembic.config import Config
from app.core.config import Settings

TABELAS = (
    "log_auditoria, pagamento, item_comanda, comanda, reserva, produto, categoria, mesa, funcionario, parametro"
)


def _url_teste() -> str:
    settings = Settings()
    url = settings.test_database_url
    if not url:
        pytest.skip("TEST_DATABASE_URL não configurada: teste de integração com banco pulado")
    # Os testes apagam o schema inteiro: nunca podem apontar para o banco da aplicação.
    if url == settings.database_url:
        pytest.exit("TEST_DATABASE_URL não pode ser igual a DATABASE_URL", returncode=2)
    return url


def alembic_config(url: str) -> Config:
    config = Config("alembic.ini")
    config.attributes["database_url"] = url
    return config


async def recriar_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))


@pytest.fixture(scope="session")
def url_teste() -> str:
    return _url_teste()


@pytest.fixture(scope="session")
async def engine(url_teste: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(url_teste)
    await recriar_schema(engine)
    # O env.py do Alembic usa asyncio.run, então roda fora do loop dos testes.
    await asyncio.to_thread(command.upgrade, alembic_config(url_teste), "head")
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    # TRUNCATE não dispara o trigger de linha que protege log_auditoria.
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {TABELAS} RESTART IDENTITY CASCADE"))
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
