# Design

## Context

Motivação em `proposal.md`. Estado atual relevante:

- `Comanda` tem `aberta_em`, `fechada_em`, status, taxa (`taxa_servico_pct`, `taxa_servico_aplicada`) e responsável; `ItemComanda` guarda `preco_unitario` do lançamento; `Pagamento` tem forma e valor. Não há índice em `aberta_em` nem em `fechada_em`; `log_auditoria.criado_em` já é indexado.
- `services/financeiro.calcular` é a regra única de subtotal, taxa, total, pago e restante usada pelas telas de comanda e pagamento.
- `services/reserva_tempo` tem `fuso_local()` e `intervalo_do_dia(dia)` (dia local → instantes UTC).
- `AuditoriaService.registrar` grava registros com snapshots Pydantic; a tabela é imutável por trigger.
- A Contabilidade hoje vê `AvisoContabilidade`; o `@media print` do `index.css` imprime só o elemento `.impressao`.

## Goals / Non-Goals

**Goals:**
- Números dos relatórios idênticos aos das telas (mesma função de cálculo).
- Consultas só de leitura, cada uma deixando rastro na auditoria.

**Non-Goals:**
- Gráficos com biblioteca, agendamento ou envio de relatórios por e-mail, comparação entre períodos, relatórios de reservas e de ocupação de mesas (ficam para evolução).

## Decisions

### D1. Período

Utilitário `periodo(inicio, fim, agora) -> (de_utc, ate_utc)` com `[início do dia inicial, início do dia seguinte ao final)` em São Paulo, padrão hoje, validando ordem e limite de 366 dias (`DadoInvalido`, 422). `fuso_local` e `intervalo_do_dia` saem de `reserva_tempo` para `core/tempo.py`, usados pelos dois módulos.

### D2. Cálculo em Python sobre poucas consultas

Cada relatório faz três consultas: as comandas do período (com mesa e responsável), os itens dessas comandas e os pagamentos dessas comandas (`WHERE comanda_id IN (...)`). Os totais de cada comanda saem de `financeiro.calcular`, e os agrupamentos (situação, produto, dia e hora locais, forma de pagamento) são feitos em Python. Alternativa considerada: agregar tudo em SQL — descartada por duplicar a regra da taxa de serviço e de itens cancelados, com risco de o relatório divergir da tela de pagamento.

- **Operacional:** comandas com `aberta_em` no período. Em aberto = ABERTA + PRE_CONTA. Faturamento, ticket médio, tempo médio, produtos e faturamento por dia usam só as fechadas desse conjunto (o dia de uma comanda é o da abertura). Tempo médio em minutos inteiros (arredondamento comercial).
- **Financeiro:** comandas FECHADA com `fechada_em` no período, em ordem de fechamento; totais somados por comanda e pagamentos agrupados por forma (as quatro formas sempre presentes, com zero).

### D3. Rotas

| Rota | Perfis |
|---|---|
| `GET /relatorios/operacional?inicio=AAAA-MM-DD&fim=AAAA-MM-DD` | Admin |
| `GET /relatorios/financeiro?inicio=&fim=` | Admin, Contabilidade |
| `GET /auditoria?inicio=&fim=&usuario_id=&acao=&entidade=&pagina=1` | Admin, Contabilidade |
| `GET /auditoria/opcoes` | Admin, Contabilidade (usuários, ações e entidades para os filtros) |

Datas devolvidas no fuso de São Paulo; valores como texto decimal, como nas demais rotas. A auditoria devolve `{registros, total, pagina, paginas}`.

### D4. Rastro das consultas

Nova ação `CONSULTAR`, entidade `Relatorio`, `entidade_id` = `operacional`, `financeiro` ou `auditoria`, e `dados_depois` = `ConsultaSnapshot` com os filtros (período, usuário, ação, entidade, página). O registro é gravado depois da leitura, em transação própria, para a consulta da auditoria não incluir a si mesma. `GET /auditoria/opcoes` não é registrado (só monta filtros).

### D5. Índices

Migração `0004` cria `ix_comanda_aberta_em` e `ix_comanda_fechada_em`, refletidos no model.

### D6. Interface

- Aba **Relatórios**: Administrador vê Operacional, Financeiro e Auditoria; Contabilidade vê Financeiro e Auditoria e entra direto nela após o login (substitui `AvisoContabilidade`).
- Filtro de período compartilhado (datas inicial e final, atalhos Hoje, Últimos 7 dias e Mês atual) e botão "Consultar"; sem polling.
- **Operacional:** cartões de indicadores, tabela de produtos, barras horizontais em CSS para dias e horários.
- **Financeiro:** totais por forma e tabela de comandas (pagamentos em linha).
- **Auditoria:** filtros de usuário, ação e entidade, tabela paginada e detalhes antes/depois expansíveis.
- **CSV** gerado no navegador (separador `;`, BOM UTF-8, vírgula decimal, datas `dd/mm/aaaa hh:mm`), baixado por `Blob`. **Imprimir** usa `window.print()` com a seção marcada como `.impressao`, em página A4 (a regra atual de 72 mm vale só para cupom e pré-conta).

## Risks / Trade-offs

- [Período de um ano carrega muitas linhas em memória] → limite de 366 dias e índices novos; o volume de um restaurante (milhares de comandas por ano) cabe com folga no plano atual do Render. Se crescer, as somas passam para SQL mantendo os testes de equivalência.
- [Registrar consulta torna um GET em escrita] → exigido pela HU07; a gravação é pequena e isolada da leitura.
- [Comanda aberta antes do período e fechada dentro dele] → aparece no financeiro (pelo fechamento) e não no operacional (pela abertura); a tela explica o critério de cada relatório.

## Migration Plan

Push na `main`: o Render roda `alembic upgrade head` (aplica a `0004`) e sobe a API; a Vercel publica a interface. Rollback: redeploy do commit anterior e `alembic downgrade 0003`.
