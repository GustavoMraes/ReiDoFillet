"""Cenários da spec `cardapio` (gestão): produtos, preço, ativação, esgotado, categorias, auditoria e acesso."""

from decimal import Decimal

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Categoria, LogAuditoria, Produto
from tests.integration.comandas_util import Ambiente, UsuarioRef, abrir, adicionar, preparar
from tests.integration.fabricas import cabecalho_de, cliente_api


async def _categorias(session: AsyncSession) -> dict[str, int]:
    return dict((await session.execute(select(Categoria.nome, Categoria.id))).all())


async def criar_produto(cliente: AsyncClient, usuario: UsuarioRef, **dados) -> Response:
    return await cliente.post("/admin/produtos", json=dados, headers=cabecalho_de(usuario))


async def alterar_produto(cliente: AsyncClient, usuario: UsuarioRef, produto_id: int, **dados) -> Response:
    return await cliente.patch(f"/admin/produtos/{produto_id}", json=dados, headers=cabecalho_de(usuario))


async def disponibilidade(cliente: AsyncClient, usuario: UsuarioRef, produto_id: int, disponivel: bool) -> Response:
    return await cliente.patch(
        f"/produtos/{produto_id}/disponibilidade", json={"disponivel": disponivel}, headers=cabecalho_de(usuario)
    )


async def _cardapio(cliente: AsyncClient, amb: Ambiente) -> dict[str, dict]:
    """Cardápio de pedidos (GET /cardapio) indexado pelo nome do produto."""
    categorias = (await cliente.get("/cardapio", headers=cabecalho_de(amb.gabriela))).json()
    return {p["nome"]: {**p, "categoria": c["nome"]} for c in categorias for p in c["produtos"]}


def _produto_da_resposta(resposta: Response, nome: str) -> dict:
    return next(p for c in resposta.json() for p in c["produtos"] if p["nome"] == nome)


# --- Cadastro de produto ---


async def test_novo_prato(session: AsyncSession):
    amb = await preparar(session)
    carnes = (await _categorias(session))["Carnes nobres"]

    async with cliente_api(session) as cliente:
        resposta = await criar_produto(
            cliente, amb.admin, categoria_id=carnes, nome="  Costela no Bafo ", descricao="", preco="79.90"
        )
        cardapio = await _cardapio(cliente, amb)

    assert resposta.status_code == 201
    produto = _produto_da_resposta(resposta, "Costela no Bafo")
    assert (produto["preco"], produto["ativo"], produto["disponivel"], produto["descricao"]) == ("79.90", True, True, None)
    assert (cardapio["Costela no Bafo"]["categoria"], cardapio["Costela no Bafo"]["disponivel"]) == ("Carnes nobres", True)
    log = (await session.execute(select(LogAuditoria).where(LogAuditoria.entidade == "Produto"))).scalar_one()
    assert (log.acao, log.usuario_id, log.dados_depois["preco"]) == ("CRIAR", amb.admin.id, "79.90")


@pytest.mark.parametrize(
    ("preco", "mensagem"),
    [
        ("0", "Informe um preço maior que zero, com até duas casas decimais"),
        ("-5.00", "Informe um preço maior que zero, com até duas casas decimais"),
        ("10.999", "Informe um preço maior que zero, com até duas casas decimais"),
        ("100000.00", "O preço máximo é R$ 99.999,99"),
    ],
)
async def test_preco_invalido(session: AsyncSession, preco: str, mensagem: str):
    amb = await preparar(session)
    carnes = (await _categorias(session))["Carnes nobres"]
    filet = amb.produtos["Filet Mignon 300g"]

    async with cliente_api(session) as cliente:
        criacao = await criar_produto(cliente, amb.admin, categoria_id=carnes, nome="Costela", preco=preco)
        alteracao = await alterar_produto(cliente, amb.admin, filet.id, preco=preco)

    assert (criacao.status_code, criacao.json()) == (422, {"detalhe": mensagem})
    assert (alteracao.status_code, alteracao.json()) == (422, {"detalhe": mensagem})
    assert (await session.execute(select(Produto.preco).where(Produto.id == filet.id))).scalar_one() == filet.preco


