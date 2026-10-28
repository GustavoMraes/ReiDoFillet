# Proposal

## Why

O projeto do Sistema de Atendimento e Comandas do Restaurante Rei do Filet ainda não possui código. Os documentos de ES II e ES III divergem entre si (stack, modelo de dados, escopo de reservas e pagamento), e o grupo consolidou as decisões finais. Este change materializa essas decisões em uma base executável — estrutura do monorepo, modelo de dados completo, auditoria e o Mapa de Mesas em modo leitura — para que os changes seguintes (comanda, cozinha, pagamento, reservas, transferência) apenas acrescentem regras e telas, sem migrações estruturais.

## What Changes

- Criação do monorepo com `backend/` (Python + FastAPI, arquitetura em camadas routers → services → repositories → models) e `frontend/` (React + Vite).
- Modelo de dados completo com 10 entidades: `Funcionario`, `Mesa`, `Reserva`, `Categoria`, `Produto`, `Comanda`, `ItemComanda`, `Pagamento`, `Parametro` e `LogAuditoria`, versionado com migrações Alembic sobre PostgreSQL (versão 18 no Neon.tech).
- Restrições de integridade no banco: no máximo uma comanda ativa (`ABERTA` ou `PRE_CONTA`) por mesa; valores monetários em `Numeric(10,2)`; datas em `timestamptz`.
- Infraestrutura de auditoria na camada de serviço, gravando cada operação de escrita na mesma transação, com registros imutáveis.
- Endpoint `GET /mesas` retornando as mesas com status **calculado na leitura** (Manutenção, Ocupada, Aguardando pagamento, Reservada, Livre), e endpoint `GET /health`.
- Tela Mapa de Mesas (somente leitura) com atualização por polling, seguindo o layout do Projeto de Interface.
- Script de seed com mesas, categorias, produtos, funcionários de exemplo e o parâmetro `taxa_servico_padrao = 10.00`.
- Configuração de deploy: banco no Neon.tech, backend no Render, frontend na Vercel, CORS restrito ao domínio do frontend.

Fora do escopo deste change: autenticação (change `autenticacao-perfis`), operações sobre comandas, cozinha, pagamento, reservas, transferência, cadastros administrativos e relatórios.

## Capabilities

### New Capabilities

- `mesas`: consulta do mapa de mesas e regra de cálculo do status de cada mesa a partir de manutenção, comanda ativa e janela de reserva.
- `auditoria`: registro imutável e transacional das operações realizadas no sistema, base para RN05, RF16 e HU07.

### Modified Capabilities

(nenhuma — não existem specs no projeto)

## Impact

- **Código novo:** `backend/` (FastAPI, SQLAlchemy async, asyncpg, Alembic, Pydantic Settings, pytest) e `frontend/` (React, Vite).
- **API:** `GET /health`, `GET /mesas`. Documentação Swagger gerada automaticamente pelo FastAPI.
- **Infraestrutura:** projeto PostgreSQL no Neon.tech, Web Service no Render, projeto na Vercel, monitor UptimeRobot.
- **Variáveis de ambiente:** `DATABASE_URL`, `CORS_ORIGINS`, `TZ_EXIBICAO` (backend); `VITE_API_URL` (frontend).
- **Desvios dos documentos de origem** registrados em `design.md`: FastAPI no lugar de Spring Boot; ausência da entidade Cliente do DER; reservas no escopo atual; fluxo alternativo de impressora da UC 7.2 e Nota Fiscal da UC 7.4 removidos.
