from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflito, DadoInvalido, RecursoNaoEncontrado, SemPermissao
from app.core.tempo import Relogio, para_exibicao
from app.db.transacao import transacao
from app.models import Comanda, Funcionario, ItemComanda, Pagamento
from app.models.enums import STATUS_COMANDA_ATIVA, FormaPagamento, Perfil, StatusComanda, StatusItem, StatusMesa
from app.repositories.cardapio import CardapioRepository
from app.repositories.comanda import ComandaRepository
from app.schemas.comanda import (
    ComandaOut,
    CupomItemOut,
    CupomOut,
    ItemComandaOut,
    MesaResumoOut,
    PagamentoOut,
    ResponsavelOut,
    TaxaServicoOut,
)
from app.schemas.snapshots import ComandaSnapshot, ItemComandaSnapshot, PagamentoSnapshot
from app.services.auditoria import Acao, AuditoriaService
from app.services.financeiro import ResumoFinanceiro, calcular, em_centavos, em_reais
from app.services.mesa import MesaService

QUANTIDADE_MAXIMA = 99
TAMANHO_MAXIMO_OBSERVACAO = 200
STATUS_ITEM_NAO_ENTREGUE = (StatusItem.PENDENTE, StatusItem.EM_PREPARO, StatusItem.PRONTO)


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
        itens_com_produto = await self.comandas.itens_com_produto(comanda.id)
        pagamentos = await self.comandas.pagamentos_com_responsavel(comanda.id)
        resumo = calcular(
            comanda.status,
            [(item.preco_unitario, item.quantidade, item.status) for item, _ in itens_com_produto],
            comanda.taxa_servico_pct,
            comanda.taxa_servico_aplicada,
            [pagamento.valor for pagamento, _ in pagamentos],
        )
        itens = []
        for item, produto_nome in itens_com_produto:
            subtotal = em_centavos(item.preco_unitario * item.quantidade)
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
            pre_conta_em=para_exibicao(comanda.pre_conta_em) if comanda.pre_conta_em else None,
            itens=itens,
            subtotal=resumo.subtotal,
            taxa_servico=TaxaServicoOut(
                aplicada=resumo.taxa_aplicada, percentual=resumo.taxa_percentual, valor=resumo.taxa_valor
            ),
            total=resumo.total,
            pago=resumo.pago,
            restante=resumo.restante,
            pagamentos=[
                PagamentoOut(
                    id=pagamento.id,
                    forma=pagamento.forma,
                    valor=pagamento.valor,
                    registrado_por=nome,
                    registrado_em=para_exibicao(pagamento.registrado_em),
                )
                for pagamento, nome in pagamentos
            ],
        )

    # --- Itens ---

    async def registrar_item(
        self, comanda_id: int, produto_id: int, quantidade: int, observacao: str, usuario: Funcionario
    ) -> Comanda:
        _validar_quantidade(quantidade)
        observacao = _normalizar_observacao(observacao)
        async with transacao(self.session):
            comanda = await self._comanda_ativa_bloqueada(comanda_id, "A comanda não está aberta para novos itens")
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
            self._invalidar_pre_conta(comanda, usuario)
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
            comanda = await self._comanda_ativa_bloqueada(comanda_id, "A comanda não está aberta para alterações")
            item = await self._item(comanda_id, item_id)
            if item.status != StatusItem.PENDENTE:
                raise Conflito("Apenas itens pendentes podem ser alterados")
            antes = ItemComandaSnapshot.model_validate(item)
            if quantidade is not None:
                item.quantidade = quantidade
            if observacao is not None:
                item.observacao = observacao
            self._auditar(usuario, Acao.ALTERAR, "ItemComanda", item.id, antes, ItemComandaSnapshot.model_validate(item))
            self._invalidar_pre_conta(comanda, usuario)
        return comanda

    async def cancelar_item(self, comanda_id: int, item_id: int, usuario: Funcionario) -> Comanda:
        async with transacao(self.session):
            comanda = await self._comanda_ativa_bloqueada(comanda_id, "A comanda não está aberta para alterações")
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
            self._invalidar_pre_conta(comanda, usuario)
        return comanda

    # --- Envio à cozinha ---

    async def enviar(self, comanda_id: int, usuario: Funcionario) -> tuple[Comanda, CupomOut]:
        """Envia todos os itens pendentes de uma vez, com um único horário de envio (o lote do cupom)."""
        async with transacao(self.session):
            comanda = await self._comanda_aberta_bloqueada(comanda_id, "A comanda não está aberta para envio")
            pendentes = [i for i in await self.comandas.itens(comanda_id) if i.status == StatusItem.PENDENTE]
            if not pendentes:
                raise Conflito("Não há itens pendentes para enviar")

            enviado_em = self.relogio.agora()
            for item in pendentes:
                antes = ItemComandaSnapshot.model_validate(item)
                item.status = StatusItem.EM_PREPARO
                item.enviado_em = enviado_em
                self._auditar(usuario, Acao.ENVIAR, "ItemComanda", item.id, antes, ItemComandaSnapshot.model_validate(item))

            numero_mesa, _ = await self.comandas.cabecalho(comanda)
            nomes = await self.cardapio.nomes_produtos({item.produto_id for item in pendentes})
            cupom = CupomOut(
                mesa_numero=numero_mesa,
                garcom=usuario.nome,
                enviado_em=para_exibicao(enviado_em),
                itens=[
                    CupomItemOut(quantidade=i.quantidade, produto_nome=nomes[i.produto_id], observacao=i.observacao)
                    for i in pendentes
                ],
            )
        return comanda, cupom

    # --- Pré-conta e ciclo da comanda ---

    async def gerar_pre_conta(self, comanda_id: int, usuario: Funcionario) -> tuple[Comanda, str | None]:
        """Passa a comanda a PRE_CONTA. Devolve um aviso se ainda houver itens não entregues (não bloqueia)."""
        async with transacao(self.session):
            comanda = await self._comanda_aberta_bloqueada(
                comanda_id, "A pré-conta só pode ser gerada para uma comanda aberta"
            )
            ativos = [i for i in await self.comandas.itens(comanda_id) if i.status != StatusItem.CANCELADO]
            if not ativos:
                raise Conflito("A comanda não tem itens para a pré-conta")

            antes = ComandaSnapshot.model_validate(comanda)
            # Só a primeira pré-conta copia a taxa padrão; as seguintes mantêm a escolha anterior.
            if comanda.taxa_servico_pct is None:
                comanda.taxa_servico_pct = await self.comandas.taxa_servico_padrao()
            comanda.status = StatusComanda.PRE_CONTA
            comanda.pre_conta_em = self.relogio.agora()
            self._auditar(usuario, Acao.PRE_CONTA, "Comanda", comanda.id, antes, ComandaSnapshot.model_validate(comanda))

            nao_entregues = sum(1 for i in ativos if i.status in STATUS_ITEM_NAO_ENTREGUE)
        aviso = (
            f"Atenção: {nao_entregues} item(ns) ainda não entregue(s) (pendente, em preparo ou pronto)."
            if nao_entregues
            else None
        )
        return comanda, aviso

    async def cancelar_comanda(self, comanda_id: int, usuario: Funcionario) -> Comanda:
        """Libera uma mesa aberta por engano: só sem itens ativos e sem pagamentos."""
        async with transacao(self.session):
            comanda = await self._comanda_ativa_bloqueada(comanda_id, "A comanda não pode mais ser cancelada")
            if any(i.status != StatusItem.CANCELADO for i in await self.comandas.itens(comanda_id)):
                raise Conflito("Cancele os itens antes de cancelar a comanda")
            if await self.comandas.pagamentos(comanda_id):
                raise Conflito("Remova os pagamentos antes de cancelar a comanda")
            antes = ComandaSnapshot.model_validate(comanda)
            comanda.status = StatusComanda.CANCELADA
            comanda.fechada_em = self.relogio.agora()
            self._auditar(usuario, Acao.CANCELAR, "Comanda", comanda.id, antes, ComandaSnapshot.model_validate(comanda))
        return comanda

    # --- Taxa de serviço e pagamentos ---

    async def alterar_taxa_servico(
        self, comanda_id: int, aplicada: bool | None, percentual: Decimal | None, usuario: Funcionario
    ) -> Comanda:
        if percentual is not None and not Decimal("0") <= percentual <= Decimal("100"):
            raise DadoInvalido("O percentual da taxa de serviço deve estar entre 0 e 100")
        async with transacao(self.session):
            comanda = await self._comanda_bloqueada(
                comanda_id, (StatusComanda.PRE_CONTA,), "A taxa de serviço só pode ser alterada na pré-conta"
            )
            novo_percentual = em_centavos(percentual) if percentual is not None else comanda.taxa_servico_pct
            nova_aplicada = aplicada if aplicada is not None else comanda.taxa_servico_aplicada
            resumo = await self._resumo(comanda, percentual=novo_percentual, aplicada=nova_aplicada)
            if resumo.total < resumo.pago:
                raise Conflito(f"O total não pode ficar menor que o valor já pago ({em_reais(resumo.pago)})")

            antes = ComandaSnapshot.model_validate(comanda)
            comanda.taxa_servico_pct = novo_percentual
            comanda.taxa_servico_aplicada = nova_aplicada
            self._auditar(usuario, Acao.ALTERAR, "Comanda", comanda.id, antes, ComandaSnapshot.model_validate(comanda))
            if resumo.pago > 0 and resumo.restante == 0:
                self._fechar(comanda, usuario)
        return comanda

    async def registrar_pagamento(
        self, comanda_id: int, forma: FormaPagamento, valor: Decimal, usuario: Funcionario
    ) -> Comanda:
        if valor <= 0:
            raise DadoInvalido("O valor do pagamento deve ser maior que zero")
        valor = em_centavos(valor)
        async with transacao(self.session):
            comanda = await self._comanda_bloqueada(
                comanda_id, (*STATUS_COMANDA_ATIVA,), "A comanda já está encerrada"
            )
            if comanda.status != StatusComanda.PRE_CONTA:
                raise Conflito("Gere a pré-conta antes de registrar pagamentos")
            resumo = await self._resumo(comanda)
            if valor > resumo.restante:
                raise Conflito(f"O valor excede o restante a pagar ({em_reais(resumo.restante)})")

            pagamento = Pagamento(
                comanda_id=comanda.id,
                forma=forma,
                valor=valor,
                registrado_por_id=usuario.id,
                registrado_em=self.relogio.agora(),
            )
            self.session.add(pagamento)
            await self.session.flush()
            self._auditar(usuario, Acao.PAGAR, "Pagamento", pagamento.id, None, PagamentoSnapshot.model_validate(pagamento))
            if valor == resumo.restante:
                self._fechar(comanda, usuario)
        return comanda

    async def remover_pagamento(self, comanda_id: int, pagamento_id: int, usuario: Funcionario) -> Comanda:
        async with transacao(self.session):
            comanda = await self.comandas.obter_para_atualizar(comanda_id)
            if comanda is None:
                raise RecursoNaoEncontrado("Comanda não encontrada")
            pagamento = await self.comandas.obter_pagamento(comanda_id, pagamento_id)
            if pagamento is None:
                raise RecursoNaoEncontrado("Pagamento não encontrado")
            if comanda.status not in STATUS_COMANDA_ATIVA:
                raise Conflito("Pagamentos de comanda fechada não podem ser removidos")
            antes = PagamentoSnapshot.model_validate(pagamento)
            await self.session.delete(pagamento)
            self._auditar(usuario, Acao.REMOVER_PAGAMENTO, "Pagamento", pagamento_id, antes, None)
        return comanda

    # --- Auxiliares ---

    async def _comanda_bloqueada(self, comanda_id: int, permitidos: tuple[StatusComanda, ...], mensagem: str) -> Comanda:
        comanda = await self.comandas.obter_para_atualizar(comanda_id)
        if comanda is None:
            raise RecursoNaoEncontrado("Comanda não encontrada")
        if comanda.status not in permitidos:
            raise Conflito(mensagem)
        return comanda

    async def _comanda_aberta_bloqueada(self, comanda_id: int, mensagem_nao_aberta: str) -> Comanda:
        return await self._comanda_bloqueada(comanda_id, (StatusComanda.ABERTA,), mensagem_nao_aberta)

    async def _comanda_ativa_bloqueada(self, comanda_id: int, mensagem: str) -> Comanda:
        return await self._comanda_bloqueada(comanda_id, STATUS_COMANDA_ATIVA, mensagem)

    def _invalidar_pre_conta(self, comanda: Comanda, usuario: Funcionario) -> None:
        """A pré-conta é um retrato: qualquer mudança nos itens devolve a comanda para ABERTA."""
        if comanda.status != StatusComanda.PRE_CONTA:
            return
        antes = ComandaSnapshot.model_validate(comanda)
        comanda.status = StatusComanda.ABERTA
        comanda.pre_conta_em = None
        self._auditar(usuario, Acao.ALTERAR, "Comanda", comanda.id, antes, ComandaSnapshot.model_validate(comanda))

    def _fechar(self, comanda: Comanda, usuario: Funcionario) -> None:
        antes = ComandaSnapshot.model_validate(comanda)
        comanda.status = StatusComanda.FECHADA
        comanda.fechada_em = self.relogio.agora()
        self._auditar(usuario, Acao.ALTERAR, "Comanda", comanda.id, antes, ComandaSnapshot.model_validate(comanda))

    async def _resumo(
        self, comanda: Comanda, percentual: Decimal | None = None, aplicada: bool | None = None
    ) -> ResumoFinanceiro:
        """Resumo atual, ou com uma taxa hipotética (para validar a mudança antes de aplicá-la)."""
        return calcular(
            comanda.status,
            [(i.preco_unitario, i.quantidade, i.status) for i in await self.comandas.itens(comanda.id)],
            percentual if percentual is not None else comanda.taxa_servico_pct,
            aplicada if aplicada is not None else comanda.taxa_servico_aplicada,
            [p.valor for p in await self.comandas.pagamentos(comanda.id)],
        )

    async def _item(self, comanda_id: int, item_id: int) -> ItemComanda:
        item = await self.comandas.obter_item(comanda_id, item_id)
        if item is None:
            raise RecursoNaoEncontrado("Item não encontrado")
        return item

    def _auditar(self, usuario: Funcionario, acao: Acao, entidade: str, entidade_id: int, antes, depois) -> None:
        self.auditoria.registrar(
            usuario_id=usuario.id, acao=acao, entidade=entidade, entidade_id=entidade_id, antes=antes, depois=depois
        )
