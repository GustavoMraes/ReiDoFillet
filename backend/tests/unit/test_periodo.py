"""Período dos relatórios (spec `relatorios`, "Período dos relatórios")."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.core.exceptions import DadoInvalido
from app.services.periodo import periodo

SP = ZoneInfo("America/Sao_Paulo")
# 01h30 de 3/11 em UTC ainda é 2/11 em São Paulo.
AGORA = datetime(2026, 11, 3, 1, 30, tzinfo=ZoneInfo("UTC"))


def test_periodo_padrao_e_hoje_em_sao_paulo():
    p = periodo(None, None, AGORA)

    assert (p.inicio, p.fim) == (date(2026, 11, 2), date(2026, 11, 2))
    assert (p.de, p.ate) == (datetime(2026, 11, 2, tzinfo=SP), datetime(2026, 11, 3, tzinfo=SP))


def test_datas_inclusivas():
    p = periodo(date(2026, 10, 1), date(2026, 10, 31), AGORA)

    assert (p.de, p.ate) == (datetime(2026, 10, 1, tzinfo=SP), datetime(2026, 11, 1, tzinfo=SP))


def test_data_que_falta_assume_a_outra():
    assert periodo(date(2026, 10, 5), None, AGORA).fim == date(2026, 10, 5)
    assert periodo(None, date(2026, 10, 5), AGORA).inicio == date(2026, 10, 5)


def test_periodo_invertido():
    with pytest.raises(DadoInvalido, match="A data final deve ser igual ou posterior à inicial"):
        periodo(date(2026, 10, 2), date(2026, 10, 1), AGORA)


def test_periodo_longo_demais():
    assert periodo(date(2025, 1, 1), date(2026, 1, 1), AGORA).fim == date(2026, 1, 1)  # 366 dias
    with pytest.raises(DadoInvalido, match="O período máximo é de 366 dias"):
        periodo(date(2025, 1, 1), date(2026, 1, 2), AGORA)
