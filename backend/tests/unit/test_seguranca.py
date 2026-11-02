import base64
import json
from datetime import UTC, datetime, timedelta

import pytest

from app.core.seguranca import (
    TokenInvalido,
    criar_token,
    decodificar_token,
    gerar_hash,
    hash_ficticio,
    verificar_senha,
)

SEGREDO = "segredo-de-teste-com-mais-de-32-caracteres"


def test_hash_confere_apenas_a_senha_correta():
    senha_hash = gerar_hash("senha-correta")

    assert senha_hash != "senha-correta"
    assert verificar_senha("senha-correta", senha_hash)
    assert not verificar_senha("senha-errada", senha_hash)


def test_hashes_da_mesma_senha_sao_diferentes():
    assert gerar_hash("mesma-senha") != gerar_hash("mesma-senha")


@pytest.mark.parametrize("senha_hash", ["!", "", "nao-e-bcrypt"])
def test_hash_inutilizavel_nunca_confere(senha_hash):
    assert not verificar_senha("qualquer", senha_hash)


def test_hash_ficticio_e_valido_e_reaproveitado():
    assert hash_ficticio() is hash_ficticio()
    assert not verificar_senha("qualquer", hash_ficticio())


def test_token_ida_e_volta():
    agora = datetime.now(UTC)
    token = criar_token(7, "FUNCIONARIO", agora, SEGREDO, 12)

    claims = decodificar_token(token.valor, SEGREDO)

    assert (claims.funcionario_id, claims.perfil) == (7, "FUNCIONARIO")
    assert token.expira_em == agora + timedelta(hours=12)


def test_token_expirado_e_recusado():
    emitido_ha_13h = datetime.now(UTC) - timedelta(hours=13)
    token = criar_token(7, "FUNCIONARIO", emitido_ha_13h, SEGREDO, 12)

    with pytest.raises(TokenInvalido):
        decodificar_token(token.valor, SEGREDO)


def test_token_adulterado_e_recusado():
    """Um funcionário que troca o próprio perfil para ADMIN sem a chave invalida a assinatura."""
    token = criar_token(7, "FUNCIONARIO", datetime.now(UTC), SEGREDO, 12).valor
    cabecalho, conteudo, assinatura = token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(conteudo + "=" * (-len(conteudo) % 4)))
    claims["perfil"] = "ADMIN"
    novo_conteudo = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()

    assert novo_conteudo != conteudo
    with pytest.raises(TokenInvalido):
        decodificar_token(f"{cabecalho}.{novo_conteudo}.{assinatura}", SEGREDO)


def test_token_de_outra_chave_e_recusado():
    token = criar_token(7, "ADMIN", datetime.now(UTC), "outra-chave-qualquer-com-32-caracteres", 12)

    with pytest.raises(TokenInvalido):
        decodificar_token(token.valor, SEGREDO)


@pytest.mark.parametrize("valor", ["", "nao.e.jwt", "abc"])
def test_texto_que_nao_e_token_e_recusado(valor):
    with pytest.raises(TokenInvalido):
        decodificar_token(valor, SEGREDO)
