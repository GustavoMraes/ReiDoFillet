"""nomes de produto e categoria únicos sem diferenciar maiúsculas

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-03
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("uq_produto_nome_sem_caixa", "produto", [sa.text("lower(nome)")], unique=True)
    op.create_index("uq_categoria_nome_sem_caixa", "categoria", [sa.text("lower(nome)")], unique=True)


def downgrade() -> None:
    op.drop_index("uq_categoria_nome_sem_caixa", table_name="categoria")
    op.drop_index("uq_produto_nome_sem_caixa", table_name="produto")
