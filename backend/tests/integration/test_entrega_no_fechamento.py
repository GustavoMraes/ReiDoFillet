"""Fechamento da comanda conclui a entrega dos itens (spec `pagamentos`, "Fechamento ao quitar o total")."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import RelogioFixo
from app.models import Comanda, ItemComanda, LogAuditoria, Produto
from tests.integration.comandas_util import abrir, adicionar, enviar, pagar, pre_conta, preparar, taxa
from tests.integration.fabricas import cabecalho_de, cliente_api

FECHAMENTO = datetime(2026, 11, 3, 23, 0, tzinfo=UTC)


async def _itens(session: AsyncSession, comanda_id: int) -> dict[str, ItemComanda]:
    consulta = (
        select(ItemComanda, Produto.nome)
        .join(Produto, Produto.id == ItemComanda.produto_id)
        .where(ItemComanda.comanda_id == comanda_id)
        .execution_options(populate_existing=True)
    )
    return {nome: item for item, nome in await session.execute(consulta)}


async def test_itens_ainda_na_cozinha_no_fechamento(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session, RelogioFixo(FECHAMENTO)) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[2])).json()["id"]
        await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Arroz Branco"])
        await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Filet Mignon 300g"])
        await enviar(cliente, amb.gabriela, comanda_id)
        itens = await _itens(session, comanda_id)
        await cliente.post(f"/cozinha/itens/{itens['Filet Mignon 300g'].id}/pronto", headers=cabecalho_de(amb.gabriela))
        comanda = (await pre_conta(cliente, amb.gabriela, comanda_id)).json()["comanda"]
        pagamento = await pagar(cliente, amb.admin, comanda_id, "PIX", comanda["total"])
        painel = (await cliente.get("/cozinha", headers=cabecalho_de(amb.gabriela))).json()

    assert pagamento.json()["status"] == "FECHADA"
    assert [i["status"] for i in pagamento.json()["itens"]] == ["ENTREGUE", "ENTREGUE"]
    itens = await _itens(session, comanda_id)
    assert {(i.status, i.entregue_em) for i in itens.values()} == {("ENTREGUE", FECHAMENTO)}
    assert itens["Arroz Branco"].pronto_em is None  # não passou pelo "pronto": o histórico mostra o que aconteceu
    assert painel == {"em_preparo": [], "pronto": []}

    logs = (
        await session.execute(select(LogAuditoria).where(LogAuditoria.acao == "ENTREGAR").order_by(LogAuditoria.id))
    ).scalars().all()
    assert {log.entidade_id for log in logs} == {str(i.id) for i in itens.values()}
    assert {log.usuario_id for log in logs} == {amb.admin.id}
    assert {log.dados_antes["status"] for log in logs} == {"EM_PREPARO", "PRONTO"}


async def test_item_cancelado_e_item_ja_entregue_no_fechamento(session: AsyncSession):
    amb = await preparar(session)
    entregue_antes = datetime(2026, 11, 3, 22, 30, tzinfo=UTC)

    async with cliente_api(session, RelogioFixo(FECHAMENTO)) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[2])).json()["id"]
        await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Arroz Branco"])
        await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Filet Mignon 300g"])
        itens = await _itens(session, comanda_id)
        await cliente.post(
            f"/comandas/{comanda_id}/itens/{itens['Arroz Branco'].id}/cancelar", headers=cabecalho_de(amb.gabriela)
        )
        await session.execute(
            update(ItemComanda)
            .where(ItemComanda.id == itens["Filet Mignon 300g"].id)
            .values(status="ENTREGUE", entregue_em=entregue_antes)
        )
        await session.commit()
        comanda = (await pre_conta(cliente, amb.gabriela, comanda_id)).json()["comanda"]
        await pagar(cliente, amb.gabriela, comanda_id, "DINHEIRO", comanda["total"])

    itens = await _itens(session, comanda_id)
    assert (itens["Arroz Branco"].status, itens["Arroz Branco"].entregue_em) == ("CANCELADO", None)
    assert (itens["Filet Mignon 300g"].status, itens["Filet Mignon 300g"].entregue_em) == ("ENTREGUE", entregue_antes)
    assert (await session.execute(select(LogAuditoria).where(LogAuditoria.acao == "ENTREGAR"))).first() is None


async def test_fechamento_pelo_ajuste_da_taxa(session: AsyncSession):
    amb = await preparar(session)
    await session.execute(update(Produto).where(Produto.nome == "Arroz Branco").values(preco=Decimal("100.00")))
    await session.commit()

    async with cliente_api(session, RelogioFixo(FECHAMENTO)) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[2])).json()["id"]
        await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Arroz Branco"])
        await enviar(cliente, amb.gabriela, comanda_id)
        await pre_conta(cliente, amb.gabriela, comanda_id)
        await pagar(cliente, amb.gabriela, comanda_id, "PIX", "100.00")  # total com taxa: 110,00
        resposta = await taxa(cliente, amb.gabriela, comanda_id, aplicada=False)

    assert resposta.json()["status"] == "FECHADA"
    [item] = (await _itens(session, comanda_id)).values()
    assert (item.status, item.entregue_em) == ("ENTREGUE", FECHAMENTO)
    status_comanda = (await session.execute(select(Comanda.status).where(Comanda.id == comanda_id))).scalar_one()
    assert status_comanda == "FECHADA"
