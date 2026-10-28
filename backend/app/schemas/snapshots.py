"""Representações das entidades gravadas na auditoria (dados_antes / dados_depois).

A serialização é explícita, campo a campo, para que dados sensíveis (como senha_hash)
nunca cheguem ao histórico.
"""

from pydantic import BaseModel, ConfigDict


class Snapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class FuncionarioSnapshot(Snapshot):
    id: int
    nome: str
    login: str
    perfil: str
    bloqueado: bool


class MesaSnapshot(Snapshot):
    id: int
    numero: int
    capacidade: int
    localizacao: str
    em_manutencao: bool
