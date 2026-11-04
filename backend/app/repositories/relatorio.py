from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import Comanda, Funcionario, ItemComanda, Mesa, Pagamento, Produto
from app.models.enums import StatusComanda

Responsavel = aliased(Funcionario)


def ids_abertas_entre(de: datetime, ate: datetime) -> Select:
    """Comandas abertas no período (relatório operacional)."""
    return select(Comanda.id).where(Comanda.aberta_em >= de, Comanda.aberta_em < ate)


def ids_fechadas_entre(de: datetime, ate: datetime) -> Select:
    """Comandas fechadas no período (relatório financeiro)."""
    return select(Comanda.id).where(
        Comanda.status == StatusComanda.FECHADA, Comanda.fechada_em >= de, Comanda.fechada_em < ate
    )


class RelatorioRepository:
    """Três consultas por relatório: comandas, itens e pagamentos do mesmo conjunto (subconsulta `ids`)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def comandas(self, ids: Select) -> list[tuple[Comanda, int, str | None]]:
        """Comandas do conjunto com número da mesa e nome do responsável, em ordem de fechamento e abertura."""
        resultado = await self.session.execute(
            select(Comanda, Mesa.numero, Responsavel.nome)
            .join(Mesa, Mesa.id == Comanda.mesa_id)
            .outerjoin(Responsavel, Responsavel.id == Comanda.funcionario_id)
            .where(Comanda.id.in_(ids))
            .order_by(Comanda.fechada_em, Comanda.aberta_em, Comanda.id)
        )
        return [(comanda, numero, nome) for comanda, numero, nome in resultado]

    async def itens(self, ids: Select) -> list[tuple[ItemComanda, str]]:
        resultado = await self.session.execute(
            select(ItemComanda, Produto.nome)
            .join(Produto, Produto.id == ItemComanda.produto_id)
            .where(ItemComanda.comanda_id.in_(ids))
        )
        return [(item, nome) for item, nome in resultado]

    async def pagamentos(self, ids: Select) -> list[Pagamento]:
        consulta = select(Pagamento).where(Pagamento.comanda_id.in_(ids)).order_by(Pagamento.registrado_em, Pagamento.id)
        return list((await self.session.execute(consulta)).scalars())
