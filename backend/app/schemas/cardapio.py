from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


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


# --- Gestão do cardápio (limites de texto e preço validados no serviço, com mensagens em português) ---


class ProdutoAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    categoria_id: int
    nome: str
    descricao: str | None
    preco: Decimal
    ativo: bool
    disponivel: bool


class CategoriaAdminOut(BaseModel):
    id: int
    nome: str
    ordem: int
    produtos: list[ProdutoAdminOut]


class ProdutoIn(BaseModel):
    categoria_id: int
    nome: str
    descricao: str | None = None
    preco: Decimal


class ProdutoAlteracaoIn(BaseModel):
    categoria_id: int | None = None
    nome: str | None = None
    descricao: str | None = None
    preco: Decimal | None = None
    ativo: bool | None = None

    @model_validator(mode="after")
    def exige_alguma_alteracao(self) -> "ProdutoAlteracaoIn":
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para alterar")
        return self


class DisponibilidadeIn(BaseModel):
    disponivel: bool


class CategoriaIn(BaseModel):
    nome: str


class MoverCategoriaIn(BaseModel):
    direcao: Literal["acima", "abaixo"]
