from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import Relogio, get_relogio
from app.db.session import get_session
from app.models import Funcionario
from app.models.enums import Perfil
from app.repositories.auditoria import AuditoriaRepository
from app.repositories.comanda import ComandaRepository
from app.repositories.cozinha import CozinhaRepository
from app.routers.dependencias import exigir_perfis
from app.schemas.cozinha import PainelCozinhaOut
from app.services.auditoria import AuditoriaService
from app.services.cozinha import CozinhaService

router = APIRouter(prefix="/cozinha", tags=["Cozinha"])

atendente = exigir_perfis(Perfil.FUNCIONARIO, Perfil.ADMIN)

ERROS = {404: {"description": "Item não encontrado"}, 409: {"description": "Item fora do estágio esperado"}}


def get_cozinha_service(
    session: AsyncSession = Depends(get_session), relogio: Relogio = Depends(get_relogio)
) -> CozinhaService:
    return CozinhaService(
        session,
        CozinhaRepository(session),
        ComandaRepository(session),
        AuditoriaService(AuditoriaRepository(session), relogio),
        relogio,
    )


@router.get("", response_model=PainelCozinhaOut, dependencies=[Depends(atendente)])
async def painel(service: CozinhaService = Depends(get_cozinha_service)) -> PainelCozinhaOut:
    """Itens enviados pelo salão, em preparo e prontos, em ordem de envio."""
    return await service.painel()


@router.post("/itens/{item_id}/pronto", response_model=PainelCozinhaOut, responses=ERROS)
async def marcar_pronto(
    item_id: int,
    usuario: Funcionario = Depends(atendente),
    service: CozinhaService = Depends(get_cozinha_service),
) -> PainelCozinhaOut:
    await service.marcar_pronto(item_id, usuario)
    return await service.painel()


@router.post("/itens/{item_id}/entregue", response_model=PainelCozinhaOut, responses=ERROS)
async def marcar_entregue(
    item_id: int,
    usuario: Funcionario = Depends(atendente),
    service: CozinhaService = Depends(get_cozinha_service),
) -> PainelCozinhaOut:
    await service.marcar_entregue(item_id, usuario)
    return await service.painel()
