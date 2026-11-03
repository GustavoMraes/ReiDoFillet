from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
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


class DadoInvalido(ErroNegocio):
    status_code = 422


class NaoAutenticado(ErroNegocio):
    status_code = 401


class SemPermissao(ErroNegocio):
    status_code = 403


async def _tratar_erro_negocio(_: Request, erro: ErroNegocio) -> JSONResponse:
    return JSONResponse(status_code=erro.status_code, content={"detalhe": erro.mensagem})


async def _tratar_validacao(_: Request, erro: RequestValidationError) -> JSONResponse:
    # Mantém o formato {"detalhe": ...} usado pela interface; os detalhes técnicos seguem em "erros".
    return JSONResponse(status_code=422, content={"detalhe": "Dados inválidos", "erros": jsonable_encoder(erro.errors())})


def registrar_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ErroNegocio, _tratar_erro_negocio)
    app.add_exception_handler(RequestValidationError, _tratar_validacao)
