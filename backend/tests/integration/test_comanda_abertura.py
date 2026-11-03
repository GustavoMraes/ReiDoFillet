"""Cenários da spec `comandas`: abertura, retomada, recusas, consulta, total e acesso."""

import asyncio
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.tempo import RelogioFixo, RelogioSistema
from app.models import Comanda, ItemComanda, LogAuditoria, Reserva
from app.repositories.auditoria import AuditoriaRepository
from app.repositories.cardapio import CardapioRepository
from app.repositories.comanda import ComandaRepository
from app.repositories.mesa import MesaRepository
from app.services.auditoria import AuditoriaService
from app.services.comanda import ComandaService
from app.services.mesa import MesaService
from tests.integration.comandas_util import abrir, preparar
from tests.integration.fabricas import cabecalho_de, cliente_api


async def test_abre_comanda_em_mesa_livre(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        resposta = await abrir(cliente, amb.gabriela, amb.mesas[1])
        mapa = await cliente.get("/mesas", headers=cabecalho_de(amb.gabriela))

    assert resposta.status_code == 201
    comanda = resposta.json()
    assert comanda["mesa"] == {"id": amb.mesas[1], "numero": 1}
    assert comanda["responsavel"] == {"id": amb.gabriela.id, "nome": "Gabriela Garcia"}
    assert (comanda["status"], comanda["itens"], comanda["total"]) == ("ABERTA", [], "0.00")
    assert comanda["aberta_em"].endswith("-03:00")
    assert next(m for m in mapa.json() if m["numero"] == 1)["status"] == "OCUPADA"
    [log] = (await session.execute(select(LogAuditoria))).scalars().all()
    assert (log.acao, log.entidade, log.usuario_id) == ("CRIAR", "Comanda", amb.gabriela.id)


async def test_cada_mesa_tem_identificador_proprio(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        primeira = (await abrir(cliente, amb.gabriela, amb.mesas[1])).json()
        segunda = (await abrir(cliente, amb.gabriela, amb.mesas[2])).json()

    assert primeira["id"] != segunda["id"]


async def test_mesa_ocupada_retoma_a_comanda_existente(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        primeira = await abrir(cliente, amb.gabriela, amb.mesas[3])
        segunda = await abrir(cliente, amb.admin, amb.mesas[3])

    assert (primeira.status_code, segunda.status_code) == (201, 200)
    assert segunda.json()["id"] == primeira.json()["id"]
    assert segunda.json()["responsavel"]["id"] == amb.gabriela.id
    total = (await session.execute(select(func.count()).select_from(Comanda))).scalar_one()
    assert total == 1


async def test_abertura_simultanea_cria_uma_unica_comanda(session: AsyncSession, engine: AsyncEngine):
    amb = await preparar(session)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    async def abrir_em_sessao_propria(usuario):
        async with fabrica() as s:
            relogio = RelogioSistema()
            servico = ComandaService(
                s,
                ComandaRepository(s),
                MesaService(MesaRepository(s), relogio),
                CardapioRepository(s),
                AuditoriaService(AuditoriaRepository(s), relogio),
                relogio,
            )
            comanda, criada = await servico.abrir(amb.mesas[5], usuario)
            return comanda.id, criada

    resultados = await asyncio.gather(*(abrir_em_sessao_propria(u) for u in (amb.gabriela, amb.admin, amb.gabriela)))

    assert len({comanda_id for comanda_id, _ in resultados}) == 1
    assert sum(criada for _, criada in resultados) == 1
    comandas = (await session.execute(select(func.count()).select_from(Comanda))).scalar_one()
    assert comandas == 1


async def test_mesa_em_manutencao_nao_abre(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        resposta = await abrir(cliente, amb.gabriela, amb.mesas[6])

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "Mesa em manutenção"})
    assert (await session.execute(select(func.count()).select_from(Comanda))).scalar_one() == 0


async def test_mesa_reservada_nao_abre(session: AsyncSession):
    amb = await preparar(session)
    relogio = RelogioSistema()
    agora = relogio.agora()
    session.add(
        Reserva(
            mesa_id=amb.mesas[4], nome_cliente="Ana", telefone="11999990000", qtd_pessoas=2,
            inicio=agora + timedelta(minutes=10), fim=agora + timedelta(hours=2, minutes=10), status="CONFIRMADA",
        )
    )
    await session.commit()

    async with cliente_api(session, RelogioFixo(agora)) as cliente:
        resposta = await abrir(cliente, amb.gabriela, amb.mesas[4])

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "Mesa reservada: aguarde o check-in do cliente"})


async def test_mesa_inexistente(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        resposta = await abrir(cliente, amb.gabriela, 999999)

    assert (resposta.status_code, resposta.json()) == (404, {"detalhe": "Mesa não encontrada"})


async def test_consulta_de_comanda_com_itens_e_total_sem_cancelados(session: AsyncSession):
    amb = await preparar(session)
    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[2])).json()["id"]
        refri, filet, batata = amb.produtos["Refrigerante Lata"], amb.produtos["Filet Mignon 300g"], amb.produtos["Batata Rústica"]
        session.add_all(
            [
                ItemComanda(comanda_id=comanda_id, produto_id=refri.id, quantidade=2, preco_unitario=Decimal("7.00"), status="PENDENTE"),
                ItemComanda(comanda_id=comanda_id, produto_id=filet.id, quantidade=1, preco_unitario=Decimal("89.90"), status="CANCELADO"),
                ItemComanda(comanda_id=comanda_id, produto_id=batata.id, quantidade=1, preco_unitario=Decimal("24.90"), status="EM_PREPARO"),
            ]
        )
        await session.commit()

        resposta = await cliente.get(f"/comandas/{comanda_id}", headers=cabecalho_de(amb.gabriela))

    corpo = resposta.json()
    assert resposta.status_code == 200
    assert [(i["produto_nome"], i["quantidade"], i["subtotal"], i["status"]) for i in corpo["itens"]] == [
        ("Refrigerante Lata", 2, "14.00", "PENDENTE"),
        ("Filet Mignon 300g", 1, "89.90", "CANCELADO"),
        ("Batata Rústica", 1, "24.90", "EM_PREPARO"),
    ]
    assert corpo["total"] == "38.90"


async def test_comanda_inexistente(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        resposta = await cliente.get("/comandas/999999", headers=cabecalho_de(amb.gabriela))

    assert (resposta.status_code, resposta.json()) == (404, {"detalhe": "Comanda não encontrada"})


async def test_contabilidade_nao_abre_nem_consulta_comanda(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        abertura = await abrir(cliente, amb.contabilidade, amb.mesas[1])
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[1])).json()["id"]
        consulta = await cliente.get(f"/comandas/{comanda_id}", headers=cabecalho_de(amb.contabilidade))
        sem_sessao = await cliente.post(f"/mesas/{amb.mesas[2]}/comanda")

    assert (abertura.status_code, consulta.status_code, sem_sessao.status_code) == (403, 403, 401)
