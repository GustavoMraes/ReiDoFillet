"""Cenários da spec `cozinha`: fila por estágio, pronto, entregue, cancelamento, auditoria e acesso."""

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.tempo import RelogioFixo, RelogioSistema
from app.main import create_app
from app.models import ItemComanda, LogAuditoria
from tests.conftest import SEGREDO_TESTE
from tests.integration.comandas_util import abrir, adicionar, enviar, preparar
from tests.integration.fabricas import cabecalho_de, cliente_api

AGORA = RelogioSistema().agora()


async def _item(session: AsyncSession, comanda_id: int, produto_id: int, status: str, enviado_ha_min: float | None) -> int:
    item = ItemComanda(
        comanda_id=comanda_id, produto_id=produto_id, quantidade=1, observacao="", preco_unitario=Decimal("10.00"),
        status=status, enviado_em=(AGORA - timedelta(minutes=enviado_ha_min)) if enviado_ha_min is not None else None,
    )
    session.add(item)
    await session.commit()
    return item.id


@pytest.fixture
async def cenario(session: AsyncSession):
    amb = await preparar(session)
    async with cliente_api(session, RelogioFixo(AGORA)) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[5])).json()["id"]
        yield amb, cliente, comanda_id


async def _painel(cliente, usuario):
    return await cliente.get("/cozinha", headers=cabecalho_de(usuario))


# --- Fila ---


