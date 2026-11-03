from sqlalchemy import func, select
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

    async def nomes_produtos(self, produto_ids: set[int]) -> dict[int, str]:
        resultado = await self.session.execute(select(Produto.id, Produto.nome).where(Produto.id.in_(produto_ids)))
        return dict(resultado.all())

    # --- Gestão do cardápio ---

    async def categorias(self, bloquear: bool = False) -> list[Categoria]:
        """Todas as categorias na ordem de exibição; `bloquear` trava as linhas para reordenar."""
        consulta = select(Categoria).order_by(Categoria.ordem, Categoria.nome, Categoria.id)
        if bloquear:
            consulta = consulta.with_for_update().execution_options(populate_existing=True)
        return list((await self.session.execute(consulta)).scalars())

    async def todos_produtos(self) -> list[Produto]:
        return list((await self.session.execute(select(Produto).order_by(Produto.nome))).scalars())

    async def obter_categoria(self, categoria_id: int, bloquear: bool = False) -> Categoria | None:
        consulta = select(Categoria).where(Categoria.id == categoria_id)
        if bloquear:
            consulta = consulta.with_for_update().execution_options(populate_existing=True)
        return (await self.session.execute(consulta)).scalar_one_or_none()

    async def produto_com_nome(self, nome: str, exceto_id: int | None = None) -> Produto | None:
        consulta = select(Produto).where(func.lower(Produto.nome) == nome.lower())
        if exceto_id is not None:
            consulta = consulta.where(Produto.id != exceto_id)
        return (await self.session.execute(consulta.limit(1))).scalar_one_or_none()

    async def categoria_com_nome(self, nome: str, exceto_id: int | None = None) -> Categoria | None:
        consulta = select(Categoria).where(func.lower(Categoria.nome) == nome.lower())
        if exceto_id is not None:
            consulta = consulta.where(Categoria.id != exceto_id)
        return (await self.session.execute(consulta.limit(1))).scalar_one_or_none()

    async def tem_produtos(self, categoria_id: int) -> bool:
        consulta = select(Produto.id).where(Produto.categoria_id == categoria_id).limit(1)
        return (await self.session.execute(consulta)).first() is not None
