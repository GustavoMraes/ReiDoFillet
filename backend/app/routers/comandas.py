from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import Relogio, get_relogio
from app.db.session import get_session
from app.models import Funcionario
from app.models.enums import Perfil
from app.repositories.auditoria import AuditoriaRepository
from app.repositories.cardapio import CardapioRepository
from app.repositories.comanda import ComandaRepository
from app.repositories.mesa import MesaRepository
from app.routers.dependencias import exigir_perfis
from app.schemas.comanda import ComandaOut, EnvioOut, ItemAlteracaoIn, ItemIn
from app.services.auditoria import AuditoriaService
from app.services.comanda import ComandaService
from app.services.mesa import MesaService

router = APIRouter(tags=["Comandas"])

atendente = exigir_perfis(Perfil.FUNCIONARIO, Perfil.ADMIN)

ERROS = {
    404: {"description": "Mesa, comanda, item ou produto não encontrado"},
    409: {"description": "Conflito com o estado atual (mesa, comanda ou item)"},
    422: {"description": "Dados inválidos (quantidade fora de 1–99, observação longa)"},
}


def get_comanda_service(
    session: AsyncSession = Depends(get_session), relogio: Relogio = Depends(get_relogio)
) -> ComandaService:
    return ComandaService(
        session,
        ComandaRepository(session),
        MesaService(MesaRepository(session), relogio),
        CardapioRepository(session),
        AuditoriaService(AuditoriaRepository(session), relogio),
        relogio,
    )


@router.post("/mesas/{mesa_id}/comanda", response_model=ComandaOut, status_code=status.HTTP_201_CREATED, responses=ERROS)
async def abrir_comanda(
    mesa_id: int,
    response: Response,
    usuario: Funcionario = Depends(atendente),
    service: ComandaService = Depends(get_comanda_service),
) -> ComandaOut:
    """Abre a comanda da mesa (201) ou devolve a comanda ativa que ela já tem (200)."""
    comanda, criada = await service.abrir(mesa_id, usuario)
    if not criada:
        response.status_code = status.HTTP_200_OK
    return await service.detalhar(comanda)


@router.get("/comandas/{comanda_id}", response_model=ComandaOut, responses=ERROS, dependencies=[Depends(atendente)])
async def obter_comanda(comanda_id: int, service: ComandaService = Depends(get_comanda_service)) -> ComandaOut:
    return await service.detalhar(await service.obter(comanda_id))


@router.post("/comandas/{comanda_id}/itens", response_model=ComandaOut, responses=ERROS)
async def registrar_item(
    comanda_id: int,
    dados: ItemIn,
    usuario: Funcionario = Depends(atendente),
    service: ComandaService = Depends(get_comanda_service),
) -> ComandaOut:
    """Registra um item; se houver item pendente idêntico, soma a quantidade nele."""
    comanda = await service.registrar_item(comanda_id, dados.produto_id, dados.quantidade, dados.observacao, usuario)
    return await service.detalhar(comanda)


@router.patch("/comandas/{comanda_id}/itens/{item_id}", response_model=ComandaOut, responses=ERROS)
async def alterar_item(
    comanda_id: int,
    item_id: int,
    dados: ItemAlteracaoIn,
    usuario: Funcionario = Depends(atendente),
    service: ComandaService = Depends(get_comanda_service),
) -> ComandaOut:
    comanda = await service.alterar_item(comanda_id, item_id, dados.quantidade, dados.observacao, usuario)
    return await service.detalhar(comanda)


@router.post(
    "/comandas/{comanda_id}/enviar",
    response_model=EnvioOut,
    responses={404: ERROS[404], 409: {"description": "Comanda não aberta ou sem itens pendentes"}},
)
async def enviar_para_cozinha(
    comanda_id: int,
    usuario: Funcionario = Depends(atendente),
    service: ComandaService = Depends(get_comanda_service),
) -> EnvioOut:
    """Envia todos os itens pendentes à cozinha (passam a EM_PREPARO) e devolve o cupom do envio."""
    comanda, cupom = await service.enviar(comanda_id, usuario)
    return EnvioOut(comanda=await service.detalhar(comanda), cupom=cupom)


@router.post(
    "/comandas/{comanda_id}/itens/{item_id}/cancelar",
    response_model=ComandaOut,
    responses={**ERROS, 403: {"description": "Item já enviado à cozinha e usuário não é administrador"}},
)
async def cancelar_item(
    comanda_id: int,
    item_id: int,
    usuario: Funcionario = Depends(atendente),
    service: ComandaService = Depends(get_comanda_service),
) -> ComandaOut:
    """Cancela o item (nunca exclui). Itens já enviados à cozinha só por administrador (RN02)."""
    comanda = await service.cancelar_item(comanda_id, item_id, usuario)
    return await service.detalhar(comanda)
