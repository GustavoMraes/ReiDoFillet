"""dados: itens não entregues de comandas fechadas passam a ENTREGUE

Comandas fechadas antes da entrega automática no fechamento deixaram itens presos no painel da cozinha.
Cada item corrigido ganha um registro de auditoria ENTREGAR feito pelo sistema (usuario_id nulo), com o
horário de fechamento da comanda como horário de entrega.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-03
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ITENS_PRESOS = """
    FROM item_comanda i
    JOIN comanda c ON c.id = i.comanda_id
    WHERE c.status = 'FECHADA' AND i.status IN ('PENDENTE', 'EM_PREPARO', 'PRONTO')
"""


def _snapshot(status: str) -> str:
    """Mesmo formato do ItemComandaSnapshot gravado pela aplicação."""
    return f"""jsonb_build_object(
        'id', i.id, 'comanda_id', i.comanda_id, 'produto_id', i.produto_id, 'quantidade', i.quantidade,
        'observacao', i.observacao, 'preco_unitario', i.preco_unitario::text, 'status', {status},
        'cancelado_por_id', i.cancelado_por_id
    )"""


def upgrade() -> None:
    # A auditoria vem antes do UPDATE para registrar o status anterior de cada item.
    op.execute(
        f"""
        INSERT INTO log_auditoria (usuario_id, acao, entidade, entidade_id, dados_antes, dados_depois, criado_em)
        SELECT NULL, 'ENTREGAR', 'ItemComanda', i.id::text, {_snapshot('i.status')}, {_snapshot("'ENTREGUE'")}, now()
        {ITENS_PRESOS}
        ORDER BY i.id
        """
    )
    op.execute(
        """
        UPDATE item_comanda i
        SET status = 'ENTREGUE', entregue_em = c.fechada_em
        FROM comanda c
        WHERE c.id = i.comanda_id AND c.status = 'FECHADA' AND i.status IN ('PENDENTE', 'EM_PREPARO', 'PRONTO')
        """
    )


def downgrade() -> None:
    # Correção de dados: o estado anterior fica registrado na auditoria e não é restaurado.
    pass
