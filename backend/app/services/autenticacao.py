import asyncio
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import NaoAutenticado, SemPermissao
from app.core.seguranca import TokenEmitido, criar_token, hash_ficticio, verificar_senha
from app.core.tempo import Relogio
from app.db.transacao import transacao
from app.models import Funcionario
from app.repositories.funcionario import FuncionarioRepository
from app.schemas.snapshots import TentativaLoginSnapshot
from app.services.auditoria import Acao, AuditoriaService

MENSAGEM_CREDENCIAIS_INVALIDAS = "Usuário ou senha incorretos"
MENSAGEM_USUARIO_BLOQUEADO = "Usuário bloqueado"


class CredenciaisInvalidas(NaoAutenticado):
    def __init__(self):
        super().__init__(MENSAGEM_CREDENCIAIS_INVALIDAS)


class UsuarioBloqueado(SemPermissao):
    def __init__(self):
        super().__init__(MENSAGEM_USUARIO_BLOQUEADO)


@dataclass(frozen=True)
class SessaoIniciada:
    token: TokenEmitido
    funcionario: Funcionario


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        funcionarios: FuncionarioRepository,
        auditoria: AuditoriaService,
        relogio: Relogio,
        settings: Settings,
    ):
        self.session = session
        self.funcionarios = funcionarios
        self.auditoria = auditoria
        self.relogio = relogio
        self.settings = settings

    async def login(self, login: str, senha: str) -> SessaoIniciada:
        login = login.strip()
        funcionario = await self.funcionarios.obter_por_login(login)
        # Sem login cadastrado, a senha ainda é verificada contra um hash fixo: o tempo de
        # resposta não revela quais logins existem. bcrypt é lento, então roda fora do event loop.
        senha_hash = funcionario.senha_hash if funcionario else hash_ficticio()
        senha_confere = await asyncio.to_thread(verificar_senha, senha, senha_hash)

        if funcionario is None or not senha_confere:
            await self._registrar_falha(funcionario, login, "CREDENCIAIS_INVALIDAS")
            raise CredenciaisInvalidas()
        if funcionario.bloqueado:
            await self._registrar_falha(funcionario, login, "USUARIO_BLOQUEADO")
            raise UsuarioBloqueado()

        token = criar_token(
            funcionario.id,
            funcionario.perfil,
            self.relogio.agora(),
            self.settings.jwt_secret,
            self.settings.jwt_expiracao_horas,
        )
        async with transacao(self.session):
            self.auditoria.registrar(
                usuario_id=funcionario.id,
                acao=Acao.LOGIN,
                entidade="Funcionario",
                entidade_id=funcionario.id,
                antes=None,
                depois=None,
            )
        return SessaoIniciada(token=token, funcionario=funcionario)

    async def _registrar_falha(self, funcionario: Funcionario | None, login: str, motivo: str) -> None:
        # Confirmada antes de a requisição ser recusada: a falha de login não desfaz a própria auditoria.
        async with transacao(self.session):
            self.auditoria.registrar(
                usuario_id=funcionario.id if funcionario else None,
                acao=Acao.LOGIN_FALHA,
                entidade="Funcionario",
                entidade_id=funcionario.id if funcionario else "-",
                antes=None,
                depois=TentativaLoginSnapshot(login=login, motivo=motivo),
            )
