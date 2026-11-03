from decimal import Decimal

from app.services.financeiro import calcular, em_reais

D = Decimal


def _itens(*valores):
    return [(D(preco), quantidade, status) for preco, quantidade, status in valores]


def test_total_com_taxa_de_servico_arredonda_para_cima_no_meio_centavo():
    resumo = calcular("PRE_CONTA", _itens(("33.90", 1, "ENTREGUE")), D("10.00"), True, [])

    assert (resumo.subtotal, resumo.taxa_valor, resumo.total) == (D("33.90"), D("3.39"), D("37.29"))


def test_meio_centavo_arredonda_para_cima():
    # 10% de 0,05 = 0,005 -> 0,01 (ROUND_HALF_UP)
    resumo = calcular("PRE_CONTA", _itens(("0.05", 1, "ENTREGUE")), D("10.00"), True, [])

    assert resumo.taxa_valor == D("0.01")


def test_comanda_aberta_nao_cobra_taxa_mesmo_com_percentual_definido():
    resumo = calcular("ABERTA", _itens(("100.00", 1, "PENDENTE")), D("10.00"), True, [])

    assert (resumo.taxa_valor, resumo.total) == (D("0.00"), D("100.00"))


def test_taxa_desligada():
    resumo = calcular("PRE_CONTA", _itens(("100.00", 1, "ENTREGUE")), D("10.00"), False, [])

    assert (resumo.taxa_aplicada, resumo.taxa_valor, resumo.total) == (False, D("0.00"), D("100.00"))


def test_cancelados_fora_do_subtotal_e_pagamentos_no_restante():
    itens = _itens(("7.00", 2, "ENTREGUE"), ("89.90", 1, "CANCELADO"), ("86.00", 1, "PRONTO"))

    resumo = calcular("PRE_CONTA", itens, D("10.00"), True, [D("50.00"), D("10.00")])

    assert (resumo.subtotal, resumo.taxa_valor, resumo.total) == (D("100.00"), D("10.00"), D("110.00"))
    assert (resumo.pago, resumo.restante) == (D("60.00"), D("50.00"))


def test_restante_nunca_negativo():
    resumo = calcular("FECHADA", _itens(("10.00", 1, "ENTREGUE")), None, True, [D("10.00")])

    assert resumo.restante == D("0.00")


def test_formato_em_reais():
    assert em_reais(D("1234.5")) == "R$ 1.234,50"
    assert em_reais(D("60")) == "R$ 60,00"
