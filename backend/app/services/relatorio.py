"""Relatórios operacional e financeiro (HU06, HU07): leitura por período, com os totais da regra única da comanda."""

import math
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import Relogio, fuso_local, para_exibicao
from app.db.transacao import transacao
from app.models import Comanda, Funcionario
from app.models.enums import STATUS_COMANDA_ATIVA, FormaPagamento, StatusComanda, StatusItem
from app.repositories.relatorio import RelatorioRepository, ids_abertas_entre, ids_fechadas_entre
from app.schemas.relatorio import (
    ComandaFechadaOut,
    MovimentoDiaOut,
    MovimentoHoraOut,
    OpcoesAuditoriaOut,
    PaginaAuditoriaOut,
    PeriodoOut,
    ProdutoVendidoOut,
    RegistroAuditoriaOut,
    RelatorioFinanceiroOut,
    RelatorioOperacionalOut,
    SituacoesOut,
    TotaisFinanceirosOut,
    UsuarioOpcaoOut,
    ValorPorFormaOut,
)
from app.schemas.snapshots import ConsultaSnapshot
from app.services.auditoria import Acao, AuditoriaService
from app.services.financeiro import ZERO, ResumoFinanceiro, calcular, em_centavos
from app.services.periodo import Periodo, periodo

PRODUTOS_NO_RANKING = 10
REGISTROS_POR_PAGINA = 50


