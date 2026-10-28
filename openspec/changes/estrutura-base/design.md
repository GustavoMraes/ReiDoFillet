# Design

## Context

O repositório contém apenas os documentos de ES II/ES III e a configuração do OpenSpec. A motivação está em `proposal.md` (Why). Restrições relevantes:

- Equipe acadêmica, hospedagem em planos gratuitos (Neon.tech, Render, Vercel): o backend hiberna após inatividade e o banco é serverless.
- Os documentos de origem divergem entre si; as decisões consolidadas pelo grupo prevalecem sobre eles (ver "Desvios dos documentos de origem").
- Este change não tem autenticação: `GET /mesas` fica temporariamente público até o change `autenticacao-perfis`.

## Goals / Non-Goals

**Goals:**
- Fixar o modelo de dados completo, para que os próximos changes não precisem de migrações estruturais (apenas eventuais colunas pontuais).
- Estabelecer o padrão de camadas, injeção de dependência, transação e auditoria que todos os serviços seguirão.
- Ter o fluxo de deploy funcionando desde o primeiro incremento.

**Non-Goals:**
- Regras de transição de comanda, item, pagamento e reserva (pertencem aos changes de cada fluxo; aqui só existem os campos e enums).
- Endpoints de consulta da auditoria (change `relatorios`).
- Tela de login e proteção de rotas.

## Decisions

### D1. Stack e estrutura do monorepo

FastAPI + SQLAlchemy 2 (async) + asyncpg + Alembic + Pydantic Settings no backend; React + Vite + TypeScript no frontend.

```
backend/
  app/
    main.py                 # instancia FastAPI, CORS, registra routers
    core/                   # config.py, exceptions.py, tempo.py (relógio injetável)
    db/                     # session.py (engine/sessão async), base.py
    models/                 # uma entidade por arquivo + enums.py
    schemas/                # contratos Pydantic de entrada/saída
    repositories/           # acesso a dados por entidade
    services/               # regras de negócio + auditoria
    routers/                # endpoints REST
  alembic/                  # migrações versionadas
  scripts/seed.py
  tests/unit/  tests/integration/
frontend/
  src/ api/  pages/  components/  hooks/
docs/                       # PDFs originais
```

Alternativa considerada: Spring Boot (Especificação de ES II e Estudo de Viabilidade). Descartada por decisão do grupo, seguindo a Pesquisa do Estilo Arquitetural de ES III, que já detalha a implementação em FastAPI e o deploy em Neon/Render/Vercel.

### D2. Modelo de dados

```
Funcionario  id, nome, login (único), senha_hash, perfil, bloqueado, criado_em
Mesa         id, numero (único), capacidade, localizacao, em_manutencao
Reserva      id, mesa_id, nome_cliente, telefone, qtd_pessoas, inicio, fim,
             status, criado_por_id, cancelado_por_id, criado_em
Categoria    id, nome (único), ordem
Produto      id, categoria_id, nome, descricao, preco, ativo, disponivel
Comanda      id, mesa_id, funcionario_id, status, aberta_em, pre_conta_em,
             fechada_em, taxa_servico_pct, taxa_servico_aplicada
ItemComanda  id, comanda_id, produto_id, quantidade, observacao, preco_unitario,
             status, criado_em, enviado_em, pronto_em, entregue_em, cancelado_em,
             cancelado_por_id
Pagamento    id, comanda_id, forma, valor, registrado_por_id, registrado_em
Parametro    chave (PK), valor, atualizado_em
LogAuditoria id, usuario_id (nulo = sistema), acao, entidade, entidade_id,
             dados_antes (JSONB), dados_depois (JSONB), criado_em
```

Enums (armazenados como texto com `CHECK`, não como tipo `ENUM` do PostgreSQL, para facilitar migrações):
- `perfil`: FUNCIONARIO, ADMIN, CONTABILIDADE
- `Reserva.status`: CONFIRMADA, CONCLUIDA, CANCELADA (NAO_COMPARECEU é derivado na leitura)
- `Comanda.status`: ABERTA, PRE_CONTA, FECHADA, CANCELADA
- `ItemComanda.status`: PENDENTE, EM_PREPARO, PRONTO, ENTREGUE, CANCELADO
- `Pagamento.forma`: PIX, CREDITO, DEBITO, DINHEIRO

Decisões embutidas no modelo:
- **Comanda virtual**: o `id` identifica o atendimento e nunca é reutilizado; não há número de cartão físico. Mesa 1–N Comandas ao longo do tempo.
- **Uma comanda ativa por mesa**: índice único parcial `UNIQUE (mesa_id) WHERE status IN ('ABERTA','PRE_CONTA')`. Garante a regra mesmo com dois garçons abrindo a mesma mesa ao mesmo tempo.
- **Preço congelado**: `ItemComanda.preco_unitario` é copiado do produto no registro; alterações no cardápio não afetam comandas existentes.
- **Taxa de serviço por comanda**: `taxa_servico_pct` é copiada de `Parametro('taxa_servico_padrao')` na pré-conta e pode ser ajustada até o fechamento.
- **Itens cancelados permanecem**: remoção de item é sempre transição para CANCELADO, nunca exclusão física.
- **Tempos do item** (`enviado_em`, `pronto_em`, `entregue_em`) existem desde já para o tempo médio da UC 7.6, sem alertas.
- **Reserva sem entidade Cliente**: nome e telefone ficam na própria reserva. `fim = inicio + 2h` é usado para detectar conflito entre reservas.
- **Dinheiro**: `Numeric(10,2)`; **datas**: `timestamptz` (gravadas em UTC).
- **Status da mesa não tem coluna**: só `em_manutencao` é armazenado.

