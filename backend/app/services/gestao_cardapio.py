from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflito, DadoInvalido, RecursoNaoEncontrado
from app.db.transacao import transacao
from app.models import Categoria, Funcionario, Produto
from app.repositories.cardapio import CardapioRepository
from app.schemas.cardapio import CategoriaAdminOut, ProdutoAdminOut
from app.schemas.snapshots import CategoriaSnapshot, ProdutoSnapshot
from app.services.auditoria import Acao, AuditoriaService

TAMANHO_MAXIMO_NOME_PRODUTO = 100
TAMANHO_MAXIMO_DESCRICAO = 300
TAMANHO_MAXIMO_NOME_CATEGORIA = 50
PRECO_MAXIMO = Decimal("99999.99")

PRODUTO_REPETIDO = "Já existe um produto com este nome"
CATEGORIA_REPETIDA = "Já existe uma categoria com este nome"
CATEGORIA_COM_PRODUTOS = "Mova os produtos para outra categoria antes de excluí-la"


def _nome_produto(nome: str) -> str:
    nome = nome.strip()
    if not nome:
        raise DadoInvalido("Informe o nome do produto")
    if len(nome) > TAMANHO_MAXIMO_NOME_PRODUTO:
        raise DadoInvalido(f"O nome do produto deve ter no máximo {TAMANHO_MAXIMO_NOME_PRODUTO} caracteres")
    return nome


def _descricao(descricao: str | None) -> str | None:
    descricao = (descricao or "").strip()
    if len(descricao) > TAMANHO_MAXIMO_DESCRICAO:
        raise DadoInvalido(f"A descrição deve ter no máximo {TAMANHO_MAXIMO_DESCRICAO} caracteres")
    return descricao or None


def _preco(preco: Decimal) -> Decimal:
    if not preco.is_finite() or preco <= 0 or preco.as_tuple().exponent < -2:
        raise DadoInvalido("Informe um preço maior que zero, com até duas casas decimais")
    if preco > PRECO_MAXIMO:
        raise DadoInvalido("O preço máximo é R$ 99.999,99")
    return preco.quantize(Decimal("0.01"))


def _nome_categoria(nome: str) -> str:
    nome = nome.strip()
    if not nome:
        raise DadoInvalido("Informe o nome da categoria")
    if len(nome) > TAMANHO_MAXIMO_NOME_CATEGORIA:
        raise DadoInvalido(f"O nome da categoria deve ter no máximo {TAMANHO_MAXIMO_NOME_CATEGORIA} caracteres")
    return nome


