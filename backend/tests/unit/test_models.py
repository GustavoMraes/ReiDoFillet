from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

import app.models  # noqa: F401  (registra as entidades no metadata)
from app.db.base import Base

TABELAS = {
    "funcionario",
    "mesa",
    "reserva",
    "categoria",
    "produto",
    "comanda",
    "item_comanda",
    "pagamento",
    "parametro",
    "log_auditoria",
}


def test_metadata_contem_as_dez_entidades():
    assert set(Base.metadata.tables) == TABELAS


def test_ddl_postgresql_e_gerado_sem_erro():
    dialeto = postgresql.dialect()
    for tabela in Base.metadata.sorted_tables:
        str(CreateTable(tabela).compile(dialect=dialeto))
        for indice in tabela.indexes:
            str(CreateIndex(indice).compile(dialect=dialeto))


def test_indice_parcial_de_comanda_ativa():
    indice = next(i for i in Base.metadata.tables["comanda"].indexes if i.name == "uq_comanda_ativa_por_mesa")
    ddl = str(CreateIndex(indice).compile(dialect=postgresql.dialect()))

    assert "UNIQUE" in ddl
    assert "WHERE status IN ('ABERTA', 'PRE_CONTA')" in ddl


def test_valores_monetarios_usam_numeric():
    tabelas = Base.metadata.tables
    for tabela, coluna in [("produto", "preco"), ("item_comanda", "preco_unitario"), ("pagamento", "valor")]:
        tipo = tabelas[tabela].c[coluna].type
        assert (tipo.precision, tipo.scale) == (10, 2), f"{tabela}.{coluna}"


def test_datas_tem_fuso_horario():
    for tabela in Base.metadata.tables.values():
        for coluna in tabela.columns:
            if coluna.type.__class__.__name__ == "DateTime":
                assert coluna.type.timezone, f"{tabela.name}.{coluna.name}"
