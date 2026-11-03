# Spec Delta

## MODIFIED Requirements

### Requirement: Fechamento ao quitar o total
Quando a soma dos pagamentos atingir o total da comanda, a comanda MUST passar a FECHADA, com o horário de fechamento, e a mesa MUST voltar a ser exibida como Livre. No fechamento, os itens ainda pendentes, em preparo ou prontos MUST passar a ENTREGUE com o horário do fechamento, deixando o painel da cozinha, com registro de auditoria; itens cancelados não mudam.

#### Scenario: Pagamento que quita a conta
- **WHEN** o restante é R$ 60,00 e o funcionário registra R$ 60,00 no cartão de crédito
- **THEN** a comanda passa a FECHADA e a mesa aparece como Livre no mapa

#### Scenario: Pagamento único do total
- **WHEN** o funcionário registra em dinheiro o valor total de uma comanda em pré-conta
- **THEN** a comanda passa a FECHADA

#### Scenario: Itens ainda na cozinha no fechamento
- **WHEN** uma comanda com um item em preparo e outro pronto é fechada pelo pagamento
- **THEN** os dois itens passam a Entregue com o horário do fechamento, saem do painel da cozinha e cada mudança gera um registro de auditoria

#### Scenario: Item cancelado no fechamento
- **WHEN** uma comanda com um item cancelado e um item entregue é fechada
- **THEN** o item cancelado continua Cancelado e o entregue mantém o horário de entrega original
