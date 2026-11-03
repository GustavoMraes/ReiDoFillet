"""Define a senha de um funcionário existente: primeiro acesso e recuperação de acesso (o dia a dia é pela aba Usuários).

Uso: python -m scripts.definir_senha <login>

A senha é pedida duas vezes, sem aparecer na tela. Usa o DATABASE_URL do .env: para
produção, aponte para o banco do Neon.
"""

import argparse
import asyncio
import sys
from getpass import getpass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErroNegocio
from app.core.tempo import RelogioSistema
from app.db.session import get_sessionmaker
from app.repositories.auditoria import AuditoriaRepository
from app.repositories.funcionario import FuncionarioRepository
from app.services.auditoria import AuditoriaService
from app.services.funcionario import FuncionarioService


class SenhasDiferentes(ErroNegocio):
    def __init__(self):
        super().__init__("As senhas digitadas não conferem")


async def executar(session: AsyncSession, login: str, senha: str, confirmacao: str) -> None:
    if senha != confirmacao:
        raise SenhasDiferentes()
    servico = FuncionarioService(
        session, FuncionarioRepository(session), AuditoriaService(AuditoriaRepository(session), RelogioSistema())
    )
    await servico.definir_senha(login, senha)


async def main(login: str) -> int:
    senha = getpass("Nova senha: ")
    confirmacao = getpass("Confirme a senha: ")
    async with get_sessionmaker()() as session:
        try:
            await executar(session, login, senha, confirmacao)
        except ErroNegocio as erro:
            print(erro.mensagem, file=sys.stderr)
            return 1
    print(f"Senha definida para '{login}'.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Define a senha de um funcionário existente.")
    parser.add_argument("login", help="login do funcionário (ex.: gabriela)")
    sys.exit(asyncio.run(main(parser.parse_args().login)))
