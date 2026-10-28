from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import StatusComanda, StatusItem, check_enum


class Comanda(Base):
    """Comanda virtual: o id identifica um atendimento e nunca é reutilizado."""

    __tablename__ = "comanda"
    __table_args__ = (
        check_enum("status", StatusComanda),
        CheckConstraint(
            "taxa_servico_pct IS NULL OR (taxa_servico_pct >= 0 AND taxa_servico_pct <= 100)",
            name="taxa_servico_valida",
        ),
        Index("ix_comanda_mesa_status", "mesa_id", "status"),
        # No máximo uma comanda ativa por mesa, inclusive sob concorrência.
        Index(
            "uq_comanda_ativa_por_mesa",
            "mesa_id",
            unique=True,
            postgresql_where=text("status IN ('ABERTA', 'PRE_CONTA')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mesa_id: Mapped[int] = mapped_column(ForeignKey("mesa.id"))
    funcionario_id: Mapped[int | None] = mapped_column(ForeignKey("funcionario.id"))
    status: Mapped[str] = mapped_column(String(20), default=StatusComanda.ABERTA)
    aberta_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    pre_conta_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fechada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Copiada do parâmetro taxa_servico_padrao na pré-conta; ajustável até o fechamento.
    taxa_servico_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    taxa_servico_aplicada: Mapped[bool] = mapped_column(default=True, server_default="true")


class ItemComanda(Base):
    """Itens nunca são excluídos fisicamente: a remoção é a transição para CANCELADO."""

    __tablename__ = "item_comanda"
    __table_args__ = (
        check_enum("status", StatusItem),
        CheckConstraint("quantidade > 0", name="quantidade_positiva"),
        CheckConstraint("preco_unitario > 0", name="preco_unitario_positivo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    comanda_id: Mapped[int] = mapped_column(ForeignKey("comanda.id"), index=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produto.id"))
    quantidade: Mapped[int]
    observacao: Mapped[str] = mapped_column(String(200), default="", server_default="")
    # Congelado no registro: alterações no cardápio não afetam comandas existentes.
    preco_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), default=StatusItem.PENDENTE)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    enviado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pronto_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    entregue_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelado_por_id: Mapped[int | None] = mapped_column(ForeignKey("funcionario.id"))
