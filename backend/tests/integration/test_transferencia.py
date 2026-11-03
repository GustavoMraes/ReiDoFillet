"""Cenários da transferência de comanda (spec `comandas`): troca de mesa, recusas, concorrência, auditoria e acesso."""

import asyncio
from datetime import timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.exceptions import Conflito
from app.core.tempo import RelogioSistema
from app.models import Comanda, Funcionario, ItemComanda, LogAuditoria, Produto, Reserva
from app.repositories.auditoria import AuditoriaRepository
from app.repositories.cardapio import CardapioRepository
from app.repositories.comanda import ComandaRepository
from app.repositories.mesa import MesaRepository
from app.services.auditoria import AuditoriaService
from app.services.comanda import ComandaService
from app.services.mesa import MesaService
from tests.integration.comandas_util import Ambiente, UsuarioRef, abrir, adicionar, enviar, pagar, pre_conta, preparar
from tests.integration.fabricas import cabecalho_de, cliente_api


async def transferir(cliente: AsyncClient, usuario: UsuarioRef, comanda_id: int, mesa_id: int) -> Response:
    return await cliente.post(
        f"/comandas/{comanda_id}/transferir", json={"mesa_id": mesa_id}, headers=cabecalho_de(usuario)
    )


async def _mapa(cliente: AsyncClient, amb: Ambiente) -> dict[int, str]:
    return {m["numero"]: m["status"] for m in (await cliente.get("/mesas", headers=cabecalho_de(amb.gabriela))).json()}


async def _mesa_da_comanda(session: AsyncSession, comanda_id: int) -> int:
    consulta = select(Comanda.mesa_id).where(Comanda.id == comanda_id).execution_options(populate_existing=True)
    return (await session.execute(consulta)).scalar_one()


async def _reservar(session: AsyncSession, mesa_id: int, daqui_a_min: int) -> None:
    inicio = RelogioSistema().agora() + timedelta(minutes=daqui_a_min)
    session.add(
        Reserva(
            mesa_id=mesa_id, nome_cliente="Ana", telefone="11999990000", qtd_pessoas=2,
            inicio=inicio, fim=inicio + timedelta(hours=2), status="CONFIRMADA",
        )
    )
    await session.commit()


def _servico(s: AsyncSession) -> ComandaService:
    relogio = RelogioSistema()
    return ComandaService(
        s,
        ComandaRepository(s),
        MesaService(MesaRepository(s), relogio),
        CardapioRepository(s),
        AuditoriaService(AuditoriaRepository(s), relogio),
        relogio,
    )


# --- Transferência da comanda para outra mesa ---


async def test_cliente_troca_de_mesa(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[3])).json()["id"]
        await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Arroz Branco"], 2)
        await enviar(cliente, amb.gabriela, comanda_id)
        antes = (await cliente.get(f"/comandas/{comanda_id}", headers=cabecalho_de(amb.gabriela))).json()
        resposta = await transferir(cliente, amb.admin, comanda_id, amb.mesas[7])
        mapa = await _mapa(cliente, amb)
        cozinha = (await cliente.get("/cozinha", headers=cabecalho_de(amb.gabriela))).json()

    assert resposta.status_code == 200
    depois = resposta.json()
    assert (depois["id"], depois["mesa"]) == (comanda_id, {"id": amb.mesas[7], "numero": 7})
    assert {k: v for k, v in depois.items() if k != "mesa"} == {k: v for k, v in antes.items() if k != "mesa"}
    assert depois["itens"][0]["status"] == "EM_PREPARO"
    assert (mapa[3], mapa[7]) == ("LIVRE", "OCUPADA")
    assert [item["mesa_numero"] for item in cozinha["em_preparo"]] == [7]

    log = (await session.execute(select(LogAuditoria).where(LogAuditoria.acao == "TRANSFERIR"))).scalar_one()
    assert (log.usuario_id, log.entidade, log.entidade_id) == (amb.admin.id, "Comanda", str(comanda_id))
    assert (log.dados_antes["mesa_id"], log.dados_depois["mesa_id"]) == (amb.mesas[3], amb.mesas[7])


async def test_transferencia_com_pre_conta_e_pagamento_parcial(session: AsyncSession):
    amb = await preparar(session)
    await session.execute(update(Produto).where(Produto.nome == "Arroz Branco").values(preco=Decimal("100.00")))
    await session.commit()

    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[2])).json()["id"]
        await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Arroz Branco"])
        await session.execute(update(ItemComanda).values(status="ENTREGUE"))
        await session.commit()
        await pre_conta(cliente, amb.gabriela, comanda_id)
        await pagar(cliente, amb.gabriela, comanda_id, "PIX", "50.00")
        resposta = await transferir(cliente, amb.gabriela, comanda_id, amb.mesas[8])
        mapa = await _mapa(cliente, amb)

    comanda = resposta.json()
    assert (comanda["status"], comanda["total"], comanda["pago"], comanda["restante"]) == (
        "PRE_CONTA", "110.00", "50.00", "60.00"
    )
    assert len(comanda["pagamentos"]) == 1
    assert (mapa[2], mapa[8]) == ("LIVRE", "AGUARDANDO_PAGAMENTO")


async def test_destino_livre_com_reserva_proxima_e_aceito(session: AsyncSession):
    amb = await preparar(session)
    await _reservar(session, amb.mesas[7], daqui_a_min=60)

    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[3])).json()["id"]
        resposta = await transferir(cliente, amb.gabriela, comanda_id, amb.mesas[7])

    assert resposta.status_code == 200
    assert resposta.json()["mesa"]["numero"] == 7


