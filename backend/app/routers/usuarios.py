from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import Relogio, get_relogio
from app.db.session import get_session
from app.models import Funcionario
from app.models.enums import Perfil
from app.repositories.auditoria import AuditoriaRepository
from app.repositories.funcionario import FuncionarioRepository
from app.routers.dependencias import exigir_perfis
from app.schemas.usuario import NovaSenhaIn, UsuarioAdminOut, UsuarioAlteracaoIn, UsuarioIn
from app.services.auditoria import AuditoriaService
from app.services.funcionario import FuncionarioService

router = APIRouter(prefix="/usuarios", tags=["Usuários"])

administrador = exigir_perfis(Perfil.ADMIN)

ERROS = {
    404: {"description": "Funcionário não encontrado"},
    409: {"description": "Login repetido, autobloqueio ou último administrador ativo"},
    422: {"description": "Dados inválidos"},
}


def get_funcionario_service(
    session: AsyncSession = Depends(get_session), relogio: Relogio = Depends(get_relogio)
) -> FuncionarioService:
    return FuncionarioService(session, FuncionarioRepository(session), AuditoriaService(AuditoriaRepository(session), relogio))


@router.get("", response_model=list[UsuarioAdminOut], dependencies=[Depends(administrador)])
async def listar_usuarios(service: FuncionarioService = Depends(get_funcionario_service)) -> list[UsuarioAdminOut]:
    """Todos os funcionários, bloqueados ou não, em ordem de nome."""
    return [UsuarioAdminOut.model_validate(f) for f in await service.listar()]


@router.post("", response_model=UsuarioAdminOut, status_code=status.HTTP_201_CREATED, responses=ERROS)
async def criar_usuario(
    dados: UsuarioIn,
    usuario: Funcionario = Depends(administrador),
    service: FuncionarioService = Depends(get_funcionario_service),
) -> UsuarioAdminOut:
    """Cadastra um funcionário ativo com senha inicial (mínimo de 8 caracteres). O login não muda depois."""
    return UsuarioAdminOut.model_validate(await service.criar(dados.nome, dados.login, dados.perfil, dados.senha, usuario))


@router.patch("/{funcionario_id}", response_model=UsuarioAdminOut, responses=ERROS)
async def alterar_usuario(
    funcionario_id: int,
    dados: UsuarioAlteracaoIn,
    usuario: Funcionario = Depends(administrador),
    service: FuncionarioService = Depends(get_funcionario_service),
) -> UsuarioAdminOut:
    """Altera nome, perfil ou bloqueio. "Remover" um usuário é bloqueá-lo: ninguém é apagado."""
    alterado = await service.alterar(funcionario_id, dados.model_dump(exclude_unset=True), usuario)
    return UsuarioAdminOut.model_validate(alterado)


@router.post(
    "/{funcionario_id}/senha", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, responses=ERROS
)
async def redefinir_senha(
    funcionario_id: int,
    dados: NovaSenhaIn,
    usuario: Funcionario = Depends(administrador),
    service: FuncionarioService = Depends(get_funcionario_service),
) -> Response:
    """Define uma nova senha para o funcionário, sem precisar da anterior."""
    await service.redefinir_senha(funcionario_id, dados.senha, usuario)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
