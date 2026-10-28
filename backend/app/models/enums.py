from enum import StrEnum

from sqlalchemy import CheckConstraint


class Perfil(StrEnum):
    FUNCIONARIO = "FUNCIONARIO"
    ADMIN = "ADMIN"
    CONTABILIDADE = "CONTABILIDADE"


class StatusReserva(StrEnum):
    CONFIRMADA = "CONFIRMADA"
    CONCLUIDA = "CONCLUIDA"
    CANCELADA = "CANCELADA"
    # NAO_COMPARECEU não é armazenado: é derivado na leitura.


class StatusComanda(StrEnum):
    ABERTA = "ABERTA"
    PRE_CONTA = "PRE_CONTA"
    FECHADA = "FECHADA"
    CANCELADA = "CANCELADA"


STATUS_COMANDA_ATIVA = (StatusComanda.ABERTA, StatusComanda.PRE_CONTA)


class StatusItem(StrEnum):
    PENDENTE = "PENDENTE"
    EM_PREPARO = "EM_PREPARO"
    PRONTO = "PRONTO"
    ENTREGUE = "ENTREGUE"
    CANCELADO = "CANCELADO"


class FormaPagamento(StrEnum):
    PIX = "PIX"
    CREDITO = "CREDITO"
    DEBITO = "DEBITO"
    DINHEIRO = "DINHEIRO"


class StatusMesa(StrEnum):
    """Status calculado na leitura; não existe coluna correspondente."""

    MANUTENCAO = "MANUTENCAO"
    OCUPADA = "OCUPADA"
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    RESERVADA = "RESERVADA"
    LIVRE = "LIVRE"


def check_enum(coluna: str, enum: type[StrEnum]) -> CheckConstraint:
    """Enums são gravados como texto e validados por CHECK (mais simples de migrar que ENUM nativo)."""
    valores = ", ".join(f"'{membro.value}'" for membro in enum)
    return CheckConstraint(f"{coluna} IN ({valores})", name=f"{coluna}_valido")
