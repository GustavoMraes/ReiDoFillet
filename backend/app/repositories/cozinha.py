from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comanda, ItemComanda, Mesa, Produto
from app.models.enums import StatusItem


class CozinhaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fila(self) -> list[tuple[ItemComanda, int, str]]:
        """Itens em preparo ou prontos, com número da mesa e nome do produto, em ordem de envio."""
        resultado = await self.session.execute(
            select(ItemComanda, Mesa.numero, Produto.nome)
            .join(Comanda, Comanda.id == ItemComanda.comanda_id)
            .join(Mesa, Mesa.id == Comanda.mesa_id)
            .join(Produto, Produto.id == ItemComanda.produto_id)
            .where(ItemComanda.status.in_((StatusItem.EM_PREPARO, StatusItem.PRONTO)))
            .order_by(ItemComanda.enviado_em, ItemComanda.id)
        )
        return [(item, numero, nome) for item, numero, nome in resultado]

    async def obter_item(self, item_id: int) -> ItemComanda | None:
        return await self.session.get(ItemComanda, item_id)
