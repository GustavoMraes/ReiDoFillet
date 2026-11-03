"""Cenários da spec `usuarios`: lista, cadastro, alteração, bloqueio, administrador ativo, senhas e acesso."""

import asyncio

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.exceptions import Conflito
from app.core.tempo import RelogioSistema
from app.models import Funcionario, LogAuditoria
from app.models.enums import Perfil
from app.repositories.auditoria import AuditoriaRepository
from app.repositories.funcionario import FuncionarioRepository
from app.services.auditoria import AuditoriaService
from app.services.funcionario import FuncionarioService
from tests.integration.comandas_util import UsuarioRef, abrir, preparar
from tests.integration.fabricas import SENHA_PADRAO, cabecalho_de, cliente_api, criar_funcionario

NOVA = "nova-senha-123"


async def entrar(cliente: AsyncClient, login: str, senha: str) -> Response:
    return await cliente.post("/auth/login", json={"login": login, "senha": senha})


async def cadastrar(cliente: AsyncClient, admin: UsuarioRef, **dados) -> Response:
    corpo = {"nome": "Bruno Lima", "login": "bruno", "perfil": "FUNCIONARIO", "senha": SENHA_PADRAO, **dados}
    return await cliente.post("/usuarios", json=corpo, headers=cabecalho_de(admin))


async def alterar(cliente: AsyncClient, admin: UsuarioRef, funcionario_id: int, **dados) -> Response:
    return await cliente.patch(f"/usuarios/{funcionario_id}", json=dados, headers=cabecalho_de(admin))


async def _logs(session: AsyncSession, acao: str) -> list[LogAuditoria]:
    consulta = select(LogAuditoria).where(LogAuditoria.entidade == "Funcionario", LogAuditoria.acao == acao)
    return list((await session.execute(consulta.order_by(LogAuditoria.id))).scalars())


# --- Lista e cadastro ---


async def test_administrador_consulta_os_usuarios(session: AsyncSession):
    amb = await preparar(session)
    await criar_funcionario(session, "zeca", bloqueado=True)

    async with cliente_api(session) as cliente:
        resposta = await cliente.get("/usuarios", headers=cabecalho_de(amb.admin))

    assert resposta.status_code == 200
    usuarios = resposta.json()
    assert [u["nome"] for u in usuarios] == sorted(u["nome"] for u in usuarios)
    assert {u["login"]: u["bloqueado"] for u in usuarios} == {
        "admin": False, "contabilidade": False, "gabriela": False, "zeca": True
    }
    assert all(set(u) == {"id", "nome", "login", "perfil", "bloqueado"} for u in usuarios)


