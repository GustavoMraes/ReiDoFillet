"""Cenários da spec `relatorios`: período, operacional, produtos, movimento, financeiro, rastro e acesso."""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import RelogioFixo
from app.models import Comanda, ItemComanda, LogAuditoria, Pagamento
from tests.integration.comandas_util import Ambiente, ProdutoRef, UsuarioRef, preparar
from tests.integration.fabricas import cabecalho_de, cliente_api

SP = ZoneInfo("America/Sao_Paulo")
DIA = "2026-10-20"
HOJE = RelogioFixo(datetime(2026, 10, 20, 23, 0, tzinfo=SP))


def _h(hora: int, minuto: int = 0, dia: int = 20) -> datetime:
    return datetime(2026, 10, dia, hora, minuto, tzinfo=SP)


async def _comanda(
    session: AsyncSession,
    amb: Ambiente,
    mesa: int,
    aberta: datetime,
    status: str = "FECHADA",
    fechada: datetime | None = None,
    itens: list[tuple[ProdutoRef, int, str | None, str]] = (),
    pagamentos: list[tuple[str, str]] = (),
    taxa: bool = True,
) -> int:
    """itens: (produto, quantidade, preço do lançamento ou None para o atual, status do item)."""
    comanda = Comanda(
        mesa_id=amb.mesas[mesa],
        funcionario_id=amb.gabriela.id,
        status=status,
        aberta_em=aberta,
        fechada_em=fechada,
        taxa_servico_pct=Decimal("10.00") if status in ("PRE_CONTA", "FECHADA") else None,
        taxa_servico_aplicada=taxa,
    )
    session.add(comanda)
    await session.flush()
    for produto, quantidade, preco, situacao in itens:
        session.add(
            ItemComanda(
                comanda_id=comanda.id,
                produto_id=produto.id,
                quantidade=quantidade,
                preco_unitario=Decimal(preco) if preco else produto.preco,
                status=situacao,
            )
        )
    for forma, valor in pagamentos:
        session.add(Pagamento(comanda_id=comanda.id, forma=forma, valor=Decimal(valor), registrado_em=fechada or aberta))
    await session.commit()
    return comanda.id


async def _operacional(cliente: AsyncClient, usuario: UsuarioRef, **periodo) -> Response:
    return await cliente.get("/relatorios/operacional", params=periodo, headers=cabecalho_de(usuario))


async def _financeiro(cliente: AsyncClient, usuario: UsuarioRef, **periodo) -> Response:
    return await cliente.get("/relatorios/financeiro", params=periodo, headers=cabecalho_de(usuario))


@pytest.fixture
async def amb(session: AsyncSession) -> Ambiente:
    return await preparar(session)


async def _dia_de_movimento(session: AsyncSession, amb: Ambiente) -> None:
    arroz, filet = amb.produtos["Arroz Branco"], amb.produtos["Filet Mignon 300g"]
    # R$ 100,00 + 10% = R$ 110,00, 30 minutos
    await _comanda(session, amb, 1, _h(12, 0), fechada=_h(12, 30),
                   itens=[(arroz, 10, "10.00", "ENTREGUE")], pagamentos=[("PIX", "110.00")])
    # R$ 50,00 + 10% = R$ 55,00, 60 minutos
    await _comanda(session, amb, 2, _h(20, 0), fechada=_h(21, 0),
                   itens=[(filet, 1, "50.00", "ENTREGUE")], pagamentos=[("CREDITO", "55.00")])
    # R$ 35,00 sem taxa, 90 minutos
    await _comanda(session, amb, 3, _h(20, 10), fechada=_h(21, 40), taxa=False,
                   itens=[(filet, 1, "35.00", "ENTREGUE")], pagamentos=[("DINHEIRO", "35.00")])
    await _comanda(session, amb, 4, _h(20, 20), status="CANCELADA", fechada=_h(20, 25))
    await _comanda(session, amb, 5, _h(20, 30), status="ABERTA", itens=[(arroz, 3, "10.00", "EM_PREPARO")])


