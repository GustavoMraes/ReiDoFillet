from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Funcionario


class FuncionarioRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def obter(self, funcionario_id: int) -> Funcionario | None:
        return await self.session.get(Funcionario, funcionario_id)

    async def obter_por_login(self, login: str) -> Funcionario | None:
        return (await self.session.execute(select(Funcionario).where(Funcionario.login == login))).scalar_one_or_none()
