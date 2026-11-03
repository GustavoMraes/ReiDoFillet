"""Cenários da spec `reservas`: criação, conflitos, consulta, cancelamento, check-in, auditoria e acesso."""

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.exceptions import Conflito
from app.core.tempo import RelogioFixo
from app.models import Comanda, Funcionario, LogAuditoria, Mesa, Reserva
from app.repositories.auditoria import AuditoriaRepository
from app.repositories.cardapio import CardapioRepository
from app.repositories.comanda import ComandaRepository
from app.repositories.mesa import MesaRepository
from app.repositories.reserva import ReservaRepository
from app.services.auditoria import AuditoriaService
from app.services.comanda import ComandaService
from app.services.mesa import MesaService
from app.services.reserva import ReservaService
from tests.integration.comandas_util import Ambiente, UsuarioRef, abrir, preparar
from tests.integration.fabricas import cabecalho_de, cliente_api

SP = ZoneInfo("America/Sao_Paulo")
DIA = "2026-11-10"


def _relogio(h: int, m: int = 0) -> RelogioFixo:
    return RelogioFixo(datetime(2026, 11, 10, h, m, tzinfo=SP))


HOJE_15H = _relogio(15)


async def reservar(
    cliente: AsyncClient,
    usuario: UsuarioRef,
    mesa_id: int,
    inicio: str,
    nome: str = "Ana Souza",
    telefone: str = "11 99999-0000",
    pessoas: int = 2,
) -> Response:
    return await cliente.post(
        "/reservas",
        json={"mesa_id": mesa_id, "nome_cliente": nome, "telefone": telefone, "qtd_pessoas": pessoas, "inicio": inicio},
        headers=cabecalho_de(usuario),
    )


async def _reserva_20h30(session: AsyncSession, amb: Ambiente, mesa: int = 4) -> int:
    async with cliente_api(session, HOJE_15H) as cliente:
        return (await reservar(cliente, amb.gabriela, amb.mesas[mesa], f"{DIA}T20:30:00")).json()["reserva"]["id"]


async def _contar(session: AsyncSession, modelo) -> int:
    return (await session.execute(select(func.count()).select_from(modelo))).scalar_one()


async def _reserva_gravada(session: AsyncSession) -> Reserva:
    return (await session.execute(select(Reserva).execution_options(populate_existing=True))).scalar_one()


async def _logs_de_reserva(session: AsyncSession) -> list[LogAuditoria]:
    consulta = select(LogAuditoria).where(LogAuditoria.entidade == "Reserva").order_by(LogAuditoria.id)
    return list((await session.execute(consulta)).scalars())


def _servico(s: AsyncSession, relogio: RelogioFixo) -> ReservaService:
    auditoria = AuditoriaService(AuditoriaRepository(s), relogio)
    comandas = ComandaService(
        s, ComandaRepository(s), MesaService(MesaRepository(s), relogio), CardapioRepository(s), auditoria, relogio
    )
    return ReservaService(s, ReservaRepository(s), MesaRepository(s), comandas, auditoria, relogio)


def _status_da_mesa(mapa: Response, numero: int) -> str:
    return next(m for m in mapa.json() if m["numero"] == numero)["status"]


# --- Criação de reserva ---


async def test_reserva_valida(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session, HOJE_15H) as cliente:
        resposta = await reservar(cliente, amb.gabriela, amb.mesas[4], f"{DIA}T20:30:00")

    assert resposta.status_code == 201
    assert resposta.json()["aviso"] is None
    reserva = resposta.json()["reserva"]
    assert reserva["mesa"] == {"id": amb.mesas[4], "numero": 4}
    assert (reserva["nome_cliente"], reserva["telefone"], reserva["qtd_pessoas"]) == ("Ana Souza", "11 99999-0000", 2)
    assert (reserva["inicio"], reserva["fim"]) == (f"{DIA}T20:30:00-03:00", f"{DIA}T22:30:00-03:00")
    assert (reserva["status"], reserva["situacao"]) == ("CONFIRMADA", "CONFIRMADA")
    assert (await _reserva_gravada(session)).criado_por_id == amb.gabriela.id
    [log] = await _logs_de_reserva(session)
    assert (log.acao, log.usuario_id, log.dados_antes) == ("CRIAR", amb.gabriela.id, None)
    assert log.dados_depois["nome_cliente"] == "Ana Souza"
    assert "telefone" not in log.dados_depois


