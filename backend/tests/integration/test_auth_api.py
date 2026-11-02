from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app
from tests.conftest import SEGREDO_TESTE
from tests.integration.fabricas import SENHA_PADRAO, criar_funcionario


def _cliente(session: AsyncSession) -> AsyncClient:
    app = create_app(Settings(_env_file=None, jwt_secret=SEGREDO_TESTE))
    app.dependency_overrides[get_session] = lambda: session
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_login_pela_api_e_consulta_do_usuario(session: AsyncSession):
    gabriela = await criar_funcionario(session, "gabriela")

    async with _cliente(session) as cliente:
        login = await cliente.post("/auth/login", json={"login": "gabriela", "senha": SENHA_PADRAO})
        corpo = login.json()
        me = await cliente.get("/auth/me", headers={"Authorization": f"Bearer {corpo['token']}"})

    assert login.status_code == 200
    assert corpo["tipo"] == "bearer"
    assert corpo["expira_em"].endswith("-03:00")
    assert corpo["usuario"] == {"id": gabriela.id, "nome": "Gabriela", "login": "gabriela", "perfil": "FUNCIONARIO"}
    assert me.status_code == 200
    assert me.json() == corpo["usuario"]
    assert "senha" not in me.text and "hash" not in me.text


async def test_login_invalido_pela_api(session: AsyncSession):
    await criar_funcionario(session, "gabriela")
    await criar_funcionario(session, "bia", bloqueado=True)

    async with _cliente(session) as cliente:
        errada = await cliente.post("/auth/login", json={"login": "gabriela", "senha": "senha-errada-123"})
        bloqueada = await cliente.post("/auth/login", json={"login": "bia", "senha": SENHA_PADRAO})
        vazia = await cliente.post("/auth/login", json={"login": "", "senha": ""})

    assert (errada.status_code, errada.json()) == (401, {"detalhe": "Usuário ou senha incorretos"})
    assert (bloqueada.status_code, bloqueada.json()) == (403, {"detalhe": "Usuário bloqueado"})
    assert vazia.status_code == 422


async def test_me_sem_sessao(session: AsyncSession):
    async with _cliente(session) as cliente:
        resposta = await cliente.get("/auth/me")

    assert resposta.status_code == 401


async def test_health_continua_publico(session: AsyncSession):
    async with _cliente(session) as cliente:
        resposta = await cliente.get("/health")

    assert resposta.status_code == 200
