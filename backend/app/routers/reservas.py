from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import Relogio, get_relogio
from app.db.session import get_session
from app.models import Funcionario
from app.models.enums import Perfil
from app.repositories.auditoria import AuditoriaRepository
from app.repositories.mesa import MesaRepository
from app.repositories.reserva import ReservaRepository
from app.routers.comandas import get_comanda_service
from app.routers.dependencias import exigir_perfis
from app.schemas.reserva import CheckInOut, CriacaoReservaOut, ReservaIn, ReservaOut
from app.services.auditoria import AuditoriaService
from app.services.comanda import ComandaService
from app.services.reserva import ReservaService

router = APIRouter(prefix="/reservas", tags=["Reservas"])

atendente = exigir_perfis(Perfil.FUNCIONARIO, Perfil.ADMIN)

ERROS = {
    404: {"description": "Mesa ou reserva não encontrada"},
    409: {"description": "Conflito de horário, mesa em manutenção ou ocupada, ou reserva não confirmada"},
    422: {"description": "Dados inválidos ou horário no passado"},
}


def get_reserva_service(
    session: AsyncSession = Depends(get_session),
    relogio: Relogio = Depends(get_relogio),
    comandas: ComandaService = Depends(get_comanda_service),
) -> ReservaService:
    return ReservaService(
        session,
        ReservaRepository(session),
        MesaRepository(session),
        comandas,
        AuditoriaService(AuditoriaRepository(session), relogio),
        relogio,
    )


@router.get("", response_model=list[ReservaOut], dependencies=[Depends(atendente)])
async def listar_reservas(data: date | None = None, service: ReservaService = Depends(get_reserva_service)) -> list[ReservaOut]:
    """Reservas que começam na data informada (padrão: hoje, no fuso de São Paulo), em ordem de horário."""
    return await service.listar(data)


@router.post("", response_model=CriacaoReservaOut, status_code=status.HTTP_201_CREATED, responses=ERROS)
async def criar_reserva(
    dados: ReservaIn,
    usuario: Funcionario = Depends(atendente),
    service: ReservaService = Depends(get_reserva_service),
) -> CriacaoReservaOut:
    """Cria uma reserva de 2 horas. `inicio` sem fuso é interpretado no fuso de São Paulo."""
    reserva, aviso = await service.criar(
        dados.mesa_id, dados.nome_cliente, dados.telefone, dados.qtd_pessoas, dados.inicio, usuario
    )
    return CriacaoReservaOut(reserva=await service.saida(reserva), aviso=aviso)


@router.post("/{reserva_id}/cancelar", response_model=ReservaOut, responses=ERROS)
async def cancelar_reserva(
    reserva_id: int,
    usuario: Funcionario = Depends(atendente),
    service: ReservaService = Depends(get_reserva_service),
) -> ReservaOut:
    return await service.saida(await service.cancelar(reserva_id, usuario))


@router.post("/{reserva_id}/check-in", response_model=CheckInOut, responses=ERROS)
async def check_in(
    reserva_id: int,
    usuario: Funcionario = Depends(atendente),
    service: ReservaService = Depends(get_reserva_service),
    comandas: ComandaService = Depends(get_comanda_service),
) -> CheckInOut:
    """Conclui a reserva e abre a comanda da mesa, com quem fez o check-in como responsável."""
    reserva, comanda = await service.check_in(reserva_id, usuario)
    return CheckInOut(reserva=await service.saida(reserva), comanda=await comandas.detalhar(comanda))