Alternativa considerada: entidades `Pedido` + `Item_Pedido` separadas (Pesquisa). Descartada: o envio à cozinha é por item (só os PENDENTE), então o agrupamento "pedido" não carrega informação que o `enviado_em` do item não tenha.

### D3. Cálculo do status da mesa

Implementado em um serviço que recebe as mesas, as comandas ativas e as reservas confirmadas candidatas, e aplica a prioridade definida em `specs/mesas/spec.md`. Para evitar N+1, o repositório busca tudo em três consultas (mesas; comandas ABERTA/PRE_CONTA; reservas CONFIRMADA com `inicio` entre `agora - 30min` e `agora + 30min`).

O horário atual vem de um relógio injetável (`core/tempo.py`), para que os testes dos limites da janela (20h00, 21h00, 21h01) sejam determinísticos.

Alternativa considerada: coluna `status` em `Mesa`, atualizada pelos serviços. Descartada: a janela de reserva depende do relógio, o que exigiria job agendado — inviável com o Render hibernando.

### D4. Transação e auditoria na camada de serviço

Cada requisição recebe uma `AsyncSession` via dependência do FastAPI. Os serviços executam a regra de negócio e chamam `AuditoriaService.registrar(...)` na **mesma sessão**; o commit acontece uma única vez, ao final do serviço. Assim, operação e auditoria são atômicas (spec `auditoria`).

`dados_antes`/`dados_depois` são produzidos por serialização explícita da entidade (schema Pydantic), não por introspecção automática, para não vazar campos sensíveis como `senha_hash`.

Imutabilidade: não existe repositório nem endpoint de update/delete para `LogAuditoria`. Como reforço, a migração cria um trigger que rejeita `UPDATE` e `DELETE` na tabela.

Alternativa considerada: middleware HTTP ou eventos do SQLAlchemy. Descartadas: o middleware não sabe o que mudou no domínio; eventos do ORM não enxergam a intenção da operação (ex.: "cancelar item" vs. "alterar status").

### D5. Atualização da interface por polling

O Mapa de Mesas consulta `GET /mesas` a cada 5 segundos (dentro do limite de 10s da spec). Em falha, mantém os dados anteriores e exibe aviso.

Alternativa considerada: WebSocket. Descartada pela complexidade e pela hibernação do Render; o volume de um restaurante não justifica.

### D6. Deploy

- Neon.tech: PostgreSQL 18 (versão padrão do Neon; o esquema não usa recursos específicos de versão e foi validado na 18.6); conexão direta, sem o host `-pooler`, pois o asyncpg usa prepared statements incompatíveis com o PgBouncer em modo transação; `DATABASE_URL` no formato `postgresql+asyncpg://...?ssl=require` (o asyncpg não aceita os parâmetros `sslmode` e `channel_binding` da string fornecida pelo Neon); migrações aplicadas com `alembic upgrade head`.
- Render: Web Service, build `pip install -r requirements.txt`, start `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Vercel: build Vite com `VITE_API_URL` apontando para o Render.
- CORS: origens permitidas lidas de `CORS_ORIGINS`, nunca `*`.
- UptimeRobot fazendo ping em `GET /health` para reduzir a hibernação.

### Desvios dos documentos de origem

| Documento | Previsto | Decisão |
|---|---|---|
| Especificação ES II / Estudo de Viabilidade | Java Spring Boot, AWS/Azure | FastAPI, Neon/Render/Vercel |
| DER (Especificação) | Entidade Cliente | Sem Cliente; contato na Reserva |
| RNF06 (Especificação) | Reservas como integração futura | Reservas no escopo atual |
| UC 7.2 | Alerta de impressora indisponível | Cupom em tela imprimível; fluxo alternativo removido |
| UC 7.4 | Integração com maquininha e emissão de NF | Pagamento apenas registrado; sem NF |
| Pesquisa | Entidades Pedido e Item_Pedido | Apenas ItemComanda |
| Projeto de Interface | Pagamento "remove a comanda ativa" | Comanda vai para FECHADA e permanece no histórico |
| Interface / UC 7.1 | Uma comanda; reuso de comanda física | Comanda virtual, uma ativa por mesa |

## Risks / Trade-offs

- [Hibernação do Render e do Neon gera primeira requisição lenta (30–50s)] → UptimeRobot no `/health`; acordar o sistema antes de apresentações.
- [Status calculado custa consultas a cada leitura do mapa, com polling de 5s] → três consultas indexadas por leitura; volume de mesas pequeno. Índices em `comanda(mesa_id, status)` e `reserva(mesa_id, status, inicio)`.
- [`GET /mesas` público até o change de autenticação] → não expõe dados pessoais (reserva retorna só horário); proteção entra no change seguinte.
- [Trigger de imutabilidade dificulta limpeza de dados de teste] → testes de integração usam banco próprio recriado a cada execução.
- [Modelo completo antes das regras pode precisar de ajustes] → ajustes pontuais via nova migração Alembic; o objetivo é evitar mudanças estruturais, não congelar o esquema.

## Migration Plan

Primeira implantação, sem dados legados:
1. Criar projeto no Neon e configurar `DATABASE_URL`.
2. Aplicar migrações e executar o seed.
3. Publicar backend no Render e frontend na Vercel; ajustar `CORS_ORIGINS` com o domínio da Vercel.
4. Rollback: `alembic downgrade` para a revisão anterior; redeploy do commit anterior no Render/Vercel.