async def test_itens_por_estagio_em_ordem_de_envio(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    p = amb.produtos
    recente = await _item(session, comanda_id, p["Arroz Branco"].id, "EM_PREPARO", 5)
    antigo = await _item(session, comanda_id, p["Batata Rústica"].id, "EM_PREPARO", 10)
    pronto = await _item(session, comanda_id, p["Farofa da Casa"].id, "PRONTO", 15)

    corpo = (await _painel(cliente, amb.gabriela)).json()

    assert [i["id"] for i in corpo["em_preparo"]] == [antigo, recente]
    assert [i["id"] for i in corpo["pronto"]] == [pronto]
    primeiro = corpo["em_preparo"][0]
    assert (primeiro["mesa_numero"], primeiro["quantidade"], primeiro["produto_nome"]) == (5, 1, "Batata Rústica")
    assert primeiro["enviado_em"].endswith("-03:00")


async def test_pendentes_entregues_e_cancelados_ficam_fora(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    for status, enviado in (("PENDENTE", None), ("ENTREGUE", 30), ("CANCELADO", 20)):
        await _item(session, comanda_id, amb.produtos["Arroz Branco"].id, status, enviado)

    corpo = (await _painel(cliente, amb.gabriela)).json()

    assert corpo == {"em_preparo": [], "pronto": []}


async def test_minutos_desde_o_envio(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await _item(session, comanda_id, amb.produtos["Arroz Branco"].id, "EM_PREPARO", 12.5)

    [item] = (await _painel(cliente, amb.gabriela)).json()["em_preparo"]

    assert item["minutos_desde_envio"] == 12


async def test_contabilidade_nao_consulta_nem_altera(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    item_id = await _item(session, comanda_id, amb.produtos["Arroz Branco"].id, "EM_PREPARO", 1)

    consulta = await _painel(cliente, amb.contabilidade)
    pronto = await cliente.post(f"/cozinha/itens/{item_id}/pronto", headers=cabecalho_de(amb.contabilidade))
    sem_sessao = await cliente.get("/cozinha")

    assert (consulta.status_code, pronto.status_code, sem_sessao.status_code) == (403, 403, 401)


# --- Mudanças de estágio ---


async def _avancar(cliente, usuario, item_id, etapa):
    return await cliente.post(f"/cozinha/itens/{item_id}/{etapa}", headers=cabecalho_de(usuario))


async def test_fluxo_completo_pronto_e_entregue(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Picanha 400g"])
    await enviar(cliente, amb.gabriela, comanda_id)
    item_id = (await _painel(cliente, amb.gabriela)).json()["em_preparo"][0]["id"]

    pronto = await _avancar(cliente, amb.gabriela, item_id, "pronto")
    assert pronto.status_code == 200
    assert ([i["id"] for i in pronto.json()["pronto"]], pronto.json()["em_preparo"]) == ([item_id], [])

    entregue = await _avancar(cliente, amb.admin, item_id, "entregue")
    assert entregue.json() == {"em_preparo": [], "pronto": []}

    item = (await session.execute(select(ItemComanda).where(ItemComanda.id == item_id))).scalar_one()
    assert (item.status, item.pronto_em is not None, item.entregue_em is not None) == ("ENTREGUE", True, True)
    comanda = (await cliente.get(f"/comandas/{comanda_id}", headers=cabecalho_de(amb.gabriela))).json()
    assert comanda["itens"][0]["status"] == "ENTREGUE"


async def test_mudancas_de_estagio_auditadas(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    item_id = await _item(session, comanda_id, amb.produtos["Arroz Branco"].id, "EM_PREPARO", 1)

    await _avancar(cliente, amb.gabriela, item_id, "pronto")
    await _avancar(cliente, amb.admin, item_id, "entregue")

    logs = list(
        (
            await session.execute(
                select(LogAuditoria)
                .where(LogAuditoria.entidade == "ItemComanda", LogAuditoria.entidade_id == str(item_id))
                .order_by(LogAuditoria.id)
            )
        ).scalars()
    )
    assert [(l.acao, l.usuario_id, l.dados_antes["status"], l.dados_depois["status"]) for l in logs] == [
        ("PRONTO", amb.gabriela.id, "EM_PREPARO", "PRONTO"),
        ("ENTREGAR", amb.admin.id, "PRONTO", "ENTREGUE"),
    ]


@pytest.mark.parametrize(
    ("status", "etapa", "mensagem"),
    [
        ("ENTREGUE", "pronto", "Somente itens em preparo podem ser marcados como prontos"),
        ("PENDENTE", "pronto", "Somente itens em preparo podem ser marcados como prontos"),
        ("EM_PREPARO", "entregue", "Somente itens prontos podem ser marcados como entregues"),
        ("CANCELADO", "entregue", "Somente itens prontos podem ser marcados como entregues"),
    ],
)
async def test_estagio_invalido(cenario, session: AsyncSession, status, etapa, mensagem):
    amb, cliente, comanda_id = cenario
    item_id = await _item(session, comanda_id, amb.produtos["Arroz Branco"].id, status, 1)

    resposta = await _avancar(cliente, amb.gabriela, item_id, etapa)

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": mensagem})
    item = (await session.execute(select(ItemComanda.status).where(ItemComanda.id == item_id))).scalar_one()
    assert item == status


async def test_item_cancelado_pelo_admin_sai_da_fila(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Picanha 400g"])
    await enviar(cliente, amb.gabriela, comanda_id)
    item_id = (await _painel(cliente, amb.gabriela)).json()["em_preparo"][0]["id"]

    await cliente.post(f"/comandas/{comanda_id}/itens/{item_id}/cancelar", headers=cabecalho_de(amb.admin))
    painel = (await _painel(cliente, amb.gabriela)).json()
    pronto = await _avancar(cliente, amb.gabriela, item_id, "pronto")

    assert painel == {"em_preparo": [], "pronto": []}
    assert pronto.status_code == 409


async def test_item_inexistente(cenario):
    amb, cliente, _ = cenario

    resposta = await _avancar(cliente, amb.gabriela, 999999, "pronto")

    assert (resposta.status_code, resposta.json()) == (404, {"detalhe": "Item não encontrado"})


def test_rotas_da_cozinha_no_swagger():
    rotas = create_app(Settings(_env_file=None, jwt_secret=SEGREDO_TESTE)).openapi()["paths"]

    assert set(rotas["/cozinha"]) == {"get"}
    assert set(rotas["/cozinha/itens/{item_id}/pronto"]) == {"post"}
    assert set(rotas["/cozinha/itens/{item_id}/entregue"]) == {"post"}
    assert set(rotas["/comandas/{comanda_id}/enviar"]) == {"post"}
