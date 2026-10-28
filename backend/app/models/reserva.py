from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import StatusReserva, check_enum


class Reserva(Base):
    """Os dados de contato do cliente ficam na própria reserva (não há entidade Cliente)."""

    __tablename__ = "reserva"
    __table_args__ = (
        check_enum("status", StatusReserva),
        CheckConstraint("qtd_pessoas > 0", name="qtd_pessoas_positiva"),
        CheckConstraint("fim > inicio", name="periodo_valido"),
        Index("ix_reserva_mesa_status_inicio", "mesa_id", "status", "inicio"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mesa_id: Mapped[int] = mapped_column(ForeignKey("mesa.id"))
    nome_cliente: Mapped[str] = mapped_column(String(100))
    telefone: Mapped[str] = mapped_column(String(20))
    qtd_pessoas: Mapped[int]
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fim: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default=StatusReserva.CONFIRMADA)
    criado_por_id: Mapped[int | None] = mapped_column(ForeignKey("funcionario.id"))
    cancelado_por_id: Mapped[int | None] = mapped_column(ForeignKey("funcionario.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