async def test_horario_com_fuso_explicito(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session, HOJE_15H) as cliente:
        resposta = await reservar(cliente, amb.gabriela, amb.mesas[4], f"{DIA}T23:30:00Z")

    assert resposta.json()["reserva"]["inicio"] == f"{DIA}T20:30:00-03:00"


async def test_horario_no_passado(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session, HOJE_15H) as cliente:
        resposta = await reservar(cliente, amb.gabriela, amb.mesas[4], f"{DIA}T14:59:00")

    assert (resposta.status_code, resposta.json()) == (422, {"detalhe": "O horário da reserva deve ser no futuro"})
    assert await _contar(session, Reserva) == 0


@pytest.mark.parametrize(
    ("dados", "mensagem"),
    [
        ({"nome": "   "}, "Informe o nome do cliente"),
        ({"nome": "A" * 101}, "O nome do cliente deve ter no máximo 100 caracteres"),
        ({"telefone": "1234567"}, "O telefone deve ter de 8 a 20 caracteres"),
        ({"telefone": "1" * 21}, "O telefone deve ter de 8 a 20 caracteres"),
        ({"pessoas": 0}, "A quantidade de pessoas deve estar entre 1 e 50"),
        ({"pessoas": 51}, "A quantidade de pessoas deve estar entre 1 e 50"),
    ],
)
async def test_dados_invalidos(session: AsyncSession, dados: dict, mensagem: str):
    amb = await preparar(session)

    async with cliente_api(session, HOJE_15H) as cliente:
        resposta = await reservar(cliente, amb.gabriela, amb.mesas[4], f"{DIA}T20:30:00", **dados)

    assert (resposta.status_code, resposta.json()) == (422, {"detalhe": mensagem})
    assert await _contar(session, Reserva) == 0


# --- Reservas sobrepostas na mesma mesa ---


async def test_horarios_sobrepostos(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session, HOJE_15H) as cliente:
        await reservar(cliente, amb.gabriela, amb.mesas[4], f"{DIA}T20:00:00")
        depois = await reservar(cliente, amb.admin, amb.mesas[4], f"{DIA}T21:00:00", nome="Bruno")
        antes = await reservar(cliente, amb.admin, amb.mesas[4], f"{DIA}T18:30:00", nome="Bruno")

    assert (depois.status_code, depois.json()) == (409, {"detalhe": "A mesa já tem reserva às 20h00 neste período"})
    assert antes.status_code == 409
    assert await _contar(session, Reserva) == 1


async def test_horarios_encostados_e_outra_mesa(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session, HOJE_15H) as cliente:
        await reservar(cliente, amb.gabriela, amb.mesas[4], f"{DIA}T20:00:00")
        depois = await reservar(cliente, amb.gabriela, amb.mesas[4], f"{DIA}T22:00:00")
        antes = await reservar(cliente, amb.gabriela, amb.mesas[4], f"{DIA}T18:00:00")
        outra_mesa = await reservar(cliente, amb.gabriela, amb.mesas[5], f"{DIA}T20:30:00")

    assert (depois.status_code, antes.status_code, outra_mesa.status_code) == (201, 201, 201)


async def test_reserva_cancelada_nao_conflita(session: AsyncSession):
    amb = await preparar(session)
    reserva_id = await _reserva_20h30(session, amb)

    async with cliente_api(session, HOJE_15H) as cliente:
        await cliente.post(f"/reservas/{reserva_id}/cancelar", headers=cabecalho_de(amb.gabriela))
        resposta = await reservar(cliente, amb.gabriela, amb.mesas[4], f"{DIA}T21:00:00")

    assert resposta.status_code == 201