# --- Período dos relatórios ---


@pytest.mark.parametrize(
    ("periodo", "mensagem"),
    [
        ({"inicio": "2026-10-02", "fim": "2026-10-01"}, "A data final deve ser igual ou posterior à inicial"),
        ({"inicio": "2025-01-01", "fim": "2026-01-02"}, "O período máximo é de 366 dias"),
    ],
)
async def test_periodo_invalido(session: AsyncSession, amb: Ambiente, periodo: dict, mensagem: str):
    async with cliente_api(session, HOJE) as cliente:
        operacional = await _operacional(cliente, amb.admin, **periodo)
        financeiro = await _financeiro(cliente, amb.admin, **periodo)

    assert (operacional.status_code, operacional.json()) == (422, {"detalhe": mensagem})
    assert (financeiro.status_code, financeiro.json()) == (422, {"detalhe": mensagem})


# --- Relatório operacional ---


async def test_dia_de_movimento(session: AsyncSession, amb: Ambiente):
    await _dia_de_movimento(session, amb)
    # Aberta na véspera e fechada no dia: fica fora do operacional do dia (critério é a abertura).
    await _comanda(session, amb, 7, _h(23, 50, dia=19), fechada=_h(0, 30),
                   itens=[(amb.produtos["Arroz Branco"], 1, "10.00", "ENTREGUE")], pagamentos=[("PIX", "11.00")])

    async with cliente_api(session, HOJE) as cliente:
        resposta = await _operacional(cliente, amb.admin)  # padrão: hoje

    assert resposta.status_code == 200
    r = resposta.json()
    assert r["periodo"] == {"inicio": DIA, "fim": DIA}
    assert r["comandas"] == {"em_aberto": 1, "fechadas": 3, "canceladas": 1, "total": 5}
    assert (r["faturamento"], r["ticket_medio"], r["tempo_medio_minutos"]) == ("200.00", "66.67", 60)
    assert r["por_dia"] == [{"data": DIA, "comandas": 5, "faturamento": "200.00"}]


async def test_periodo_sem_comandas_fechadas(session: AsyncSession, amb: Ambiente):
    await _comanda(session, amb, 1, _h(12), status="ABERTA")

    async with cliente_api(session, HOJE) as cliente:
        r = (await _operacional(cliente, amb.admin, inicio=DIA, fim=DIA)).json()

    assert (r["faturamento"], r["ticket_medio"], r["tempo_medio_minutos"], r["produtos"]) == ("0.00", None, None, [])


async def test_ranking_do_periodo(session: AsyncSession, amb: Ambiente):
    arroz, filet, picanha = (amb.produtos[n] for n in ("Arroz Branco", "Filet Mignon 300g", "Picanha 400g"))
    await _comanda(session, amb, 1, _h(12), fechada=_h(13), itens=[
        (arroz, 5, None, "ENTREGUE"), (filet, 5, None, "ENTREGUE"), (picanha, 2, None, "CANCELADO"),
    ])
    await _comanda(session, amb, 2, _h(19), fechada=_h(20), itens=[(arroz, 3, None, "ENTREGUE")])
    await _comanda(session, amb, 3, _h(20), status="ABERTA", itens=[(picanha, 9, None, "EM_PREPARO")])

    async with cliente_api(session, HOJE) as cliente:
        produtos = (await _operacional(cliente, amb.admin, inicio=DIA)).json()["produtos"]

    assert [(p["nome"], p["quantidade"], p["valor"]) for p in produtos] == [
        ("Arroz Branco", 8, str(arroz.preco * 8)),
        ("Filet Mignon 300g", 5, str(filet.preco * 5)),
    ]


