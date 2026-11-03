from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Categoria, Produto


class CardapioRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def produtos_ativos(self) -> list[tuple[Categoria, Produto]]:
        """Produtos ativos com a categoria, já na ordem de exibição do cardápio."""
        resultado = await self.session.execute(
            select(Categoria, Produto)
            .join(Produto, Produto.categoria_id == Categoria.id)
            .where(Produto.ativo)
            .order_by(Categoria.ordem, Categoria.nome, Produto.nome)
        )
        return [(categoria, produto) for categoria, produto in resultado]

    async def obter_produto(self, produto_id: int) -> Produto | None:
        return await self.session.get(Produto, produto_id)
