"""Representações das entidades gravadas na auditoria (dados_antes / dados_depois).

A serialização é explícita, campo a campo, para que dados sensíveis (como senha_hash)
nunca cheguem ao histórico.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class Snapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class FuncionarioSnapshot(Snapshot):
    id: int
    nome: str
    login: str
    perfil: str
    bloqueado: bool


class TentativaLoginSnapshot(Snapshot):
    """Dados de uma falha de login. Não aceita campos extras: a senha nunca entra na auditoria."""

    model_config = ConfigDict(extra="forbid")

    login: str
    motivo: str


class ConsultaSnapshot(Snapshot):
    """Filtros de uma consulta de relatório ou da auditoria (HU07: toda consulta fica registrada)."""

    model_config = ConfigDict(extra="forbid")

    inicio: date
    fim: date
    usuario_id: int | None = None
    acao: str | None = None
    entidade: str | None = None
    pagina: int | None = None


class ComandaSnapshot(Snapshot):
    id: int
    mesa_id: int
    funcionario_id: int | None
    status: str
    taxa_servico_pct: Decimal | None
    taxa_servico_aplicada: bool


class PagamentoSnapshot(Snapshot):
    id: int
    comanda_id: int
    forma: str
    valor: Decimal
    registrado_por_id: int | None


class ItemComandaSnapshot(Snapshot):
    id: int
    comanda_id: int
    produto_id: int
    quantidade: int
    observacao: str
    preco_unitario: Decimal
    status: str
    cancelado_por_id: int | None


class CategoriaSnapshot(Snapshot):
    id: int
    nome: str
    ordem: int


class ProdutoSnapshot(Snapshot):
    id: int
    categoria_id: int
    nome: str
    preco: Decimal
    ativo: bool
    disponivel: bool


class ReservaSnapshot(Snapshot):
    """Sem o telefone: dado pessoal desnecessário para o rastro de auditoria."""

    id: int
    mesa_id: int
    status: str
    inicio: datetime
    qtd_pessoas: int
    nome_cliente: str


class MesaSnapshot(Snapshot):
    id: int
    numero: int
    capacidade: int
    localizacao: str
    em_manutencao: bool
