# Tasks

## 1. Fechamento

- [x] 1.1 No fechamento da comanda (pagamento e ajuste de taxa), marcar itens PENDENTE, EM_PREPARO e PRONTO como ENTREGUE com o horário do fechamento e auditoria `ENTREGAR` (D1); testes de integração de "Itens ainda na cozinha no fechamento" (status, horário, saída do painel e auditoria), "Item cancelado no fechamento" e fechamento pelo ajuste da taxa

## 2. Dados já gravados

- [x] 2.1 Criar a migração de dados `0002` (D2); teste de integração que volta à `0001`, grava uma comanda fechada com itens em preparo, pronto, entregue e cancelado e uma comanda aberta com item em preparo, aplica a `0002` e verifica que só os dois itens não entregues da comanda fechada mudaram, com um registro de auditoria do sistema para cada um

## 3. Implantação e verificação

- [x] 3.1 Rodar `pytest` completo e verificar que tudo passa
- [ ] 3.2 Publicar (push na `main`), confirmar que o deploy aplicou a migração e que os itens presos sumiram do painel da cozinha em produção; repetir o fluxo do problema (pagar uma comanda com item em preparo) e confirmar que o item sai do painel

## Workflow follow-up

- Arquivar o change (`/opsx:archive`), aplicando a delta de `pagamentos`.
