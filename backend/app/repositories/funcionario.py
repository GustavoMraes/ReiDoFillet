from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Funcionario
from app.models.enums import Perfil


class FuncionarioRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def obter(self, funcionario_id: int) -> Funcionario | None:
        return await self.session.get(Funcionario, funcionario_id)

    async def obter_por_login(self, login: str) -> Funcionario | None:
        return (await self.session.execute(select(Funcionario).where(Funcionario.login == login))).scalar_one_or_none()

    async def listar(self) -> list[Funcionario]:
        return list((await self.session.execute(select(Funcionario).order_by(Funcionario.nome, Funcionario.id))).scalars())

    async def obter_para_atualizar(self, funcionario_id: int) -> Funcionario | None:
        consulta = (
            select(Funcionario)
            .where(Funcionario.id == funcionario_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(consulta)).scalar_one_or_none()

    async def administradores_ativos_para_atualizar(self) -> list[Funcionario]:
        """Bloqueia, em ordem de id, as linhas dos administradores ativos e as relê do banco."""
        consulta = (
            select(Funcionario)
            .where(Funcionario.perfil == Perfil.ADMIN, Funcionario.bloqueado.is_(False))
            .order_by(Funcionario.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return list((await self.session.execute(consulta)).scalars())
