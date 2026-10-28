from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Categoria, Funcionario, Mesa, Parametro, Produto
from scripts.seed import seed


async def _contagens(session: AsyncSession) -> dict[str, int]:
    return {
        modelo.__name__: (await session.execute(select(func.count()).select_from(modelo))).scalar_one()
        for modelo in (Mesa, Categoria, Produto, Funcionario, Parametro)
    }


async def test_seed_e_idempotente(session: AsyncSession):
    await seed(session)
    primeira = await _contagens(session)

    await seed(session)
    segunda = await _contagens(session)

    assert primeira == segunda
    assert primeira == {"Mesa": 8, "Categoria": 4, "Produto": 11, "Funcionario": 3, "Parametro": 1}


async def test_seed_tem_mesa_em_manutencao_e_taxa_padrao(session: AsyncSession):
    await seed(session)

    em_manutencao = (await session.execute(select(Mesa.numero).where(Mesa.em_manutencao))).scalars().all()
    taxa = (await session.execute(select(Parametro.valor).where(Parametro.chave == "taxa_servico_padrao"))).scalar_one()

    assert em_manutencao == [6]
    assert taxa == "10.00"
