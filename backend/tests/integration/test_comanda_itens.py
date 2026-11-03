"""Cenários da spec `comandas`: registro, soma de idênticos, alteração e cancelamento de itens."""

from decimal import Decimal

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comanda, ItemComanda, LogAuditoria, Produto
from tests.integration.comandas_util import abrir, adicionar, preparar
from tests.integration.fabricas import cabecalho_de, cliente_api


@pytest.fixture
async def cenario(session: AsyncSession):
    """Ambiente do seed com a comanda da mesa 2 aberta pela gabriela."""
    amb = await preparar(session)
    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[2])).json()["id"]
        yield amb, cliente, comanda_id


async def _logs(session: AsyncSession, entidade: str = "ItemComanda") -> list[LogAuditoria]:
    return list((await session.execute(select(LogAuditoria).where(LogAuditoria.entidade == entidade).order_by(LogAuditoria.id))).scalars())


# --- Registro de item ---


async def test_item_com_observacao_e_preco_atual(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    filet = amb.produtos["Filet Mignon 300g"]

    resposta = await adicionar(cliente, amb.gabriela, comanda_id, filet, observacao="  ao ponto ")

    assert resposta.status_code == 200
    [item] = resposta.json()["itens"]
    assert (item["produto_nome"], item["quantidade"], item["observacao"], item["preco_unitario"], item["status"]) == (
        "Filet Mignon 300g", 1, "ao ponto", "89.90", "PENDENTE",
    )
    assert resposta.json()["total"] == "89.90"
    [log] = await _logs(session)
    assert (log.acao, log.usuario_id, log.dados_depois["observacao"]) == ("CRIAR", amb.gabriela.id, "ao ponto")


async def test_preco_congelado(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    refri = amb.produtos["Refrigerante Lata"]
    await adicionar(cliente, amb.gabriela, comanda_id, refri)

    await session.execute(update(Produto).where(Produto.id == refri.id).values(preco=Decimal("9.00")))
    await session.commit()
    resposta = await cliente.get(f"/comandas/{comanda_id}", headers=cabecalho_de(amb.gabriela))

    assert resposta.json()["itens"][0]["preco_unitario"] == "7.00"


@pytest.mark.parametrize("quantidade", [0, 100])
async def test_quantidade_fora_da_faixa(cenario, quantidade):
    amb, cliente, comanda_id = cenario

    resposta = await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Refrigerante Lata"], quantidade=quantidade)

    assert (resposta.status_code, resposta.json()) == (422, {"detalhe": "A quantidade deve estar entre 1 e 99"})


async def test_observacao_longa(cenario):
    amb, cliente, comanda_id = cenario

    resposta = await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Refrigerante Lata"], observacao="x" * 201)

    assert (resposta.status_code, resposta.json()) == (422, {"detalhe": "A observação deve ter no máximo 200 caracteres"})


@pytest.mark.parametrize("status", ["FECHADA", "CANCELADA"])
async def test_comanda_que_nao_esta_aberta(cenario, session: AsyncSession, status):
    amb, cliente, comanda_id = cenario
    await session.execute(update(Comanda).where(Comanda.id == comanda_id).values(status=status))
    await session.commit()

    resposta = await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Refrigerante Lata"])

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "A comanda não está aberta para novos itens"})


@pytest.mark.parametrize("campo", ["disponivel", "ativo"], ids=["esgotado", "inativo"])
async def test_item_indisponivel(cenario, session: AsyncSession, campo):
    amb, cliente, comanda_id = cenario
    pudim = amb.produtos["Pudim de Leite"]
    await session.execute(update(Produto).where(Produto.id == pudim.id).values({campo: False}))
    await session.commit()

    resposta = await adicionar(cliente, amb.gabriela, comanda_id, pudim)

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "Item indisponível"})
    assert (await session.execute(select(ItemComanda))).first() is None


# --- Itens idênticos ---