async def test_novo_garcom(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        resposta = await cadastrar(cliente, amb.admin, nome="  Bruno Lima ", login=" Bruno ")
        login = await entrar(cliente, "bruno", SENHA_PADRAO)

    assert resposta.status_code == 201
    assert {k: v for k, v in resposta.json().items() if k != "id"} == {
        "nome": "Bruno Lima", "login": "bruno", "perfil": "FUNCIONARIO", "bloqueado": False
    }
    assert login.status_code == 200
    [log] = await _logs(session, "CRIAR")
    assert (log.usuario_id, log.dados_depois["login"]) == (amb.admin.id, "bruno")
    assert "senha" not in str(log.dados_depois) and "hash" not in str(log.dados_depois)


async def test_login_repetido(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        repetido = await cadastrar(cliente, amb.admin, login="GABRIELA")

    assert (repetido.status_code, repetido.json()) == (409, {"detalhe": "Já existe um usuário com este login"})


@pytest.mark.parametrize(
    ("dados", "mensagem"),
    [
        ({"nome": " "}, "Informe o nome do usuário"),
        ({"login": "ab"}, "O login deve ter de 3 a 50 caracteres: letras minúsculas sem acento, números, ponto, hífen ou sublinhado"),
        ({"login": "joão"}, "O login deve ter de 3 a 50 caracteres: letras minúsculas sem acento, números, ponto, hífen ou sublinhado"),
        ({"login": "bruno lima"}, "O login deve ter de 3 a 50 caracteres: letras minúsculas sem acento, números, ponto, hífen ou sublinhado"),
        ({"senha": "1234567"}, "A senha deve ter no mínimo 8 caracteres"),
    ],
)
async def test_dados_invalidos(session: AsyncSession, dados: dict, mensagem: str):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        resposta = await cadastrar(cliente, amb.admin, **dados)

    assert (resposta.status_code, resposta.json()) == (422, {"detalhe": mensagem})
    assert await FuncionarioRepository(session).obter_por_login("bruno") is None


async def test_perfil_invalido(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        resposta = await cadastrar(cliente, amb.admin, perfil="GERENTE")

    assert resposta.status_code == 422


# --- Alteração, bloqueio e desbloqueio ---


async def test_funcionario_promovido(session: AsyncSession):
    amb = await preparar(session)
    bruno = await criar_funcionario(session, "bruno")
    bruno_ref = UsuarioRef(bruno.id, bruno.perfil)

    async with cliente_api(session) as cliente:
        antes = await cliente.get("/usuarios", headers=cabecalho_de(bruno_ref))
        resposta = await alterar(cliente, amb.admin, bruno_ref.id, perfil="ADMIN", nome="Bruno L.")
        depois = await cliente.get("/usuarios", headers=cabecalho_de(bruno_ref))  # mesmo token de antes

    assert antes.status_code == 403
    assert (resposta.json()["perfil"], resposta.json()["nome"]) == ("ADMIN", "Bruno L.")
    assert depois.status_code == 200
    [log] = await _logs(session, "ALTERAR")
    assert (log.dados_antes["perfil"], log.dados_depois["perfil"]) == ("FUNCIONARIO", "ADMIN")


async def test_funcionario_desligado_e_desbloqueado(session: AsyncSession):
    amb = await preparar(session)
    bruno = await criar_funcionario(session, "bruno")
    bruno_ref = UsuarioRef(bruno.id, bruno.perfil)

    async with cliente_api(session) as cliente:
        comanda_id = (await abrir(cliente, bruno_ref, amb.mesas[1])).json()["id"]
        bloqueio = await alterar(cliente, amb.admin, bruno_ref.id, bloqueado=True)
        sessao_aberta = await cliente.get("/mesas", headers=cabecalho_de(bruno_ref))
        login_bloqueado = await entrar(cliente, "bruno", SENHA_PADRAO)
        comanda = (await cliente.get(f"/comandas/{comanda_id}", headers=cabecalho_de(amb.gabriela))).json()
        desbloqueio = await alterar(cliente, amb.admin, bruno_ref.id, bloqueado=False)
        login_de_volta = await entrar(cliente, "bruno", SENHA_PADRAO)

    assert bloqueio.json()["bloqueado"] is True
    assert (sessao_aberta.status_code, sessao_aberta.json()) == (401, {"detalhe": "Usuário bloqueado"})
    assert login_bloqueado.status_code == 403
    assert comanda["responsavel"] == {"id": bruno_ref.id, "nome": "Bruno"}
    assert desbloqueio.json()["bloqueado"] is False
    assert login_de_volta.status_code == 200

    bloqueio_log, _ = await _logs(session, "ALTERAR")
    assert (bloqueio_log.usuario_id, bloqueio_log.dados_antes["bloqueado"], bloqueio_log.dados_depois["bloqueado"]) == (
        amb.admin.id, False, True
    )
    assert "hash" not in str(bloqueio_log.dados_depois)


async def test_alteracao_de_usuario_inexistente_e_sem_campos(session: AsyncSession):
    amb = await preparar(session)

    async with cliente_api(session) as cliente:
        inexistente = await alterar(cliente, amb.admin, 999999, nome="X")
        vazia = await alterar(cliente, amb.admin, amb.gabriela.id)
        nome_vazio = await alterar(cliente, amb.admin, amb.gabriela.id, nome=" ")

    assert (inexistente.status_code, inexistente.json()) == (404, {"detalhe": "Funcionário não encontrado"})
    assert vazia.status_code == 422
    assert (nome_vazio.status_code, nome_vazio.json()) == (422, {"detalhe": "Informe o nome do usuário"})


# --- Administrador ativo garantido ---


@pytest.mark.parametrize("dados", [{"bloqueado": True}, {"perfil": "FUNCIONARIO"}])
async def test_administrador_tenta_se_bloquear_ou_rebaixar(session: AsyncSession, dados: dict):
    amb = await preparar(session)
    await criar_funcionario(session, "outro_admin", perfil=Perfil.ADMIN)

    async with cliente_api(session) as cliente:
        resposta = await alterar(cliente, amb.admin, amb.admin.id, **dados)
        so_nome = await alterar(cliente, amb.admin, amb.admin.id, nome="Administrador Geral")

    assert (resposta.status_code, resposta.json()) == (
        409, {"detalhe": "Você não pode bloquear nem rebaixar o próprio usuário"}
    )
    assert so_nome.status_code == 200
    admin = await session.get(Funcionario, amb.admin.id, populate_existing=True)
    assert (admin.perfil, admin.bloqueado) == ("ADMIN", False)


async def test_ultimo_administrador(session: AsyncSession, engine: AsyncEngine):
    amb = await preparar(session)
    # Situação que a interface não produz sozinha: um único administrador ativo tenta perder o perfil por outra via.
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    async with fabrica() as s:
        servico = FuncionarioService(s, FuncionarioRepository(s), AuditoriaService(AuditoriaRepository(s), RelogioSistema()))
        sistema = Funcionario(id=0, nome="Sistema", login="-", perfil=Perfil.ADMIN, senha_hash="!", bloqueado=False)
        with pytest.raises(Conflito, match="O sistema precisa de ao menos um administrador ativo"):
            await servico.alterar(amb.admin.id, {"bloqueado": True}, sistema)

    admin = await session.get(Funcionario, amb.admin.id, populate_existing=True)
    assert admin.bloqueado is False


async def test_dois_administradores_se_rebaixando_ao_mesmo_tempo(session: AsyncSession, engine: AsyncEngine):
    amb = await preparar(session)
    outro = await criar_funcionario(session, "outro_admin", perfil=Perfil.ADMIN)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    async def rebaixar(quem: int, alvo: int) -> str:
        async with fabrica() as s:
            servico = FuncionarioService(
                s, FuncionarioRepository(s), AuditoriaService(AuditoriaRepository(s), RelogioSistema())
            )
            try:
                await servico.alterar(alvo, {"perfil": Perfil.FUNCIONARIO}, await s.get(Funcionario, quem))
                return "ok"
            except Conflito as erro:
                return erro.mensagem

    resultados = await asyncio.gather(rebaixar(amb.admin.id, outro.id), rebaixar(outro.id, amb.admin.id))

    assert sorted(resultados) == ["O sistema precisa de ao menos um administrador ativo", "ok"]
    ativos = select(Funcionario).where(Funcionario.perfil == "ADMIN", Funcionario.bloqueado.is_(False))
    assert len((await session.execute(ativos.execution_options(populate_existing=True))).scalars().all()) == 1


# --- Senhas ---


async def test_funcionario_esqueceu_a_senha(session: AsyncSession):
    amb = await preparar(session)
    await criar_funcionario(session, "bruno")
    bruno_id = (await FuncionarioRepository(session).obter_por_login("bruno")).id

    async with cliente_api(session) as cliente:
        resposta = await cliente.post(f"/usuarios/{bruno_id}/senha", json={"senha": NOVA}, headers=cabecalho_de(amb.admin))
        curta = await cliente.post(f"/usuarios/{bruno_id}/senha", json={"senha": "curta"}, headers=cabecalho_de(amb.admin))
        inexistente = await cliente.post("/usuarios/999999/senha", json={"senha": NOVA}, headers=cabecalho_de(amb.admin))
        com_a_nova = await entrar(cliente, "bruno", NOVA)
        com_a_antiga = await entrar(cliente, "bruno", SENHA_PADRAO)

    assert resposta.status_code == 204
    assert (curta.status_code, curta.json()) == (422, {"detalhe": "A senha deve ter no mínimo 8 caracteres"})
    assert inexistente.status_code == 404
    assert (com_a_nova.status_code, com_a_antiga.status_code) == (200, 401)
    [log] = await _logs(session, "DEFINIR_SENHA")
    assert (log.usuario_id, log.entidade_id, log.dados_antes, log.dados_depois) == (amb.admin.id, str(bruno_id), None, None)


@pytest.mark.parametrize("perfil", [Perfil.FUNCIONARIO, Perfil.ADMIN, Perfil.CONTABILIDADE])
async def test_troca_da_propria_senha(session: AsyncSession, perfil: Perfil):
    await preparar(session)
    usuario = await criar_funcionario(session, "bruno", perfil=perfil)
    ref = UsuarioRef(usuario.id, usuario.perfil)

    async with cliente_api(session) as cliente:
        errada = await cliente.post(
            "/auth/senha", json={"senha_atual": "errada-123", "nova_senha": NOVA}, headers=cabecalho_de(ref)
        )
        curta = await cliente.post(
            "/auth/senha", json={"senha_atual": SENHA_PADRAO, "nova_senha": "curta"}, headers=cabecalho_de(ref)
        )
        ok = await cliente.post(
            "/auth/senha", json={"senha_atual": SENHA_PADRAO, "nova_senha": NOVA}, headers=cabecalho_de(ref)
        )
        com_a_nova = await entrar(cliente, "bruno", NOVA)
        com_a_antiga = await entrar(cliente, "bruno", SENHA_PADRAO)
        sem_sessao = await cliente.post("/auth/senha", json={"senha_atual": NOVA, "nova_senha": NOVA})

    assert (errada.status_code, errada.json()) == (422, {"detalhe": "Senha atual incorreta"})
    assert (curta.status_code, curta.json()) == (422, {"detalhe": "A senha deve ter no mínimo 8 caracteres"})
    assert ok.status_code == 204
    assert (com_a_nova.status_code, com_a_antiga.status_code) == (200, 401)
    assert sem_sessao.status_code == 401
    [log] = await _logs(session, "DEFINIR_SENHA")
    assert (log.usuario_id, log.entidade_id, log.dados_depois) == (ref.id, str(ref.id), None)


# --- Acesso ---


@pytest.mark.parametrize("login", ["gabriela", "contabilidade"])
async def test_funcionario_tenta_gerenciar_usuarios(session: AsyncSession, login: str):
    amb = await preparar(session)
    usuario = {"gabriela": amb.gabriela, "contabilidade": amb.contabilidade}[login]

    async with cliente_api(session) as cliente:
        lista = await cliente.get("/usuarios", headers=cabecalho_de(usuario))
        cadastro = await cadastrar(cliente, usuario)
        senha = await cliente.post(f"/usuarios/{amb.admin.id}/senha", json={"senha": NOVA}, headers=cabecalho_de(usuario))

    assert (lista.status_code, lista.json()) == (403, {"detalhe": "Sem permissão para esta funcionalidade"})
    assert (cadastro.status_code, senha.status_code) == (403, 403)