@pytest.mark.parametrize(
    ("dados", "mensagem"),
    [
        ({"nome": "   "}, "Informe o nome do produto"),
        ({"nome": "A" * 101}, "O nome do produto deve ter no máximo 100 caracteres"),
        ({"descricao": "D" * 301}, "A descrição deve ter no máximo 300 caracteres"),
    ],
)
async def test_dados_do_produto_invalidos(session: AsyncSession, dados: dict, mensagem: str):
    amb = await preparar(session)
    carnes = (await _categorias(session))["Carnes nobres"]

    async with cliente_api(session) as cliente:
        resposta = await criar_produto(cliente, amb.admin, **{"categoria_id": carnes, "nome": "Costela", "preco": "50", **dados})

    assert (resposta.status_code, resposta.json()) == (422, {"detalhe": mensagem})


async def test_nome_repetido_e_categoria_inexistente(session: AsyncSession):
    amb = await preparar(session)
    carnes = (await _categorias(session))["Carnes nobres"]
    arroz = amb.produtos["Arroz Branco"]

    async with cliente_api(session) as cliente:
        criacao = await criar_produto(cliente, amb.admin, categoria_id=carnes, nome="FILET MIGNON 300G", preco="50")
        renomeado = await alterar_produto(cliente, amb.admin, arroz.id, nome="picanha 400g")
        mesma_caixa = await alterar_produto(cliente, amb.admin, arroz.id, nome="ARROZ BRANCO")
        sem_categoria = await criar_produto(cliente, amb.admin, categoria_id=999999, nome="Costela", preco="50")
        inexistente = await alterar_produto(cliente, amb.admin, 999999, preco="10")

    assert (criacao.status_code, criacao.json()) == (409, {"detalhe": "Já existe um produto com este nome"})
    assert (renomeado.status_code, renomeado.json()) == (409, {"detalhe": "Já existe um produto com este nome"})
    assert mesma_caixa.status_code == 200  # o próprio produto pode mudar só a caixa do nome
    assert (sem_categoria.status_code, sem_categoria.json()) == (404, {"detalhe": "Categoria não encontrada"})
    assert (inexistente.status_code, inexistente.json()) == (404, {"detalhe": "Produto não encontrado"})


async def test_alteracao_sem_campos(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        resposta = await alterar_produto(cliente, amb.admin, amb.produtos["Arroz Branco"].id)

    assert resposta.status_code == 422


# --- Mudança de preço não altera comandas ---


async def test_aumento_de_preco_com_comanda_aberta(session: AsyncSession):
    amb = await preparar(session)
    filet = amb.produtos["Filet Mignon 300g"]

    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[1])).json()["id"]
        await adicionar(cliente, amb.gabriela, comanda_id, filet)
        resposta = await alterar_produto(cliente, amb.admin, filet.id, preco="95.00")
        comanda = (await adicionar(cliente, amb.gabriela, comanda_id, filet)).json()

    assert _produto_da_resposta(resposta, "Filet Mignon 300g")["preco"] == "95.00"
    assert sorted(item["preco_unitario"] for item in comanda["itens"]) == ["89.90", "95.00"]
    log = (await session.execute(select(LogAuditoria).where(LogAuditoria.entidade == "Produto"))).scalar_one()
    assert (log.acao, log.usuario_id) == ("ALTERAR", amb.admin.id)
    assert (log.dados_antes["preco"], log.dados_depois["preco"]) == ("89.90", "95.00")


# --- Ativação e desativação ---


async def test_prato_retirado_do_cardapio(session: AsyncSession):
    amb = await preparar(session)
    picanha = amb.produtos["Picanha 400g"]

    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[1])).json()["id"]
        await adicionar(cliente, amb.gabriela, comanda_id, picanha)
        await alterar_produto(cliente, amb.admin, picanha.id, ativo=False)
        cardapio = await _cardapio(cliente, amb)
        comanda = (await cliente.get(f"/comandas/{comanda_id}", headers=cabecalho_de(amb.gabriela))).json()
        novo_pedido = await adicionar(cliente, amb.gabriela, comanda_id, picanha)
        admin = (await cliente.get("/admin/cardapio", headers=cabecalho_de(amb.admin))).json()
        await alterar_produto(cliente, amb.admin, picanha.id, ativo=True)
        reativado = await _cardapio(cliente, amb)

    assert "Picanha 400g" not in cardapio
    assert [item["produto_nome"] for item in comanda["itens"]] == ["Picanha 400g"]
    assert (novo_pedido.status_code, novo_pedido.json()) == (409, {"detalhe": "Item indisponível"})
    assert next(p for c in admin for p in c["produtos"] if p["nome"] == "Picanha 400g")["ativo"] is False
    assert "Picanha 400g" in reativado


# --- Produto esgotado no dia ---