async def test_reservas_simultaneas(session: AsyncSession, engine: AsyncEngine):
    amb = await preparar(session)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    async def reservar_em_sessao_propria(usuario: UsuarioRef, hora: int) -> bool:
        async with fabrica() as s:
            funcionario = await s.get(Funcionario, usuario.id)
            try:
                await _servico(s, HOJE_15H).criar(
                    amb.mesas[4], "Cliente", "11999990000", 2, datetime(2026, 11, 10, hora, 0), funcionario
                )
                return True
            except Conflito:
                return False

    resultados = await asyncio.gather(
        reservar_em_sessao_propria(amb.gabriela, 20), reservar_em_sessao_propria(amb.admin, 21)
    )

    assert sorted(resultados) == [False, True]
    assert await _contar(session, Reserva) == 1


# --- Restrições da mesa na reserva ---


async def test_mesa_em_manutencao(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session, HOJE_15H) as cliente:
        resposta = await reservar(cliente, amb.gabriela, amb.mesas[6], f"{DIA}T20:30:00")

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "Mesa em manutenção"})


async def test_mesa_inexistente(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session, HOJE_15H) as cliente:
        resposta = await reservar(cliente, amb.gabriela, 999999, f"{DIA}T20:30:00")

    assert (resposta.status_code, resposta.json()) == (404, {"detalhe": "Mesa não encontrada"})


async def test_acima_da_capacidade(session: AsyncSession):
    amb = await preparar(session)
    capacidade = (await session.get(Mesa, amb.mesas[4])).capacidade
    pessoas = capacidade + 2

    async with cliente_api(session, HOJE_15H) as cliente:
        resposta = await reservar(cliente, amb.gabriela, amb.mesas[4], f"{DIA}T20:30:00", pessoas=pessoas)

    assert resposta.status_code == 201
    assert resposta.json()["aviso"] == f"Atenção: {pessoas} pessoas excedem a capacidade da mesa ({capacidade} lugares)."


# --- Consulta das reservas do dia ---


async def _reservas_de_varios_dias(session: AsyncSession, amb: Ambiente) -> None:
    async with cliente_api(session, _relogio(9)) as cliente:
        await reservar(cliente, amb.gabriela, amb.mesas[2], f"{DIA}T10:00:00", nome="Manhã")
    async with cliente_api(session, HOJE_15H) as cliente:
        await reservar(cliente, amb.gabriela, amb.mesas[4], f"{DIA}T20:30:00", nome="Segunda")
        await reservar(cliente, amb.gabriela, amb.mesas[5], f"{DIA}T19:00:00", nome="Primeira")
        await reservar(cliente, amb.gabriela, amb.mesas[3], f"{DIA}T23:59:00", nome="Fim do dia")
        await reservar(cliente, amb.gabriela, amb.mesas[4], "2026-11-11T19:00:00", nome="Amanhã")
        await reservar(cliente, amb.gabriela, amb.mesas[1], "2026-12-01T12:00:00", nome="Mês que vem")
    session.add(
        Reserva(
            mesa_id=amb.mesas[1], nome_cliente="Ontem", telefone="11999990000", qtd_pessoas=2,
            inicio=datetime(2026, 11, 9, 20, 0, tzinfo=SP), fim=datetime(2026, 11, 9, 22, 0, tzinfo=SP),
        )
    )
    await session.commit()


async def test_reservas_de_um_dia(session: AsyncSession):
    amb = await preparar(session)
    await _reservas_de_varios_dias(session, amb)

    async with cliente_api(session, HOJE_15H) as cliente:
        hoje = await cliente.get("/reservas", params={"data": DIA}, headers=cabecalho_de(amb.gabriela))
        amanha = await cliente.get("/reservas", params={"data": "2026-11-11"}, headers=cabecalho_de(amb.gabriela))

    assert hoje.status_code == 200
    assert [r["nome_cliente"] for r in hoje.json()] == ["Manhã", "Primeira", "Segunda", "Fim do dia"]
    assert [r["nome_cliente"] for r in amanha.json()] == ["Amanhã"]


async def test_sem_data_lista_de_hoje_em_diante(session: AsyncSession):
    amb = await preparar(session)
    await _reservas_de_varios_dias(session, amb)

    async with cliente_api(session, HOJE_15H) as cliente:
        resposta = await cliente.get("/reservas", headers=cabecalho_de(amb.gabriela))

    assert resposta.status_code == 200
    assert [r["nome_cliente"] for r in resposta.json()] == [
        "Manhã", "Primeira", "Segunda", "Fim do dia", "Amanhã", "Mês que vem"
    ]


