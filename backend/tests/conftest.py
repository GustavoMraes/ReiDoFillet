import os

import pytest
from pytest_asyncio import is_async_test

# Chave usada pelos testes quando não houver JWT_SECRET no ambiente; precisa existir antes de
# `app.main` ser importado, pois o módulo cria a aplicação na importação.
SEGREDO_TESTE = "segredo-de-teste-com-mais-de-32-caracteres"
os.environ.setdefault("JWT_SECRET", SEGREDO_TESTE)


def pytest_collection_modifyitems(items):
    # Todos os testes assíncronos compartilham o loop da sessão, o mesmo do engine dos testes
    # de integração; conexões asyncpg não podem ser usadas a partir de outro loop.
    marcador = pytest.mark.asyncio(loop_scope="session")
    for item in items:
        if is_async_test(item):
            item.add_marker(marcador, append=False)
