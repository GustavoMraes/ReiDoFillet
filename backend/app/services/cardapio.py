from app.repositories.cardapio import CardapioRepository
from app.schemas.cardapio import CategoriaCardapioOut, ProdutoCardapioOut


class CardapioService:
    def __init__(self, repositorio: CardapioRepository):
        self.repositorio = repositorio

    async def cardapio(self) -> list[CategoriaCardapioOut]:
        """Categorias na ordem definida, só com produtos ativos; categorias sem produtos ativos ficam de fora."""
        categorias: dict[int, CategoriaCardapioOut] = {}
        for categoria, produto in await self.repositorio.produtos_ativos():
            grupo = categorias.setdefault(
                categoria.id, CategoriaCardapioOut(id=categoria.id, nome=categoria.nome, produtos=[])
            )
            grupo.produtos.append(ProdutoCardapioOut.model_validate(produto))
        return list(categorias.values())