async def test_situacao_nao_compareceu_na_listagem(session: AsyncSession):
    amb = await preparar(session)
    await _reserva_20h30(session, amb)

    async with cliente_api(session, _relogio(21, 1)) as cliente:
        [reserva] = (await cliente.get("/reservas", headers=cabecalho_de(amb.gabriela))).json()

    assert (reserva["status"], reserva["situacao"]) == ("CONFIRMADA", "NAO_COMPARECEU")


# --- Cancelamento de reserva ---


async def test_cliente_avisa_que_nao_vem(session: AsyncSession):
    amb = await preparar(session)
    reserva_id = await _reserva_20h30(session, amb)

    async with cliente_api(session, _relogio(20, 15)) as cliente:
        antes = await cliente.get("/mesas", headers=cabecalho_de(amb.gabriela))
        resposta = await cliente.post(f"/reservas/{reserva_id}/cancelar", headers=cabecalho_de(amb.admin))
        depois = await cliente.get("/mesas", headers=cabecalho_de(amb.gabriela))

    assert _status_da_mesa(antes, 4) == "RESERVADA"
    assert resposta.status_code == 200
    assert (resposta.json()["status"], resposta.json()["situacao"]) == ("CANCELADA", "CANCELADA")
    assert _status_da_mesa(depois, 4) == "LIVRE"
    assert (await _reserva_gravada(session)).cancelado_por_id == amb.admin.id
    _, log = await _logs_de_reserva(session)
    assert (log.acao, log.usuario_id) == ("CANCELAR", amb.admin.id)
    assert (log.dados_antes["status"], log.dados_depois["status"]) == ("CONFIRMADA", "CANCELADA")


async def test_cancelar_reserva_ja_cancelada_ou_inexistente(session: AsyncSession):
    amb = await preparar(session)
    reserva_id = await _reserva_20h30(session, amb)

    async with cliente_api(session, HOJE_15H) as cliente:
        await cliente.post(f"/reservas/{reserva_id}/cancelar", headers=cabecalho_de(amb.gabriela))
        de_novo = await cliente.post(f"/reservas/{reserva_id}/cancelar", headers=cabecalho_de(amb.gabriela))
        inexistente = await cliente.post("/reservas/999999/cancelar", headers=cabecalho_de(amb.gabriela))

    assert (de_novo.status_code, de_novo.json()) == (409, {"detalhe": "Somente reservas confirmadas podem ser canceladas"})
    assert (inexistente.status_code, inexistente.json()) == (404, {"detalhe": "Reserva não encontrada"})


# --- Check-in da reserva ---


async def test_cliente_chega_no_horario(session: AsyncSession):
    amb = await preparar(session)
    reserva_id = await _reserva_20h30(session, amb)

    async with cliente_api(session, _relogio(20, 25)) as cliente:
        resposta = await cliente.post(f"/reservas/{reserva_id}/check-in", headers=cabecalho_de(amb.admin))
        mapa = await cliente.get("/mesas", headers=cabecalho_de(amb.gabriela))
        cancelamento = await cliente.post(f"/reservas/{reserva_id}/cancelar", headers=cabecalho_de(amb.admin))

    assert resposta.status_code == 200
    reserva, comanda = resposta.json()["reserva"], resposta.json()["comanda"]
    assert (reserva["status"], reserva["situacao"]) == ("CONCLUIDA", "CONCLUIDA")
    assert (comanda["mesa"]["numero"], comanda["status"], comanda["responsavel"]["id"]) == (4, "ABERTA", amb.admin.id)
    assert _status_da_mesa(mapa, 4) == "OCUPADA"
    assert (cancelamento.status_code, cancelamento.json()) == (
        409,
        {"detalhe": "Somente reservas confirmadas podem ser canceladas"},
    )
    logs = (await session.execute(select(LogAuditoria).order_by(LogAuditoria.id))).scalars().all()
    assert [(log.entidade, log.acao) for log in logs][-2:] == [("Reserva", "CHECK_IN"), ("Comanda", "CRIAR")]


