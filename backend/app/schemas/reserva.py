from datetime import datetime

from pydantic import BaseModel

from app.schemas.comanda import ComandaOut, MesaResumoOut


class ReservaIn(BaseModel):
    """Limites de texto e quantidade são validados no serviço, com mensagens em português.

    `inicio` sem fuso é interpretado no fuso de São Paulo.
    """

    mesa_id: int
    nome_cliente: str
    telefone: str
    qtd_pessoas: int
    inicio: datetime


class ReservaOut(BaseModel):
    id: int
    mesa: MesaResumoOut
    nome_cliente: str
    telefone: str
    qtd_pessoas: int
    inicio: datetime
    fim: datetime
    status: str
    situacao: str


class CriacaoReservaOut(BaseModel):
    reserva: ReservaOut
    aviso: str | None


class CheckInOut(BaseModel):
    reserva: ReservaOut
    comanda: ComandaOut