async def test_acabou_o_petit_gateau(session: AsyncSession):
    amb = await preparar(session)
    petit = amb.produtos["Petit Gâteau"]

    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[1])).json()["id"]
        resposta = await disponibilidade(cliente, amb.gabriela, petit.id, False)
        cardapio = await _cardapio(cliente, amb)
        pedido = await adicionar(cliente, amb.gabriela, comanda_id, petit)
        de_volta = await disponibilidade(cliente, amb.admin, petit.id, True)
        pedido_depois = await adicionar(cliente, amb.gabriela, comanda_id, petit)

    assert (resposta.status_code, resposta.json()["disponivel"]) == (200, False)
    assert cardapio["Petit Gâteau"]["disponivel"] is False
    assert (pedido.status_code, pedido.json()) == (409, {"detalhe": "Item indisponível"})
    assert de_volta.json()["disponivel"] is True
    assert pedido_depois.status_code == 200
    logs = (await session.execute(select(LogAuditoria).where(LogAuditoria.entidade == "Produto"))).scalars().all()
    assert [(log.usuario_id, log.dados_depois["disponivel"]) for log in logs] == [
        (amb.gabriela.id, False),
        (amb.admin.id, True),
    ]


async def test_disponibilidade_de_produto_inativo(session: AsyncSession):
    amb = await preparar(session)
    petit = amb.produtos["Petit Gâteau"]

    async with cliente_api(session) as cliente:
        await alterar_produto(cliente, amb.admin, petit.id, ativo=False)
        resposta = await disponibilidade(cliente, amb.gabriela, petit.id, False)
        inexistente = await disponibilidade(cliente, amb.gabriela, 999999, False)

    assert (resposta.status_code, resposta.json()) == (
        409,
        {"detalhe": "Produto inativo: reative-o no cadastro antes de mudar a disponibilidade"},
    )
    assert inexistente.status_code == 404


# --- Acesso ---


async def test_funcionario_tenta_mudar_preco_e_contabilidade_recusada(session: AsyncSession):
    amb = await preparar(session)
    filet = amb.produtos["Filet Mignon 300g"]

    async with cliente_api(session) as cliente:
        preco = await alterar_produto(cliente, amb.gabriela, filet.id, preco="1.00")
        lista = await cliente.get("/admin/cardapio", headers=cabecalho_de(amb.gabriela))
        categoria = await cliente.post("/admin/categorias", json={"nome": "X"}, headers=cabecalho_de(amb.gabriela))
        contabilidade = await disponibilidade(cliente, amb.contabilidade, filet.id, False)
        sem_sessao = await cliente.get("/admin/cardapio")

    assert (preco.status_code, preco.json()) == (403, {"detalhe": "Sem permissão para esta funcionalidade"})
    assert (lista.status_code, categoria.status_code, contabilidade.status_code) == (403, 403, 403)
    assert sem_sessao.status_code == 401
    assert (await session.execute(select(Produto.preco).where(Produto.id == filet.id))).scalar_one() == Decimal("89.90")


# --- Categorias ---


async def _ordem(cliente: AsyncClient, amb: Ambiente) -> list[str]:
    return [c["nome"] for c in (await cliente.get("/admin/cardapio", headers=cabecalho_de(amb.admin))).json()]


async def mover(cliente: AsyncClient, amb: Ambiente, categoria_id: int, direcao: str) -> Response:
    return await cliente.post(
        f"/admin/categorias/{categoria_id}/mover", json={"direcao": direcao}, headers=cabecalho_de(amb.admin)
    )


