from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.tempo import Relogio, get_relogio, para_exibicao
from app.db.session import get_session
from app.models import Funcionario
from app.repositories.auditoria import AuditoriaRepository
from app.repositories.funcionario import FuncionarioRepository
from app.routers.dependencias import get_app_settings, usuario_atual
from app.schemas.autenticacao import LoginIn, LoginOut, UsuarioOut
from app.services.auditoria import AuditoriaService
from app.services.autenticacao import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticação"])


def get_auth_service(
    session: AsyncSession = Depends(get_session),
    relogio: Relogio = Depends(get_relogio),
    settings: Settings = Depends(get_app_settings),
) -> AuthService:
    return AuthService(
        session,
        FuncionarioRepository(session),
        AuditoriaService(AuditoriaRepository(session), relogio),
        relogio,
        settings,
    )


@router.post(
    "/login",
    response_model=LoginOut,
    responses={401: {"description": "Usuário ou senha incorretos"}, 403: {"description": "Usuário bloqueado"}},
)
async def login(dados: LoginIn, service: AuthService = Depends(get_auth_service)) -> LoginOut:
    """Inicia uma sessão. Use o `token` retornado no botão *Authorize* do Swagger."""
    sessao = await service.login(dados.login, dados.senha)
    return LoginOut(
        token=sessao.token.valor,
        expira_em=para_exibicao(sessao.token.expira_em),
        usuario=UsuarioOut.model_validate(sessao.funcionario),
    )


@router.get("/me", response_model=UsuarioOut)
async def usuario_logado(funcionario: Funcionario = Depends(usuario_atual)) -> UsuarioOut:
    return UsuarioOut.model_validate(funcionario)
