from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comanda, Mesa, Reserva
from app.models.enums import STATUS_COMANDA_ATIVA, StatusReserva

TOLERANCIA_RESERVA = timedelta(minutes=30)


@dataclass(frozen=True)
class ComandaAtiva:
    mesa_id: int
    status: str
    aberta_em: datetime


@dataclass(frozen=True)
class ReservaNaJanela:
    mesa_id: int
    inicio: datetime


class MesaRepository:
    """Busca tudo o que o mapa de mesas precisa em exatamente três consultas."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def listar(self) -> list[Mesa]:
        return list((await self.session.execute(select(Mesa).order_by(Mesa.numero))).scalars())

    async def comandas_ativas(self) -> list[ComandaAtiva]:
        resultado = await self.session.execute(
            select(Comanda.mesa_id, Comanda.status, Comanda.aberta_em).where(Comanda.status.in_(STATUS_COMANDA_ATIVA))
        )
        return [ComandaAtiva(*linha) for linha in resultado]

    async def reservas_na_janela(self, agora: datetime) -> list[ReservaNaJanela]:
        """Reservas confirmadas cuja janela [inicio - 30min, inicio + 30min] contém `agora`."""
        resultado = await self.session.execute(
            select(Reserva.mesa_id, Reserva.inicio).where(
                Reserva.status == StatusReserva.CONFIRMADA,
                Reserva.inicio.between(agora - TOLERANCIA_RESERVA, agora + TOLERANCIA_RESERVA),
            )
        )
        return [ReservaNaJanela(*linha) for linha in resultado]
