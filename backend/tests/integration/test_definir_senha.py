"""Cenários da spec `autenticacao`: definição de senha de funcionário."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguranca import verificar_senha
from app.models import LogAuditoria
from app.repositories.funcionario import FuncionarioRepository
from app.services.funcionario import FuncionarioNaoEncontrado, SenhaCurta
from scripts.definir_senha import SenhasDiferentes, executar
from tests.integration.fabricas import criar_funcionario
from tests.integration.test_login import _servico as servico_login

NOVA_SENHA = "nova-senha-forte"


async def _logs(session: AsyncSession) -> list[LogAuditoria]:
    return list((await session.execute(select(LogAuditoria))).scalars())


async def test_senha_valida_permite_login_e_e_auditada(session: AsyncSession):
    gabriela = await criar_funcionario(session, "gabriela", senha=None)

    await executar(session, "gabriela", NOVA_SENHA, NOVA_SENHA)

    atualizado = await FuncionarioRepository(session).obter_por_login("gabriela")
    assert atualizado.senha_hash != NOVA_SENHA
    assert verificar_senha(NOVA_SENHA, atualizado.senha_hash)
    [log] = await _logs(session)
    assert (log.acao, log.usuario_id, log.entidade_id) == ("DEFINIR_SENHA", None, str(gabriela.id))
    assert log.dados_antes is None and log.dados_depois is None

    sessao = await servico_login(session).login("gabriela", NOVA_SENHA)
    assert sessao.funcionario.id == gabriela.id


@pytest.mark.parametrize(
    ("login", "senha", "confirmacao", "erro", "mensagem"),
    [
        ("gabriela", "curta12", "curta12", SenhaCurta, "A senha deve ter no mínimo 8 caracteres"),
        ("ninguem", NOVA_SENHA, NOVA_SENHA, FuncionarioNaoEncontrado, "Funcionário não encontrado"),
        ("gabriela", NOVA_SENHA, "outra-senha-forte", SenhasDiferentes, "As senhas digitadas não conferem"),
    ],
    ids=["senha-curta", "funcionario-inexistente", "confirmacao-diferente"],
)
async def test_senha_nao_e_alterada_em_caso_de_erro(session: AsyncSession, login, senha, confirmacao, erro, mensagem):
    await criar_funcionario(session, "gabriela", senha=None)

    with pytest.raises(erro) as excecao:
        await executar(session, login, senha, confirmacao)

    assert excecao.value.mensagem == mensagem
    assert (await FuncionarioRepository(session).obter_por_login("gabriela")).senha_hash == "!"
    assert await _logs(session) == []
