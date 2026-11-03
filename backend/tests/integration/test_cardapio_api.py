"""Cenários da spec `cardapio`."""

from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Categoria, Produto
from scripts.seed import seed
from tests.integration.fabricas import cabecalho_de, cliente_api, criar_funcionario


async def _cardapio(session: AsyncSession, perfil: str = "FUNCIONARIO"):
    usuario = await criar_funcionario(session, "usuario", perfil=perfil)
    async with cliente_api(session) as cliente:
        return await cliente.get("/cardapio", headers=cabecalho_de(usuario))


async def test_cardapio_por_categoria_em_ordem(session: AsyncSession):
    await seed(session)

    resposta = await _cardapio(session)

    assert resposta.status_code == 200
    categorias = resposta.json()
    assert [c["nome"] for c in categorias] == ["Carnes nobres", "Acompanhamentos", "Bebidas", "Sobremesas"]
    for categoria in categorias:
        nomes = [p["nome"] for p in categoria["produtos"]]
        assert nomes == sorted(nomes)
    filet = next(p for c in categorias for p in c["produtos"] if p["nome"] == "Filet Mignon 300g")
    assert set(filet) == {"id", "nome", "descricao", "preco", "disponivel"}
    assert (Decimal(filet["preco"]), filet["disponivel"]) == (Decimal("89.90"), True)


async def test_categoria_sem_produtos_ativos_nao_aparece(session: AsyncSession):
    await seed(session)
    session.add(Categoria(nome="Vinhos", ordem=10))
    sobremesas = (await session.execute(select(Categoria.id).where(Categoria.nome == "Sobremesas"))).scalar_one()
    await session.execute(update(Produto).where(Produto.categoria_id == sobremesas).values(ativo=False))
    await session.commit()

    nomes = [c["nome"] for c in (await _cardapio(session)).json()]

    assert "Vinhos" not in nomes
    assert "Sobremesas" not in nomes


async def test_inativo_some_e_indisponivel_aparece_identificado(session: AsyncSession):
    await seed(session)
    await session.execute(update(Produto).where(Produto.nome == "Picanha 400g").values(ativo=False))
    await session.execute(update(Produto).where(Produto.nome == "Petit Gâteau").values(disponivel=False))
    await session.commit()

    produtos = {p["nome"]: p for c in (await _cardapio(session)).json() for p in c["produtos"]}

    assert "Picanha 400g" not in produtos
    assert produtos["Petit Gâteau"]["disponivel"] is False


async def test_acesso_ao_cardapio_por_perfil(session: AsyncSession):
    await seed(session)

    assert (await _cardapio(session, "ADMIN")).status_code == 200
    contabilidade = await criar_funcionario(session, "contab", perfil="CONTABILIDADE")
    async with cliente_api(session) as cliente:
        negado = await cliente.get("/cardapio", headers=cabecalho_de(contabilidade))
        sem_sessao = await cliente.get("/cardapio")

    assert negado.status_code == 403
    assert sem_sessao.status_code == 401
