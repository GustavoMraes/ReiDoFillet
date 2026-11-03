"""Contrato HTTP das rotas de itens (404, 422, 403) e concorrência na mesma comanda."""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.models import ItemComanda
from tests.conftest import SEGREDO_TESTE
from tests.integration.comandas_util import abrir, adicionar, preparar
from tests.integration.fabricas import cabecalho_de, cliente_api


async def test_erros_de_recurso_e_de_dados(session: AsyncSession):
    amb = await preparar(session)
    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[1])).json()["id"]
        h = cabecalho_de(amb.gabriela)

        comanda_inexistente = await cliente.post("/comandas/999999/itens", json={"produto_id": 1}, headers=h)
        produto_inexistente = await cliente.post(f"/comandas/{comanda_id}/itens", json={"produto_id": 999999}, headers=h)
        item_inexistente = await cliente.post(f"/comandas/{comanda_id}/itens/999999/cancelar", headers=h)
        corpo_invalido = await cliente.post(f"/comandas/{comanda_id}/itens", json={"quantidade": 1}, headers=h)
        alteracao_vazia = await cliente.patch(f"/comandas/{comanda_id}/itens/1", json={}, headers=h)

    assert (comanda_inexistente.status_code, comanda_inexistente.json()) == (404, {"detalhe": "Comanda não encontrada"})
    assert (produto_inexistente.status_code, produto_inexistente.json()) == (404, {"detalhe": "Produto não encontrado"})
    assert (item_inexistente.status_code, item_inexistente.json()) == (404, {"detalhe": "Item não encontrado"})
    assert (corpo_invalido.status_code, corpo_invalido.json()["detalhe"]) == (422, "Dados inválidos")
    assert (alteracao_vazia.status_code, alteracao_vazia.json()["detalhe"]) == (422, "Dados inválidos")


async def test_item_de_outra_comanda_nao_e_encontrado(session: AsyncSession):
    amb = await preparar(session)
    async with cliente_api(session) as cliente:
        comanda_a = (await abrir(cliente, amb.gabriela, amb.mesas[1])).json()["id"]
        comanda_b = (await abrir(cliente, amb.gabriela, amb.mesas[2])).json()["id"]
        item_a = (await adicionar(cliente, amb.gabriela, comanda_a, amb.produtos["Arroz Branco"])).json()["itens"][0]["id"]

        resposta = await cliente.post(f"/comandas/{comanda_b}/itens/{item_a}/cancelar", headers=cabecalho_de(amb.gabriela))

    assert resposta.status_code == 404


async def test_contabilidade_nao_manipula_itens(session: AsyncSession):
    amb = await preparar(session)
    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[1])).json()["id"]

        resposta = await adicionar(cliente, amb.contabilidade, comanda_id, amb.produtos["Arroz Branco"])

    assert resposta.status_code == 403


def test_rotas_documentadas_no_swagger():
    rotas = create_app(Settings(_env_file=None, jwt_secret=SEGREDO_TESTE)).openapi()["paths"]

    assert set(rotas["/mesas/{mesa_id}/comanda"]) == {"post"}
    assert set(rotas["/comandas/{comanda_id}"]) == {"get"}
    assert set(rotas["/comandas/{comanda_id}/itens"]) == {"post"}
    assert set(rotas["/comandas/{comanda_id}/itens/{item_id}"]) == {"patch"}
    assert set(rotas["/comandas/{comanda_id}/itens/{item_id}/cancelar"]) == {"post"}
    assert set(rotas["/cardapio"]) == {"get"}
    assert rotas["/comandas/{comanda_id}/itens"]["post"]["security"] == [{"HTTPBearer": []}]


async def test_adicoes_simultaneas_do_mesmo_produto_somam_em_um_item(session: AsyncSession, engine: AsyncEngine):
    amb = await preparar(session)
    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[1])).json()["id"]
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    refri = amb.produtos["Refrigerante Lata"]

    async def adicionar_em_sessao_propria(usuario):
        async with fabrica() as s, cliente_api(s) as cliente:
            resposta = await adicionar(cliente, usuario, comanda_id, refri)
            assert resposta.status_code == 200

    await asyncio.gather(*(adicionar_em_sessao_propria(u) for u in (amb.gabriela, amb.admin, amb.gabriela, amb.admin)))

    itens = list((await session.execute(select(ItemComanda).where(ItemComanda.comanda_id == comanda_id))).scalars())
    assert [(i.produto_id, i.quantidade) for i in itens] == [(refri.id, 4)]
