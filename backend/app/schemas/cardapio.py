from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProdutoCardapioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    descricao: str | None
    preco: Decimal
    disponivel: bool


class CategoriaCardapioOut(BaseModel):
    id: int
    nome: str
    produtos: list[ProdutoCardapioOut]
