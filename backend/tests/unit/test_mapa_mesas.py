"""Cenários da spec `mesas`: status calculado, janela de reserva e informações complementares."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.models import Mesa
from app.models.enums import StatusMesa
from app.repositories.mesa import ComandaAtiva, ReservaNaJanela
from app.services.mesa import calcular_mapa

SP = ZoneInfo("America/Sao_Paulo")
RESERVA_20H30 = datetime(2026, 10, 25, 20, 30, tzinfo=SP)


def _hora(h: int, m: int, s: int = 0) -> datetime:
    return datetime(2026, 10, 25, h, m, s, tzinfo=SP)


def _mesa(id=1, numero=None, manutencao=False) -> Mesa:
    return Mesa(id=id, numero=numero or id, capacidade=4, localizacao="Salão", em_manutencao=manutencao)


def _uma(mesa, comandas=(), reservas=(), agora=None):
    [resultado] = calcular_mapa([mesa], list(comandas), list(reservas), agora or _hora(20, 0))
    return resultado


def _aberta(status="ABERTA", aberta_em=None, mesa_id=1):
    return ComandaAtiva(mesa_id=mesa_id, status=status, aberta_em=aberta_em or _hora(19, 0))


def _reserva(inicio=RESERVA_20H30, mesa_id=1):
    return ReservaNaJanela(mesa_id=mesa_id, inicio=inicio)


# --- Listagem do mapa de mesas ---


def test_mapa_ordenado_por_numero_com_dados_basicos():
    mesas = [_mesa(id=i, numero=n) for i, n in [(1, 3), (2, 1), (3, 8), (4, 2), (5, 5), (6, 7), (7, 4), (8, 6)]]

    mapa = calcular_mapa(mesas, [], [], _hora(12, 0))

    assert [m.numero for m in mapa] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert all(m.capacidade == 4 and m.localizacao == "Salão" and m.status for m in mapa)


def test_mapa_vazio():
    assert calcular_mapa([], [], [], _hora(12, 0)) == []


# --- Status da mesa calculado na leitura ---


def test_manutencao_prevalece_sobre_reserva():
    assert _uma(_mesa(manutencao=True), reservas=[_reserva()], agora=_hora(20, 30)).status == StatusMesa.MANUTENCAO


def test_comanda_aberta_ocupa_a_mesa():
    assert _uma(_mesa(), comandas=[_aberta()]).status == StatusMesa.OCUPADA


def test_comanda_em_pre_conta_aguarda_pagamento():
    assert _uma(_mesa(), comandas=[_aberta("PRE_CONTA")]).status == StatusMesa.AGUARDANDO_PAGAMENTO


def test_ocupada_prevalece_sobre_reserva_na_janela():
    mesa = _uma(_mesa(), comandas=[_aberta()], reservas=[_reserva()], agora=_hora(20, 15))

    assert mesa.status == StatusMesa.OCUPADA
    assert mesa.reserva_inicio is None


def test_mesa_livre_sem_nenhuma_condicao():
    assert _uma(_mesa()).status == StatusMesa.LIVRE


def test_comanda_de_outra_mesa_nao_influencia():
    assert _uma(_mesa(id=1), comandas=[_aberta(mesa_id=2)]).status == StatusMesa.LIVRE


# Comandas FECHADA/CANCELADA nunca chegam ao cálculo: o repositório só busca ABERTA e PRE_CONTA
# (coberto pelo teste de integração do endpoint).


# --- Janela de bloqueio por reserva ---


@pytest.mark.parametrize(
    ("agora", "esperado"),
    [
        (_hora(19, 59), StatusMesa.LIVRE),
        (_hora(20, 0), StatusMesa.RESERVADA),
        (_hora(20, 30), StatusMesa.RESERVADA),
        (_hora(21, 0), StatusMesa.RESERVADA),
        (_hora(21, 1), StatusMesa.LIVRE),
    ],
    ids=["antes-19h59", "inicio-20h00", "horario-20h30", "fim-21h00", "apos-21h01"],
)
def test_janela_de_reserva(agora, esperado):
    assert _uma(_mesa(), reservas=[_reserva()], agora=agora).status == esperado


def test_janela_ignora_reserva_fora_mesmo_que_o_repositorio_a_retorne():
    assert _uma(_mesa(), reservas=[_reserva(inicio=_hora(22, 0))], agora=_hora(20, 0)).status == StatusMesa.LIVRE


# Reservas CANCELADA/CONCLUIDA também são filtradas no repositório (teste de integração).


# --- Informações complementares do atendimento ---


def test_tempo_de_atendimento_em_minutos_inteiros():
    mesa = _uma(_mesa(), comandas=[_aberta(aberta_em=_hora(19, 41, 20))], agora=_hora(20, 0))

    assert mesa.minutos_atendimento == 18


def test_tempo_de_atendimento_tambem_em_aguardando_pagamento():
    mesa = _uma(_mesa(), comandas=[_aberta("PRE_CONTA", aberta_em=_hora(19, 8))], agora=_hora(20, 0))

    assert mesa.minutos_atendimento == 52


def test_horario_da_reserva_em_mesa_reservada():
    mesa = _uma(_mesa(), reservas=[_reserva()], agora=_hora(20, 10))

    assert mesa.reserva_inicio == RESERVA_20H30
    assert mesa.minutos_atendimento is None


def test_mesa_livre_sem_informacao_complementar():
    mesa = _uma(_mesa())

    assert mesa.minutos_atendimento is None
    assert mesa.reserva_inicio is None


def test_duas_reservas_na_janela_usa_a_mais_proxima_do_inicio():
    reservas = [_reserva(inicio=_hora(20, 40)), _reserva(inicio=_hora(20, 30))]

    assert _uma(_mesa(), reservas=reservas, agora=_hora(20, 20)).reserva_inicio == _hora(20, 30)


def test_relogio_do_servidor_em_utc_nao_altera_o_resultado():
    agora_utc = _hora(20, 0).astimezone(ZoneInfo("UTC"))

    assert _uma(_mesa(), reservas=[_reserva()], agora=agora_utc).status == StatusMesa.RESERVADA
    assert _uma(_mesa(), reservas=[_reserva()], agora=agora_utc - timedelta(minutes=1)).status == StatusMesa.LIVRE
