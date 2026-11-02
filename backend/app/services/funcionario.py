import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErroNegocio, RecursoNaoEncontrado
from app.core.seguranca import gerar_hash
from app.db.transacao import transacao
from app.repositories.funcionario import FuncionarioRepository
from app.services.auditoria import Acao, AuditoriaService

TAMANHO_MINIMO_SENHA = 8


class SenhaCurta(ErroNegocio):
    def __init__(self):
        super().__init__(f"A senha deve ter no mínimo {TAMANHO_MINIMO_SENHA} caracteres")


class FuncionarioNaoEncontrado(RecursoNaoEncontrado):
    def __init__(self):
        super().__init__("Funcionário não encontrado")


class FuncionarioService:
    def __init__(self, session: AsyncSession, funcionarios: FuncionarioRepository, auditoria: AuditoriaService):
        self.session = session
        self.funcionarios = funcionarios
        self.auditoria = auditoria

    async def definir_senha(self, login: str, senha: str, usuario_id: int | None = None) -> None:
        """usuario_id=None: executada pelo sistema (script administrativo). Grava apenas o hash."""
        if len(senha) < TAMANHO_MINIMO_SENHA:
            raise SenhaCurta()
        funcionario = await self.funcionarios.obter_por_login(login.strip())
        if funcionario is None:
            raise FuncionarioNaoEncontrado()

        senha_hash = await asyncio.to_thread(gerar_hash, senha)
        async with transacao(self.session):
            funcionario.senha_hash = senha_hash
            self.auditoria.registrar(
                usuario_id=usuario_id,
                acao=Acao.DEFINIR_SENHA,
                entidade="Funcionario",
                entidade_id=funcionario.id,
                antes=None,
                depois=None,
            )
