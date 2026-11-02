"""Cenários da spec `autenticacao`: sessão obrigatória, bloqueio em sessão aberta e perfis."""

from datetime import UTC, datetime, timedelta

from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.seguranca import criar_token
from app.db.session import get_session
from app.main import create_app
from app.models import Funcionario
from app.models.enums import Perfil
from app.routers.dependencias import exigir_perfis
from tests.conftest import SEGREDO_TESTE
from tests.integration.fabricas import cabecalho_de, criar_funcionario


def _cliente(session: AsyncSession) -> AsyncClient:
    app = create_app(Settings(_env_file=None, jwt_secret=SEGREDO_TESTE))

    @app.get("/teste/admin")
    async def so_admin(funcionario: Funcionario = Depends(exigir_perfis(Perfil.ADMIN))):
        return {"login": funcionario.login}

    app.dependency_overrides[get_session] = lambda: session
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_requisicao_sem_sessao_e_nao_autenticada(session: AsyncSession):
    async with _cliente(session) as cliente:
        resposta = await cliente.get("/teste/admin")

    assert resposta.status_code == 401
    assert resposta.json() == {"detalhe": "Sessão inválida ou expirada"}


async def test_sessao_adulterada_e_nao_autenticada(session: AsyncSession):
    funcionario = await criar_funcionario(session, "gabriela")
    token = cabecalho_de(funcionario)["Authorization"]

    async with _cliente(session) as cliente:
        resposta = await cliente.get("/teste/admin", headers={"Authorization": token[:-3] + "xyz"})

    assert resposta.status_code == 401


async def test_sessao_expirada_e_nao_autenticada(session: AsyncSession):
    admin = await criar_funcionario(session, "admin", perfil="ADMIN")

    async with _cliente(session) as cliente:
        resposta = await cliente.get("/teste/admin", headers=cabecalho_de(admin, datetime.now(UTC) - timedelta(hours=13)))

    assert resposta.status_code == 401


async def test_sessao_de_outra_chave_e_nao_autenticada(session: AsyncSession):
    admin = await criar_funcionario(session, "admin", perfil="ADMIN")
    token = criar_token(admin.id, "ADMIN", datetime.now(UTC), "outra-chave-qualquer-com-32-caracteres", 12)

    async with _cliente(session) as cliente:
        resposta = await cliente.get("/teste/admin", headers={"Authorization": f"Bearer {token.valor}"})

    assert resposta.status_code == 401


async def test_bloqueio_durante_sessao_aberta(session: AsyncSession):
    admin = await criar_funcionario(session, "admin", perfil="ADMIN")
    cabecalho = cabecalho_de(admin)

    async with _cliente(session) as cliente:
        antes = await cliente.get("/teste/admin", headers=cabecalho)
        admin.bloqueado = True
        await session.commit()
        depois = await cliente.get("/teste/admin", headers=cabecalho)

    assert antes.status_code == 200
    assert depois.status_code == 401
    assert depois.json() == {"detalhe": "Usuário bloqueado"}


async def test_perfil_autorizado(session: AsyncSession):
    admin = await criar_funcionario(session, "admin", perfil="ADMIN")

    async with _cliente(session) as cliente:
        resposta = await cliente.get("/teste/admin", headers=cabecalho_de(admin))

    assert resposta.status_code == 200
    assert resposta.json() == {"login": "admin"}


async def test_perfil_nao_autorizado(session: AsyncSession):
    funcionario = await criar_funcionario(session, "gabriela")

    async with _cliente(session) as cliente:
        resposta = await cliente.get("/teste/admin", headers=cabecalho_de(funcionario))

    assert resposta.status_code == 403
    assert resposta.json() == {"detalhe": "Sem permissão para esta funcionalidade"}


async def test_perfil_vem_do_banco_e_nao_do_token(session: AsyncSession):
    """Um token emitido como ADMIN deixa de valer como ADMIN quando o perfil muda no banco."""
    funcionario = await criar_funcionario(session, "gabriela", perfil="ADMIN")
    cabecalho = cabecalho_de(funcionario)
    funcionario.perfil = "FUNCIONARIO"
    await session.commit()

    async with _cliente(session) as cliente:
        resposta = await cliente.get("/teste/admin", headers=cabecalho)

    assert resposta.status_code == 403
