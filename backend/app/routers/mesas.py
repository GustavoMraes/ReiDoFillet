from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import Relogio, get_relogio, para_exibicao
from app.db.session import get_session
from app.models.enums import Perfil
from app.repositories.mesa import MesaRepository
from app.routers.dependencias import exigir_perfis
from app.schemas.mesa import MesaMapaOut
from app.services.mesa import MesaService

router = APIRouter(prefix="/mesas", tags=["Mesas"])


def get_mesa_service(
    session: AsyncSession = Depends(get_session), relogio: Relogio = Depends(get_relogio)
) -> MesaService:
    return MesaService(MesaRepository(session), relogio)


@router.get(
    "",
    response_model=list[MesaMapaOut],
    dependencies=[Depends(exigir_perfis(Perfil.FUNCIONARIO, Perfil.ADMIN))],
)
async def mapa_de_mesas(service: MesaService = Depends(get_mesa_service)) -> list[MesaMapaOut]:
    """Mapa de mesas com o status calculado no momento da consulta, ordenado pelo número."""
    return [
        MesaMapaOut(
            id=mesa.id,
            numero=mesa.numero,
            capacidade=mesa.capacidade,
            localizacao=mesa.localizacao,
            status=mesa.status,
            minutos_atendimento=mesa.minutos_atendimento,
            reserva_inicio=para_exibicao(mesa.reserva_inicio) if mesa.reserva_inicio else None,
            proxima_reserva_inicio=(
                para_exibicao(mesa.proxima_reserva_inicio) if mesa.proxima_reserva_inicio else None
            ),
        )
        for mesa in await service.mapa()
    ]
