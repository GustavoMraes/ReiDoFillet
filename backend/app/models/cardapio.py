from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Categoria(Base):
    __tablename__ = "categoria"
    __table_args__ = (Index("uq_categoria_nome_sem_caixa", text("lower(nome)"), unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(50), unique=True)
    ordem: Mapped[int] = mapped_column(default=0, server_default="0")


class Produto(Base):
    """`ativo`: aparece no cardápio (HU05). `disponivel`: não está esgotado no momento (UC 7.1)."""

    __tablename__ = "produto"
    __table_args__ = (
        CheckConstraint("preco > 0", name="preco_positivo"),
        # Nomes únicos sem diferenciar maiúsculas ("Arroz" e "arroz" são o mesmo produto).
        Index("uq_produto_nome_sem_caixa", text("lower(nome)"), unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categoria.id"))
    nome: Mapped[str] = mapped_column(String(100))
    descricao: Mapped[str | None] = mapped_column(Text)
    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    ativo: Mapped[bool] = mapped_column(default=True, server_default="true")
    disponivel: Mapped[bool] = mapped_column(default=True, server_default="true")
