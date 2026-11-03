"""Delta de `comandas`: pré-conta, retorno a ABERTA, cancelamento de comanda e resumo financeiro."""

from decimal import Decimal

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comanda, ItemComanda, LogAuditoria, Parametro, Produto
from tests.integration.comandas_util import abrir, adicionar, enviar, pagar, pre_conta, preparar, taxa
from tests.integration.fabricas import cabecalho_de, cliente_api


@pytest.fixture
async def cenario(session: AsyncSession):
    """Comanda da mesa 2 com "Arroz Branco" a R$ 100,00 (subtotal redondo para os cálculos)."""
    amb = await preparar(session)
    await session.execute(update(Produto).where(Produto.nome == "Arroz Branco").values(preco=Decimal("100.00")))
    await session.commit()
    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[2])).json()["id"]
        yield amb, cliente, comanda_id


async def _com_item_entregue(session, cliente, amb, comanda_id):
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Arroz Branco"])
    await session.execute(update(ItemComanda).where(ItemComanda.comanda_id == comanda_id).values(status="ENTREGUE"))
    await session.commit()


async def _status_mesa(cliente, usuario, numero):
    mapa = (await cliente.get("/mesas", headers=cabecalho_de(usuario))).json()
    return next(m["status"] for m in mapa if m["numero"] == numero)


# --- Geração da pré-conta ---


