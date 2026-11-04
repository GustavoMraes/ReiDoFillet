"""Cenários da spec `auditoria`: consulta do histórico, paginação, filtros, rastro da consulta e acesso."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import RelogioFixo
from app.models import LogAuditoria
from tests.integration.comandas_util import Ambiente, UsuarioRef, preparar
from tests.integration.fabricas import cabecalho_de, cliente_api

SP = ZoneInfo("America/Sao_Paulo")
DIA = "2026-10-20"
HOJE = RelogioFixo(datetime(2026, 10, 20, 23, 0, tzinfo=SP))
MEIO_DIA = datetime(2026, 10, 20, 12, 0, tzinfo=SP)


async def _log(session: AsyncSession, quando: datetime, usuario_id: int | None, acao: str, entidade: str, entidade_id: str,
               antes: dict | None = None, depois: dict | None = None) -> None:
    session.add(LogAuditoria(usuario_id=usuario_id, acao=acao, entidade=entidade, entidade_id=entidade_id,
                             dados_antes=antes, dados_depois=depois, criado_em=quando))


async def consultar(cliente: AsyncClient, usuario: UsuarioRef, **filtros) -> Response:
    return await cliente.get("/auditoria", params={"inicio": DIA, **filtros}, headers=cabecalho_de(usuario))


async def _cenario(session: AsyncSession) -> Ambiente:
    amb = await preparar(session)
    await _log(session, MEIO_DIA, amb.gabriela.id, "CRIAR", "ItemComanda", "1", None, {"status": "PENDENTE"})
    await _log(session, MEIO_DIA + timedelta(minutes=5), amb.gabriela.id, "CANCELAR", "ItemComanda", "1",
               {"status": "PENDENTE"}, {"status": "CANCELADO"})
    await _log(session, MEIO_DIA + timedelta(minutes=10), amb.admin.id, "CANCELAR", "Comanda", "7")
    await _log(session, MEIO_DIA + timedelta(minutes=15), None, "ENTREGAR", "ItemComanda", "2")
    await _log(session, MEIO_DIA - timedelta(days=1), amb.gabriela.id, "CANCELAR", "ItemComanda", "9")  # outro dia
    await session.commit()
    return amb


async def test_quem_cancelou_o_item(session: AsyncSession):
    amb = await _cenario(session)

    async with cliente_api(session, HOJE) as cliente:
        resposta = await consultar(cliente, amb.admin, acao="CANCELAR", entidade="ItemComanda")

    assert resposta.status_code == 200
    r = resposta.json()
    assert (r["total"], r["pagina"], r["paginas"]) == (1, 1, 1)
    [registro] = r["registros"]
    assert (registro["usuario"], registro["usuario_id"], registro["acao"], registro["entidade"], registro["entidade_id"]) == (
        "Gabriela Garcia", amb.gabriela.id, "CANCELAR", "ItemComanda", "1"
    )
    assert (registro["dados_antes"], registro["dados_depois"]) == ({"status": "PENDENTE"}, {"status": "CANCELADO"})
    assert registro["criado_em"] == f"{DIA}T12:05:00-03:00"


async def test_filtros_por_usuario_e_sistema(session: AsyncSession):
    amb = await _cenario(session)

    async with cliente_api(session, HOJE) as cliente:
        da_gabriela = (await consultar(cliente, amb.contabilidade, usuario_id=amb.gabriela.id)).json()
        do_sistema = (await consultar(cliente, amb.contabilidade, usuario_id=0)).json()
        tudo = (await consultar(cliente, amb.contabilidade)).json()

    assert [r["acao"] for r in da_gabriela["registros"]] == ["CANCELAR", "CRIAR"]  # mais recente primeiro
    assert [(r["usuario"], r["acao"]) for r in do_sistema["registros"]] == [(None, "ENTREGAR")]
    # 4 do cenário (o da véspera fica fora do período) + as 2 consultas anteriores deste teste, já registradas.
    assert tudo["total"] == 6
    assert [r["acao"] for r in tudo["registros"]][:2] == ["CONSULTAR", "CONSULTAR"]


async def test_muitos_registros(session: AsyncSession):
    amb = await preparar(session)
    for n in range(120):
        await _log(session, MEIO_DIA + timedelta(seconds=n), amb.admin.id, "ALTERAR", "Produto", str(n))
    await session.commit()

    async with cliente_api(session, HOJE) as cliente:
        # Filtrando a ação: as consultas deste teste também viram registros do período.
        primeira = (await consultar(cliente, amb.admin, acao="ALTERAR")).json()
        terceira = (await consultar(cliente, amb.admin, acao="ALTERAR", pagina=3)).json()
        invalida = await consultar(cliente, amb.admin, pagina=0)

    assert (primeira["total"], primeira["paginas"], len(primeira["registros"])) == (120, 3, 50)
    assert [r["entidade_id"] for r in primeira["registros"][:2]] == ["119", "118"]
    assert (terceira["pagina"], len(terceira["registros"]), terceira["registros"][-1]["entidade_id"]) == (3, 20, "0")
    assert invalida.status_code == 422


async def test_consulta_registrada(session: AsyncSession):
    amb = await _cenario(session)

    async with cliente_api(session, HOJE) as cliente:
        primeira = (await consultar(cliente, amb.contabilidade, acao="CANCELAR")).json()
        segunda = (await cliente.get("/auditoria", params={"inicio": DIA, "acao": "CONSULTAR"},
                                     headers=cabecalho_de(amb.contabilidade))).json()

    assert primeira["total"] == 2  # a própria consulta não aparece na página
    [registro] = segunda["registros"]  # a primeira consulta aparece na seguinte
    assert (registro["usuario_id"], registro["entidade"], registro["entidade_id"]) == (
        amb.contabilidade.id, "Relatorio", "auditoria"
    )
    assert registro["dados_depois"] == {
        "inicio": DIA, "fim": DIA, "usuario_id": None, "acao": "CANCELAR", "entidade": None, "pagina": 1
    }
    logs = (await session.execute(select(LogAuditoria).where(LogAuditoria.acao == "CONSULTAR"))).scalars().all()
    assert len(logs) == 2


async def test_opcoes_dos_filtros(session: AsyncSession):
    amb = await _cenario(session)

    async with cliente_api(session, HOJE) as cliente:
        opcoes = (await cliente.get("/auditoria/opcoes", headers=cabecalho_de(amb.admin))).json()

    assert {"CRIAR", "CANCELAR", "CONSULTAR", "TRANSFERIR"} <= set(opcoes["acoes"])
    assert opcoes["entidades"] == ["Comanda", "ItemComanda"]
    assert "Gabriela Garcia" in [u["nome"] for u in opcoes["usuarios"]]
    consultas = (await session.execute(select(LogAuditoria).where(LogAuditoria.acao == "CONSULTAR"))).scalars().all()
    assert consultas == []  # montar os filtros não é registrado


async def test_funcionario_tenta_consultar_a_auditoria(session: AsyncSession):
    amb = await _cenario(session)

    async with cliente_api(session, HOJE) as cliente:
        consulta = await consultar(cliente, amb.gabriela)
        opcoes = await cliente.get("/auditoria/opcoes", headers=cabecalho_de(amb.gabriela))
        invertido = await consultar(cliente, amb.admin, fim="2026-10-19")

    assert (consulta.status_code, consulta.json()) == (403, {"detalhe": "Sem permissão para esta funcionalidade"})
    assert opcoes.status_code == 403
    assert (invertido.status_code, invertido.json()) == (422, {"detalhe": "A data final deve ser igual ou posterior à inicial"})
