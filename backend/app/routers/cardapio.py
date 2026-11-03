from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.enums import Perfil
from app.repositories.cardapio import CardapioRepository
from app.routers.dependencias import exigir_perfis
from app.schemas.cardapio import CategoriaCardapioOut
from app.services.cardapio import CardapioService

router = APIRouter(prefix="/cardapio", tags=["Cardápio"])


@router.get(
    "",
    response_model=list[CategoriaCardapioOut],
    dependencies=[Depends(exigir_perfis(Perfil.FUNCIONARIO, Perfil.ADMIN))],
)
async def cardapio(session: AsyncSession = Depends(get_session)) -> list[CategoriaCardapioOut]:
    """Cardápio para lançamento de pedidos: produtos ativos por categoria, com a disponibilidade atual."""
    return await CardapioService(CardapioRepository(session)).cardapio()
