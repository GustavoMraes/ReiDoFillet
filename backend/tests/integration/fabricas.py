from datetime import UTC, datetime

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.seguranca import criar_token, gerar_hash
from app.core.tempo import Relogio, get_relogio
from app.db.session import get_session
from app.main import create_app
from app.models import Funcionario
from tests.conftest import SEGREDO_TESTE


def cliente_api(session: AsyncSession, relogio: Relogio | None = None) -> AsyncClient:
    """Cliente HTTP da aplicação usando a sessão do teste (e, opcionalmente, um relógio fixo)."""
    app = create_app(Settings(_env_file=None, jwt_secret=SEGREDO_TESTE))
    app.dependency_overrides[get_session] = lambda: session
    if relogio is not None:
        app.dependency_overrides[get_relogio] = lambda: relogio
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

SENHA_PADRAO = "senha-de-teste-123"


async def criar_funcionario(
    session: AsyncSession,
    login: str,
    perfil: str = "FUNCIONARIO",
    senha: str | None = SENHA_PADRAO,
    bloqueado: bool = False,
) -> Funcionario:
    """senha=None cria o funcionário com a senha inutilizável do seed ("!")."""
    funcionario = Funcionario(
        nome=login.capitalize(),
        login=login,
        perfil=perfil,
        senha_hash=gerar_hash(senha) if senha else "!",
        bloqueado=bloqueado,
    )
    session.add(funcionario)
    await session.commit()
    return funcionario


def cabecalho_de(funcionario: Funcionario, emitido_em: datetime | None = None) -> dict[str, str]:
    token = criar_token(funcionario.id, funcionario.perfil, emitido_em or datetime.now(UTC), SEGREDO_TESTE, 12)
    return {"Authorization": f"Bearer {token.valor}"}
