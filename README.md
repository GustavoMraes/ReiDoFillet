# Rei do Filet — Sistema de Atendimento e Comandas

Projeto da disciplina Engenharia de Software III (IES300) — Grupo 4.

```
backend/    API REST em Python + FastAPI (camadas routers -> services -> repositories -> models)
frontend/   Interface web em React + Vite + TypeScript
docs/       Documentos de especificação, viabilidade, arquitetura, interface e modelagem
openspec/   Specs e changes do OpenSpec
```

## Pré-requisitos

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+ (local ou Neon.tech, que usa a versão 18)

No Neon, use a connection string **direta** (sem `-pooler` no host) e ajuste o formato para o driver asyncpg:
`postgresql://...?sslmode=require&channel_binding=require` vira `postgresql+asyncpg://...?ssl=require`.
`TEST_DATABASE_URL` deve apontar para um banco separado (`reidofilet_test`): os testes apagam e recriam o schema dele.

## Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows (Git Bash). Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # ajuste DATABASE_URL
alembic upgrade head            # cria as tabelas
python -m scripts.seed          # dados de exemplo (pode rodar mais de uma vez)
uvicorn app.main:app --reload   # http://localhost:8000  (Swagger em /docs)
```

Testes:

```bash
pytest tests/unit               # regras de negócio, sem banco
pytest tests/integration        # exige TEST_DATABASE_URL no .env; sem ela, são pulados
```

## Frontend

```bash
cd frontend
npm install
cp .env.example .env            # ajuste VITE_API_URL
npm run dev                     # http://localhost:5173
```
