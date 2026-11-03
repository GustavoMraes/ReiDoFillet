from datetime import datetime

from pydantic import BaseModel


class ItemCozinhaOut(BaseModel):
    id: int
    comanda_id: int
    mesa_numero: int
    quantidade: int
    produto_nome: str
    observacao: str
    enviado_em: datetime
    minutos_desde_envio: int


class PainelCozinhaOut(BaseModel):
    em_preparo: list[ItemCozinhaOut]
    pronto: list[ItemCozinhaOut]
