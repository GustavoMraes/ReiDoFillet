from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Mesa, Reserva
from app.models.enums import StatusReserva


class ReservaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def obter_para_atualizar(self, reserva_id: int) -> Reserva | None:
        resultado = await self.session.execute(
            select(Reserva).where(Reserva.id == reserva_id).with_for_update().execution_options(populate_existing=True)
        )
        return resultado.scalar_one_or_none()

    async def conflitante(self, mesa_id: int, inicio: datetime, fim: datetime) -> Reserva | None:
        """Reserva confirmada da mesa cujo período [inicio, fim) se sobrepõe ao informado."""
        resultado = await self.session.execute(
            select(Reserva)
            .where(
                Reserva.mesa_id == mesa_id,
                Reserva.status == StatusReserva.CONFIRMADA,
                Reserva.inicio < fim,
                Reserva.fim > inicio,
            )
            .order_by(Reserva.inicio)
            .limit(1)
        )
        return resultado.scalar_one_or_none()

    async def do_periodo(self, inicio: datetime, fim: datetime) -> list[tuple[Reserva, int]]:
        """Reservas que começam no período, com o número da mesa, em ordem de horário."""
        resultado = await self.session.execute(
            select(Reserva, Mesa.numero)
            .join(Mesa, Mesa.id == Reserva.mesa_id)
            .where(Reserva.inicio >= inicio, Reserva.inicio < fim)
            .order_by(Reserva.inicio, Mesa.numero)
        )
        return [(reserva, numero) for reserva, numero in resultado]

    async def numero_da_mesa(self, mesa_id: int) -> int:
        return (await self.session.execute(select(Mesa.numero).where(Mesa.id == mesa_id))).scalar_one()
