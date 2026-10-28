from dataclasses import dataclass
from datetime import datetime

from app.core.tempo import Relogio
from app.models import Mesa
from app.models.enums import StatusComanda, StatusMesa
from app.repositories.mesa import TOLERANCIA_RESERVA, ComandaAtiva, MesaRepository, ReservaNaJanela


@dataclass(frozen=True)
class MesaNoMapa:
    id: int
    numero: int
    capacidade: int
    localizacao: str
    status: StatusMesa
    minutos_atendimento: int | None = None
    reserva_inicio: datetime | None = None


def calcular_mapa(
    mesas: list[Mesa],
    comandas: list[ComandaAtiva],
    reservas: list[ReservaNaJanela],
    agora: datetime,
) -> list[MesaNoMapa]:
    """Status por prioridade: MANUTENCAO > OCUPADA > AGUARDANDO_PAGAMENTO > RESERVADA > LIVRE."""
    comanda_por_mesa = {comanda.mesa_id: comanda for comanda in comandas}
    reserva_por_mesa: dict[int, ReservaNaJanela] = {}
    for reserva in sorted(reservas, key=lambda r: r.inicio):
        if abs(agora - reserva.inicio) <= TOLERANCIA_RESERVA:
            reserva_por_mesa.setdefault(reserva.mesa_id, reserva)

    mapa = []
    for mesa in sorted(mesas, key=lambda m: m.numero):
        comanda = comanda_por_mesa.get(mesa.id)
        reserva = reserva_por_mesa.get(mesa.id)
        minutos = None
        inicio_reserva = None

        if mesa.em_manutencao:
            status = StatusMesa.MANUTENCAO
        elif comanda is not None:
            status = StatusMesa.OCUPADA if comanda.status == StatusComanda.ABERTA else StatusMesa.AGUARDANDO_PAGAMENTO
            minutos = max(0, int((agora - comanda.aberta_em).total_seconds() // 60))
        elif reserva is not None:
            status = StatusMesa.RESERVADA
            inicio_reserva = reserva.inicio
        else:
            status = StatusMesa.LIVRE

        mapa.append(
            MesaNoMapa(
                id=mesa.id,
                numero=mesa.numero,
                capacidade=mesa.capacidade,
                localizacao=mesa.localizacao,
                status=status,
                minutos_atendimento=minutos,
                reserva_inicio=inicio_reserva,
            )
        )
    return mapa


class MesaService:
    def __init__(self, repositorio: MesaRepository, relogio: Relogio):
        self.repositorio = repositorio
        self.relogio = relogio

    async def mapa(self) -> list[MesaNoMapa]:
        agora = self.relogio.agora()
        return calcular_mapa(
            await self.repositorio.listar(),
            await self.repositorio.comandas_ativas(),
            await self.repositorio.reservas_na_janela(agora),
            agora,
        )
