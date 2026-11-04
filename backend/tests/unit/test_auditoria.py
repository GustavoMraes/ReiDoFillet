from datetime import UTC, date, datetime
from decimal import Decimal

import pydantic
import pytest

from app.core.tempo import RelogioFixo
from app.models import Funcionario, ItemComanda, Mesa
from app.repositories.auditoria import AuditoriaRepository
from app.schemas.snapshots import (
    ConsultaSnapshot,
    FuncionarioSnapshot,
    ItemComandaSnapshot,
    MesaSnapshot,
    TentativaLoginSnapshot,
)
from app.services.auditoria import Acao, AuditoriaService

AGORA = datetime(2026, 10, 25, 23, 15, tzinfo=UTC)


class SessaoFalsa:
    def __init__(self):
        self.adicionados = []

    def add(self, objeto):
        self.adicionados.append(objeto)


def _servico() -> tuple[AuditoriaService, SessaoFalsa]:
    sessao = SessaoFalsa()
    return AuditoriaService(AuditoriaRepository(sessao), RelogioFixo(AGORA)), sessao


def _mesa(**alteracoes) -> MesaSnapshot:
    dados = {"id": 7, "numero": 7, "capacidade": 4, "localizacao": "Salão", "em_manutencao": False}
    return MesaSnapshot.model_validate(Mesa(**(dados | alteracoes)))


def test_criacao_grava_estado_posterior_e_antes_vazio():
    servico, sessao = _servico()

    log = servico.registrar(usuario_id=1, acao=Acao.CRIAR, entidade="Mesa", entidade_id=7, antes=None, depois=_mesa())

    assert sessao.adicionados == [log]
    assert (log.usuario_id, log.acao, log.entidade, log.entidade_id) == (1, "CRIAR", "Mesa", "7")
    assert log.dados_antes is None
    assert log.dados_depois["numero"] == 7
    assert log.criado_em == AGORA


def test_alteracao_grava_antes_e_depois():
    servico, _ = _servico()

    log = servico.registrar(
        usuario_id=1,
        acao=Acao.ALTERAR,
        entidade="Mesa",
        entidade_id=7,
        antes=_mesa(),
        depois=_mesa(em_manutencao=True),
    )

    assert log.dados_antes["em_manutencao"] is False
    assert log.dados_depois["em_manutencao"] is True


def test_exclusao_grava_antes_e_depois_vazio():
    servico, _ = _servico()

    log = servico.registrar(usuario_id=1, acao=Acao.EXCLUIR, entidade="Mesa", entidade_id=7, antes=_mesa(), depois=None)

    assert log.dados_antes["id"] == 7
    assert log.dados_depois is None


def test_operacao_do_sistema_nao_tem_usuario():
    servico, _ = _servico()

    log = servico.registrar(usuario_id=None, acao=Acao.CRIAR, entidade="Mesa", entidade_id=7, antes=None, depois=_mesa())

    assert log.usuario_id is None


def test_snapshot_de_funcionario_nao_inclui_senha():
    funcionario = Funcionario(
        id=3, nome="Gabriela", login="gabriela", senha_hash="hash-secreto", perfil="FUNCIONARIO", bloqueado=False
    )
    servico, _ = _servico()

    log = servico.registrar(
        usuario_id=None,
        acao=Acao.CRIAR,
        entidade="Funcionario",
        entidade_id=3,
        antes=None,
        depois=FuncionarioSnapshot.model_validate(funcionario),
    )

    assert "senha_hash" not in log.dados_depois
    assert "hash-secreto" not in str(log.dados_depois)


def test_snapshot_de_tentativa_de_login_nao_aceita_senha():
    with pytest.raises(pydantic.ValidationError):
        TentativaLoginSnapshot(login="gabriela", motivo="CREDENCIAIS_INVALIDAS", senha="segredo")

    assert TentativaLoginSnapshot(login="gabriela", motivo="CREDENCIAIS_INVALIDAS").model_dump() == {
        "login": "gabriela",
        "motivo": "CREDENCIAIS_INVALIDAS",
    }


def test_snapshot_de_item_serializa_dinheiro_como_texto_decimal():
    item = ItemComanda(
        id=1, comanda_id=2, produto_id=3, quantidade=2, observacao="sem sal",
        preco_unitario=Decimal("89.90"), status="PENDENTE", cancelado_por_id=None,
    )

    dados = ItemComandaSnapshot.model_validate(item).model_dump(mode="json")

    assert dados["preco_unitario"] == "89.90"
    assert dados["observacao"] == "sem sal"


def test_snapshot_da_consulta_grava_os_filtros():
    servico, _ = _servico()

    log = servico.registrar(
        usuario_id=7,
        acao=Acao.CONSULTAR,
        entidade="Relatorio",
        entidade_id="auditoria",
        antes=None,
        depois=ConsultaSnapshot(inicio=date(2026, 10, 1), fim=date(2026, 10, 31), acao="PAGAR", pagina=2),
    )

    assert (log.acao, log.entidade, log.entidade_id) == ("CONSULTAR", "Relatorio", "auditoria")
    assert log.dados_depois == {
        "inicio": "2026-10-01", "fim": "2026-10-31", "usuario_id": None, "acao": "PAGAR", "entidade": None, "pagina": 2
    }


def test_snapshot_da_consulta_recusa_campos_extras():
    with pytest.raises(pydantic.ValidationError):
        ConsultaSnapshot(inicio=date(2026, 10, 1), fim=date(2026, 10, 1), senha="x")