class GestaoCardapioService:
    """Cadastro de produtos e categorias (Administrador) e disponibilidade no dia (Funcionário e Administrador)."""

    def __init__(self, session: AsyncSession, cardapio: CardapioRepository, auditoria: AuditoriaService):
        self.session = session
        self.cardapio = cardapio
        self.auditoria = auditoria

    async def listar(self) -> list[CategoriaAdminOut]:
        """Categorias na ordem de exibição, cada uma com todos os seus produtos (inclusive inativos)."""
        produtos_por_categoria: dict[int, list[ProdutoAdminOut]] = {}
        for produto in await self.cardapio.todos_produtos():
            produtos_por_categoria.setdefault(produto.categoria_id, []).append(ProdutoAdminOut.model_validate(produto))
        return [
            CategoriaAdminOut(id=c.id, nome=c.nome, ordem=c.ordem, produtos=produtos_por_categoria.get(c.id, []))
            for c in await self.cardapio.categorias()
        ]

    # --- Produtos ---

    async def criar_produto(
        self, categoria_id: int, nome: str, descricao: str | None, preco: Decimal, usuario: Funcionario
    ) -> None:
        nome, descricao, preco = _nome_produto(nome), _descricao(descricao), _preco(preco)
        async with self._nome_unico(PRODUTO_REPETIDO):
            await self._categoria(categoria_id)
            if await self.cardapio.produto_com_nome(nome) is not None:
                raise Conflito(PRODUTO_REPETIDO)
            produto = Produto(
                categoria_id=categoria_id, nome=nome, descricao=descricao, preco=preco, ativo=True, disponivel=True
            )
            self.session.add(produto)
            await self.session.flush()
            self._auditar(usuario, Acao.CRIAR, "Produto", produto.id, None, ProdutoSnapshot.model_validate(produto))

    async def alterar_produto(self, produto_id: int, alteracoes: dict[str, Any], usuario: Funcionario) -> None:
        """`alteracoes` traz só os campos enviados (descrição nula apaga a descrição)."""
        async with self._nome_unico(PRODUTO_REPETIDO):
            produto = await self._produto(produto_id)
            antes = ProdutoSnapshot.model_validate(produto)
            if "nome" in alteracoes:
                nome = _nome_produto(alteracoes["nome"] or "")
                if await self.cardapio.produto_com_nome(nome, exceto_id=produto.id) is not None:
                    raise Conflito(PRODUTO_REPETIDO)
                produto.nome = nome
            if "descricao" in alteracoes:
                produto.descricao = _descricao(alteracoes["descricao"])
            if alteracoes.get("preco") is not None:
                produto.preco = _preco(alteracoes["preco"])
            if alteracoes.get("categoria_id") is not None:
                await self._categoria(alteracoes["categoria_id"])
                produto.categoria_id = alteracoes["categoria_id"]
            if alteracoes.get("ativo") is not None:
                produto.ativo = alteracoes["ativo"]
            await self.session.flush()
            self._auditar(usuario, Acao.ALTERAR, "Produto", produto.id, antes, ProdutoSnapshot.model_validate(produto))

    async def definir_disponibilidade(self, produto_id: int, disponivel: bool, usuario: Funcionario) -> Produto:
        """Esgotado no dia: vale para novos lançamentos; itens já lançados guardam seus próprios dados."""
        async with transacao(self.session):
            produto = await self._produto(produto_id)
            if not produto.ativo:
                raise Conflito("Produto inativo: reative-o no cadastro antes de mudar a disponibilidade")
            if produto.disponivel != disponivel:
                antes = ProdutoSnapshot.model_validate(produto)
                produto.disponivel = disponivel
                self._auditar(usuario, Acao.ALTERAR, "Produto", produto.id, antes, ProdutoSnapshot.model_validate(produto))
        return produto

    # --- Categorias ---

    async def criar_categoria(self, nome: str, usuario: Funcionario) -> None:
        nome = _nome_categoria(nome)
        async with self._nome_unico(CATEGORIA_REPETIDA):
            categorias = await self.cardapio.categorias(bloquear=True)
            if await self.cardapio.categoria_com_nome(nome) is not None:
                raise Conflito(CATEGORIA_REPETIDA)
            categoria = Categoria(nome=nome, ordem=max((c.ordem for c in categorias), default=-1) + 1)
            self.session.add(categoria)
            await self.session.flush()
            self._auditar(usuario, Acao.CRIAR, "Categoria", categoria.id, None, CategoriaSnapshot.model_validate(categoria))

    async def renomear_categoria(self, categoria_id: int, nome: str, usuario: Funcionario) -> None:
        nome = _nome_categoria(nome)
        async with self._nome_unico(CATEGORIA_REPETIDA):
            categoria = await self._categoria(categoria_id, bloquear=True)
            if await self.cardapio.categoria_com_nome(nome, exceto_id=categoria.id) is not None:
                raise Conflito(CATEGORIA_REPETIDA)
            antes = CategoriaSnapshot.model_validate(categoria)
            categoria.nome = nome
            await self.session.flush()
            self._auditar(usuario, Acao.ALTERAR, "Categoria", categoria.id, antes, CategoriaSnapshot.model_validate(categoria))

    async def mover_categoria(self, categoria_id: int, direcao: Literal["acima", "abaixo"], usuario: Funcionario) -> None:
        """Troca de posição com a vizinha e renumera de 0 a n-1 (elimina empates de ordem)."""
        async with transacao(self.session):
            categorias = await self.cardapio.categorias(bloquear=True)
            posicao = next((i for i, c in enumerate(categorias) if c.id == categoria_id), None)
            if posicao is None:
                raise RecursoNaoEncontrado("Categoria não encontrada")
            vizinha = posicao - 1 if direcao == "acima" else posicao + 1
            if 0 <= vizinha < len(categorias):
                categorias[posicao], categorias[vizinha] = categorias[vizinha], categorias[posicao]
            for ordem, categoria in enumerate(categorias):
                if categoria.ordem != ordem:
                    antes = CategoriaSnapshot.model_validate(categoria)
                    categoria.ordem = ordem
                    self._auditar(
                        usuario, Acao.ALTERAR, "Categoria", categoria.id, antes, CategoriaSnapshot.model_validate(categoria)
                    )

    async def excluir_categoria(self, categoria_id: int, usuario: Funcionario) -> None:
        try:
            async with transacao(self.session):
                categoria = await self._categoria(categoria_id, bloquear=True)
                if await self.cardapio.tem_produtos(categoria.id):
                    raise Conflito(CATEGORIA_COM_PRODUTOS)
                antes = CategoriaSnapshot.model_validate(categoria)
                await self.session.delete(categoria)
                await self.session.flush()
                self._auditar(usuario, Acao.EXCLUIR, "Categoria", categoria_id, antes, None)
        except IntegrityError:
            # Um produto foi cadastrado na categoria ao mesmo tempo: a chave estrangeira impede a exclusão.
            raise Conflito(CATEGORIA_COM_PRODUTOS) from None

    # --- Auxiliares ---

    def _nome_unico(self, mensagem: str):
        return _transacao_nome_unico(self.session, mensagem)

    async def _produto(self, produto_id: int) -> Produto:
        produto = await self.cardapio.obter_produto(produto_id)
        if produto is None:
            raise RecursoNaoEncontrado("Produto não encontrado")
        return produto

    async def _categoria(self, categoria_id: int, bloquear: bool = False) -> Categoria:
        categoria = await self.cardapio.obter_categoria(categoria_id, bloquear=bloquear)
        if categoria is None:
            raise RecursoNaoEncontrado("Categoria não encontrada")
        return categoria

    def _auditar(self, usuario: Funcionario, acao: Acao, entidade: str, entidade_id: int, antes, depois) -> None:
        self.auditoria.registrar(
            usuario_id=usuario.id, acao=acao, entidade=entidade, entidade_id=entidade_id, antes=antes, depois=depois
        )


@asynccontextmanager
async def _transacao_nome_unico(session: AsyncSession, mensagem: str) -> AsyncIterator[None]:
    """Transação que traduz a violação do índice único de nome (corrida entre dois cadastros) na mensagem certa."""
    try:
        async with transacao(session):
            yield
    except IntegrityError as erro:
        raise Conflito(mensagem) from erro
