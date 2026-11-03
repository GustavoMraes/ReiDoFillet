from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflito, RecursoNaoEncontrado
from app.core.tempo import Relogio, para_exibicao
from app.db.transacao import transacao
from app.models import Funcionario
from app.models.enums import STATUS_COMANDA_ATIVA, StatusItem
from app.repositories.comanda import ComandaRepository
from app.repositories.cozinha import CozinhaRepository
from app.schemas.cozinha import ItemCozinhaOut, PainelCozinhaOut
from app.schemas.snapshots import ItemComandaSnapshot
from app.services.auditoria import Acao, AuditoriaService


class CozinhaService:
    def __init__(
        self,
        session: AsyncSession,
        cozinha: CozinhaRepository,
        comandas: ComandaRepository,
        auditoria: AuditoriaService,
        relogio: Relogio,
    ):
        self.session = session
        self.cozinha = cozinha
        self.comandas = comandas
        self.auditoria = auditoria
        self.relogio = relogio

    async def painel(self) -> PainelCozinhaOut:
        agora = self.relogio.agora()
        painel = PainelCozinhaOut(em_preparo=[], pronto=[])
        for item, mesa_numero, produto_nome in await self.cozinha.fila():
            saida = ItemCozinhaOut(
                id=item.id,
                comanda_id=item.comanda_id,
                mesa_numero=mesa_numero,
                quantidade=item.quantidade,
                produto_nome=produto_nome,
                observacao=item.observacao,
                enviado_em=para_exibicao(item.enviado_em),
                minutos_desde_envio=max(0, int((agora - item.enviado_em).total_seconds() // 60)),
            )
            (painel.em_preparo if item.status == StatusItem.EM_PREPARO else painel.pronto).append(saida)
        return painel

    async def marcar_pronto(self, item_id: int, usuario: Funcionario) -> None:
        await self._avancar(
            item_id,
            usuario,
            de=StatusItem.EM_PREPARO,
            para=StatusItem.PRONTO,
            campo_horario="pronto_em",
            acao=Acao.PRONTO,
            mensagem="Somente itens em preparo podem ser marcados como prontos",
        )

    async def marcar_entregue(self, item_id: int, usuario: Funcionario) -> None:
        await self._avancar(
            item_id,
            usuario,
            de=StatusItem.PRONTO,
            para=StatusItem.ENTREGUE,
            campo_horario="entregue_em",
            acao=Acao.ENTREGAR,
            mensagem="Somente itens prontos podem ser marcados como entregues",
        )

    async def _avancar(
        self,
        item_id: int,
        usuario: Funcionario,
        de: StatusItem,
        para: StatusItem,
        campo_horario: str,
        acao: Acao,
        mensagem: str,
    ) -> None:
        async with transacao(self.session):
            item = await self.cozinha.obter_item(item_id)
            if item is None:
                raise RecursoNaoEncontrado("Item não encontrado")
            # Mesmo protocolo das operações de comanda: bloqueia a comanda e só então lê o status do item,
            # para não cruzar com um cancelamento ou com outro toque simultâneo.
            comanda = await self.comandas.obter_para_atualizar(item.comanda_id)
            await self.session.refresh(item)
            if comanda is None or comanda.status not in STATUS_COMANDA_ATIVA:
                raise Conflito("A comanda deste item não está ativa")
            if item.status != de:
                raise Conflito(mensagem)

            antes = ItemComandaSnapshot.model_validate(item)
            item.status = para
            setattr(item, campo_horario, self.relogio.agora())
            self.auditoria.registrar(
                usuario_id=usuario.id,
                acao=acao,
                entidade="ItemComanda",
                entidade_id=item.id,
                antes=antes,
                depois=ItemComandaSnapshot.model_validate(item),
            )
