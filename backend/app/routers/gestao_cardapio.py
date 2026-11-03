from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import Relogio, get_relogio
from app.db.session import get_session
from app.models import Funcionario
from app.models.enums import Perfil
from app.repositories.auditoria import AuditoriaRepository
from app.repositories.cardapio import CardapioRepository
from app.routers.dependencias import exigir_perfis
from app.schemas.cardapio import (
    CategoriaAdminOut,
    CategoriaIn,
    DisponibilidadeIn,
    MoverCategoriaIn,
    ProdutoAdminOut,
    ProdutoAlteracaoIn,
    ProdutoIn,
)
from app.services.auditoria import AuditoriaService
from app.services.gestao_cardapio import GestaoCardapioService

router = APIRouter(tags=["Gestão do cardápio"])

administrador = exigir_perfis(Perfil.ADMIN)
atendente = exigir_perfis(Perfil.FUNCIONARIO, Perfil.ADMIN)

ERROS = {
    404: {"description": "Produto ou categoria não encontrado"},
    409: {"description": "Nome repetido, categoria com produtos ou produto inativo"},
    422: {"description": "Dados inválidos"},
}


def get_gestao_cardapio_service(
    session: AsyncSession = Depends(get_session), relogio: Relogio = Depends(get_relogio)
) -> GestaoCardapioService:
    return GestaoCardapioService(
        session, CardapioRepository(session), AuditoriaService(AuditoriaRepository(session), relogio)
    )


@router.get("/admin/cardapio", response_model=list[CategoriaAdminOut], dependencies=[Depends(administrador)])
async def cardapio_completo(service: GestaoCardapioService = Depends(get_gestao_cardapio_service)) -> list[CategoriaAdminOut]:
    """Categorias na ordem de exibição com todos os produtos, inclusive inativos."""
    return await service.listar()


@router.post(
    "/admin/produtos", response_model=list[CategoriaAdminOut], status_code=status.HTTP_201_CREATED, responses=ERROS
)
async def criar_produto(
    dados: ProdutoIn,
    usuario: Funcionario = Depends(administrador),
    service: GestaoCardapioService = Depends(get_gestao_cardapio_service),
) -> list[CategoriaAdminOut]:
    """Cadastra um produto ativo e disponível; devolve o cardápio completo atualizado."""
    await service.criar_produto(dados.categoria_id, dados.nome, dados.descricao, dados.preco, usuario)
    return await service.listar()


@router.patch("/admin/produtos/{produto_id}", response_model=list[CategoriaAdminOut], responses=ERROS)
async def alterar_produto(
    produto_id: int,
    dados: ProdutoAlteracaoIn,
    usuario: Funcionario = Depends(administrador),
    service: GestaoCardapioService = Depends(get_gestao_cardapio_service),
) -> list[CategoriaAdminOut]:
    """Altera só os campos enviados (nome, descrição, preço, categoria, ativo). Itens já lançados não mudam."""
    await service.alterar_produto(produto_id, dados.model_dump(exclude_unset=True), usuario)
    return await service.listar()


@router.patch("/produtos/{produto_id}/disponibilidade", response_model=ProdutoAdminOut, responses=ERROS)
async def definir_disponibilidade(
    produto_id: int,
    dados: DisponibilidadeIn,
    usuario: Funcionario = Depends(atendente),
    service: GestaoCardapioService = Depends(get_gestao_cardapio_service),
) -> ProdutoAdminOut:
    """Marca um produto ativo como esgotado (indisponível) ou disponível novamente."""
    return ProdutoAdminOut.model_validate(await service.definir_disponibilidade(produto_id, dados.disponivel, usuario))


@router.post(
    "/admin/categorias", response_model=list[CategoriaAdminOut], status_code=status.HTTP_201_CREATED, responses=ERROS
)
async def criar_categoria(
    dados: CategoriaIn,
    usuario: Funcionario = Depends(administrador),
    service: GestaoCardapioService = Depends(get_gestao_cardapio_service),
) -> list[CategoriaAdminOut]:
    """Cria uma categoria no fim da ordem de exibição."""
    await service.criar_categoria(dados.nome, usuario)
    return await service.listar()


@router.patch("/admin/categorias/{categoria_id}", response_model=list[CategoriaAdminOut], responses=ERROS)
async def renomear_categoria(
    categoria_id: int,
    dados: CategoriaIn,
    usuario: Funcionario = Depends(administrador),
    service: GestaoCardapioService = Depends(get_gestao_cardapio_service),
) -> list[CategoriaAdminOut]:
    await service.renomear_categoria(categoria_id, dados.nome, usuario)
    return await service.listar()


@router.post("/admin/categorias/{categoria_id}/mover", response_model=list[CategoriaAdminOut], responses=ERROS)
async def mover_categoria(
    categoria_id: int,
    dados: MoverCategoriaIn,
    usuario: Funcionario = Depends(administrador),
    service: GestaoCardapioService = Depends(get_gestao_cardapio_service),
) -> list[CategoriaAdminOut]:
    """Troca a posição da categoria com a vizinha de cima ou de baixo."""
    await service.mover_categoria(categoria_id, dados.direcao, usuario)
    return await service.listar()


@router.delete("/admin/categorias/{categoria_id}", response_model=list[CategoriaAdminOut], responses=ERROS)
async def excluir_categoria(
    categoria_id: int,
    usuario: Funcionario = Depends(administrador),
    service: GestaoCardapioService = Depends(get_gestao_cardapio_service),
) -> list[CategoriaAdminOut]:
    """Exclui uma categoria sem nenhum produto (ativo ou inativo)."""
    await service.excluir_categoria(categoria_id, usuario)
    return await service.listar()
