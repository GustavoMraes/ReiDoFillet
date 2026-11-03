from datetime import date, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflito, DadoInvalido, RecursoNaoEncontrado
from app.core.tempo import Relogio, para_exibicao
from app.db.transacao import transacao
from app.models import Comanda, Funcionario, Reserva
from app.models.enums import StatusReserva
from app.repositories.mesa import MesaRepository
from app.repositories.reserva import ReservaRepository
from app.schemas.comanda import MesaResumoOut
from app.schemas.reserva import ReservaOut
from app.schemas.snapshots import ReservaSnapshot
from app.services.auditoria import Acao, AuditoriaService
from app.services.comanda import ComandaService
from app.services.reserva_tempo import DURACAO_RESERVA, hora_curta, intervalo_do_dia, normalizar_inicio, situacao

TAMANHO_MAXIMO_NOME = 100
TELEFONE_MINIMO, TELEFONE_MAXIMO = 8, 20
PESSOAS_MAXIMO = 50
MESA_OCUPADA = "A mesa ainda está ocupada: encerre o atendimento anterior antes do check-in"


def _validar(nome_cliente: str, telefone: str, qtd_pessoas: int) -> tuple[str, str]:
    nome_cliente, telefone = nome_cliente.strip(), telefone.strip()
    if not nome_cliente:
        raise DadoInvalido("Informe o nome do cliente")
    if len(nome_cliente) > TAMANHO_MAXIMO_NOME:
        raise DadoInvalido(f"O nome do cliente deve ter no máximo {TAMANHO_MAXIMO_NOME} caracteres")
    if not TELEFONE_MINIMO <= len(telefone) <= TELEFONE_MAXIMO:
        raise DadoInvalido(f"O telefone deve ter de {TELEFONE_MINIMO} a {TELEFONE_MAXIMO} caracteres")
    if not 1 <= qtd_pessoas <= PESSOAS_MAXIMO:
        raise DadoInvalido(f"A quantidade de pessoas deve estar entre 1 e {PESSOAS_MAXIMO}")
    return nome_cliente, telefone


