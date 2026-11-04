from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from app.core.config import get_settings


class Relogio(Protocol):
    def agora(self) -> datetime:
        """Retorna o instante atual em UTC (timezone-aware)."""
        ...


class RelogioSistema:
    def agora(self) -> datetime:
        return datetime.now(UTC)


class RelogioFixo:
    """Relógio parado em um instante, usado nos testes."""

    def __init__(self, instante: datetime):
        if instante.tzinfo is None:
            raise ValueError("O instante do relógio precisa ter fuso horário")
        self.instante = instante

    def agora(self) -> datetime:
        return self.instante


def get_relogio() -> Relogio:
    return RelogioSistema()


def fuso_local() -> ZoneInfo:
    """Fuso do restaurante (America/Sao_Paulo por padrão)."""
    return ZoneInfo(get_settings().tz_exibicao)


def intervalo_do_dia(dia: date) -> tuple[datetime, datetime]:
    """[00:00, 00:00 do dia seguinte) no fuso local: os limites de uma data para consultas."""
    inicio = datetime.combine(dia, time.min, tzinfo=fuso_local())
    return inicio, datetime.combine(dia + timedelta(days=1), time.min, tzinfo=fuso_local())


def para_exibicao(instante: datetime, fuso: str | None = None) -> datetime:
    """Converte um instante com fuso para o fuso de exibição (America/Sao_Paulo por padrão)."""
    if instante.tzinfo is None:
        raise ValueError("O instante precisa ter fuso horário")
    return instante.astimezone(ZoneInfo(fuso or get_settings().tz_exibicao))