# --- Destinos que não recebem transferência ---


@pytest.mark.parametrize(
    ("destino", "status_esperado", "mensagem"),
    [
        ("mesma", 409, "A comanda já está nesta mesa"),
        ("ocupada", 409, "A mesa de destino já está em atendimento"),
        ("aguardando", 409, "A mesa de destino já está em atendimento"),
        ("reservada", 409, "A mesa de destino está reservada"),
        ("manutencao", 409, "Mesa em manutenção"),
        ("inexistente", 404, "Mesa não encontrada"),
    ],
)
async def test_destino_recusado(session: AsyncSession, destino: str, status_esperado: int, mensagem: str):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[3])).json()["id"]
        mesa_id = {"mesma": amb.mesas[3], "manutencao": amb.mesas[6], "inexistente": 999999}.get(destino, amb.mesas[7])
        if destino in ("ocupada", "aguardando"):
            outra = (await abrir(cliente, amb.gabriela, amb.mesas[7])).json()["id"]
            if destino == "aguardando":
                await adicionar(cliente, amb.gabriela, outra, amb.produtos["Arroz Branco"])
                await pre_conta(cliente, amb.gabriela, outra)
        if destino == "reservada":
            await _reservar(session, amb.mesas[7], daqui_a_min=10)
        logs_antes = (await session.execute(select(func.count()).select_from(LogAuditoria))).scalar_one()

        resposta = await transferir(cliente, amb.gabriela, comanda_id, mesa_id)

    assert (resposta.status_code, resposta.json()) == (status_esperado, {"detalhe": mensagem})
    assert await _mesa_da_comanda(session, comanda_id) == amb.mesas[3]
    assert (await session.execute(select(func.count()).select_from(LogAuditoria))).scalar_one() == logs_antes


@pytest.mark.parametrize("encerramento", ["FECHADA", "CANCELADA"])
async def test_comanda_encerrada(session: AsyncSession, encerramento: str):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[3])).json()["id"]
        await session.execute(update(Comanda).values(status=encerramento))
        await session.commit()
        resposta = await transferir(cliente, amb.gabriela, comanda_id, amb.mesas[7])
        inexistente = await transferir(cliente, amb.gabriela, 999999, amb.mesas[7])

    assert (resposta.status_code, resposta.json()) == (
        409, {"detalhe": "Somente comandas em atendimento podem ser transferidas"}
    )
    assert (inexistente.status_code, inexistente.json()) == (404, {"detalhe": "Comanda não encontrada"})


async def test_contabilidade_nao_transfere(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[3])).json()["id"]
        resposta = await transferir(cliente, amb.contabilidade, comanda_id, amb.mesas[7])
        sem_sessao = await cliente.post(f"/comandas/{comanda_id}/transferir", json={"mesa_id": amb.mesas[7]})

    assert (resposta.status_code, resposta.json()) == (403, {"detalhe": "Sem permissão para esta funcionalidade"})
    assert sem_sessao.status_code == 401
    assert await _mesa_da_comanda(session, comanda_id) == amb.mesas[3]


# --- Concorrência ---


async def test_transferencias_simultaneas_para_a_mesma_mesa(session: AsyncSession, engine: AsyncEngine):
    amb = await preparar(session)
    async with cliente_api(session) as cliente:
        comandas = [(await abrir(cliente, amb.gabriela, amb.mesas[n])).json()["id"] for n in (1, 2)]
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    async def transferir_em_sessao_propria(comanda_id: int) -> str:
        async with fabrica() as s:
            try:
                await _servico(s).transferir(comanda_id, amb.mesas[7], await s.get(Funcionario, amb.gabriela.id))
                return "ok"
            except Conflito as erro:
                return erro.mensagem

    resultados = await asyncio.gather(*(transferir_em_sessao_propria(c) for c in comandas))

    assert sorted(resultados) == ["A mesa de destino já está em atendimento", "ok"]
    na_mesa_7 = select(func.count()).select_from(Comanda).where(Comanda.mesa_id == amb.mesas[7])
    assert (await session.execute(na_mesa_7)).scalar_one() == 1


async def test_transferencia_disputando_com_abertura_no_destino(session: AsyncSession, engine: AsyncEngine):
    amb = await preparar(session)
    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[1])).json()["id"]
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    async def transferir_comanda() -> str:
        async with fabrica() as s:
            try:
                await _servico(s).transferir(comanda_id, amb.mesas[8], await s.get(Funcionario, amb.gabriela.id))
                return "transferida"
            except Conflito:
                return "recusada"

    async def abrir_no_destino() -> str:
        async with fabrica() as s:
            comanda, criada = await _servico(s).abrir(amb.mesas[8], await s.get(Funcionario, amb.admin.id))
            return "aberta" if criada else f"retomou {comanda.id}"

    resultados = await asyncio.gather(transferir_comanda(), abrir_no_destino())

    # Ou a transferência vence (e a abertura retoma a comanda transferida), ou a abertura vence e a transferência é recusada.
    assert resultados in (["transferida", f"retomou {comanda_id}"], ["recusada", "aberta"])
    ativas_na_8 = select(func.count()).select_from(Comanda).where(
        Comanda.mesa_id == amb.mesas[8], Comanda.status.in_(("ABERTA", "PRE_CONTA"))
    )
    assert (await session.execute(ativas_na_8)).scalar_one() == 1
