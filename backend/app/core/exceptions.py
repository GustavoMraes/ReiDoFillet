from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ErroNegocio(Exception):
    """Violação de regra de negócio, exibida ao usuário como mensagem."""

    status_code = 400

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class RecursoNaoEncontrado(ErroNegocio):
    status_code = 404


class Conflito(ErroNegocio):
    status_code = 409


async def _tratar_erro_negocio(_: Request, erro: ErroNegocio) -> JSONResponse:
    return JSONResponse(status_code=erro.status_code, content={"detalhe": erro.mensagem})


def registrar_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ErroNegocio, _tratar_erro_negocio)
