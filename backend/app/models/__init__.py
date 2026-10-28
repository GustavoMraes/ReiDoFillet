"""Importa todas as entidades para que o metadata (e o Alembic) as conheça."""

from app.models.cardapio import Categoria, Produto
from app.models.comanda import Comanda, ItemComanda
from app.models.funcionario import Funcionario
from app.models.log_auditoria import LogAuditoria
from app.models.mesa import Mesa
from app.models.pagamento import Pagamento
from app.models.parametro import Parametro
from app.models.reserva import Reserva

__all__ = [
    "Categoria",
    "Comanda",
    "Funcionario",
    "ItemComanda",
    "LogAuditoria",
    "Mesa",
    "Pagamento",
    "Parametro",
    "Produto",
    "Reserva",
]
