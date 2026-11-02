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
cp .env.example .env            # ajuste DATABASE_URL e JWT_SECRET (abaixo)
alembic upgrade head            # cria as tabelas
python -m scripts.seed          # dados de exemplo (pode rodar mais de uma vez)
uvicorn app.main:app --reload   # http://localhost:8000  (Swagger em /docs)
```

### Autenticação

A API não sobe sem `JWT_SECRET` (mínimo de 32 caracteres), a chave que assina os tokens de sessão. Gere uma com:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Trocar a chave encerra todas as sessões abertas. A sessão dura `JWT_EXPIRACAO_HORAS` (padrão: 12).

O seed cria os funcionários `gabriela` (Funcionário), `admin` (Administrador) e `contabilidade` (Contabilidade) **sem senha**: ninguém entra até a senha ser definida. Até existir a tela de usuários, defina a senha pelo script (pede a senha duas vezes, sem exibir; mínimo de 8 caracteres):

```bash
python -m scripts.definir_senha gabriela
```

O script usa o `DATABASE_URL` do `.env`: para definir senhas em produção, ele precisa apontar para o banco do Neon.

Para testar rotas protegidas no Swagger (`/docs`): chame `POST /auth/login`, copie o `token` da resposta, clique em **Authorize** e cole o token.

Testes:

```bash
pytest tests/unit               # regras de negócio, sem banco
pytest tests/integration        # exige TEST_DATABASE_URL no .env; sem ela, são pulados
```

## Ambiente publicado

| Serviço | URL | Plataforma |
|---|---|---|
| Frontend | https://reidofilet.vercel.app | Vercel (Root Directory `frontend`) |
| API | https://reidofilet-api.onrender.com (Swagger em `/docs`) | Render, plano Free (Root Directory `backend`) |
| Banco | PostgreSQL 18, região São Paulo | Neon.tech |
| Monitor | ping em `/health` a cada 5 min, evita a hibernação do Render | UptimeRobot |

Variáveis de ambiente (os valores reais ficam só nos painéis, nunca no repositório):

| Onde | Variável | Valor |
|---|---|---|
| Render | `DATABASE_URL` | connection string direta do Neon no formato `postgresql+asyncpg://...?ssl=require` |
| Render | `CORS_ORIGINS` | `https://reidofilet.vercel.app,http://localhost:5173` |
| Render | `TZ_EXIBICAO` | `America/Sao_Paulo` |
| Render | `JWT_SECRET` | chave gerada com o comando da seção Autenticação, diferente da usada localmente |
| Render | `PYTHON_VERSION` | `3.13.14` (o SQLAlchemy 2.0.36 não é compatível com o Python 3.14 padrão do Render) |
| Vercel | `VITE_API_URL` | `https://reidofilet-api.onrender.com` |

Comandos do Render: build `pip install -r requirements.txt`; start `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` (as migrações rodam a cada deploy). Cada push na `main` dispara um novo deploy nas duas plataformas.

## Frontend

```bash
cd frontend
npm install
cp .env.example .env            # ajuste VITE_API_URL
npm run dev                     # http://localhost:5173
```
