from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import Relogio, get_relogio
from app.db.session import get_session
from app.models import Funcionario
from app.models.enums import Perfil
from app.repositories.auditoria import AuditoriaRepository
from app.repositories.relatorio import RelatorioRepository
from app.routers.dependencias import exigir_perfis
from app.schemas.relatorio import OpcoesAuditoriaOut, PaginaAuditoriaOut, RelatorioFinanceiroOut, RelatorioOperacionalOut
from app.services.auditoria import AuditoriaService
from app.services.relatorio import RelatorioService

router = APIRouter(prefix="/relatorios", tags=["Relatórios"])
router_auditoria = APIRouter(prefix="/auditoria", tags=["Auditoria"])

ERROS = {422: {"description": "Período inválido (final antes do inicial ou mais de 366 dias)"}}


def get_relatorio_service(
    session: AsyncSession = Depends(get_session), relogio: Relogio = Depends(get_relogio)
) -> RelatorioService:
    return RelatorioService(
        session, RelatorioRepository(session), AuditoriaService(AuditoriaRepository(session), relogio), relogio
    )


@router.get("/operacional", response_model=RelatorioOperacionalOut, responses=ERROS)
async def relatorio_operacional(
    inicio: date | None = None,
    fim: date | None = None,
    usuario: Funcionario = Depends(exigir_perfis(Perfil.ADMIN)),
    service: RelatorioService = Depends(get_relatorio_service),
) -> RelatorioOperacionalOut:
    """Comandas abertas no período (padrão: hoje, em São Paulo): situações, faturamento, produtos e movimento."""
    return await service.operacional(inicio, fim, usuario)


@router_auditoria.get("", response_model=PaginaAuditoriaOut, responses=ERROS)
async def consultar_auditoria(
    inicio: date | None = None,
    fim: date | None = None,
    usuario_id: int | None = Query(None, description="0 = operações do sistema (sem usuário)"),
    acao: str | None = None,
    entidade: str | None = None,
    pagina: int = Query(1, ge=1),
    usuario: Funcionario = Depends(exigir_perfis(Perfil.ADMIN, Perfil.CONTABILIDADE)),
    service: RelatorioService = Depends(get_relatorio_service),
) -> PaginaAuditoriaOut:
    """Histórico de auditoria do período, mais recente primeiro, 50 por página. Somente leitura."""
    return await service.auditoria_paginada(inicio, fim, usuario_id, acao, entidade, pagina, usuario)


@router_auditoria.get(
    "/opcoes",
    response_model=OpcoesAuditoriaOut,
    dependencies=[Depends(exigir_perfis(Perfil.ADMIN, Perfil.CONTABILIDADE))],
)
async def opcoes_da_auditoria(service: RelatorioService = Depends(get_relatorio_service)) -> OpcoesAuditoriaOut:
    """Usuários, ações e entidades para os filtros da consulta da auditoria."""
    return await service.opcoes_auditoria()


@router.get("/financeiro", response_model=RelatorioFinanceiroOut, responses=ERROS)
async def relatorio_financeiro(
    inicio: date | None = None,
    fim: date | None = None,
    usuario: Funcionario = Depends(exigir_perfis(Perfil.ADMIN, Perfil.CONTABILIDADE)),
    service: RelatorioService = Depends(get_relatorio_service),
) -> RelatorioFinanceiroOut:
    """Comandas fechadas no período, com totais e valores por forma de pagamento. Somente leitura."""
    return await service.financeiro(inicio, fim, usuario)
