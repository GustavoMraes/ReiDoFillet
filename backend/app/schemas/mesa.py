from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import StatusMesa


class MesaMapaOut(BaseModel):
    id: int
    numero: int
    capacidade: int
    localizacao: str
    status: StatusMesa
    minutos_atendimento: int | None = Field(
        None, description="Minutos desde a abertura da comanda ativa (mesas OCUPADA ou AGUARDANDO_PAGAMENTO)"
    )
    reserva_inicio: datetime | None = Field(
        None, description="Início da reserva que bloqueia a mesa, no fuso de exibição (mesas RESERVADA)"
    )
    proxima_reserva_inicio: datetime | None = Field(
        None, description="Início da próxima reserva (em até 2h), no fuso de exibição (mesas LIVRE)"
    )
