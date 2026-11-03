from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflito, DadoInvalido, RecursoNaoEncontrado, SemPermissao
from app.core.tempo import Relogio, para_exibicao
from app.db.transacao import transacao
from app.models import Comanda, Funcionario, ItemComanda
from app.models.enums import Perfil, StatusComanda, StatusItem, StatusMesa
from app.repositories.cardapio import CardapioRepository
from app.repositories.comanda import ComandaRepository
from app.schemas.comanda import ComandaOut, ItemComandaOut, MesaResumoOut, ResponsavelOut
from app.schemas.snapshots import ComandaSnapshot, ItemComandaSnapshot
from app.services.auditoria import Acao, AuditoriaService
from app.services.mesa import MesaService

QUANTIDADE_MAXIMA = 99
TAMANHO_MAXIMO_OBSERVACAO = 200
CENTAVOS = Decimal("0.01")


def _validar_quantidade(quantidade: int) -> None:
    if not 1 <= quantidade <= QUANTIDADE_MAXIMA:
        raise DadoInvalido(f"A quantidade deve estar entre 1 e {QUANTIDADE_MAXIMA}")


def _normalizar_observacao(observacao: str) -> str:
    observacao = observacao.strip()
    if len(observacao) > TAMANHO_MAXIMO_OBSERVACAO:
        raise DadoInvalido(f"A observação deve ter no máximo {TAMANHO_MAXIMO_OBSERVACAO} caracteres")
    return observacao


