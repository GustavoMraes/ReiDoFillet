"""Cálculo financeiro da comanda: a mesma regra para a tela e para as validações de pagamento."""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.models.enums import StatusComanda, StatusItem

CENTAVOS = Decimal("0.01")
ZERO = Decimal("0.00")
STATUS_COM_TAXA = (StatusComanda.PRE_CONTA, StatusComanda.FECHADA)


def em_centavos(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def em_reais(valor: Decimal) -> str:
    """Formato para mensagens ao usuário: R$ 1.234,56."""
    inteiro, centavos = f"{em_centavos(valor):.2f}".split(".")
    return f"R$ {int(inteiro):,}".replace(",", ".") + f",{centavos}"


@dataclass(frozen=True)
class ResumoFinanceiro:
    subtotal: Decimal
    taxa_aplicada: bool
    taxa_percentual: Decimal | None
    taxa_valor: Decimal
    total: Decimal
    pago: Decimal
    restante: Decimal


def calcular(
    status: str,
    itens: Iterable[tuple[Decimal, int, str]],
    taxa_percentual: Decimal | None,
    taxa_aplicada: bool,
    pagamentos: Iterable[Decimal],
) -> ResumoFinanceiro:
    """itens: (preço unitário, quantidade, status). A taxa só vale na pré-conta e na comanda fechada."""
    subtotal = sum(
        (em_centavos(preco * quantidade) for preco, quantidade, situacao in itens if situacao != StatusItem.CANCELADO),
        ZERO,
    )
    cobra_taxa = status in STATUS_COM_TAXA and taxa_aplicada and taxa_percentual is not None
    taxa = em_centavos(subtotal * taxa_percentual / 100) if cobra_taxa else ZERO
    total = subtotal + taxa
    pago = sum((em_centavos(valor) for valor in pagamentos), ZERO)
    return ResumoFinanceiro(
        subtotal=subtotal,
        taxa_aplicada=taxa_aplicada,
        taxa_percentual=taxa_percentual,
        taxa_valor=taxa,
        total=total,
        pago=pago,
        restante=max(total - pago, ZERO),
    )
