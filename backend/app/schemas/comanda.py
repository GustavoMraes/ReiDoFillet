from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, model_validator

from app.models.enums import FormaPagamento


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


class TaxaServicoOut(BaseModel):
    aplicada: bool
    percentual: Decimal | None
    valor: Decimal


class PagamentoOut(BaseModel):
    id: int
    forma: str
    valor: Decimal
    registrado_por: str | None
    registrado_em: datetime


class ComandaOut(BaseModel):
    id: int
    mesa: MesaResumoOut
    responsavel: ResponsavelOut | None
    status: str
    aberta_em: datetime
    pre_conta_em: datetime | None
    itens: list[ItemComandaOut]
    subtotal: Decimal
    taxa_servico: TaxaServicoOut
    total: Decimal
    pago: Decimal
    restante: Decimal
    pagamentos: list[PagamentoOut]


class PreContaOut(BaseModel):
    comanda: ComandaOut
    aviso: str | None


class TaxaServicoIn(BaseModel):
    """Faixa do percentual validada no serviço, com mensagem em português."""

    aplicada: bool | None = None
    percentual: Decimal | None = None

    @model_validator(mode="after")
    def exige_alguma_alteracao(self) -> "TaxaServicoIn":
        if self.aplicada is None and self.percentual is None:
            raise ValueError("Informe se a taxa é aplicada ou o percentual")
        return self


class TransferenciaIn(BaseModel):
    mesa_id: int


class PagamentoIn(BaseModel):
    forma: FormaPagamento
    valor: Decimal


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
