from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguranca import criar_token, gerar_hash
from app.models import Funcionario
from tests.conftest import SEGREDO_TESTE

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