async def test_nova_categoria_antes_de_sobremesas(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        resposta = await cliente.post("/admin/categorias", json={"nome": " Porções "}, headers=cabecalho_de(amb.admin))
        porcoes = next(c for c in resposta.json() if c["nome"] == "Porções")
        await criar_produto(cliente, amb.admin, categoria_id=porcoes["id"], nome="Isca de Peixe", preco="39.90")
        await mover(cliente, amb, porcoes["id"], "acima")
        ordem_admin = await _ordem(cliente, amb)
        cardapio = (await cliente.get("/cardapio", headers=cabecalho_de(amb.gabriela))).json()

    assert resposta.status_code == 201
    assert ordem_admin == ["Carnes nobres", "Acompanhamentos", "Bebidas", "Porções", "Sobremesas"]
    assert [c["nome"] for c in cardapio] == ordem_admin
    criacao = (
        await session.execute(select(LogAuditoria).where(LogAuditoria.entidade == "Categoria", LogAuditoria.acao == "CRIAR"))
    ).scalar_one()
    assert criacao.dados_depois == {"id": porcoes["id"], "nome": "Porções", "ordem": 4}


async def test_mover_renumera_e_nao_passa_das_pontas(session: AsyncSession):
    amb = await preparar(session)
    categorias = await _categorias(session)
    # Empate herdado: todas na mesma ordem, desempatadas pelo nome.
    for categoria in (await session.execute(select(Categoria))).scalars():
        categoria.ordem = 0
    await session.commit()

    async with cliente_api(session) as cliente:
        antes = await _ordem(cliente, amb)
        await mover(cliente, amb, categorias["Acompanhamentos"], "acima")  # já é a primeira
        no_topo = await _ordem(cliente, amb)
        await mover(cliente, amb, categorias["Sobremesas"], "abaixo")  # já é a última
        await mover(cliente, amb, categorias["Sobremesas"], "acima")
        depois = await _ordem(cliente, amb)
        inexistente = await mover(cliente, amb, 999999, "acima")

    assert antes == no_topo == ["Acompanhamentos", "Bebidas", "Carnes nobres", "Sobremesas"]
    assert depois == ["Acompanhamentos", "Bebidas", "Sobremesas", "Carnes nobres"]
    ordens = sorted((await session.execute(select(Categoria.ordem))).scalars())
    assert ordens == [0, 1, 2, 3]
    assert inexistente.status_code == 404


async def test_renomear_e_nomes_repetidos(session: AsyncSession):
    amb = await preparar(session)
    categorias = await _categorias(session)

    async with cliente_api(session) as cliente:
        repetida = await cliente.post("/admin/categorias", json={"nome": "BEBIDAS"}, headers=cabecalho_de(amb.admin))
        vazia = await cliente.post("/admin/categorias", json={"nome": " "}, headers=cabecalho_de(amb.admin))
        renomeada = await cliente.patch(
            f"/admin/categorias/{categorias['Bebidas']}", json={"nome": "Drinks"}, headers=cabecalho_de(amb.admin)
        )
        conflito = await cliente.patch(
            f"/admin/categorias/{categorias['Sobremesas']}",
            json={"nome": "drinks"},
            headers=cabecalho_de(amb.admin),
        )

    assert (repetida.status_code, repetida.json()) == (409, {"detalhe": "Já existe uma categoria com este nome"})
    assert (vazia.status_code, vazia.json()) == (422, {"detalhe": "Informe o nome da categoria"})
    assert "Drinks" in [c["nome"] for c in renomeada.json()]
    assert (conflito.status_code, conflito.json()) == (409, {"detalhe": "Já existe uma categoria com este nome"})
    log = (
        await session.execute(select(LogAuditoria).where(LogAuditoria.entidade == "Categoria", LogAuditoria.acao == "ALTERAR"))
    ).scalar_one()
    assert (log.dados_antes["nome"], log.dados_depois["nome"]) == ("Bebidas", "Drinks")


async def test_categoria_com_produtos_e_exclusao(session: AsyncSession):
    amb = await preparar(session)
    categorias = await _categorias(session)

    async with cliente_api(session) as cliente:
        com_ativos = await cliente.delete(f"/admin/categorias/{categorias['Sobremesas']}", headers=cabecalho_de(amb.admin))
        for nome in ("Pudim de Leite", "Petit Gâteau"):
            await alterar_produto(cliente, amb.admin, amb.produtos[nome].id, ativo=False)
        so_inativos = await cliente.delete(f"/admin/categorias/{categorias['Sobremesas']}", headers=cabecalho_de(amb.admin))
        nova = await cliente.post("/admin/categorias", json={"nome": "Vazia"}, headers=cabecalho_de(amb.admin))
        vazia_id = next(c["id"] for c in nova.json() if c["nome"] == "Vazia")
        excluida = await cliente.delete(f"/admin/categorias/{vazia_id}", headers=cabecalho_de(amb.admin))

    mensagem = {"detalhe": "Mova os produtos para outra categoria antes de excluí-la"}
    assert (com_ativos.status_code, com_ativos.json()) == (409, mensagem)
    assert (so_inativos.status_code, so_inativos.json()) == (409, mensagem)
    assert excluida.status_code == 200
    assert "Vazia" not in [c["nome"] for c in excluida.json()]
    log = (
        await session.execute(select(LogAuditoria).where(LogAuditoria.entidade == "Categoria", LogAuditoria.acao == "EXCLUIR"))
    ).scalar_one()
    assert (log.entidade_id, log.dados_antes["nome"], log.dados_depois) == (str(vazia_id), "Vazia", None)