class ComandaService:
    def __init__(
        self,
        session: AsyncSession,
        comandas: ComandaRepository,
        mesas: MesaService,
        cardapio: CardapioRepository,
        auditoria: AuditoriaService,
        relogio: Relogio,
    ):
        self.session = session
        self.comandas = comandas
        self.mesas = mesas
        self.cardapio = cardapio
        self.auditoria = auditoria
        self.relogio = relogio

    # --- Abertura e consulta ---

    async def abrir(self, mesa_id: int, funcionario: Funcionario) -> tuple[Comanda, bool]:
        """Abre a comanda da mesa ou devolve a comanda ativa existente. Retorna (comanda, criada)."""
        situacao = await self.mesas.situacao(mesa_id)
        if situacao is None:
            raise RecursoNaoEncontrado("Mesa não encontrada")
        existente = await self.comandas.ativa_da_mesa(mesa_id)
        if existente is not None:
            return existente, False
        if situacao.status == StatusMesa.MANUTENCAO:
            raise Conflito("Mesa em manutenção")
        if situacao.status == StatusMesa.RESERVADA:
            raise Conflito("Mesa reservada: aguarde o check-in do cliente")

        try:
            async with transacao(self.session):
                comanda = Comanda(
                    mesa_id=mesa_id,
                    funcionario_id=funcionario.id,
                    status=StatusComanda.ABERTA,
                    aberta_em=self.relogio.agora(),
                )
                self.session.add(comanda)
                await self.session.flush()
                self._auditar(funcionario, Acao.CRIAR, "Comanda", comanda.id, None, ComandaSnapshot.model_validate(comanda))
        except IntegrityError:
            # Outra abertura simultânea venceu a corrida pelo índice único: devolve a comanda dela.
            existente = await self.comandas.ativa_da_mesa(mesa_id)
            if existente is None:
                raise
            return existente, False
        return comanda, True

    async def obter(self, comanda_id: int) -> Comanda:
        comanda = await self.comandas.obter(comanda_id)
        if comanda is None:
            raise RecursoNaoEncontrado("Comanda não encontrada")
        return comanda

    async def detalhar(self, comanda: Comanda) -> ComandaOut:
        numero_mesa, nome_responsavel = await self.comandas.cabecalho(comanda)
        itens = []
        total = Decimal("0")
        for item, produto_nome in await self.comandas.itens_com_produto(comanda.id):
            subtotal = (item.preco_unitario * item.quantidade).quantize(CENTAVOS)
            if item.status != StatusItem.CANCELADO:
                total += subtotal
            itens.append(
                ItemComandaOut(
                    id=item.id,
                    produto_id=item.produto_id,
                    produto_nome=produto_nome,
                    quantidade=item.quantidade,
                    observacao=item.observacao,
                    preco_unitario=item.preco_unitario,
                    subtotal=subtotal,
                    status=item.status,
                )
            )
        return ComandaOut(
            id=comanda.id,
            mesa=MesaResumoOut(id=comanda.mesa_id, numero=numero_mesa),
            responsavel=(
                ResponsavelOut(id=comanda.funcionario_id, nome=nome_responsavel)
                if comanda.funcionario_id is not None and nome_responsavel is not None
                else None
            ),
            status=comanda.status,
            aberta_em=para_exibicao(comanda.aberta_em),
            itens=itens,
            total=total.quantize(CENTAVOS),
        )

    # --- Itens ---

    async def registrar_item(
        self, comanda_id: int, produto_id: int, quantidade: int, observacao: str, usuario: Funcionario
    ) -> Comanda:
        _validar_quantidade(quantidade)
        observacao = _normalizar_observacao(observacao)
        async with transacao(self.session):
            comanda = await self._comanda_aberta_bloqueada(comanda_id, "A comanda não está aberta para novos itens")
            produto = await self.cardapio.obter_produto(produto_id)
            if produto is None:
                raise RecursoNaoEncontrado("Produto não encontrado")
            if not (produto.ativo and produto.disponivel):
                raise Conflito("Item indisponível")

            identico = next(
                (
                    item
                    for item in await self.comandas.itens(comanda_id)
                    if item.status == StatusItem.PENDENTE
                    and item.produto_id == produto.id
                    and item.preco_unitario == produto.preco
                    and item.observacao.casefold() == observacao.casefold()
                ),
                None,
            )
            if identico is not None:
                if identico.quantidade + quantidade > QUANTIDADE_MAXIMA:
                    raise Conflito(f"A quantidade máxima por item é {QUANTIDADE_MAXIMA}")
                antes = ItemComandaSnapshot.model_validate(identico)
                identico.quantidade += quantidade
                self._auditar(usuario, Acao.ALTERAR, "ItemComanda", identico.id, antes, ItemComandaSnapshot.model_validate(identico))
            else:
                item = ItemComanda(
                    comanda_id=comanda_id,
                    produto_id=produto.id,
                    quantidade=quantidade,
                    observacao=observacao,
                    preco_unitario=produto.preco,
                    status=StatusItem.PENDENTE,
                )
                self.session.add(item)
                await self.session.flush()
                self._auditar(usuario, Acao.CRIAR, "ItemComanda", item.id, None, ItemComandaSnapshot.model_validate(item))
        return comanda

    async def alterar_item(
        self,
        comanda_id: int,
        item_id: int,
        quantidade: int | None,
        observacao: str | None,
        usuario: Funcionario,
    ) -> Comanda:
        if quantidade is not None:
            _validar_quantidade(quantidade)
        if observacao is not None:
            observacao = _normalizar_observacao(observacao)
        async with transacao(self.session):
            comanda = await self._comanda_aberta_bloqueada(comanda_id, "A comanda não está aberta para alterações")
            item = await self._item(comanda_id, item_id)
            if item.status != StatusItem.PENDENTE:
                raise Conflito("Apenas itens pendentes podem ser alterados")
            antes = ItemComandaSnapshot.model_validate(item)
            if quantidade is not None:
                item.quantidade = quantidade
            if observacao is not None:
                item.observacao = observacao
            self._auditar(usuario, Acao.ALTERAR, "ItemComanda", item.id, antes, ItemComandaSnapshot.model_validate(item))
        return comanda

    async def cancelar_item(self, comanda_id: int, item_id: int, usuario: Funcionario) -> Comanda:
        async with transacao(self.session):
            comanda = await self._comanda_aberta_bloqueada(comanda_id, "A comanda não está aberta para alterações")
            item = await self._item(comanda_id, item_id)
            if item.status == StatusItem.CANCELADO:
                raise Conflito("Item já cancelado")
            if item.status != StatusItem.PENDENTE and usuario.perfil != Perfil.ADMIN:
                raise SemPermissao("Itens enviados à cozinha só podem ser cancelados por um administrador")
            antes = ItemComandaSnapshot.model_validate(item)
            item.status = StatusItem.CANCELADO
            item.cancelado_em = self.relogio.agora()
            item.cancelado_por_id = usuario.id
            self._auditar(usuario, Acao.CANCELAR, "ItemComanda", item.id, antes, ItemComandaSnapshot.model_validate(item))
        return comanda

    # --- Auxiliares ---

    async def _comanda_aberta_bloqueada(self, comanda_id: int, mensagem_nao_aberta: str) -> Comanda:
        comanda = await self.comandas.obter_para_atualizar(comanda_id)
        if comanda is None:
            raise RecursoNaoEncontrado("Comanda não encontrada")
        if comanda.status != StatusComanda.ABERTA:
            raise Conflito(mensagem_nao_aberta)
        return comanda

    async def _item(self, comanda_id: int, item_id: int) -> ItemComanda:
        item = await self.comandas.obter_item(comanda_id, item_id)
        if item is None:
            raise RecursoNaoEncontrado("Item não encontrado")
        return item

    def _auditar(self, usuario: Funcionario, acao: Acao, entidade: str, entidade_id: int, antes, depois) -> None:
        self.auditoria.registrar(
            usuario_id=usuario.id, acao=acao, entidade=entidade, entidade_id=entidade_id, antes=antes, depois=depois
        )