class ReservaService:
    def __init__(
        self,
        session: AsyncSession,
        reservas: ReservaRepository,
        mesas: MesaRepository,
        comandas: ComandaService,
        auditoria: AuditoriaService,
        relogio: Relogio,
    ):
        self.session = session
        self.reservas = reservas
        self.mesas = mesas
        self.comandas = comandas
        self.auditoria = auditoria
        self.relogio = relogio

    async def criar(
        self, mesa_id: int, nome_cliente: str, telefone: str, qtd_pessoas: int, inicio: datetime, usuario: Funcionario
    ) -> tuple[Reserva, str | None]:
        """Cria a reserva CONFIRMADA. Devolve um aviso (não bloqueia) se as pessoas excederem a capacidade."""
        nome_cliente, telefone = _validar(nome_cliente, telefone, qtd_pessoas)
        inicio = normalizar_inicio(inicio)
        if inicio <= self.relogio.agora():
            raise DadoInvalido("O horário da reserva deve ser no futuro")
        fim = inicio + DURACAO_RESERVA

        async with transacao(self.session):
            # O bloqueio da mesa serializa criações simultâneas: a segunda enxerga a primeira.
            mesa = await self.mesas.obter_para_atualizar(mesa_id)
            if mesa is None:
                raise RecursoNaoEncontrado("Mesa não encontrada")
            if mesa.em_manutencao:
                raise Conflito("Mesa em manutenção")
            existente = await self.reservas.conflitante(mesa_id, inicio, fim)
            if existente is not None:
                raise Conflito(f"A mesa já tem reserva às {hora_curta(existente.inicio)} neste período")

            reserva = Reserva(
                mesa_id=mesa_id,
                nome_cliente=nome_cliente,
                telefone=telefone,
                qtd_pessoas=qtd_pessoas,
                inicio=inicio,
                fim=fim,
                status=StatusReserva.CONFIRMADA,
                criado_por_id=usuario.id,
            )
            self.session.add(reserva)
            await self.session.flush()
            self._auditar(usuario, Acao.CRIAR, reserva.id, None, ReservaSnapshot.model_validate(reserva))
            capacidade = mesa.capacidade

        aviso = (
            f"Atenção: {qtd_pessoas} pessoas excedem a capacidade da mesa ({capacidade} lugares)."
            if qtd_pessoas > capacidade
            else None
        )
        return reserva, aviso

    async def listar(self, dia: date | None) -> list[ReservaOut]:
        agora = self.relogio.agora()
        dia = dia or para_exibicao(agora).date()
        return [self._saida(reserva, numero, agora) for reserva, numero in await self.reservas.do_periodo(*intervalo_do_dia(dia))]

    async def cancelar(self, reserva_id: int, usuario: Funcionario) -> Reserva:
        async with transacao(self.session):
            reserva = await self._reserva_confirmada(reserva_id, "Somente reservas confirmadas podem ser canceladas")
            antes = ReservaSnapshot.model_validate(reserva)
            reserva.status = StatusReserva.CANCELADA
            reserva.cancelado_por_id = usuario.id
            self._auditar(usuario, Acao.CANCELAR, reserva.id, antes, ReservaSnapshot.model_validate(reserva))
        return reserva

    async def check_in(self, reserva_id: int, usuario: Funcionario) -> tuple[Reserva, Comanda]:
        """Conclui a reserva e abre a comanda da mesa na mesma transação: as duas coisas ou nenhuma."""
        try:
            async with transacao(self.session):
                reserva = await self._reserva_confirmada(reserva_id, "Somente reservas confirmadas podem fazer check-in")
                mesa = await self.mesas.obter_para_atualizar(reserva.mesa_id)
                if mesa.em_manutencao:
                    raise Conflito("Mesa em manutenção")
                if await self.mesas.comandas_ativas(reserva.mesa_id):
                    raise Conflito(MESA_OCUPADA)
                antes = ReservaSnapshot.model_validate(reserva)
                reserva.status = StatusReserva.CONCLUIDA
                self._auditar(usuario, Acao.CHECK_IN, reserva.id, antes, ReservaSnapshot.model_validate(reserva))
                comanda = await self.comandas.criar_na_transacao(reserva.mesa_id, usuario)
        except IntegrityError:
            # Uma abertura comum de comanda venceu a corrida pelo índice único: nada foi gravado.
            raise Conflito(MESA_OCUPADA) from None
        return reserva, comanda

    async def saida(self, reserva: Reserva) -> ReservaOut:
        return self._saida(reserva, await self.reservas.numero_da_mesa(reserva.mesa_id), self.relogio.agora())

    def _saida(self, reserva: Reserva, numero_mesa: int, agora: datetime) -> ReservaOut:
        return ReservaOut(
            id=reserva.id,
            mesa=MesaResumoOut(id=reserva.mesa_id, numero=numero_mesa),
            nome_cliente=reserva.nome_cliente,
            telefone=reserva.telefone,
            qtd_pessoas=reserva.qtd_pessoas,
            inicio=para_exibicao(reserva.inicio),
            fim=para_exibicao(reserva.fim),
            status=reserva.status,
            situacao=situacao(reserva.status, reserva.inicio, agora),
        )

    async def _reserva_confirmada(self, reserva_id: int, mensagem: str) -> Reserva:
        reserva = await self.reservas.obter_para_atualizar(reserva_id)
        if reserva is None:
            raise RecursoNaoEncontrado("Reserva não encontrada")
        if reserva.status != StatusReserva.CONFIRMADA:
            raise Conflito(mensagem)
        return reserva

    def _auditar(self, usuario: Funcionario, acao: Acao, reserva_id: int, antes, depois) -> None:
        self.auditoria.registrar(
            usuario_id=usuario.id, acao=acao, entidade="Reserva", entidade_id=reserva_id, antes=antes, depois=depois
        )
