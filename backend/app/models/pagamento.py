from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import FormaPagamento, check_enum


class Pagamento(Base):
    """Apenas o registro do que foi pago nas máquinas do estabelecimento; não há integração externa."""

    __tablename__ = "pagamento"
    __table_args__ = (
        check_enum("forma", FormaPagamento),
        CheckConstraint("valor > 0", name="valor_positivo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    comanda_id: Mapped[int] = mapped_column(ForeignKey("comanda.id"), index=True)
    forma: Mapped[str] = mapped_column(String(20))
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    registrado_por_id: Mapped[int | None] = mapped_column(ForeignKey("funcionario.id"))
    registrado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
