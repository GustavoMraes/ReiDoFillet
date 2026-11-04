from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.core.tempo import intervalo_do_dia
from app.services.reserva_tempo import hora_curta, normalizar_inicio, situacao

SP = ZoneInfo("America/Sao_Paulo")
RESERVA = datetime(2026, 11, 2, 20, 30, tzinfo=SP)


def test_cliente_nao_apareceu_apos_a_tolerancia():
    assert situacao("CONFIRMADA", RESERVA, datetime(2026, 11, 2, 21, 1, tzinfo=SP)) == "NAO_COMPARECEU"


def test_ainda_dentro_da_tolerancia():
    assert situacao("CONFIRMADA", RESERVA, datetime(2026, 11, 2, 21, 0, tzinfo=SP)) == "CONFIRMADA"


def test_concluida_e_cancelada_nao_viram_nao_compareceu():
    depois = datetime(2026, 11, 3, 10, 0, tzinfo=SP)
    assert situacao("CONCLUIDA", RESERVA, depois) == "CONCLUIDA"
    assert situacao("CANCELADA", RESERVA, depois) == "CANCELADA"


def test_horario_sem_fuso_e_de_sao_paulo():
    normalizado = normalizar_inicio(datetime(2026, 11, 2, 20, 30))

    assert normalizado.astimezone(UTC) == datetime(2026, 11, 2, 23, 30, tzinfo=UTC)


def test_horario_com_fuso_e_mantido():
    em_utc = datetime(2026, 11, 2, 23, 30, tzinfo=UTC)

    assert normalizar_inicio(em_utc) == em_utc


def test_limites_do_dia_no_fuso_local():
    inicio, fim = intervalo_do_dia(date(2026, 11, 2))

    assert inicio.astimezone(UTC) == datetime(2026, 11, 2, 3, 0, tzinfo=UTC)
    assert fim.astimezone(UTC) == datetime(2026, 11, 3, 3, 0, tzinfo=UTC)


def test_hora_curta():
    assert hora_curta(datetime(2026, 11, 2, 23, 30, tzinfo=UTC)) == "20h30"
