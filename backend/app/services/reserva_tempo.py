"""Regras de tempo das reservas: duração, tolerância, situação calculada e dia no fuso de exibição."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.models.enums import StatusReserva
from app.repositories.mesa import TOLERANCIA_RESERVA

DURACAO_RESERVA = timedelta(hours=2)
NAO_COMPARECEU = "NAO_COMPARECEU"


def fuso_local() -> ZoneInfo:
    return ZoneInfo(get_settings().tz_exibicao)


def normalizar_inicio(inicio: datetime) -> datetime:
    """Horário sem fuso vem da tela do restaurante: é interpretado no fuso de São Paulo."""
    return inicio.replace(tzinfo=fuso_local()) if inicio.tzinfo is None else inicio


def intervalo_do_dia(dia: date) -> tuple[datetime, datetime]:
    """[00:00, 00:00 do dia seguinte) no fuso local, para consultar as reservas de uma data."""
    inicio = datetime.combine(dia, time.min, tzinfo=fuso_local())
    return inicio, datetime.combine(dia + timedelta(days=1), time.min, tzinfo=fuso_local())


def situacao(status: str, inicio: datetime, agora: datetime) -> str:
    """Não comparecimento é calculado na leitura: nada é gravado e não há tarefa agendada."""
    if status == StatusReserva.CONFIRMADA and agora > inicio + TOLERANCIA_RESERVA:
        return NAO_COMPARECEU
    return status


def hora_curta(instante: datetime) -> str:
    """20h30, no fuso local."""
    return instante.astimezone(fuso_local()).strftime("%Hh%M")
