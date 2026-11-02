"""Hash de senha (bcrypt) e tokens de sessão (JWT HS256)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache

import bcrypt
import jwt

ALGORITMO = "HS256"


class TokenInvalido(Exception):
    """Token ausente, adulterado, assinado com outra chave ou expirado."""


@dataclass(frozen=True)
class TokenEmitido:
    valor: str
    expira_em: datetime


@dataclass(frozen=True)
class ClaimsToken:
    funcionario_id: int
    perfil: str


def gerar_hash(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Falso para senha errada e também para hash inválido (como a senha inutilizável "!")."""
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("ascii"))
    except ValueError:
        return False


@lru_cache
def hash_ficticio() -> str:
    """Hash usado quando o login não existe, para que o tempo de resposta não revele isso."""
    return gerar_hash("senha-ficticia-para-tempo-constante")


def criar_token(funcionario_id: int, perfil: str, agora: datetime, segredo: str, horas: float) -> TokenEmitido:
    expira_em = agora + timedelta(hours=horas)
    valor = jwt.encode(
        {"sub": str(funcionario_id), "perfil": perfil, "iat": agora, "exp": expira_em},
        segredo,
        algorithm=ALGORITMO,
    )
    return TokenEmitido(valor=valor, expira_em=expira_em)


def decodificar_token(valor: str, segredo: str) -> ClaimsToken:
    try:
        claims = jwt.decode(valor, segredo, algorithms=[ALGORITMO], options={"require": ["sub", "exp", "iat"]})
        return ClaimsToken(funcionario_id=int(claims["sub"]), perfil=str(claims.get("perfil", "")))
    except (jwt.PyJWTError, ValueError, KeyError) as erro:
        raise TokenInvalido(str(erro)) from erro
