"""índices de abertura e fechamento da comanda para os relatórios por período

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-03
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_comanda_aberta_em", "comanda", ["aberta_em"])
    op.create_index("ix_comanda_fechada_em", "comanda", ["fechada_em"])


def downgrade() -> None:
    op.drop_index("ix_comanda_fechada_em", table_name="comanda")
    op.drop_index("ix_comanda_aberta_em", table_name="comanda")
