from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import Perfil


class UsuarioAdminOut(BaseModel):
    """Funcionário na gestão de usuários: nunca inclui senha nem hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    login: str
    perfil: Perfil
    bloqueado: bool


class UsuarioIn(BaseModel):
    """Nome, login e senha são validados no serviço, com mensagens em português."""

    nome: str
    login: str
    perfil: Perfil
    senha: str = Field(max_length=200)


class UsuarioAlteracaoIn(BaseModel):
    nome: str | None = None
    perfil: Perfil | None = None
    bloqueado: bool | None = None

    @model_validator(mode="after")
    def exige_alguma_alteracao(self) -> "UsuarioAlteracaoIn":
        if self.nome is None and self.perfil is None and self.bloqueado is None:
            raise ValueError("Informe ao menos um campo para alterar")
        return self


class NovaSenhaIn(BaseModel):
    senha: str = Field(max_length=200)
