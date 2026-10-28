from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LogAuditoria(Base):
    """Registro imutável (um trigger no banco rejeita UPDATE e DELETE)."""

    __tablename__ = "log_auditoria"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("funcionario.id"))  # nulo = sistema
    acao: Mapped[str] = mapped_column(String(30))
    entidade: Mapped[str] = mapped_column(String(50))
    entidade_id: Mapped[str] = mapped_column(String(50))
    dados_antes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    dados_depois: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