@pytest.mark.parametrize(("hora", "minuto"), [(19, 0), (22, 0)])
async def test_check_in_antecipado_ou_atrasado(session: AsyncSession, hora: int, minuto: int):
    amb = await preparar(session)
    reserva_id = await _reserva_20h30(session, amb)

    async with cliente_api(session, _relogio(hora, minuto)) as cliente:
        resposta = await cliente.post(f"/reservas/{reserva_id}/check-in", headers=cabecalho_de(amb.gabriela))

    assert resposta.status_code == 200
    assert resposta.json()["reserva"]["status"] == "CONCLUIDA"


async def test_mesa_ainda_ocupada(session: AsyncSession):
    amb = await preparar(session)
    reserva_id = await _reserva_20h30(session, amb)

    async with cliente_api(session, _relogio(18, 0)) as cliente:
        await abrir(cliente, amb.gabriela, amb.mesas[4])
    async with cliente_api(session, _relogio(20, 25)) as cliente:
        resposta = await cliente.post(f"/reservas/{reserva_id}/check-in", headers=cabecalho_de(amb.gabriela))

    assert (resposta.status_code, resposta.json()) == (
        409,
        {"detalhe": "A mesa ainda está ocupada: encerre o atendimento anterior antes do check-in"},
    )
    assert (await _reserva_gravada(session)).status == "CONFIRMADA"
    assert await _contar(session, Comanda) == 1


async def test_check_in_com_mesa_em_manutencao(session: AsyncSession):
    amb = await preparar(session)
    reserva_id = await _reserva_20h30(session, amb)
    (await session.get(Mesa, amb.mesas[4])).em_manutencao = True
    await session.commit()

    async with cliente_api(session, _relogio(20, 25)) as cliente:
        resposta = await cliente.post(f"/reservas/{reserva_id}/check-in", headers=cabecalho_de(amb.gabriela))

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "Mesa em manutenção"})
    assert (await _reserva_gravada(session)).status == "CONFIRMADA"
    assert await _contar(session, Comanda) == 0


async def test_reserva_nao_confirmada(session: AsyncSession):
    amb = await preparar(session)
    reserva_id = await _reserva_20h30(session, amb)

    async with cliente_api(session, _relogio(20, 0)) as cliente:
        await cliente.post(f"/reservas/{reserva_id}/cancelar", headers=cabecalho_de(amb.gabriela))
        resposta = await cliente.post(f"/reservas/{reserva_id}/check-in", headers=cabecalho_de(amb.gabriela))
        inexistente = await cliente.post("/reservas/999999/check-in", headers=cabecalho_de(amb.gabriela))

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "Somente reservas confirmadas podem fazer check-in"})
    assert inexistente.status_code == 404
    assert await _contar(session, Comanda) == 0


# --- Mapa: próxima reserva ---


async def test_mapa_informa_proxima_reserva(session: AsyncSession):
    amb = await preparar(session)
    await _reserva_20h30(session, amb)

    async with cliente_api(session, _relogio(19, 0)) as cliente:
        mapa = (await cliente.get("/mesas", headers=cabecalho_de(amb.gabriela))).json()

    mesa_4 = next(m for m in mapa if m["numero"] == 4)
    assert (mesa_4["status"], mesa_4["proxima_reserva_inicio"]) == ("LIVRE", f"{DIA}T20:30:00-03:00")
    assert all(m["proxima_reserva_inicio"] is None for m in mapa if m["numero"] != 4)


# --- Acesso às reservas restrito por perfil ---


async def test_contabilidade_consulta_reservas(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session, HOJE_15H) as cliente:
        consulta = await cliente.get("/reservas", headers=cabecalho_de(amb.contabilidade))
        criacao = await reservar(cliente, amb.contabilidade, amb.mesas[4], f"{DIA}T20:30:00")
        sem_sessao = await cliente.get("/reservas")

    assert (consulta.status_code, consulta.json()) == (403, {"detalhe": "Sem permissão para esta funcionalidade"})
    assert criacao.status_code == 403
    assert sem_sessao.status_code == 401
