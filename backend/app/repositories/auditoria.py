from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LogAuditoria


class AuditoriaRepository:
    """Somente inserção: registros de auditoria nunca são alterados nem excluídos."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def adicionar(self, log: LogAuditoria) -> None:
        self.session.add(log)
