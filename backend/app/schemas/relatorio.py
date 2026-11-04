from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from app.models.enums import FormaPagamento


class PeriodoOut(BaseModel):
    inicio: date
    fim: date


# --- Operacional ---


class SituacoesOut(BaseModel):
    em_aberto: int
    fechadas: int
    canceladas: int
    total: int


class ProdutoVendidoOut(BaseModel):
    produto_id: int
    nome: str
    quantidade: int
    valor: Decimal


class MovimentoDiaOut(BaseModel):
    data: date
    comandas: int
    faturamento: Decimal


class MovimentoHoraOut(BaseModel):
    hora: int
    comandas: int


class RelatorioOperacionalOut(BaseModel):
    periodo: PeriodoOut
    comandas: SituacoesOut
    faturamento: Decimal
    ticket_medio: Decimal | None
    tempo_medio_minutos: int | None
    produtos: list[ProdutoVendidoOut]
    por_dia: list[MovimentoDiaOut]
    por_hora: list[MovimentoHoraOut]


# --- Financeiro ---


class ValorPorFormaOut(BaseModel):
    forma: FormaPagamento
    valor: Decimal


class ComandaFechadaOut(BaseModel):
    id: int
    mesa_numero: int
    responsavel: str | None
    aberta_em: datetime
    fechada_em: datetime
    subtotal: Decimal
    taxa_servico: Decimal
    total: Decimal
    pagamentos: list[ValorPorFormaOut]


class TotaisFinanceirosOut(BaseModel):
    comandas: int
    subtotal: Decimal
    taxa_servico: Decimal
    total: Decimal
    por_forma: list[ValorPorFormaOut]


class RelatorioFinanceiroOut(BaseModel):
    periodo: PeriodoOut
    totais: TotaisFinanceirosOut
    comandas: list[ComandaFechadaOut]


# --- Auditoria ---


class RegistroAuditoriaOut(BaseModel):
    id: int
    criado_em: datetime
    usuario_id: int | None
    usuario: str | None  # None = operação do sistema
    acao: str
    entidade: str
    entidade_id: str
    dados_antes: dict[str, Any] | None
    dados_depois: dict[str, Any] | None


class PaginaAuditoriaOut(BaseModel):
    registros: list[RegistroAuditoriaOut]
    total: int
    pagina: int
    paginas: int


class UsuarioOpcaoOut(BaseModel):
    id: int
    nome: str


class OpcoesAuditoriaOut(BaseModel):
    usuarios: list[UsuarioOpcaoOut]
    acoes: list[str]
    entidades: list[str]
