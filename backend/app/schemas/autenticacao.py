from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Perfil


class LoginIn(BaseModel):
    login: str = Field(min_length=1, max_length=50)
    senha: str = Field(min_length=1, max_length=200)


class UsuarioOut(BaseModel):
    """Dados públicos do usuário: nunca inclui senha nem hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    login: str
    perfil: Perfil


class LoginOut(BaseModel):
    token: str
    tipo: Literal["bearer"] = "bearer"
    expira_em: datetime
    usuario: UsuarioOut