async def test_mesmo_produto_e_observacao_soma(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    refri = amb.produtos["Refrigerante Lata"]

    await adicionar(cliente, amb.gabriela, comanda_id, refri)
    resposta = await adicionar(cliente, amb.gabriela, comanda_id, refri, quantidade=2)

    assert [(i["produto_nome"], i["quantidade"]) for i in resposta.json()["itens"]] == [("Refrigerante Lata", 3)]
    assert resposta.json()["total"] == "21.00"
    assert [log.acao for log in await _logs(session)] == ["CRIAR", "ALTERAR"]


async def test_observacao_igual_ignorando_maiusculas_e_espacos(cenario):
    amb, cliente, comanda_id = cenario
    filet = amb.produtos["Filet Mignon 300g"]

    await adicionar(cliente, amb.gabriela, comanda_id, filet, observacao="Sem sal")
    resposta = await adicionar(cliente, amb.gabriela, comanda_id, filet, observacao="  sem SAL ")

    assert [i["quantidade"] for i in resposta.json()["itens"]] == [2]


async def test_observacao_diferente_cria_outro_item(cenario):
    amb, cliente, comanda_id = cenario
    filet = amb.produtos["Filet Mignon 300g"]

    await adicionar(cliente, amb.gabriela, comanda_id, filet)
    resposta = await adicionar(cliente, amb.gabriela, comanda_id, filet, observacao="sem sal")

    assert [(i["observacao"], i["quantidade"]) for i in resposta.json()["itens"]] == [("", 1), ("sem sal", 1)]


async def test_item_igual_ja_enviado_cria_novo_pendente(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    batata = amb.produtos["Batata Rústica"]
    await adicionar(cliente, amb.gabriela, comanda_id, batata)
    await session.execute(update(ItemComanda).values(status="EM_PREPARO"))
    await session.commit()

    resposta = await adicionar(cliente, amb.gabriela, comanda_id, batata)

    assert [(i["status"], i["quantidade"]) for i in resposta.json()["itens"]] == [("EM_PREPARO", 1), ("PENDENTE", 1)]


async def test_preco_diferente_nao_soma(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    refri = amb.produtos["Refrigerante Lata"]
    await adicionar(cliente, amb.gabriela, comanda_id, refri)
    await session.execute(update(Produto).where(Produto.id == refri.id).values(preco=Decimal("8.00")))
    await session.commit()

    resposta = await adicionar(cliente, amb.gabriela, comanda_id, refri)

    assert [(i["preco_unitario"], i["quantidade"]) for i in resposta.json()["itens"]] == [("7.00", 1), ("8.00", 1)]


async def test_soma_acima_do_maximo(cenario):
    amb, cliente, comanda_id = cenario
    refri = amb.produtos["Refrigerante Lata"]
    await adicionar(cliente, amb.gabriela, comanda_id, refri, quantidade=98)

    resposta = await adicionar(cliente, amb.gabriela, comanda_id, refri, quantidade=2)
    comanda = await cliente.get(f"/comandas/{comanda_id}", headers=cabecalho_de(amb.gabriela))

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "A quantidade máxima por item é 99"})
    assert comanda.json()["itens"][0]["quantidade"] == 98


# --- Alteração ---


async def test_alterar_quantidade_recalcula_total(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    item_id = (await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Refrigerante Lata"])).json()["itens"][0]["id"]

    resposta = await cliente.patch(
        f"/comandas/{comanda_id}/itens/{item_id}", json={"quantidade": 2, "observacao": "gelado"}, headers=cabecalho_de(amb.gabriela)
    )

    [item] = resposta.json()["itens"]
    assert (item["quantidade"], item["observacao"], item["subtotal"], resposta.json()["total"]) == (2, "gelado", "14.00", "14.00")
    ultimo = (await _logs(session))[-1]
    assert (ultimo.acao, ultimo.dados_antes["quantidade"], ultimo.dados_depois["quantidade"]) == ("ALTERAR", 1, 2)


async def test_alterar_item_ja_enviado(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    item_id = (await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Batata Rústica"])).json()["itens"][0]["id"]
    await session.execute(update(ItemComanda).values(status="EM_PREPARO"))
    await session.commit()

    resposta = await cliente.patch(f"/comandas/{comanda_id}/itens/{item_id}", json={"quantidade": 2}, headers=cabecalho_de(amb.gabriela))

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "Apenas itens pendentes podem ser alterados"})


# --- Cancelamento ---


async def _cancelar(cliente, usuario, comanda_id, item_id):
    return await cliente.post(f"/comandas/{comanda_id}/itens/{item_id}/cancelar", headers=cabecalho_de(usuario))


async def test_cancelar_item_pendente(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Refrigerante Lata"], quantidade=2)
    item_id = (await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Filet Mignon 300g"])).json()["itens"][1]["id"]

    resposta = await _cancelar(cliente, amb.gabriela, comanda_id, item_id)

    assert resposta.status_code == 200
    assert [i["status"] for i in resposta.json()["itens"]] == ["PENDENTE", "CANCELADO"]
    assert resposta.json()["total"] == "14.00"
    item = (await session.execute(select(ItemComanda).where(ItemComanda.id == item_id))).scalar_one()
    assert (item.cancelado_por_id, item.cancelado_em is not None) == (amb.gabriela.id, True)
    ultimo = (await _logs(session))[-1]
    assert (ultimo.acao, ultimo.usuario_id, ultimo.dados_antes["status"], ultimo.dados_depois["status"]) == (
        "CANCELAR", amb.gabriela.id, "PENDENTE", "CANCELADO",
    )


async def test_funcionario_nao_cancela_item_enviado(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    item_id = (await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Batata Rústica"])).json()["itens"][0]["id"]
    await session.execute(update(ItemComanda).values(status="EM_PREPARO"))
    await session.commit()

    resposta = await _cancelar(cliente, amb.gabriela, comanda_id, item_id)

    assert (resposta.status_code, resposta.json()) == (
        403, {"detalhe": "Itens enviados à cozinha só podem ser cancelados por um administrador"},
    )


@pytest.mark.parametrize("status_enviado", ["EM_PREPARO", "PRONTO", "ENTREGUE"])
async def test_administrador_cancela_item_enviado(cenario, session: AsyncSession, status_enviado):
    amb, cliente, comanda_id = cenario
    item_id = (await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Batata Rústica"])).json()["itens"][0]["id"]
    await session.execute(update(ItemComanda).values(status=status_enviado))
    await session.commit()

    resposta = await _cancelar(cliente, amb.admin, comanda_id, item_id)

    assert resposta.status_code == 200
    assert (resposta.json()["itens"][0]["status"], resposta.json()["total"]) == ("CANCELADO", "0.00")


async def test_item_ja_cancelado(cenario):
    amb, cliente, comanda_id = cenario
    item_id = (await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Batata Rústica"])).json()["itens"][0]["id"]
    await _cancelar(cliente, amb.gabriela, comanda_id, item_id)

    resposta = await _cancelar(cliente, amb.admin, comanda_id, item_id)

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "Item já cancelado"})
