from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Funcionario, LogAuditoria

USUARIO_SISTEMA = 0  # filtro: registros sem usuário (operações do sistema)


class AuditoriaRepository:
    """Somente inserção e leitura: registros de auditoria nunca são alterados nem excluídos."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def adicionar(self, log: LogAuditoria) -> None:
        self.session.add(log)

    async def consultar(
        self,
        de: datetime,
        ate: datetime,
        usuario_id: int | None,
        acao: str | None,
        entidade: str | None,
        deslocamento: int,
        limite: int,
    ) -> tuple[list[tuple[LogAuditoria, str | None]], int]:
        """Registros do período (mais recentes primeiro) com o nome do usuário, e o total sem paginação."""
        filtros = [LogAuditoria.criado_em >= de, LogAuditoria.criado_em < ate]
        if usuario_id == USUARIO_SISTEMA:
            filtros.append(LogAuditoria.usuario_id.is_(None))
        elif usuario_id is not None:
            filtros.append(LogAuditoria.usuario_id == usuario_id)
        if acao:
            filtros.append(LogAuditoria.acao == acao)
        if entidade:
            filtros.append(LogAuditoria.entidade == entidade)

        total = (await self.session.execute(select(func.count()).select_from(LogAuditoria).where(*filtros))).scalar_one()
        resultado = await self.session.execute(
            select(LogAuditoria, Funcionario.nome)
            .outerjoin(Funcionario, Funcionario.id == LogAuditoria.usuario_id)
            .where(*filtros)
            .order_by(LogAuditoria.criado_em.desc(), LogAuditoria.id.desc())
            .offset(deslocamento)
            .limit(limite)
        )
        return [(log, nome) for log, nome in resultado], total

    async def entidades(self) -> list[str]:
        consulta = select(LogAuditoria.entidade).distinct().order_by(LogAuditoria.entidade)
        return list((await self.session.execute(consulta)).scalars())

    async def usuarios(self) -> list[tuple[int, str]]:
        resultado = await self.session.execute(select(Funcionario.id, Funcionario.nome).order_by(Funcionario.nome))
        return [(i, nome) for i, nome in resultado]
