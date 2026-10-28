from datetime import UTC, datetime
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


def para_exibicao(instante: datetime, fuso: str | None = None) -> datetime:
    """Converte um instante com fuso para o fuso de exibição (America/Sao_Paulo por padrão)."""
    if instante.tzinfo is None:
        raise ValueError("O instante precisa ter fuso horário")
    return instante.astimezone(ZoneInfo(fuso or get_settings().tz_exibicao))
