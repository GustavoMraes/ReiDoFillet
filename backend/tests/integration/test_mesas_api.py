from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.config import Settings
from app.core.tempo import RelogioFixo, get_relogio
from app.db.session import get_session
from app.main import create_app
from app.models import Comanda, Mesa, Reserva
from app.repositories.funcionario import FuncionarioRepository
from app.repositories.mesa import MesaRepository
from app.services.mesa import MesaService
from scripts.seed import seed
from tests.conftest import SEGREDO_TESTE
from tests.integration.fabricas import cabecalho_de, criar_funcionario

SP = ZoneInfo("America/Sao_Paulo")
AGORA = datetime(2026, 10, 25, 20, 10, tzinfo=SP)


def _cliente(session: AsyncSession) -> AsyncClient:
    app = create_app(Settings(_env_file=None, jwt_secret=SEGREDO_TESTE))
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_relogio] = lambda: RelogioFixo(AGORA)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_mapa_com_mesas_do_seed_e_status_calculados(session: AsyncSession):
    await seed(session)
    mesas = {m.numero: m.id for m in (await MesaRepository(session).listar())}
    session.add_all(
        [
            Comanda(mesa_id=mesas[3], status="ABERTA", aberta_em=AGORA - timedelta(minutes=18)),
            Comanda(mesa_id=mesas[7], status="PRE_CONTA", aberta_em=AGORA - timedelta(minutes=52)),
            Comanda(mesa_id=mesas[5], status="FECHADA", aberta_em=AGORA - timedelta(hours=2)),
            Reserva(
                mesa_id=mesas[4], nome_cliente="Ana", telefone="11999990000", qtd_pessoas=2,
                inicio=datetime(2026, 10, 25, 20, 30, tzinfo=SP), fim=datetime(2026, 10, 25, 22, 30, tzinfo=SP),
                status="CONFIRMADA",
            ),
            Reserva(
                mesa_id=mesas[8], nome_cliente="Bia", telefone="11999990001", qtd_pessoas=4,
                inicio=datetime(2026, 10, 25, 20, 30, tzinfo=SP), fim=datetime(2026, 10, 25, 22, 30, tzinfo=SP),
                status="CANCELADA",
            ),
            Reserva(
                mesa_id=mesas[2], nome_cliente="Caio", telefone="11999990002", qtd_pessoas=4,
                inicio=datetime(2026, 10, 25, 20, 0, tzinfo=SP), fim=datetime(2026, 10, 25, 22, 0, tzinfo=SP),
                status="CONCLUIDA",
            ),
        ]
    )
    await session.commit()
    gabriela = await FuncionarioRepository(session).obter_por_login("gabriela")

    async with _cliente(session) as cliente:
        resposta = await cliente.get("/mesas", headers=cabecalho_de(gabriela))

    assert resposta.status_code == 200
    mapa = resposta.json()
    assert [m["numero"] for m in mapa] == [1, 2, 3, 4, 5, 6, 7, 8]
    status = {m["numero"]: m["status"] for m in mapa}
    assert status == {
        1: "LIVRE",
        2: "LIVRE",  # reserva CONCLUIDA não bloqueia
        3: "OCUPADA",
        4: "RESERVADA",
        5: "LIVRE",  # comanda FECHADA não ocupa
        6: "MANUTENCAO",
        7: "AGUARDANDO_PAGAMENTO",
        8: "LIVRE",  # reserva CANCELADA não bloqueia
    }
    por_numero = {m["numero"]: m for m in mapa}
    assert por_numero[3]["minutos_atendimento"] == 18
    assert por_numero[7]["minutos_atendimento"] == 52
    assert por_numero[4]["reserva_inicio"].startswith("2026-10-25T20:30:00") and por_numero[4]["reserva_inicio"].endswith("-03:00")
    assert por_numero[1]["minutos_atendimento"] is None and por_numero[1]["reserva_inicio"] is None


async def test_mapa_sem_mesas_retorna_lista_vazia(session: AsyncSession):
    funcionario = await criar_funcionario(session, "gabriela")

    async with _cliente(session) as cliente:
        resposta = await cliente.get("/mesas", headers=cabecalho_de(funcionario))

    assert resposta.status_code == 200
    assert resposta.json() == []


@pytest.mark.parametrize(("perfil", "status_esperado"), [("FUNCIONARIO", 200), ("ADMIN", 200), ("CONTABILIDADE", 403)])
async def test_acesso_ao_mapa_por_perfil(session: AsyncSession, perfil: str, status_esperado: int):
    usuario = await criar_funcionario(session, "usuario", perfil=perfil)

    async with _cliente(session) as cliente:
        resposta = await cliente.get("/mesas", headers=cabecalho_de(usuario))

    assert resposta.status_code == status_esperado


async def test_mapa_sem_sessao(session: AsyncSession):
    async with _cliente(session) as cliente:
        resposta = await cliente.get("/mesas")

    assert resposta.status_code == 401


async def test_mapa_usa_no_maximo_tres_consultas(session: AsyncSession, engine: AsyncEngine):
    await seed(session)
    consultas = []

    def contar(conn, cursor, statement, *args):
        consultas.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", contar)
    try:
        await MesaService(MesaRepository(session), RelogioFixo(AGORA)).mapa()
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", contar)

    assert len(consultas) <= 3
