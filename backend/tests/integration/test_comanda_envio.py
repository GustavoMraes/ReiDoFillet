"""Cenários da delta `comandas` deste change: envio à cozinha, cupom e auditoria do envio."""

import asyncio

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models import Comanda, ItemComanda, LogAuditoria
from tests.integration.comandas_util import abrir, adicionar, enviar, preparar
from tests.integration.fabricas import cabecalho_de, cliente_api


@pytest.fixture
async def cenario(session: AsyncSession):
    amb = await preparar(session)
    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[3])).json()["id"]
        yield amb, cliente, comanda_id


async def _itens(session: AsyncSession, comanda_id: int) -> list[ItemComanda]:
    resultado = await session.execute(select(ItemComanda).where(ItemComanda.comanda_id == comanda_id).order_by(ItemComanda.id))
    return list(resultado.scalars())


async def test_envia_so_os_pendentes_com_o_mesmo_horario(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Batata Rústica"])
    await enviar(cliente, amb.gabriela, comanda_id)
    primeiro_envio = (await _itens(session, comanda_id))[0].enviado_em
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Filet Mignon 300g"], observacao="sem sal")
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Refrigerante Lata"], quantidade=2)

    resposta = await enviar(cliente, amb.gabriela, comanda_id)

    assert resposta.status_code == 200
    batata, filet, refri = await _itens(session, comanda_id)
    assert batata.enviado_em == primeiro_envio  # já estava em preparo: não foi alterado
    assert (filet.status, refri.status) == ("EM_PREPARO", "EM_PREPARO")
    assert filet.enviado_em == refri.enviado_em != primeiro_envio
    assert [i["status"] for i in resposta.json()["comanda"]["itens"]] == ["EM_PREPARO"] * 3


async def test_cupom_traz_so_o_lote_enviado(cenario):
    amb, cliente, comanda_id = cenario
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Batata Rústica"])
    await enviar(cliente, amb.gabriela, comanda_id)
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Filet Mignon 300g"], observacao="sem sal")
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Refrigerante Lata"], quantidade=2)

    cupom = (await enviar(cliente, amb.admin, comanda_id)).json()["cupom"]

    assert (cupom["mesa_numero"], cupom["garcom"]) == (3, "Administrador")
    assert cupom["enviado_em"].endswith("-03:00")
    assert cupom["itens"] == [
        {"quantidade": 1, "produto_nome": "Filet Mignon 300g", "observacao": "sem sal"},
        {"quantidade": 2, "produto_nome": "Refrigerante Lata", "observacao": ""},
    ]


async def test_nada_a_enviar(cenario):
    amb, cliente, comanda_id = cenario

    resposta = await enviar(cliente, amb.gabriela, comanda_id)

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "Não há itens pendentes para enviar"})


async def test_cancelados_nao_sao_enviados(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    item_id = (await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Arroz Branco"])).json()["itens"][0]["id"]
    await cliente.post(f"/comandas/{comanda_id}/itens/{item_id}/cancelar", headers=cabecalho_de(amb.gabriela))

    resposta = await enviar(cliente, amb.gabriela, comanda_id)

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "Não há itens pendentes para enviar"})
    assert (await _itens(session, comanda_id))[0].status == "CANCELADO"


async def test_comanda_que_nao_esta_aberta(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Arroz Branco"])
    await session.execute(update(Comanda).where(Comanda.id == comanda_id).values(status="PRE_CONTA"))
    await session.commit()

    resposta = await enviar(cliente, amb.gabriela, comanda_id)

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "A comanda não está aberta para envio"})
    assert (await _itens(session, comanda_id))[0].status == "PENDENTE"


async def test_envio_auditado_por_item(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Arroz Branco"])
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Farofa da Casa"])

    await enviar(cliente, amb.gabriela, comanda_id)

    logs = list((await session.execute(select(LogAuditoria).where(LogAuditoria.acao == "ENVIAR"))).scalars())
    assert len(logs) == 2
    assert all(
        (log.usuario_id, log.dados_antes["status"], log.dados_depois["status"]) == (amb.gabriela.id, "PENDENTE", "EM_PREPARO")
        for log in logs
    )


async def test_erros_de_acesso_e_recurso(cenario):
    amb, cliente, comanda_id = cenario

    inexistente = await enviar(cliente, amb.gabriela, 999999)
    contabilidade = await enviar(cliente, amb.contabilidade, comanda_id)
    sem_sessao = await cliente.post(f"/comandas/{comanda_id}/enviar")

    assert (inexistente.status_code, contabilidade.status_code, sem_sessao.status_code) == (404, 403, 401)


async def test_envios_simultaneos_enviam_cada_item_uma_vez(session: AsyncSession, engine: AsyncEngine):
    amb = await preparar(session)
    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[1])).json()["id"]
        for nome in ("Arroz Branco", "Farofa da Casa", "Batata Rústica"):
            await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos[nome])
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    async def enviar_em_sessao_propria(usuario):
        async with fabrica() as s, cliente_api(s) as cliente:
            return (await enviar(cliente, usuario, comanda_id)).status_code

    codigos = await asyncio.gather(*(enviar_em_sessao_propria(u) for u in (amb.gabriela, amb.admin, amb.gabriela)))

    assert sorted(codigos) == [200, 409, 409]
    envios = list((await session.execute(select(LogAuditoria).where(LogAuditoria.acao == "ENVIAR"))).scalars())
    assert len(envios) == 3  # um registro por item, cada item enviado uma única vez
    assert len({i.enviado_em for i in await _itens(session, comanda_id)}) == 1
