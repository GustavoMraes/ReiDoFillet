"""Dados de exemplo. Idempotente: pode ser executado várias vezes sem duplicar registros.

Uso: python -m scripts.seed
"""

import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_sessionmaker
from app.models import Categoria, Funcionario, Mesa, Parametro, Produto
from app.models.enums import Perfil
from app.models.parametro import TAXA_SERVICO_PADRAO

# Senha inutilizável: as senhas reais são definidas no change de autenticação.
SENHA_INUTILIZAVEL = "!"

MESAS = [
    # numero, capacidade, localizacao, em_manutencao
    (1, 2, "Janela", False),
    (2, 4, "Salão", False),
    (3, 4, "Salão", False),
    (4, 2, "Varanda", False),
    (5, 6, "Salão", False),
    (6, 2, "Janela", True),
    (7, 4, "Salão", False),
    (8, 4, "Varanda", False),
]

CARDAPIO = {
    # categoria: [(nome, descricao, preco)]
    "Carnes nobres": [
        ("Filet Mignon 300g", "Filé mignon grelhado ao ponto desejado", "89.90"),
        ("Picanha 400g", "Picanha na brasa com sal grosso", "94.90"),
        ("Filet à Parmegiana", "Filé empanado com molho de tomate e queijo", "79.90"),
    ],
    "Acompanhamentos": [
        ("Batata Rústica", "Batatas assadas com alecrim", "24.90"),
        ("Arroz Branco", "Porção de arroz soltinho", "14.90"),
        ("Farofa da Casa", "Farofa com bacon e ovos", "16.90"),
    ],
    "Bebidas": [
        ("Refrigerante Lata", "350 ml", "7.00"),
        ("Suco Natural", "Laranja, limão ou abacaxi - 500 ml", "12.00"),
        ("Cerveja Long Neck", "355 ml", "11.00"),
    ],
    "Sobremesas": [
        ("Pudim de Leite", "Fatia individual", "15.90"),
        ("Petit Gâteau", "Com sorvete de creme", "29.90"),
    ],
}

FUNCIONARIOS = [
    # nome, login, perfil
    ("Gabriela Garcia", "gabriela", Perfil.FUNCIONARIO),
    ("Administrador", "admin", Perfil.ADMIN),
    ("Contabilidade", "contabilidade", Perfil.CONTABILIDADE),
]


async def seed(session: AsyncSession) -> None:
    await session.execute(
        insert(Mesa)
        .values([{"numero": n, "capacidade": c, "localizacao": l, "em_manutencao": m} for n, c, l, m in MESAS])
        .on_conflict_do_nothing(index_elements=["numero"])
    )

    await session.execute(
        insert(Categoria)
        .values([{"nome": nome, "ordem": ordem} for ordem, nome in enumerate(CARDAPIO)])
        .on_conflict_do_nothing(index_elements=["nome"])
    )
    categorias = dict((await session.execute(select(Categoria.nome, Categoria.id))).all())
    existentes = set((await session.execute(select(Produto.nome))).scalars())
    for categoria, produtos in CARDAPIO.items():
        for nome, descricao, preco in produtos:
            if nome not in existentes:
                session.add(
                    Produto(categoria_id=categorias[categoria], nome=nome, descricao=descricao, preco=Decimal(preco))
                )

    await session.execute(
        insert(Funcionario)
        .values(
            [
                {"nome": nome, "login": login, "perfil": perfil, "senha_hash": SENHA_INUTILIZAVEL}
                for nome, login, perfil in FUNCIONARIOS
            ]
        )
        .on_conflict_do_nothing(index_elements=["login"])
    )

    await session.execute(
        insert(Parametro).values(chave=TAXA_SERVICO_PADRAO, valor="10.00").on_conflict_do_nothing(index_elements=["chave"])
    )

    await session.commit()


async def main() -> None:
    async with get_sessionmaker()() as session:
        await seed(session)
    print("Seed concluído.")


if __name__ == "__main__":
    asyncio.run(main())
