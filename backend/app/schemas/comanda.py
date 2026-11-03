from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, model_validator


class MesaResumoOut(BaseModel):
    id: int
    numero: int


class ResponsavelOut(BaseModel):
    id: int
    nome: str


class ItemComandaOut(BaseModel):
    id: int
    produto_id: int
    produto_nome: str
    quantidade: int
    observacao: str
    preco_unitario: Decimal
    subtotal: Decimal
    status: str


class ComandaOut(BaseModel):
    id: int
    mesa: MesaResumoOut
    responsavel: ResponsavelOut | None
    status: str
    aberta_em: datetime
    itens: list[ItemComandaOut]
    total: Decimal


class CupomItemOut(BaseModel):
    quantidade: int
    produto_nome: str
    observacao: str


class CupomOut(BaseModel):
    """Cupom de um envio à cozinha: só os itens enviados nesse envio."""

    mesa_numero: int
    garcom: str
    enviado_em: datetime
    itens: list[CupomItemOut]


class EnvioOut(BaseModel):
    comanda: ComandaOut
    cupom: CupomOut


class ItemIn(BaseModel):
    """Faixas de quantidade e tamanho da observação são validados no serviço, com mensagens em português."""

    produto_id: int
    quantidade: int = 1
    observacao: str = ""


class ItemAlteracaoIn(BaseModel):
    quantidade: int | None = None
    observacao: str | None = None

    @model_validator(mode="after")
    def exige_alguma_alteracao(self) -> "ItemAlteracaoIn":
        if self.quantidade is None and self.observacao is None:
            raise ValueError("Informe a quantidade ou a observação")
        return self
