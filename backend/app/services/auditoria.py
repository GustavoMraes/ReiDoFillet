from enum import StrEnum

from app.core.tempo import Relogio
from app.models import LogAuditoria
from app.repositories.auditoria import AuditoriaRepository
from app.schemas.snapshots import Snapshot


class Acao(StrEnum):
    CRIAR = "CRIAR"
    ALTERAR = "ALTERAR"
    EXCLUIR = "EXCLUIR"
    CANCELAR = "CANCELAR"
    ENVIAR = "ENVIAR"
    PRONTO = "PRONTO"
    ENTREGAR = "ENTREGAR"
    PRE_CONTA = "PRE_CONTA"
    PAGAR = "PAGAR"
    REMOVER_PAGAMENTO = "REMOVER_PAGAMENTO"
    CHECK_IN = "CHECK_IN"
    LOGIN = "LOGIN"
    LOGIN_FALHA = "LOGIN_FALHA"
    DEFINIR_SENHA = "DEFINIR_SENHA"


class AuditoriaService:
    """Registra operações na mesma sessão da operação de negócio.

    Não faz commit: o registro é confirmado ou desfeito junto com a operação (ver transacao()).
    """

    def __init__(self, repositorio: AuditoriaRepository, relogio: Relogio):
        self.repositorio = repositorio
        self.relogio = relogio

    def registrar(
        self,
        *,
        usuario_id: int | None,
        acao: Acao,
        entidade: str,
        entidade_id: int | str,
        antes: Snapshot | None,
        depois: Snapshot | None,
    ) -> LogAuditoria:
        """usuario_id=None indica operação executada pelo sistema."""
        log = LogAuditoria(
            usuario_id=usuario_id,
            acao=acao,
            entidade=entidade,
            entidade_id=str(entidade_id),
            dados_antes=antes.model_dump(mode="json") if antes is not None else None,
            dados_depois=depois.model_dump(mode="json") if depois is not None else None,
            criado_em=self.relogio.agora(),
        )
        self.repositorio.adicionar(log)
        return log
