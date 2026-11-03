import asyncio
import re
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflito, DadoInvalido, RecursoNaoEncontrado
from app.core.seguranca import gerar_hash, verificar_senha
from app.db.transacao import transacao
from app.models import Funcionario
from app.models.enums import Perfil
from app.repositories.funcionario import FuncionarioRepository
from app.schemas.snapshots import FuncionarioSnapshot
from app.services.auditoria import Acao, AuditoriaService

TAMANHO_MINIMO_SENHA = 8
TAMANHO_MAXIMO_SENHA = 72  # limite do bcrypt, em bytes
TAMANHO_MAXIMO_NOME = 100
FORMATO_LOGIN = re.compile(r"[a-z0-9._-]{3,50}")

LOGIN_REPETIDO = "Já existe um usuário com este login"


class SenhaCurta(DadoInvalido):
    def __init__(self):
        super().__init__(f"A senha deve ter no mínimo {TAMANHO_MINIMO_SENHA} caracteres")


class FuncionarioNaoEncontrado(RecursoNaoEncontrado):
    def __init__(self):
        super().__init__("Funcionário não encontrado")


def _validar_senha(senha: str) -> None:
    if len(senha) < TAMANHO_MINIMO_SENHA:
        raise SenhaCurta()
    if len(senha.encode("utf-8")) > TAMANHO_MAXIMO_SENHA:
        raise DadoInvalido(f"A senha deve ter no máximo {TAMANHO_MAXIMO_SENHA} caracteres")


def _nome(nome: str) -> str:
    nome = nome.strip()
    if not nome:
        raise DadoInvalido("Informe o nome do usuário")
    if len(nome) > TAMANHO_MAXIMO_NOME:
        raise DadoInvalido(f"O nome deve ter no máximo {TAMANHO_MAXIMO_NOME} caracteres")
    return nome


def _login(login: str) -> str:
    login = login.strip().lower()
    if not FORMATO_LOGIN.fullmatch(login):
        raise DadoInvalido(
            "O login deve ter de 3 a 50 caracteres: letras minúsculas sem acento, números, ponto, hífen ou sublinhado"
        )
    return login


class FuncionarioService:
    def __init__(self, session: AsyncSession, funcionarios: FuncionarioRepository, auditoria: AuditoriaService):
        self.session = session
        self.funcionarios = funcionarios
        self.auditoria = auditoria

    # --- Senhas ---

    async def definir_senha(self, login: str, senha: str, usuario_id: int | None = None) -> None:
        """Usada pelo script administrativo (usuario_id=None: operação do sistema). Grava apenas o hash."""
        _validar_senha(senha)
        funcionario = await self.funcionarios.obter_por_login(login.strip())
        if funcionario is None:
            raise FuncionarioNaoEncontrado()
        await self._gravar_senha(funcionario.id, senha, usuario_id)

    async def redefinir_senha(self, funcionario_id: int, senha: str, administrador: Funcionario) -> None:
        """O administrador define uma nova senha sem conhecer a anterior."""
        _validar_senha(senha)
        if await self.funcionarios.obter(funcionario_id) is None:
            raise FuncionarioNaoEncontrado()
        await self._gravar_senha(funcionario_id, senha, administrador.id)

    async def trocar_propria_senha(self, usuario: Funcionario, senha_atual: str, nova_senha: str) -> None:
        _validar_senha(nova_senha)
        if not await asyncio.to_thread(verificar_senha, senha_atual, usuario.senha_hash):
            # 422, não 401: a interface não deve tratar como sessão expirada.
            raise DadoInvalido("Senha atual incorreta")
        await self._gravar_senha(usuario.id, nova_senha, usuario.id)

    async def _gravar_senha(self, funcionario_id: int, senha: str, usuario_id: int | None) -> None:
        senha_hash = await asyncio.to_thread(gerar_hash, senha)  # bcrypt é lento: fora do event loop
        async with transacao(self.session):
            funcionario = await self.funcionarios.obter(funcionario_id)
            funcionario.senha_hash = senha_hash
            self.auditoria.registrar(
                usuario_id=usuario_id,
                acao=Acao.DEFINIR_SENHA,
                entidade="Funcionario",
                entidade_id=funcionario.id,
                antes=None,
                depois=None,
            )

    # --- Gestão de usuários (Administrador) ---

    async def listar(self) -> list[Funcionario]:
        return await self.funcionarios.listar()

    async def criar(self, nome: str, login: str, perfil: Perfil, senha: str, administrador: Funcionario) -> Funcionario:
        nome, login = _nome(nome), _login(login)
        _validar_senha(senha)
        if await self.funcionarios.obter_por_login(login) is not None:
            raise Conflito(LOGIN_REPETIDO)
        senha_hash = await asyncio.to_thread(gerar_hash, senha)
        try:
            async with transacao(self.session):
                funcionario = Funcionario(nome=nome, login=login, perfil=perfil, senha_hash=senha_hash, bloqueado=False)
                self.session.add(funcionario)
                await self.session.flush()
                self._auditar(administrador, Acao.CRIAR, funcionario.id, None, FuncionarioSnapshot.model_validate(funcionario))
        except IntegrityError:
            raise Conflito(LOGIN_REPETIDO) from None  # cadastro simultâneo do mesmo login
        return funcionario

    async def alterar(self, funcionario_id: int, alteracoes: dict[str, Any], administrador: Funcionario) -> Funcionario:
        """Nome, perfil e bloqueio (`alteracoes` traz só os campos enviados). O login nunca muda."""
        nome = _nome(alteracoes["nome"] or "") if "nome" in alteracoes else None
        async with transacao(self.session):
            # Administradores ativos primeiro, sempre na mesma ordem: duas alterações simultâneas não se cruzam
            # (nem em deadlock, nem deixando o sistema sem administrador).
            administradores_ativos = await self.funcionarios.administradores_ativos_para_atualizar()
            alvo = await self.funcionarios.obter_para_atualizar(funcionario_id)
            if alvo is None:
                raise FuncionarioNaoEncontrado()

            perfil = alteracoes.get("perfil") or alvo.perfil
            bloqueado = alteracoes["bloqueado"] if alteracoes.get("bloqueado") is not None else alvo.bloqueado
            deixa_de_ser_admin_ativo = alvo.perfil == Perfil.ADMIN and not alvo.bloqueado and (
                perfil != Perfil.ADMIN or bloqueado
            )
            if deixa_de_ser_admin_ativo:
                if alvo.id == administrador.id:
                    raise Conflito("Você não pode bloquear nem rebaixar o próprio usuário")
                if not any(a.id != alvo.id for a in administradores_ativos):
                    raise Conflito("O sistema precisa de ao menos um administrador ativo")

            antes = FuncionarioSnapshot.model_validate(alvo)
            if nome is not None:
                alvo.nome = nome
            alvo.perfil = perfil
            alvo.bloqueado = bloqueado
            self._auditar(administrador, Acao.ALTERAR, alvo.id, antes, FuncionarioSnapshot.model_validate(alvo))
        return alvo

    def _auditar(self, usuario: Funcionario, acao: Acao, funcionario_id: int, antes, depois) -> None:
        self.auditoria.registrar(
            usuario_id=usuario.id, acao=acao, entidade="Funcionario", entidade_id=funcionario_id, antes=antes, depois=depois
        )