async def test_ranking_limitado_a_dez(session: AsyncSession, amb: Ambiente):
    produtos = list(amb.produtos.values())
    assert len(produtos) > 10
    await _comanda(session, amb, 1, _h(12), fechada=_h(13), itens=[(p, 1, None, "ENTREGUE") for p in produtos])

    async with cliente_api(session, HOJE) as cliente:
        ranking = (await _operacional(cliente, amb.admin, inicio=DIA)).json()["produtos"]

    assert len(ranking) == 10
    valores = [Decimal(p["valor"]) for p in ranking]
    assert valores == sorted(valores, reverse=True)  # empate na quantidade: maior valor primeiro


async def test_preco_alterado_no_periodo(session: AsyncSession, amb: Ambiente):
    filet = amb.produtos["Filet Mignon 300g"]
    await _comanda(session, amb, 1, _h(12), fechada=_h(13), itens=[(filet, 1, "89.90", "ENTREGUE")])
    await _comanda(session, amb, 2, _h(19), fechada=_h(20), itens=[(filet, 1, "95.00", "ENTREGUE")])

    async with cliente_api(session, HOJE) as cliente:
        [produto] = (await _operacional(cliente, amb.admin, inicio=DIA)).json()["produtos"]

    assert (produto["quantidade"], produto["valor"]) == (2, "184.90")


async def test_horario_de_pico_e_movimento_por_dia(session: AsyncSession, amb: Ambiente):
    for mesa, minuto in zip((1, 2, 3, 4), (0, 15, 30, 59)):
        await _comanda(session, amb, mesa, _h(20, minuto), status="CANCELADA", fechada=_h(21))
    await _comanda(session, amb, 5, _h(12, 10, dia=21), fechada=_h(13, dia=21),
                   itens=[(amb.produtos["Arroz Branco"], 2, "10.00", "ENTREGUE")])

    async with cliente_api(session, HOJE) as cliente:
        r = (await _operacional(cliente, amb.admin, inicio=DIA, fim="2026-10-21")).json()

    por_hora = {h["hora"]: h["comandas"] for h in r["por_hora"]}
    assert (len(r["por_hora"]), por_hora[20], por_hora[12], sum(por_hora.values())) == (24, 4, 1, 5)
    assert r["por_dia"] == [
        {"data": DIA, "comandas": 4, "faturamento": "0.00"},
        {"data": "2026-10-21", "comandas": 1, "faturamento": "22.00"},
    ]


# --- Relatório financeiro ---


