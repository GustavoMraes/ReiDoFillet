from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def transacao(session: AsyncSession) -> AsyncIterator[AsyncSession]:
    """Unidade de trabalho dos serviços: um único commit ao final, rollback em qualquer exceção.

    Operação de negócio e auditoria são gravadas dentro do mesmo bloco, logo são atômicas.
    """
    try:
        yield session
        await session.commit()
    except BaseException:
        await session.rollback()
        raise
