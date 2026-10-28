"""esquema inicial: 10 entidades, comanda ativa única por mesa e auditoria imutável

Revision ID: 0001
Revises:
Create Date: 2026-10-28
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _criado_em(nome: str = "criado_em") -> sa.Column:
    return sa.Column(nome, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def _ts(nome: str) -> sa.Column:
    return sa.Column(nome, sa.DateTime(timezone=True), nullable=True)


def _fk_funcionario(tabela: str, coluna: str) -> sa.Column:
    return sa.Column(
        coluna,
        sa.Integer(),
        sa.ForeignKey("funcionario.id", name=f"fk_{tabela}_{coluna}_funcionario"),
        nullable=True,
    )


def upgrade() -> None:
    op.create_table(
        "funcionario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("login", sa.String(50), nullable=False),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("perfil", sa.String(20), nullable=False),
        sa.Column("bloqueado", sa.Boolean(), server_default="false", nullable=False),
        _criado_em(),
        sa.PrimaryKeyConstraint("id", name="pk_funcionario"),
        sa.UniqueConstraint("login", name="uq_funcionario_login"),
        sa.CheckConstraint(
            "perfil IN ('FUNCIONARIO', 'ADMIN', 'CONTABILIDADE')", name="ck_funcionario_perfil_valido"
        ),
    )

    op.create_table(
        "mesa",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("capacidade", sa.Integer(), nullable=False),
        sa.Column("localizacao", sa.String(30), nullable=False),
        sa.Column("em_manutencao", sa.Boolean(), server_default="false", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_mesa"),
        sa.UniqueConstraint("numero", name="uq_mesa_numero"),
        sa.CheckConstraint("capacidade > 0", name="ck_mesa_capacidade_positiva"),
    )

    op.create_table(
        "reserva",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mesa_id", sa.Integer(), sa.ForeignKey("mesa.id", name="fk_reserva_mesa_id_mesa"), nullable=False),
        sa.Column("nome_cliente", sa.String(100), nullable=False),
        sa.Column("telefone", sa.String(20), nullable=False),
        sa.Column("qtd_pessoas", sa.Integer(), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fim", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        _fk_funcionario("reserva", "criado_por_id"),
        _fk_funcionario("reserva", "cancelado_por_id"),
        _criado_em(),
        sa.PrimaryKeyConstraint("id", name="pk_reserva"),
        sa.CheckConstraint(
            "status IN ('CONFIRMADA', 'CONCLUIDA', 'CANCELADA')", name="ck_reserva_status_valido"
        ),
        sa.CheckConstraint("qtd_pessoas > 0", name="ck_reserva_qtd_pessoas_positiva"),
        sa.CheckConstraint("fim > inicio", name="ck_reserva_periodo_valido"),
    )
    op.create_index("ix_reserva_mesa_status_inicio", "reserva", ["mesa_id", "status", "inicio"])

    op.create_table(
        "categoria",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(50), nullable=False),
        sa.Column("ordem", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_categoria"),
        sa.UniqueConstraint("nome", name="uq_categoria_nome"),
    )

    op.create_table(
        "produto",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "categoria_id",
            sa.Integer(),
            sa.ForeignKey("categoria.id", name="fk_produto_categoria_id_categoria"),
            nullable=False,
        ),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("preco", sa.Numeric(10, 2), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("disponivel", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_produto"),
        sa.CheckConstraint("preco > 0", name="ck_produto_preco_positivo"),
    )

    op.create_table(
        "comanda",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mesa_id", sa.Integer(), sa.ForeignKey("mesa.id", name="fk_comanda_mesa_id_mesa"), nullable=False),
        _fk_funcionario("comanda", "funcionario_id"),
        sa.Column("status", sa.String(20), nullable=False),
        _criado_em("aberta_em"),
        _ts("pre_conta_em"),
        _ts("fechada_em"),
        sa.Column("taxa_servico_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("taxa_servico_aplicada", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_comanda"),
        sa.CheckConstraint(
            "status IN ('ABERTA', 'PRE_CONTA', 'FECHADA', 'CANCELADA')", name="ck_comanda_status_valido"
        ),
        sa.CheckConstraint(
            "taxa_servico_pct IS NULL OR (taxa_servico_pct >= 0 AND taxa_servico_pct <= 100)",
            name="ck_comanda_taxa_servico_valida",
        ),
    )
    op.create_index("ix_comanda_mesa_status", "comanda", ["mesa_id", "status"])
    op.create_index(
        "uq_comanda_ativa_por_mesa",
        "comanda",
        ["mesa_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('ABERTA', 'PRE_CONTA')"),
    )

    op.create_table(
        "item_comanda",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "comanda_id",
            sa.Integer(),
            sa.ForeignKey("comanda.id", name="fk_item_comanda_comanda_id_comanda"),
            nullable=False,
        ),
        sa.Column(
            "produto_id",
            sa.Integer(),
            sa.ForeignKey("produto.id", name="fk_item_comanda_produto_id_produto"),
            nullable=False,
        ),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("observacao", sa.String(200), server_default="", nullable=False),
        sa.Column("preco_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        _criado_em(),
        _ts("enviado_em"),
        _ts("pronto_em"),
        _ts("entregue_em"),
        _ts("cancelado_em"),
        _fk_funcionario("item_comanda", "cancelado_por_id"),
        sa.PrimaryKeyConstraint("id", name="pk_item_comanda"),
        sa.CheckConstraint(
            "status IN ('PENDENTE', 'EM_PREPARO', 'PRONTO', 'ENTREGUE', 'CANCELADO')",
            name="ck_item_comanda_status_valido",
        ),
        sa.CheckConstraint("quantidade > 0", name="ck_item_comanda_quantidade_positiva"),
        sa.CheckConstraint("preco_unitario > 0", name="ck_item_comanda_preco_unitario_positivo"),
    )
    op.create_index("ix_item_comanda_comanda_id", "item_comanda", ["comanda_id"])

    op.create_table(
        "pagamento",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "comanda_id",
            sa.Integer(),
            sa.ForeignKey("comanda.id", name="fk_pagamento_comanda_id_comanda"),
            nullable=False,
        ),
        sa.Column("forma", sa.String(20), nullable=False),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        _fk_funcionario("pagamento", "registrado_por_id"),
        _criado_em("registrado_em"),
        sa.PrimaryKeyConstraint("id", name="pk_pagamento"),
        sa.CheckConstraint(
            "forma IN ('PIX', 'CREDITO', 'DEBITO', 'DINHEIRO')", name="ck_pagamento_forma_valido"
        ),
        sa.CheckConstraint("valor > 0", name="ck_pagamento_valor_positivo"),
    )
    op.create_index("ix_pagamento_comanda_id", "pagamento", ["comanda_id"])

    op.create_table(
        "parametro",
        sa.Column("chave", sa.String(50), primary_key=True),
        sa.Column("valor", sa.String(100), nullable=False),
        _criado_em("atualizado_em"),
        sa.PrimaryKeyConstraint("chave", name="pk_parametro"),
    )

    op.create_table(
        "log_auditoria",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        _fk_funcionario("log_auditoria", "usuario_id"),
        sa.Column("acao", sa.String(30), nullable=False),
        sa.Column("entidade", sa.String(50), nullable=False),
        sa.Column("entidade_id", sa.String(50), nullable=False),
        sa.Column("dados_antes", postgresql.JSONB(), nullable=True),
        sa.Column("dados_depois", postgresql.JSONB(), nullable=True),
        _criado_em(),
        sa.PrimaryKeyConstraint("id", name="pk_log_auditoria"),
    )
    op.create_index("ix_log_auditoria_criado_em", "log_auditoria", ["criado_em"])

    # Auditoria imutável: nenhuma funcionalidade pode alterar ou excluir registros.
    op.execute(
        """
        CREATE FUNCTION log_auditoria_imutavel() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Registros de auditoria são imutáveis';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_log_auditoria_imutavel
        BEFORE UPDATE OR DELETE ON log_auditoria
        FOR EACH ROW EXECUTE FUNCTION log_auditoria_imutavel();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_log_auditoria_imutavel ON log_auditoria")
    op.execute("DROP FUNCTION IF EXISTS log_auditoria_imutavel()")
    for tabela in (
        "log_auditoria",
        "parametro",
        "pagamento",
        "item_comanda",
        "comanda",
        "produto",
        "categoria",
        "reserva",
        "mesa",
        "funcionario",
    ):
        op.drop_table(tabela)
