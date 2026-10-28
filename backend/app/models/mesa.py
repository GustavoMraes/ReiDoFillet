from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Mesa(Base):
    """O status da mesa não é armazenado: é calculado na leitura (ver MesaService)."""

    __tablename__ = "mesa"
    __table_args__ = (CheckConstraint("capacidade > 0", name="capacidade_positiva"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[int] = mapped_column(unique=True)
    capacidade: Mapped[int]
    localizacao: Mapped[str] = mapped_column(String(30))
    em_manutencao: Mapped[bool] = mapped_column(default=False, server_default="false")
