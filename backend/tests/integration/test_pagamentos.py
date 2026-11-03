"""Cenários da spec `pagamentos`: taxa de serviço, registro, fechamento, remoção, auditoria e acesso."""

import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.models import Comanda, ItemComanda, LogAuditoria, Pagamento, Produto
from tests.conftest import SEGREDO_TESTE
from tests.integration.comandas_util import abrir, adicionar, pagar, pre_conta, preparar, taxa
from tests.integration.fabricas import cabecalho_de, cliente_api


@pytest.fixture
async def cenario(session: AsyncSession):
    """Comanda da mesa 2 em PRE_CONTA: subtotal R$ 100,00, taxa 10%, total R$ 110,00."""
    amb = await preparar(session)
    await session.execute(update(Produto).where(Produto.nome == "Arroz Branco").values(preco=Decimal("100.00")))
    await session.commit()
    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, amb.gabriela, amb.mesas[2])).json()["id"]
        await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Arroz Branco"])
        await session.execute(update(ItemComanda).values(status="ENTREGUE"))
        await session.commit()
        await pre_conta(cliente, amb.gabriela, comanda_id)
        yield amb, cliente, comanda_id


async def _comanda(cliente, amb, comanda_id):
    return (await cliente.get(f"/comandas/{comanda_id}", headers=cabecalho_de(amb.gabriela))).json()


# --- Taxa de serviço ---


async def test_cliente_recusa_a_taxa(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario

    comanda = (await taxa(cliente, amb.gabriela, comanda_id, aplicada=False)).json()

    assert (comanda["taxa_servico"]["aplicada"], comanda["total"]) == (False, "100.00")
    log = (await session.execute(select(LogAuditoria).where(LogAuditoria.acao == "ALTERAR", LogAuditoria.entidade == "Comanda"))).scalars().all()[-1]
    assert (log.dados_antes["taxa_servico_aplicada"], log.dados_depois["taxa_servico_aplicada"]) == (True, False)


async def test_percentual_ajustado(cenario):
    amb, cliente, comanda_id = cenario

    comanda = (await taxa(cliente, amb.gabriela, comanda_id, percentual="12")).json()

    assert (comanda["taxa_servico"]["percentual"], comanda["taxa_servico"]["valor"], comanda["total"]) == ("12.00", "12.00", "112.00")


@pytest.mark.parametrize("percentual", ["-1", "100.01"])
async def test_percentual_invalido(cenario, percentual):
    amb, cliente, comanda_id = cenario

    resposta = await taxa(cliente, amb.gabriela, comanda_id, percentual=percentual)

    assert (resposta.status_code, resposta.json()) == (422, {"detalhe": "O percentual da taxa de serviço deve estar entre 0 e 100"})
    assert (await _comanda(cliente, amb, comanda_id))["total"] == "110.00"


async def test_taxa_nao_fica_abaixo_do_ja_pago(cenario):
    amb, cliente, comanda_id = cenario
    await pagar(cliente, amb.gabriela, comanda_id, "PIX", "105.00")

    resposta = await taxa(cliente, amb.gabriela, comanda_id, aplicada=False)

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "O total não pode ficar menor que o valor já pago (R$ 105,00)"})


async def test_taxa_fora_da_pre_conta(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Refrigerante Lata"])  # volta para ABERTA

    resposta = await taxa(cliente, amb.gabriela, comanda_id, aplicada=False)

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "A taxa de serviço só pode ser alterada na pré-conta"})


# --- Registro de pagamento e fechamento ---


async def test_pagamento_parcial_e_quitacao(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario

    parcial = (await pagar(cliente, amb.gabriela, comanda_id, "PIX", "50.00")).json()
    assert (parcial["status"], parcial["restante"]) == ("PRE_CONTA", "60.00")

    final = (await pagar(cliente, amb.admin, comanda_id, "CREDITO", "60.00")).json()
    assert (final["status"], final["pago"], final["restante"]) == ("FECHADA", "110.00", "0.00")
    assert [(p["forma"], p["valor"]) for p in final["pagamentos"]] == [("PIX", "50.00"), ("CREDITO", "60.00")]

    mapa = (await cliente.get("/mesas", headers=cabecalho_de(amb.gabriela))).json()
    assert next(m["status"] for m in mapa if m["numero"] == 2) == "LIVRE"
    fechada_em = (await session.execute(select(Comanda.fechada_em).where(Comanda.id == comanda_id))).scalar_one()
    assert fechada_em is not None


async def test_pagamento_unico_do_total_em_dinheiro(cenario):
    amb, cliente, comanda_id = cenario

    comanda = (await pagar(cliente, amb.gabriela, comanda_id, "DINHEIRO", "110.00")).json()

    assert comanda["status"] == "FECHADA"


async def test_valor_acima_do_restante(cenario):
    amb, cliente, comanda_id = cenario
    await pagar(cliente, amb.gabriela, comanda_id, "PIX", "50.00")

    resposta = await pagar(cliente, amb.gabriela, comanda_id, "PIX", "70.00")

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "O valor excede o restante a pagar (R$ 60,00)"})


