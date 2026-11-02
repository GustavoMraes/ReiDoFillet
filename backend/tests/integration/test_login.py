"""Cenários da spec `autenticacao`: login, credenciais inválidas, bloqueio e auditoria de login."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.seguranca import decodificar_token
from app.core.tempo import RelogioSistema
from app.models import LogAuditoria
from app.repositories.auditoria import AuditoriaRepository
from app.repositories.funcionario import FuncionarioRepository
from app.services.auditoria import AuditoriaService
from app.services.autenticacao import AuthService, CredenciaisInvalidas, UsuarioBloqueado
from tests.conftest import SEGREDO_TESTE
from tests.integration.fabricas import SENHA_PADRAO, criar_funcionario


def _servico(session: AsyncSession) -> AuthService:
    relogio = RelogioSistema()
    return AuthService(
        session,
        FuncionarioRepository(session),
        AuditoriaService(AuditoriaRepository(session), relogio),
        relogio,
        Settings(_env_file=None, jwt_secret=SEGREDO_TESTE),
    )


async def _logs(session: AsyncSession) -> list[LogAuditoria]:
    return list((await session.execute(select(LogAuditoria).order_by(LogAuditoria.id))).scalars())


async def test_credenciais_corretas_iniciam_sessao_de_12_horas(session: AsyncSession):
    gabriela = await criar_funcionario(session, "gabriela")
    antes = datetime.now(UTC)

    sessao = await _servico(session).login("gabriela", SENHA_PADRAO)

    claims = decodificar_token(sessao.token.valor, SEGREDO_TESTE)
    assert (claims.funcionario_id, claims.perfil) == (gabriela.id, "FUNCIONARIO")
    assert (sessao.funcionario.nome, sessao.funcionario.perfil) == ("Gabriela", "FUNCIONARIO")
    assert timedelta(hours=11, minutes=59) < sessao.token.expira_em - antes <= timedelta(hours=12, seconds=5)


async def test_login_bem_sucedido_e_auditado(session: AsyncSession):
    gabriela = await criar_funcionario(session, "gabriela")

    await _servico(session).login("gabriela", SENHA_PADRAO)

    [log] = await _logs(session)
    assert (log.acao, log.usuario_id, log.entidade, log.entidade_id) == ("LOGIN", gabriela.id, "Funcionario", str(gabriela.id))


@pytest.mark.parametrize(
    ("login", "senha", "senha_definida"),
    [
        ("gabriela", "senha-errada-123", True),
        ("ninguem", SENHA_PADRAO, True),
        ("gabriela", SENHA_PADRAO, False),
    ],
    ids=["senha-incorreta", "login-inexistente", "usuario-sem-senha-definida"],
)
async def test_credenciais_invalidas_tem_a_mesma_mensagem(session: AsyncSession, login, senha, senha_definida):
    await criar_funcionario(session, "gabriela", senha=SENHA_PADRAO if senha_definida else None)

    with pytest.raises(CredenciaisInvalidas) as erro:
        await _servico(session).login(login, senha)

    assert erro.value.status_code == 401
    assert erro.value.mensagem == "Usuário ou senha incorretos"


async def test_falha_de_login_e_auditada_sem_a_senha(session: AsyncSession):
    gabriela = await criar_funcionario(session, "gabriela")

    with pytest.raises(CredenciaisInvalidas):
        await _servico(session).login("gabriela", "senha-errada-123")
    with pytest.raises(CredenciaisInvalidas):
        await _servico(session).login("ninguem", "outra-senha-456")

    existente, inexistente = await _logs(session)
    assert (existente.acao, existente.usuario_id, existente.entidade_id) == ("LOGIN_FALHA", gabriela.id, str(gabriela.id))
    assert existente.dados_depois == {"login": "gabriela", "motivo": "CREDENCIAIS_INVALIDAS"}
    assert (inexistente.usuario_id, inexistente.entidade_id) == (None, "-")
    assert inexistente.dados_depois == {"login": "ninguem", "motivo": "CREDENCIAIS_INVALIDAS"}
    for log in (existente, inexistente):
        assert "senha-errada-123" not in str(log.dados_depois) and "outra-senha-456" not in str(log.dados_depois)


async def test_usuario_bloqueado_com_senha_correta(session: AsyncSession):
    bia = await criar_funcionario(session, "bia", bloqueado=True)

    with pytest.raises(UsuarioBloqueado) as erro:
        await _servico(session).login("bia", SENHA_PADRAO)

    assert (erro.value.status_code, erro.value.mensagem) == (403, "Usuário bloqueado")
    [log] = await _logs(session)
    assert (log.acao, log.usuario_id) == ("LOGIN_FALHA", bia.id)
    assert log.dados_depois == {"login": "bia", "motivo": "USUARIO_BLOQUEADO"}


async def test_usuario_bloqueado_com_senha_errada_nao_revela_o_bloqueio(session: AsyncSession):
    await criar_funcionario(session, "bia", bloqueado=True)

    with pytest.raises(CredenciaisInvalidas):
        await _servico(session).login("bia", "senha-errada-123")
