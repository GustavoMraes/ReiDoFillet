from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comanda, Mesa, Reserva
from app.models.enums import STATUS_COMANDA_ATIVA, StatusReserva

TOLERANCIA_RESERVA = timedelta(minutes=30)
ANTECEDENCIA_AVISO_RESERVA = timedelta(hours=2)


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

    async def obter(self, mesa_id: int) -> Mesa | None:
        return await self.session.get(Mesa, mesa_id)

    async def obter_para_atualizar(self, mesa_id: int) -> Mesa | None:
        """Bloqueia a linha da mesa até o fim da transação: serializa reservas, check-ins e transferências da mesa.

        FOR NO KEY UPDATE não conflita com o FOR KEY SHARE que o PostgreSQL usa ao conferir a chave estrangeira
        de uma comanda inserida na mesa; com FOR UPDATE, transferência e abertura simultâneas entravam em deadlock.
        """
        consulta = select(Mesa).where(Mesa.id == mesa_id).with_for_update(key_share=True)
        resultado = await self.session.execute(consulta)
        return resultado.scalar_one_or_none()

    async def comandas_ativas(self, mesa_id: int | None = None) -> list[ComandaAtiva]:
        consulta = select(Comanda.mesa_id, Comanda.status, Comanda.aberta_em).where(
            Comanda.status.in_(STATUS_COMANDA_ATIVA)
        )
        if mesa_id is not None:
            consulta = consulta.where(Comanda.mesa_id == mesa_id)
        return [ComandaAtiva(*linha) for linha in await self.session.execute(consulta)]

    async def reservas_na_janela(self, agora: datetime, mesa_id: int | None = None) -> list[ReservaNaJanela]:
        """Reservas confirmadas com início em [agora - 30min, agora + 2h]: as que bloqueiam a mesa agora
        (janela de ±30min) e as próximas, avisadas no mapa."""
        consulta = select(Reserva.mesa_id, Reserva.inicio).where(
            Reserva.status == StatusReserva.CONFIRMADA,
            Reserva.inicio.between(agora - TOLERANCIA_RESERVA, agora + ANTECEDENCIA_AVISO_RESERVA),
        )
        if mesa_id is not None:
            consulta = consulta.where(Reserva.mesa_id == mesa_id)
        return [ReservaNaJanela(*linha) for linha in await self.session.execute(consulta)]
