# Design

## Context

Motivação em `proposal.md`. O fechamento acontece em `ComandaService._fechar`, chamado por `registrar_pagamento` e `alterar_taxa_servico`, dentro da transação que já bloqueia a comanda (`FOR UPDATE`). O painel da cozinha lista itens EM_PREPARO e PRONTO, sem olhar a comanda. O `log_auditoria` aceita `usuario_id` nulo para operações do sistema e só recusa UPDATE/DELETE.

## Goals / Non-Goals

**Goals:**
- Nenhum item de comanda fechada fica "em andamento", nem no painel nem no histórico.
- Corrigir os dados já gravados em produção sem acesso manual ao banco.

**Non-Goals:**
- Alterar o fluxo da cozinha ou bloquear a pré-conta com itens não entregues (continua só com aviso).

## Decisions

### D1. Entregar no fechamento, em vez de filtrar o painel

O fechamento marca os itens PENDENTE, EM_PREPARO e PRONTO como ENTREGUE (`entregue_em` = horário do fechamento), cada um com auditoria `ENTREGAR` do usuário que fechou, na mesma transação. Alternativa considerada: o painel ignorar itens de comandas fechadas — descartada pelo grupo porque deixaria o histórico inconsistente para os relatórios. `enviado_em` e `pronto_em` de itens que não passaram por essas etapas continuam nulos, registrando o que de fato aconteceu.

### D2. Migração de dados `0002`

Revisão Alembic só de dados, em duas instruções na mesma transação: primeiro insere no `log_auditoria` um registro `ENTREGAR` por item afetado (usuário nulo = sistema, snapshot antes e depois no formato do `ItemComandaSnapshot`), depois atualiza os itens não entregues de comandas FECHADA para ENTREGUE com `entregue_em` = `fechada_em` da comanda. O downgrade não desfaz a correção (não há como distinguir o estado anterior com segurança fora da auditoria). Alternativa considerada: script manual no banco de produção — descartada por não ser revisável nem reproduzível e por exigir acesso direto às credenciais.

## Risks / Trade-offs

- [Item pendente nunca enviado à cozinha fica como entregue] → aceito: o cliente pagou pela conta com o item; a pré-conta já avisa sobre itens não entregues antes do pagamento.
- [Migração roda a cada banco novo] → em banco vazio não afeta nada; é idempotente (só pega itens não entregues de comandas fechadas).

## Migration Plan

Push na `main`: o Render roda `alembic upgrade head` antes de subir a API, aplicando a `0002`. Rollback: redeploy do commit anterior; os itens corrigidos permanecem entregues (estado correto).
