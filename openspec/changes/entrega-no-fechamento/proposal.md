# Proposal

## Why

Na verificação em produção, uma comanda foi paga e fechada enquanto seus itens ainda estavam "em preparo" no painel da cozinha. Como a comanda fechada não aceita mais alterações e o painel lista todo item em preparo ou pronto, esses itens ficaram presos na cozinha para sempre, e o histórico passou a registrar como não entregue algo que o cliente consumiu e pagou.

## What Changes

- Ao fechar a comanda (pagamento que quita o total, ou ajuste da taxa que zera o restante), os itens ainda pendentes, em preparo ou prontos MUST passar a ENTREGUE, com o horário do fechamento e registro de auditoria; com isso saem do painel da cozinha.
- Migração de dados corrige os itens já presos em produção: itens não entregues de comandas FECHADA passam a ENTREGUE com o horário de fechamento da comanda, com registro de auditoria feito pelo sistema.
- Itens cancelados não mudam. Comandas canceladas não são afetadas (só podem ser canceladas sem itens ativos).

## Capabilities

### New Capabilities

(nenhuma)

### Modified Capabilities

- `pagamentos`: o requisito "Fechamento ao quitar o total" passa a concluir a entrega dos itens não entregues.

## Impact

- **Backend:** fechamento em `ComandaService` (usado por pagamento e por alteração da taxa), nova migração Alembic `0002` só de dados, testes de integração do fechamento e da migração.
- **Frontend:** nenhum código; o painel da cozinha deixa de mostrar os itens assim que a comanda fecha.
- **Banco:** sem mudança de esquema; a migração roda no deploy (`alembic upgrade head` no Render).
