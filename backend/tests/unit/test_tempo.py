from datetime import UTC, datetime

import pytest

from app.core.tempo import RelogioFixo, para_exibicao


def test_converte_utc_para_sao_paulo():
    instante_utc = datetime(2026, 10, 25, 23, 15, tzinfo=UTC)

    local = para_exibicao(instante_utc, "America/Sao_Paulo")

    assert (local.hour, local.minute) == (20, 15)
    assert local.utcoffset().total_seconds() == -3 * 3600


def test_rejeita_instante_sem_fuso():
    with pytest.raises(ValueError):
        para_exibicao(datetime(2026, 10, 25, 20, 15))


def test_relogio_fixo_retorna_o_instante_configurado():
    instante = datetime(2026, 10, 25, 23, 0, tzinfo=UTC)

    assert RelogioFixo(instante).agora() == instante
