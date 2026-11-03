from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comanda, Funcionario, ItemComanda, Mesa, Produto
from app.models.enums import STATUS_COMANDA_ATIVA


class ComandaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def obter(self, comanda_id: int) -> Comanda | None:
        return await self.session.get(Comanda, comanda_id)

    async def obter_para_atualizar(self, comanda_id: int) -> Comanda | None:
        """Bloqueia a linha da comanda até o fim da transação (SELECT ... FOR UPDATE)."""
        resultado = await self.session.execute(
            select(Comanda).where(Comanda.id == comanda_id).with_for_update().execution_options(populate_existing=True)
        )
        return resultado.scalar_one_or_none()

    async def ativa_da_mesa(self, mesa_id: int) -> Comanda | None:
        resultado = await self.session.execute(
            select(Comanda).where(Comanda.mesa_id == mesa_id, Comanda.status.in_(STATUS_COMANDA_ATIVA))
        )
        return resultado.scalar_one_or_none()

    async def cabecalho(self, comanda: Comanda) -> tuple[int, str | None]:
        """Número da mesa e nome do funcionário responsável."""
        numero = (await self.session.execute(select(Mesa.numero).where(Mesa.id == comanda.mesa_id))).scalar_one()
        nome = None
        if comanda.funcionario_id is not None:
            nome = (
                await self.session.execute(select(Funcionario.nome).where(Funcionario.id == comanda.funcionario_id))
            ).scalar_one_or_none()
        return numero, nome

    async def itens_com_produto(self, comanda_id: int) -> list[tuple[ItemComanda, str]]:
        """Itens da comanda com o nome do produto, em ordem de lançamento."""
        resultado = await self.session.execute(
            select(ItemComanda, Produto.nome)
            .join(Produto, Produto.id == ItemComanda.produto_id)
            .where(ItemComanda.comanda_id == comanda_id)
            .order_by(ItemComanda.criado_em, ItemComanda.id)
        )
        return [(item, nome) for item, nome in resultado]

    async def itens(self, comanda_id: int) -> list[ItemComanda]:
        resultado = await self.session.execute(
            select(ItemComanda).where(ItemComanda.comanda_id == comanda_id).order_by(ItemComanda.id)
        )
        return list(resultado.scalars())

    async def obter_item(self, comanda_id: int, item_id: int) -> ItemComanda | None:
        item = await self.session.get(ItemComanda, item_id)
        return item if item is not None and item.comanda_id == comanda_id else None
