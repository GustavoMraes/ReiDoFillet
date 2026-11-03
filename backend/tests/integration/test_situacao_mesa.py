from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import RelogioFixo
from app.models import Comanda, Mesa, Reserva
from app.models.enums import StatusMesa
from app.repositories.mesa import MesaRepository
from app.services.mesa import MesaService

AGORA = datetime(2026, 11, 2, 20, 10, tzinfo=ZoneInfo("America/Sao_Paulo"))


async def _mesa(session: AsyncSession, numero: int, manutencao: bool = False) -> Mesa:
    mesa = Mesa(numero=numero, capacidade=4, localizacao="Salão", em_manutencao=manutencao)
    session.add(mesa)
    await session.flush()
    return mesa


async def test_situacao_de_cada_tipo_de_mesa(session: AsyncSession):
    livre = await _mesa(session, 1)
    ocupada = await _mesa(session, 2)
    manutencao = await _mesa(session, 3, manutencao=True)
    reservada = await _mesa(session, 4)
    session.add(Comanda(mesa_id=ocupada.id, status="ABERTA", aberta_em=AGORA - timedelta(minutes=5)))
    session.add(
        Reserva(
            mesa_id=reservada.id, nome_cliente="Ana", telefone="11999990000", qtd_pessoas=2,
            inicio=AGORA + timedelta(minutes=20), fim=AGORA + timedelta(hours=2, minutes=20), status="CONFIRMADA",
        )
    )
    await session.commit()
    servico = MesaService(MesaRepository(session), RelogioFixo(AGORA))

    situacoes = {mesa.numero: (await servico.situacao(mesa.id)).status for mesa in (livre, ocupada, manutencao, reservada)}

    assert situacoes == {
        1: StatusMesa.LIVRE,
        2: StatusMesa.OCUPADA,
        3: StatusMesa.MANUTENCAO,
        4: StatusMesa.RESERVADA,
    }


async def test_situacao_de_mesa_inexistente(session: AsyncSession):
    servico = MesaService(MesaRepository(session), RelogioFixo(AGORA))

    assert await servico.situacao(999999) is None
