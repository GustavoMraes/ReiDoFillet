"""Cria (ou atualiza) as três contas de teste públicas, uma por perfil.

Uso: python -m scripts.criar_contas_teste

As senhas são pedidas sem aparecer na tela (mínimo de 8 caracteres). Se a conta já existir, a senha é
redefinida e a conta é desbloqueada. Usa o DATABASE_URL do .env: para produção, aponte para o Neon.
"""

import asyncio
import sys
from getpass import getpass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErroNegocio
from app.core.seguranca import gerar_hash
from app.core.tempo import RelogioSistema
from app.db.session import get_sessionmaker
from app.db.transacao import transacao
from app.models import Funcionario
from app.models.enums import Perfil
from app.repositories.auditoria import AuditoriaRepository
from app.repositories.funcionario import FuncionarioRepository
from app.schemas.snapshots import FuncionarioSnapshot
from app.services.auditoria import Acao, AuditoriaService
from app.services.funcionario import FuncionarioService, _validar_senha

CONTAS = [
    # login, nome, perfil
    ("teste.garcom", "Teste Garçom", Perfil.FUNCIONARIO),
    ("teste.admin", "Teste Administrador", Perfil.ADMIN),
    ("teste.contabil", "Teste Contabilidade", Perfil.CONTABILIDADE),
]


async def criar_ou_atualizar(session: AsyncSession, login: str, nome: str, perfil: Perfil, senha: str) -> str:
    """Operação do sistema (sem usuário na auditoria). Devolve "criada" ou "atualizada"."""
    _validar_senha(senha)
    funcionarios = FuncionarioRepository(session)
    auditoria = AuditoriaService(AuditoriaRepository(session), RelogioSistema())
    existente = await funcionarios.obter_por_login(login)
    if existente is not None:
        async with transacao(session):
            antes = FuncionarioSnapshot.model_validate(existente)
            existente.bloqueado = False
            auditoria.registrar(usuario_id=None, acao=Acao.ALTERAR, entidade="Funcionario", entidade_id=existente.id,
                                antes=antes, depois=FuncionarioSnapshot.model_validate(existente))
        await FuncionarioService(session, funcionarios, auditoria).definir_senha(login, senha)
        return "atualizada"

    senha_hash = await asyncio.to_thread(gerar_hash, senha)
    async with transacao(session):
        funcionario = Funcionario(nome=nome, login=login, perfil=perfil, senha_hash=senha_hash, bloqueado=False)
        session.add(funcionario)
        await session.flush()
        auditoria.registrar(usuario_id=None, acao=Acao.CRIAR, entidade="Funcionario", entidade_id=funcionario.id,
                            antes=None, depois=FuncionarioSnapshot.model_validate(funcionario))
    return "criada"


async def main() -> int:
    async with get_sessionmaker()() as session:
        for login, nome, perfil in CONTAS:
            senha = getpass(f"Senha para {login} ({perfil.value}): ")
            if senha != getpass("Confirme a senha: "):
                print("As senhas digitadas não conferem", file=sys.stderr)
                return 1
            try:
                print(f"Conta {login} {await criar_ou_atualizar(session, login, nome, perfil, senha)}.")
            except ErroNegocio as erro:
                print(f"{login}: {erro.mensagem}", file=sys.stderr)
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
