# Tasks

## 1. Estrutura do monorepo

- [x] 1.1 Criar `backend/` com a árvore de pastas do design (D1), `requirements.txt` (fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, pytest, pytest-asyncio, httpx) e `.env.example`; verificar com `pip install -r requirements.txt` em um venv limpo
- [x] 1.2 Criar `frontend/` com Vite + React + TypeScript e `.env.example` contendo `VITE_API_URL`; verificar com `npm run build` sem erros
- [x] 1.3 Criar `.gitignore` na raiz (venv, node_modules, `.env`, build) e `README.md` com instruções de execução local; verificar que `git status` não lista arquivos de ambiente
- [x] 1.4 Mover os PDFs de documentação para `docs/`; verificar que a raiz contém apenas `backend/`, `frontend/`, `docs/`, `openspec/` e arquivos de configuração

## 2. Núcleo do backend

- [x] 2.1 Implementar `core/config.py` com Pydantic Settings (`DATABASE_URL`, `CORS_ORIGINS`, `TZ_EXIBICAO`) e teste unitário que carrega a configuração a partir de variáveis de ambiente
- [x] 2.2 Implementar `core/tempo.py` com relógio injetável (agora em UTC e conversão para America/Sao_Paulo) e teste unitário da conversão de fuso
- [x] 2.3 Implementar `db/session.py` e `db/base.py` (engine e sessão async, dependência por requisição) e `core/exceptions.py` com handler padrão de erro; verificar subindo `uvicorn app.main:app` localmente
- [x] 2.4 Implementar `main.py` com CORS restrito a `CORS_ORIGINS` e `GET /health`; teste de integração verificando resposta 200 do `/health` e cabeçalho CORS apenas para a origem configurada

## 3. Modelo de dados e migrações

- [x] 3.1 Criar `models/enums.py` e os modelos `Funcionario`, `Mesa`, `Categoria`, `Produto`, `Parametro` conforme D2 (`Numeric(10,2)`, `timestamptz`, `CHECK` nos enums, unicidades); verificar com teste que importa todos os modelos e gera o metadata sem erro
- [x] 3.2 Criar os modelos `Reserva`, `Comanda`, `ItemComanda`, `Pagamento` e `LogAuditoria` conforme D2, incluindo índices `comanda(mesa_id, status)` e `reserva(mesa_id, status, inicio)`; verificar com o mesmo teste de metadata
- [x] 3.3 Configurar Alembic para async e gerar a migração inicial; verificar com `alembic upgrade head` e `alembic downgrade base` sem erros (validado no banco de testes do Neon, PostgreSQL 18.6)
- [x] 3.4 Adicionar na migração o índice único parcial `comanda(mesa_id) WHERE status IN ('ABERTA','PRE_CONTA')`; teste de integração que tenta inserir duas comandas ativas na mesma mesa e espera erro de integridade, e que aceita uma ativa mais uma FECHADA
- [x] 3.5 Adicionar na migração o trigger que rejeita `UPDATE`/`DELETE` em `log_auditoria`; teste de integração que tenta alterar e excluir um registro e espera erro
- [x] 3.6 Criar `scripts/seed.py` idempotente com 8 mesas (incluindo uma em manutenção), categorias (carnes nobres, acompanhamentos, bebidas, sobremesas), produtos, um funcionário de cada perfil e `taxa_servico_padrao = 10.00`; verificar executando o seed duas vezes seguidas sem duplicar dados

## 4. Auditoria

- [x] 4.1 Implementar `AuditoriaRepository` (somente inserção) e `AuditoriaService.registrar(usuario_id, acao, entidade, entidade_id, antes, depois)` usando a sessão da operação; testes unitários dos cenários de criação, alteração, exclusão e operação do sistema da spec `auditoria`
- [x] 4.2 Implementar o padrão de serviço com commit único ao final e rollback em exceção (D4); testes de integração dos cenários "Falha na operação de negócio" e "Falha na gravação da auditoria", verificando que nada é persistido
- [x] 4.3 Garantir serialização explícita sem campos sensíveis (`senha_hash` nunca aparece em `dados_antes`/`dados_depois`); teste unitário com um `Funcionario`
- [x] 4.4 Teste de integração do cenário "Consistência do horário": registro criado às 20h15 de São Paulo é exibido como 20h15 com o servidor em UTC

## 5. Mapa de mesas (backend)

- [x] 5.1 Implementar `MesaRepository` com as três consultas do D3 (mesas, comandas ativas, reservas confirmadas candidatas); teste de integração verificando que a listagem executa no máximo três consultas
- [x] 5.2 Implementar `MesaService` com o cálculo de status por prioridade, janela de reserva e informações complementares, usando o relógio injetável; testes unitários cobrindo todos os cenários dos requisitos "Status da mesa calculado na leitura", "Janela de bloqueio por reserva" (19h59, 20h00, 21h00, 21h01, cancelada) e "Informações complementares do atendimento"
- [x] 5.3 Implementar schemas de saída e `GET /mesas` (ordenado por número); testes de integração dos cenários "Consulta do mapa com mesas cadastradas" e "Consulta do mapa sem mesas cadastradas"
- [x] 5.4 Verificar no Swagger (`/docs`) que `GET /mesas` e `GET /health` estão documentados com os schemas de resposta

## 6. Mapa de mesas (frontend)

- [x] 6.1 Criar cliente HTTP em `src/api/` lendo `VITE_API_URL` e o layout base (barra superior com as abas Mapa de Mesas, Comanda, Cozinha, Pagamento; apenas Mapa de Mesas ativa); verificar visualmente com `npm run dev`
- [x] 6.2 Implementar a página Mapa de Mesas com cartões (número, capacidade, localização, status com cor, tempo de atendimento ou horário da reserva) e legenda dos cinco status; verificar contra o seed que as 8 mesas aparecem com os dados corretos
- [x] 6.3 Implementar polling de 5s com manutenção dos últimos dados e aviso de desatualização em caso de falha; verificar alterando o status de uma mesa no banco (cenário "Atualização automática") e derrubando o backend (cenário "Falha temporária de comunicação")

## 7. Deploy

- [x] 7.1 Provisionar o PostgreSQL no Neon.tech, aplicar migrações e seed; verificar conectando ao banco e listando as 8 mesas
- [x] 7.2 Publicar o backend no Render com o comando de start do D6 e as variáveis de ambiente; verificar `GET /health` e `GET /mesas` pela URL pública
- [x] 7.3 Publicar o frontend na Vercel com `VITE_API_URL` e ajustar `CORS_ORIGINS` no Render; verificar o Mapa de Mesas carregando na URL pública sem erro de CORS
- [x] 7.4 Configurar o UptimeRobot com ping em `/health` e documentar as URLs e variáveis no `README.md`; verificar o monitor ativo

## 8. Verificação integrada

- [x] 8.1 Rodar `pytest tests/unit` e `pytest tests/integration` completos e verificar que todos passam
- [x] 8.2 No ambiente publicado, criar manualmente no banco uma comanda ABERTA, uma PRE_CONTA e uma reserva dentro da janela; verificar que o Mapa de Mesas exibe Ocupada, Aguardando pagamento e Reservada em até 10s

## Workflow follow-up

- Arquivar o change após revisão do grupo (`/opsx:archive`), promovendo as specs `mesas` e `auditoria` para `openspec/specs/`.
- Próximo change: `autenticacao-perfis`.