class RelatorioService:
    def __init__(self, session: AsyncSession, repositorio: RelatorioRepository, auditoria: AuditoriaService, relogio: Relogio):
        self.session = session
        self.repositorio = repositorio
        self.auditoria = auditoria
        self.relogio = relogio

    async def operacional(self, inicio: date | None, fim: date | None, usuario: Funcionario) -> RelatorioOperacionalOut:
        """Comandas abertas no período; valores, tempos e produtos só das que já fecharam."""
        p = periodo(inicio, fim, self.relogio.agora())
        ids = ids_abertas_entre(p.de, p.ate)
        comandas = [c for c, _, _ in await self.repositorio.comandas(ids)]
        itens = await self.repositorio.itens(ids)
        resumos = self._resumos(comandas, itens, await self.repositorio.pagamentos(ids))

        fechadas = [c for c in comandas if c.status == StatusComanda.FECHADA]
        faturamento = sum((resumos[c.id].total for c in fechadas), ZERO)
        minutos = [(c.fechada_em - c.aberta_em).total_seconds() / 60 for c in fechadas]

        vendidos: dict[int, ProdutoVendidoOut] = {}
        ids_fechadas = {c.id for c in fechadas}
        for item, nome in itens:
            if item.comanda_id in ids_fechadas and item.status != StatusItem.CANCELADO:
                atual = vendidos.setdefault(
                    item.produto_id, ProdutoVendidoOut(produto_id=item.produto_id, nome=nome, quantidade=0, valor=ZERO)
                )
                atual.quantidade += item.quantidade
                atual.valor += em_centavos(item.preco_unitario * item.quantidade)
        ranking = sorted(vendidos.values(), key=lambda p: (-p.quantidade, -p.valor, p.nome))[:PRODUTOS_NO_RANKING]

        fuso = fuso_local()
        comandas_por_dia = Counter(c.aberta_em.astimezone(fuso).date() for c in comandas)
        faturamento_por_dia: dict[date, Decimal] = defaultdict(lambda: ZERO)
        for c in fechadas:
            faturamento_por_dia[c.aberta_em.astimezone(fuso).date()] += resumos[c.id].total
        comandas_por_hora = Counter(c.aberta_em.astimezone(fuso).hour for c in comandas)

        relatorio = RelatorioOperacionalOut(
            periodo=PeriodoOut(inicio=p.inicio, fim=p.fim),
            comandas=SituacoesOut(
                em_aberto=sum(1 for c in comandas if c.status in STATUS_COMANDA_ATIVA),
                fechadas=len(fechadas),
                canceladas=sum(1 for c in comandas if c.status == StatusComanda.CANCELADA),
                total=len(comandas),
            ),
            faturamento=faturamento,
            ticket_medio=em_centavos(faturamento / len(fechadas)) if fechadas else None,
            tempo_medio_minutos=(
                int(Decimal(sum(minutos) / len(minutos)).quantize(Decimal(1), rounding=ROUND_HALF_UP)) if minutos else None
            ),
            produtos=ranking,
            por_dia=[
                MovimentoDiaOut(data=dia, comandas=comandas_por_dia[dia], faturamento=faturamento_por_dia[dia])
                for dia in _dias(p)
            ],
            por_hora=[MovimentoHoraOut(hora=hora, comandas=comandas_por_hora[hora]) for hora in range(24)],
        )
        await self._registrar_consulta(usuario, "operacional", p)
        return relatorio

    async def financeiro(self, inicio: date | None, fim: date | None, usuario: Funcionario) -> RelatorioFinanceiroOut:
        """Comandas fechadas no período, em ordem de fechamento, com totais por forma de pagamento."""
        p = periodo(inicio, fim, self.relogio.agora())
        ids = ids_fechadas_entre(p.de, p.ate)
        linhas = await self.repositorio.comandas(ids)
        pagamentos = await self.repositorio.pagamentos(ids)
        resumos = self._resumos([c for c, _, _ in linhas], await self.repositorio.itens(ids), pagamentos)

        pagamentos_por_comanda = defaultdict(list)
        por_forma = {forma: ZERO for forma in FormaPagamento}
        for pagamento in pagamentos:
            pagamentos_por_comanda[pagamento.comanda_id].append(
                ValorPorFormaOut(forma=pagamento.forma, valor=pagamento.valor)
            )
            por_forma[FormaPagamento(pagamento.forma)] += pagamento.valor

        comandas = [
            ComandaFechadaOut(
                id=comanda.id,
                mesa_numero=numero,
                responsavel=responsavel,
                aberta_em=para_exibicao(comanda.aberta_em),
                fechada_em=para_exibicao(comanda.fechada_em),
                subtotal=resumos[comanda.id].subtotal,
                taxa_servico=resumos[comanda.id].taxa_valor,
                total=resumos[comanda.id].total,
                pagamentos=pagamentos_por_comanda[comanda.id],
            )
            for comanda, numero, responsavel in linhas
        ]
        relatorio = RelatorioFinanceiroOut(
            periodo=PeriodoOut(inicio=p.inicio, fim=p.fim),
            totais=TotaisFinanceirosOut(
                comandas=len(comandas),
                subtotal=sum((c.subtotal for c in comandas), ZERO),
                taxa_servico=sum((c.taxa_servico for c in comandas), ZERO),
                total=sum((c.total for c in comandas), ZERO),
                por_forma=[ValorPorFormaOut(forma=forma, valor=valor) for forma, valor in por_forma.items()],
            ),
            comandas=comandas,
        )
        await self._registrar_consulta(usuario, "financeiro", p)
        return relatorio

    @staticmethod
    def _resumos(comandas: list[Comanda], itens, pagamentos) -> dict[int, ResumoFinanceiro]:
        itens_por_comanda = defaultdict(list)
        for item, _ in itens:
            itens_por_comanda[item.comanda_id].append((item.preco_unitario, item.quantidade, item.status))
        pagos_por_comanda = defaultdict(list)
        for pagamento in pagamentos:
            pagos_por_comanda[pagamento.comanda_id].append(pagamento.valor)
        return {
            c.id: calcular(
                c.status, itens_por_comanda[c.id], c.taxa_servico_pct, c.taxa_servico_aplicada, pagos_por_comanda[c.id]
            )
            for c in comandas
        }

    async def auditoria_paginada(
        self,
        inicio: date | None,
        fim: date | None,
        usuario_id: int | None,
        acao: str | None,
        entidade: str | None,
        pagina: int,
        usuario: Funcionario,
    ) -> PaginaAuditoriaOut:
        """Histórico de auditoria do período, mais recente primeiro, em páginas de 50 (somente leitura)."""
        p = periodo(inicio, fim, self.relogio.agora())
        registros, total = await self.auditoria.repositorio.consultar(
            p.de, p.ate, usuario_id, acao, entidade, (pagina - 1) * REGISTROS_POR_PAGINA, REGISTROS_POR_PAGINA
        )
        resultado = PaginaAuditoriaOut(
            registros=[
                RegistroAuditoriaOut(
                    id=log.id,
                    criado_em=para_exibicao(log.criado_em),
                    usuario_id=log.usuario_id,
                    usuario=nome,
                    acao=log.acao,
                    entidade=log.entidade,
                    entidade_id=log.entidade_id,
                    dados_antes=log.dados_antes,
                    dados_depois=log.dados_depois,
                )
                for log, nome in registros
            ],
            total=total,
            pagina=pagina,
            paginas=max(1, math.ceil(total / REGISTROS_POR_PAGINA)),
        )
        # Gravado depois da leitura: a consulta não aparece na própria página.
        await self._registrar_consulta(
            usuario,
            "auditoria",
            ConsultaSnapshot(
                inicio=p.inicio, fim=p.fim, usuario_id=usuario_id, acao=acao, entidade=entidade, pagina=pagina
            ),
        )
        return resultado

    async def opcoes_auditoria(self) -> OpcoesAuditoriaOut:
        """Valores dos filtros da auditoria (não é registrada: só monta a tela)."""
        return OpcoesAuditoriaOut(
            usuarios=[UsuarioOpcaoOut(id=i, nome=nome) for i, nome in await self.auditoria.repositorio.usuarios()],
            acoes=[acao.value for acao in Acao],
            entidades=await self.auditoria.repositorio.entidades(),
        )

    async def _registrar_consulta(self, usuario: Funcionario, consulta: str, filtros: Periodo | ConsultaSnapshot) -> None:
        """HU07: toda consulta fica no histórico auditável (gravada depois da leitura, em transação própria)."""
        if isinstance(filtros, Periodo):
            filtros = ConsultaSnapshot(inicio=filtros.inicio, fim=filtros.fim)
        async with transacao(self.session):
            self.auditoria.registrar(
                usuario_id=usuario.id,
                acao=Acao.CONSULTAR,
                entidade="Relatorio",
                entidade_id=consulta,
                antes=None,
                depois=filtros,
            )


def _dias(p: Periodo) -> list[date]:
    return [p.inicio + timedelta(days=n) for n in range((p.fim - p.inicio).days + 1)]
