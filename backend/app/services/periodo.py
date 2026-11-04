"""Período dos relatórios e da consulta da auditoria: datas locais (São Paulo), ambas inclusivas."""

from dataclasses import dataclass
from datetime import date, datetime

from app.core.exceptions import DadoInvalido
from app.core.tempo import intervalo_do_dia, para_exibicao

DIAS_MAXIMOS = 366


@dataclass(frozen=True)
class Periodo:
    inicio: date
    fim: date
    de: datetime  # 00:00 do dia inicial, no fuso local
    ate: datetime  # 00:00 do dia seguinte ao final (exclusivo)


def periodo(inicio: date | None, fim: date | None, agora: datetime) -> Periodo:
    """Sem datas, o período é hoje. A data que faltar assume a outra."""
    hoje = para_exibicao(agora).date()
    inicio = inicio or fim or hoje
    fim = fim or inicio
    if fim < inicio:
        raise DadoInvalido("A data final deve ser igual ou posterior à inicial")
    if (fim - inicio).days + 1 > DIAS_MAXIMOS:
        raise DadoInvalido(f"O período máximo é de {DIAS_MAXIMOS} dias")
    return Periodo(inicio=inicio, fim=fim, de=intervalo_do_dia(inicio)[0], ate=intervalo_do_dia(fim)[1])