async def test_pre_conta_com_itens_entregues(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await _com_item_entregue(session, cliente, amb, comanda_id)

    resposta = await pre_conta(cliente, amb.gabriela, comanda_id)

    corpo = resposta.json()
    assert resposta.status_code == 200
    assert (corpo["comanda"]["status"], corpo["aviso"]) == ("PRE_CONTA", None)
    assert corpo["comanda"]["pre_conta_em"].endswith("-03:00")
    assert await _status_mesa(cliente, amb.gabriela, 2) == "AGUARDANDO_PAGAMENTO"
    log = (await session.execute(select(LogAuditoria).where(LogAuditoria.acao == "PRE_CONTA"))).scalar_one()
    assert (log.usuario_id, log.dados_antes["status"], log.dados_depois["status"]) == (amb.gabriela.id, "ABERTA", "PRE_CONTA")


async def test_taxa_padrao_na_primeira_pre_conta(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await _com_item_entregue(session, cliente, amb, comanda_id)

    comanda = (await pre_conta(cliente, amb.gabriela, comanda_id)).json()["comanda"]

    assert comanda["taxa_servico"] == {"aplicada": True, "percentual": "10.00", "valor": "10.00"}
    assert (comanda["subtotal"], comanda["total"], comanda["pago"], comanda["restante"]) == ("100.00", "110.00", "0.00", "110.00")


async def test_taxa_padrao_vem_do_parametro(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await session.execute(update(Parametro).values(valor="12.50"))
    await session.commit()
    await _com_item_entregue(session, cliente, amb, comanda_id)

    comanda = (await pre_conta(cliente, amb.gabriela, comanda_id)).json()["comanda"]

    assert (comanda["taxa_servico"]["percentual"], comanda["total"]) == ("12.50", "112.50")


async def test_itens_ainda_em_preparo_geram_aviso(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Arroz Branco"])
    await enviar(cliente, amb.gabriela, comanda_id)

    corpo = (await pre_conta(cliente, amb.gabriela, comanda_id)).json()

    assert corpo["comanda"]["status"] == "PRE_CONTA"
    assert "1 item(ns) ainda não entregue(s)" in corpo["aviso"]


@pytest.mark.parametrize("so_cancelados", [False, True], ids=["sem-itens", "so-cancelados"])
async def test_comanda_sem_itens_nao_gera_pre_conta(cenario, so_cancelados):
    amb, cliente, comanda_id = cenario
    if so_cancelados:
        item_id = (await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Arroz Branco"])).json()["itens"][0]["id"]
        await cliente.post(f"/comandas/{comanda_id}/itens/{item_id}/cancelar", headers=cabecalho_de(amb.gabriela))

    resposta = await pre_conta(cliente, amb.gabriela, comanda_id)

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "A comanda não tem itens para a pré-conta"})


async def test_pre_conta_de_comanda_que_nao_esta_aberta(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await _com_item_entregue(session, cliente, amb, comanda_id)
    await pre_conta(cliente, amb.gabriela, comanda_id)

    resposta = await pre_conta(cliente, amb.gabriela, comanda_id)

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "A pré-conta só pode ser gerada para uma comanda aberta"})


# --- Retorno a ABERTA ---


async def test_item_novo_apos_pre_conta_volta_para_aberta(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await _com_item_entregue(session, cliente, amb, comanda_id)
    await pre_conta(cliente, amb.gabriela, comanda_id)

    comanda = (await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Refrigerante Lata"])).json()

    assert (comanda["status"], comanda["pre_conta_em"]) == ("ABERTA", None)
    assert comanda["itens"][-1]["status"] == "PENDENTE"
    # Taxa não se aplica a comanda aberta: o total volta a ser o subtotal.
    assert (comanda["subtotal"], comanda["taxa_servico"]["valor"], comanda["total"]) == ("107.00", "0.00", "107.00")
    # Envio à cozinha continua exigindo ABERTA, e agora funciona.
    assert (await enviar(cliente, amb.gabriela, comanda_id)).status_code == 200


async def test_cancelamento_apos_pre_conta_mantem_pagamentos(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await _com_item_entregue(session, cliente, amb, comanda_id)
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Refrigerante Lata"])
    await pre_conta(cliente, amb.gabriela, comanda_id)
    await pagar(cliente, amb.gabriela, comanda_id, "PIX", "50.00")
    refri_id = (await cliente.get(f"/comandas/{comanda_id}", headers=cabecalho_de(amb.gabriela))).json()["itens"][1]["id"]

    resposta = await cliente.post(f"/comandas/{comanda_id}/itens/{refri_id}/cancelar", headers=cabecalho_de(amb.gabriela))

    comanda = resposta.json()
    assert (comanda["status"], comanda["itens"][1]["status"]) == ("ABERTA", "CANCELADO")
    assert (comanda["pago"], [p["valor"] for p in comanda["pagamentos"]]) == ("50.00", ["50.00"])


async def test_alteracao_de_item_na_pre_conta_volta_para_aberta(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    item_id = (await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Refrigerante Lata"])).json()["itens"][0]["id"]
    await pre_conta(cliente, amb.gabriela, comanda_id)

    resposta = await cliente.patch(f"/comandas/{comanda_id}/itens/{item_id}", json={"quantidade": 2}, headers=cabecalho_de(amb.gabriela))

    assert (resposta.json()["status"], resposta.json()["itens"][0]["quantidade"]) == ("ABERTA", 2)


async def test_nova_pre_conta_mantem_a_escolha_da_taxa(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await _com_item_entregue(session, cliente, amb, comanda_id)
    await pre_conta(cliente, amb.gabriela, comanda_id)
    await taxa(cliente, amb.gabriela, comanda_id, aplicada=False)
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Refrigerante Lata"])

    comanda = (await pre_conta(cliente, amb.gabriela, comanda_id)).json()["comanda"]

    assert comanda["taxa_servico"]["aplicada"] is False
    assert comanda["total"] == comanda["subtotal"] == "107.00"


# --- Cancelamento de comanda ---


async def test_mesa_aberta_por_engano(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario

    resposta = await cliente.post(f"/comandas/{comanda_id}/cancelar", headers=cabecalho_de(amb.gabriela))

    assert (resposta.status_code, resposta.json()["status"]) == (200, "CANCELADA")
    assert await _status_mesa(cliente, amb.gabriela, 2) == "LIVRE"
    log = (await session.execute(select(LogAuditoria).where(LogAuditoria.acao == "CANCELAR", LogAuditoria.entidade == "Comanda"))).scalar_one()
    assert (log.usuario_id, log.dados_depois["status"]) == (amb.gabriela.id, "CANCELADA")


async def test_comanda_so_com_itens_cancelados_pode_ser_cancelada(cenario):
    amb, cliente, comanda_id = cenario
    item_id = (await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Arroz Branco"])).json()["itens"][0]["id"]
    await cliente.post(f"/comandas/{comanda_id}/itens/{item_id}/cancelar", headers=cabecalho_de(amb.gabriela))

    resposta = await cliente.post(f"/comandas/{comanda_id}/cancelar", headers=cabecalho_de(amb.gabriela))

    assert resposta.json()["status"] == "CANCELADA"


async def test_comanda_com_itens_ativos_nao_e_cancelada(cenario):
    amb, cliente, comanda_id = cenario
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Arroz Branco"])

    resposta = await cliente.post(f"/comandas/{comanda_id}/cancelar", headers=cabecalho_de(amb.gabriela))

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "Cancele os itens antes de cancelar a comanda"})


async def test_comanda_com_pagamento_nao_e_cancelada(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    item_id = (await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Arroz Branco"])).json()["itens"][0]["id"]
    await pre_conta(cliente, amb.gabriela, comanda_id)
    await pagar(cliente, amb.gabriela, comanda_id, "PIX", "10.00")
    await cliente.post(f"/comandas/{comanda_id}/itens/{item_id}/cancelar", headers=cabecalho_de(amb.gabriela))

    resposta = await cliente.post(f"/comandas/{comanda_id}/cancelar", headers=cabecalho_de(amb.gabriela))

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "Remova os pagamentos antes de cancelar a comanda"})


# --- Resumo financeiro ---


async def test_resumo_financeiro_com_pagamento_parcial(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await _com_item_entregue(session, cliente, amb, comanda_id)
    await pre_conta(cliente, amb.gabriela, comanda_id)
    await pagar(cliente, amb.gabriela, comanda_id, "PIX", "50.00")

    comanda = (await cliente.get(f"/comandas/{comanda_id}", headers=cabecalho_de(amb.gabriela))).json()

    assert (comanda["subtotal"], comanda["taxa_servico"]["valor"], comanda["total"]) == ("100.00", "10.00", "110.00")
    assert (comanda["pago"], comanda["restante"]) == ("50.00", "60.00")
    [pagamento] = comanda["pagamentos"]
    assert (pagamento["forma"], pagamento["valor"], pagamento["registrado_por"]) == ("PIX", "50.00", "Gabriela Garcia")
    assert pagamento["registrado_em"].endswith("-03:00")
    assert (await session.execute(select(Comanda.status).where(Comanda.id == comanda_id))).scalar_one() == "PRE_CONTA"
