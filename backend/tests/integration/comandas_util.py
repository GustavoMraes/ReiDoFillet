"""Apoio aos testes de comanda: ambiente com o seed e atalhos para a API."""

from dataclasses import dataclass
from decimal import Decimal

from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Funcionario, Mesa, Produto
from scripts.seed import seed
from tests.integration.fabricas import cabecalho_de


@dataclass(frozen=True)
class UsuarioRef:
    """Cópia simples do funcionário: objetos do ORM expiram quando um teste provoca rollback na sessão."""

    id: int
    perfil: str


@dataclass(frozen=True)
class ProdutoRef:
    id: int
    nome: str
    preco: Decimal


@dataclass
class Ambiente:
    gabriela: UsuarioRef
    admin: UsuarioRef
    contabilidade: UsuarioRef
    mesas: dict[int, int]  # número -> id
    produtos: dict[str, ProdutoRef]  # nome -> produto


async def preparar(session: AsyncSession) -> Ambiente:
    await seed(session)
    usuarios = {f.login: UsuarioRef(f.id, f.perfil) for f in (await session.execute(select(Funcionario))).scalars()}
    mesas = dict((await session.execute(select(Mesa.numero, Mesa.id))).all())
    produtos = {p.nome: ProdutoRef(p.id, p.nome, p.preco) for p in (await session.execute(select(Produto))).scalars()}
    return Ambiente(
        gabriela=usuarios["gabriela"],
        admin=usuarios["admin"],
        contabilidade=usuarios["contabilidade"],
        mesas=mesas,
        produtos=produtos,
    )


async def abrir(cliente: AsyncClient, usuario: UsuarioRef, mesa_id: int) -> Response:
    return await cliente.post(f"/mesas/{mesa_id}/comanda", headers=cabecalho_de(usuario))


async def pre_conta(cliente: AsyncClient, usuario: UsuarioRef, comanda_id: int) -> Response:
    return await cliente.post(f"/comandas/{comanda_id}/pre-conta", headers=cabecalho_de(usuario))


async def pagar(cliente: AsyncClient, usuario: UsuarioRef, comanda_id: int, forma: str, valor: str) -> Response:
    return await cliente.post(
        f"/comandas/{comanda_id}/pagamentos", json={"forma": forma, "valor": valor}, headers=cabecalho_de(usuario)
    )


async def taxa(cliente: AsyncClient, usuario: UsuarioRef, comanda_id: int, **dados) -> Response:
    return await cliente.patch(f"/comandas/{comanda_id}/taxa-servico", json=dados, headers=cabecalho_de(usuario))


async def enviar(cliente: AsyncClient, usuario: UsuarioRef, comanda_id: int) -> Response:
    return await cliente.post(f"/comandas/{comanda_id}/enviar", headers=cabecalho_de(usuario))


async def adicionar(
    cliente: AsyncClient, usuario: UsuarioRef, comanda_id: int, produto: ProdutoRef, quantidade: int = 1, observacao: str = ""
) -> Response:
    return await cliente.post(
        f"/comandas/{comanda_id}/itens",
        json={"produto_id": produto.id, "quantidade": quantidade, "observacao": observacao},
        headers=cabecalho_de(usuario),
    )