async def test_fechamento_do_dia(session: AsyncSession, amb: Ambiente):
    arroz = amb.produtos["Arroz Branco"]
    a = await _comanda(session, amb, 1, _h(12), fechada=_h(13), itens=[(arroz, 10, "10.00", "ENTREGUE")],
                       pagamentos=[("PIX", "60.00"), ("CREDITO", "50.00")])
    b = await _comanda(session, amb, 2, _h(19), fechada=_h(20), taxa=False, itens=[(arroz, 1, "35.00", "ENTREGUE")],
                       pagamentos=[("DINHEIRO", "35.00")])
    # Fora do financeiro: aberta, em pré-conta e cancelada.
    await _comanda(session, amb, 3, _h(20), status="ABERTA", itens=[(arroz, 1, None, "PENDENTE")])
    await _comanda(session, amb, 4, _h(20), status="PRE_CONTA", itens=[(arroz, 1, None, "ENTREGUE")])
    await _comanda(session, amb, 5, _h(20), status="CANCELADA", fechada=_h(20, 5))
    # Aberta na véspera e fechada no dia: entra (critério é o fechamento).
    c = await _comanda(session, amb, 7, _h(23, 50, dia=19), fechada=_h(0, 30), taxa=False,
                       itens=[(arroz, 1, "10.00", "ENTREGUE")], pagamentos=[("DEBITO", "10.00")])

    async with cliente_api(session, HOJE) as cliente:
        resposta = await _financeiro(cliente, amb.contabilidade, inicio=DIA, fim=DIA)
        telas = {i: (await cliente.get(f"/comandas/{i}", headers=cabecalho_de(amb.gabriela))).json() for i in (a, b, c)}

    assert resposta.status_code == 200
    r = resposta.json()
    assert [comanda["id"] for comanda in r["comandas"]] == [c, a, b]  # ordem de fechamento
    assert r["totais"] == {
        "comandas": 3,
        "subtotal": "145.00",
        "taxa_servico": "10.00",
        "total": "155.00",
        "por_forma": [
            {"forma": "PIX", "valor": "60.00"},
            {"forma": "CREDITO", "valor": "50.00"},
            {"forma": "DEBITO", "valor": "10.00"},
            {"forma": "DINHEIRO", "valor": "35.00"},
        ],
    }
    primeira = next(comanda for comanda in r["comandas"] if comanda["id"] == a)
    assert (primeira["mesa_numero"], primeira["responsavel"]) == (1, "Gabriela Garcia")
    assert (primeira["aberta_em"], primeira["fechada_em"]) == (f"{DIA}T12:00:00-03:00", f"{DIA}T13:00:00-03:00")
    assert primeira["pagamentos"] == [{"forma": "PIX", "valor": "60.00"}, {"forma": "CREDITO", "valor": "50.00"}]
    for comanda in r["comandas"]:  # os mesmos números da tela da comanda
        tela = telas[comanda["id"]]
        assert (comanda["subtotal"], comanda["taxa_servico"], comanda["total"]) == (
            tela["subtotal"], tela["taxa_servico"]["valor"], tela["total"]
        )


async def test_financeiro_sem_comandas(session: AsyncSession, amb: Ambiente):
    async with cliente_api(session, HOJE) as cliente:
        r = (await _financeiro(cliente, amb.admin)).json()

    assert r["comandas"] == []
    assert r["totais"]["total"] == "0.00"
    assert [f["valor"] for f in r["totais"]["por_forma"]] == ["0.00"] * 4


# --- Rastro das consultas e acesso ---


async def test_consultas_auditadas(session: AsyncSession, amb: Ambiente):
    async with cliente_api(session, HOJE) as cliente:
        await _financeiro(cliente, amb.contabilidade, inicio="2026-10-01", fim="2026-10-31")
        await _operacional(cliente, amb.admin)

    logs = (await session.execute(select(LogAuditoria).where(LogAuditoria.acao == "CONSULTAR").order_by(LogAuditoria.id))).scalars().all()
    assert [(log.usuario_id, log.entidade, log.entidade_id) for log in logs] == [
        (amb.contabilidade.id, "Relatorio", "financeiro"),
        (amb.admin.id, "Relatorio", "operacional"),
    ]
    assert (logs[0].dados_depois["inicio"], logs[0].dados_depois["fim"]) == ("2026-10-01", "2026-10-31")
    assert (logs[1].dados_depois["inicio"], logs[1].dados_depois["fim"]) == (DIA, DIA)


async def test_acesso_aos_relatorios(session: AsyncSession, amb: Ambiente):
    async with cliente_api(session, HOJE) as cliente:
        contabilidade_operacional = await _operacional(cliente, amb.contabilidade)
        funcionario_financeiro = await _financeiro(cliente, amb.gabriela)
        funcionario_operacional = await _operacional(cliente, amb.gabriela)
        admin_financeiro = await _financeiro(cliente, amb.admin)
        sem_sessao = await cliente.get("/relatorios/financeiro")

    sem_permissao = {"detalhe": "Sem permissão para esta funcionalidade"}
    assert (contabilidade_operacional.status_code, contabilidade_operacional.json()) == (403, sem_permissao)
    assert (funcionario_financeiro.status_code, funcionario_operacional.status_code) == (403, 403)
    assert admin_financeiro.status_code == 200
    assert sem_sessao.status_code == 401
