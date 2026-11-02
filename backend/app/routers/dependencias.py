"""Dependências compartilhadas pelos routers: configuração, sessão do usuário e perfis autorizados."""

from collections.abc import Awaitable, Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import NaoAutenticado, SemPermissao
from app.core.seguranca import TokenInvalido, decodificar_token
from app.db.session import get_session
from app.models import Funcionario
from app.models.enums import Perfil
from app.repositories.funcionario import FuncionarioRepository
from app.services.autenticacao import MENSAGEM_USUARIO_BLOQUEADO

MENSAGEM_SESSAO_INVALIDA = "Sessão inválida ou expirada"
MENSAGEM_SEM_PERMISSAO = "Sem permissão para esta funcionalidade"

_bearer = HTTPBearer(auto_error=False, description="Token obtido em POST /auth/login")


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


async def usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> Funcionario:
    """Valida o token e recarrega o funcionário do banco: bloqueio e mudança de perfil valem na hora."""
    if credenciais is None:
        raise NaoAutenticado(MENSAGEM_SESSAO_INVALIDA)
    try:
        claims = decodificar_token(credenciais.credentials, settings.jwt_secret)
    except TokenInvalido:
        raise NaoAutenticado(MENSAGEM_SESSAO_INVALIDA) from None

    funcionario = await FuncionarioRepository(session).obter(claims.funcionario_id)
    if funcionario is None:
        raise NaoAutenticado(MENSAGEM_SESSAO_INVALIDA)
    if funcionario.bloqueado:
        raise NaoAutenticado(MENSAGEM_USUARIO_BLOQUEADO)
    return funcionario


def exigir_perfis(*perfis: Perfil) -> Callable[..., Awaitable[Funcionario]]:
    """Uso: `funcionario: Funcionario = Depends(exigir_perfis(Perfil.FUNCIONARIO, Perfil.ADMIN))`."""

    async def verificar(funcionario: Funcionario = Depends(usuario_atual)) -> Funcionario:
        if funcionario.perfil not in perfis:
            raise SemPermissao(MENSAGEM_SEM_PERMISSAO)
        return funcionario

    return verificar