@pytest.mark.parametrize("valor", ["0", "-5"])
async def test_valor_invalido(cenario, valor):
    amb, cliente, comanda_id = cenario

    resposta = await pagar(cliente, amb.gabriela, comanda_id, "PIX", valor)

    assert (resposta.status_code, resposta.json()) == (422, {"detalhe": "O valor do pagamento deve ser maior que zero"})


async def test_forma_invalida(cenario):
    amb, cliente, comanda_id = cenario

    resposta = await pagar(cliente, amb.gabriela, comanda_id, "CHEQUE", "10.00")

    assert (resposta.status_code, resposta.json()["detalhe"]) == (422, "Dados inválidos")


async def test_pagamento_sem_pre_conta(cenario):
    amb, cliente, comanda_id = cenario
    await adicionar(cliente, amb.gabriela, comanda_id, amb.produtos["Refrigerante Lata"])  # volta para ABERTA

    resposta = await pagar(cliente, amb.gabriela, comanda_id, "PIX", "10.00")

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "Gere a pré-conta antes de registrar pagamentos"})


async def test_pagamento_auditado(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario

    await pagar(cliente, amb.gabriela, comanda_id, "DEBITO", "30.00")

    log = (await session.execute(select(LogAuditoria).where(LogAuditoria.acao == "PAGAR"))).scalar_one()
    assert (log.usuario_id, log.dados_depois["forma"], log.dados_depois["valor"]) == (amb.gabriela.id, "DEBITO", "30.00")


async def test_contabilidade_nao_registra_pagamento(cenario):
    amb, cliente, comanda_id = cenario

    resposta = await pagar(cliente, amb.contabilidade, comanda_id, "PIX", "10.00")

    assert resposta.status_code == 403


async def test_pagamentos_simultaneos_nao_ultrapassam_o_total(cenario, session: AsyncSession, engine: AsyncEngine):
    amb, _, comanda_id = cenario
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    async def pagar_em_sessao_propria(usuario):
        async with fabrica() as s, cliente_api(s) as cliente:
            return (await pagar(cliente, usuario, comanda_id, "PIX", "80.00")).status_code

    codigos = await asyncio.gather(*(pagar_em_sessao_propria(u) for u in (amb.gabriela, amb.admin)))

    assert sorted(codigos) == [200, 409]
    total_pago = sum(v for v in (await session.execute(select(Pagamento.valor))).scalars())
    assert total_pago == Decimal("80.00")


# --- Remoção ---


async def test_remover_pagamento_parcial(cenario, session: AsyncSession):
    amb, cliente, comanda_id = cenario
    pagamento_id = (await pagar(cliente, amb.gabriela, comanda_id, "PIX", "50.00")).json()["pagamentos"][0]["id"]

    resposta = await cliente.delete(f"/comandas/{comanda_id}/pagamentos/{pagamento_id}", headers=cabecalho_de(amb.gabriela))

    assert (resposta.json()["pagamentos"], resposta.json()["restante"]) == ([], "110.00")
    log = (await session.execute(select(LogAuditoria).where(LogAuditoria.acao == "REMOVER_PAGAMENTO"))).scalar_one()
    assert (log.dados_antes["valor"], log.dados_antes["forma"], log.dados_depois) == ("50.00", "PIX", None)


async def test_nao_remove_pagamento_de_comanda_fechada(cenario):
    amb, cliente, comanda_id = cenario
    pagamento_id = (await pagar(cliente, amb.gabriela, comanda_id, "PIX", "110.00")).json()["pagamentos"][0]["id"]

    resposta = await cliente.delete(f"/comandas/{comanda_id}/pagamentos/{pagamento_id}", headers=cabecalho_de(amb.gabriela))

    assert (resposta.status_code, resposta.json()) == (409, {"detalhe": "Pagamentos de comanda fechada não podem ser removidos"})


async def test_pagamento_inexistente(cenario):
    amb, cliente, comanda_id = cenario

    resposta = await cliente.delete(f"/comandas/{comanda_id}/pagamentos/999999", headers=cabecalho_de(amb.gabriela))

    assert (resposta.status_code, resposta.json()) == (404, {"detalhe": "Pagamento não encontrado"})


def test_rotas_no_swagger():
    rotas = create_app(Settings(_env_file=None, jwt_secret=SEGREDO_TESTE)).openapi()["paths"]

    assert set(rotas["/comandas/{comanda_id}/pre-conta"]) == {"post"}
    assert set(rotas["/comandas/{comanda_id}/taxa-servico"]) == {"patch"}
    assert set(rotas["/comandas/{comanda_id}/pagamentos"]) == {"post"}
    assert set(rotas["/comandas/{comanda_id}/pagamentos/{pagamento_id}"]) == {"delete"}
    assert set(rotas["/comandas/{comanda_id}/cancelar"]) == {"post"}
