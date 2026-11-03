# Spec Delta

## ADDED Requirements

### Requirement: Geração da pré-conta
O sistema SHALL gerar a pré-conta de uma comanda ABERTA com ao menos um item não cancelado, passando-a a PRE_CONTA com o horário e consolidando os itens consumidos (UC 7.3, RF09). Itens ainda em preparo ou prontos MUST gerar aviso, sem impedir a pré-conta. A mesa passa a ser exibida como Aguardando pagamento.

#### Scenario: Pré-conta com itens entregues
- **WHEN** um funcionário gera a pré-conta de uma comanda com itens entregues
- **THEN** a comanda passa a PRE_CONTA e a mesa aparece como Aguardando pagamento no mapa

#### Scenario: Itens ainda em preparo
- **WHEN** um funcionário gera a pré-conta de uma comanda com um item em preparo
- **THEN** a pré-conta é gerada e o sistema avisa que há itens pendentes de preparo ou entrega

#### Scenario: Comanda sem itens
- **WHEN** um funcionário tenta gerar a pré-conta de uma comanda sem itens ou só com itens cancelados
- **THEN** nada é alterado e o sistema informa "A comanda não tem itens para a pré-conta"

#### Scenario: Comanda que não está aberta
- **WHEN** é solicitada a pré-conta de uma comanda que não está ABERTA
- **THEN** nada é alterado e o sistema informa "A pré-conta só pode ser gerada para uma comanda aberta"

### Requirement: Alteração devolve a comanda para ABERTA
A pré-conta é um retrato da comanda: incluir, alterar ou cancelar item em uma comanda em PRE_CONTA MUST devolvê-la para ABERTA, descartando o horário da pré-conta. Pagamentos já registrados e a configuração da taxa de serviço MUST ser mantidos.

#### Scenario: Item novo após a pré-conta
- **WHEN** um funcionário registra um item em uma comanda em PRE_CONTA
- **THEN** o item é registrado como PENDENTE e a comanda volta para ABERTA

#### Scenario: Cancelamento após a pré-conta
- **WHEN** um item de uma comanda em PRE_CONTA é cancelado
- **THEN** o item passa a CANCELADO e a comanda volta para ABERTA, mantendo os pagamentos já registrados

### Requirement: Cancelamento de comanda sem itens ativos
O sistema SHALL permitir cancelar uma comanda ABERTA ou em PRE_CONTA sem itens ativos (sem itens, ou todos cancelados) e sem pagamentos, passando-a a CANCELADA e liberando a mesa. Com itens ativos MUST ser informado "Cancele os itens antes de cancelar a comanda"; com pagamentos, "Remova os pagamentos antes de cancelar a comanda".

#### Scenario: Mesa aberta por engano
- **WHEN** um funcionário cancela uma comanda aberta sem nenhum item
- **THEN** a comanda passa a CANCELADA, a operação é registrada na auditoria e a mesa aparece como Livre no mapa

#### Scenario: Comanda com itens ativos
- **WHEN** um funcionário tenta cancelar uma comanda com um item pendente
- **THEN** nada é alterado e o sistema informa "Cancele os itens antes de cancelar a comanda"

#### Scenario: Comanda com pagamento registrado
- **WHEN** um funcionário tenta cancelar uma comanda em pré-conta com um pagamento registrado
- **THEN** nada é alterado e o sistema informa "Remova os pagamentos antes de cancelar a comanda"

### Requirement: Pré-conta pela tela da comanda
A tela da comanda SHALL oferecer "Gerar pré-conta", habilitado quando houver itens não cancelados, e "Cancelar comanda", habilitado quando não houver itens ativos. Após gerar a pré-conta, MUST exibir o aviso de itens em preparo quando houver, oferecer a pré-conta em tela própria para impressão e o acesso à tela de pagamento.

#### Scenario: Pré-conta imprimível
- **WHEN** o funcionário gera a pré-conta
- **THEN** é exibida a pré-conta com mesa, garçom, itens com quantidade e subtotal, subtotal, taxa de serviço e total, com opção de imprimir apenas esse conteúdo

#### Scenario: Ir para o pagamento
- **WHEN** a comanda está em PRE_CONTA
- **THEN** a tela da comanda oferece o acesso à tela de pagamento e a aba Pagamento fica disponível

## MODIFIED Requirements

### Requirement: Registro de item na comanda
O sistema SHALL registrar um item em uma comanda ABERTA ou em PRE_CONTA a partir de um produto ativo e disponível, com quantidade entre 1 e 99 e observação opcional de até 200 caracteres. O item MUST iniciar como PENDENTE e MUST guardar o preço do produto no momento do lançamento.

#### Scenario: Item com observação
- **WHEN** um funcionário registra 1 "Filet Mignon 300g" com a observação "ao ponto"
- **THEN** a comanda passa a ter o item PENDENTE com quantidade 1, observação "ao ponto" e o preço atual do produto

#### Scenario: Preço congelado
- **WHEN** o preço de um produto é alterado depois que um item com esse produto foi registrado
- **THEN** o item já registrado mantém o preço do momento do lançamento

#### Scenario: Quantidade inválida
- **WHEN** um funcionário tenta registrar um item com quantidade 0 ou maior que 99
- **THEN** o item não é registrado e o sistema informa a faixa permitida

#### Scenario: Comanda que não está aberta
- **WHEN** um funcionário tenta registrar um item em uma comanda FECHADA ou CANCELADA
- **THEN** o item não é registrado e é exibida a mensagem "A comanda não está aberta para novos itens"

### Requirement: Alteração de item pendente
O sistema SHALL permitir alterar a quantidade (entre 1 e 99) e a observação de um item PENDENTE de uma comanda ABERTA ou em PRE_CONTA. Itens em qualquer outro status MUST NOT ser alterados, com a mensagem "Apenas itens pendentes podem ser alterados".

#### Scenario: Alterar quantidade
- **WHEN** um funcionário altera a quantidade de um item pendente de 1 para 2
- **THEN** o item passa a ter quantidade 2 e o subtotal e o total são recalculados

#### Scenario: Item já enviado
- **WHEN** um funcionário tenta alterar um item em preparo
- **THEN** o item não é alterado e é exibida a mensagem "Apenas itens pendentes podem ser alterados"

### Requirement: Total da comanda
O subtotal da comanda MUST ser a soma de quantidade vezes preço unitário dos itens não cancelados. O total MUST ser o subtotal acrescido da taxa de serviço quando a comanda estiver em PRE_CONTA ou FECHADA com a taxa aplicada, arredondado para duas casas decimais; em comanda ABERTA, o total é o subtotal. Ambos são recalculados a cada consulta.

#### Scenario: Total com item cancelado
- **WHEN** a comanda tem 2 itens de R$ 7,00 e 1 item de R$ 89,90 cancelado
- **THEN** o total da comanda é R$ 14,00

#### Scenario: Total com taxa de serviço
- **WHEN** uma comanda em PRE_CONTA tem subtotal de R$ 33,90 e taxa de 10% aplicada
- **THEN** a taxa é R$ 3,39 e o total é R$ 37,29

#### Scenario: Taxa não se aplica a comanda aberta
- **WHEN** uma comanda volta para ABERTA após a pré-conta
- **THEN** o total volta a ser igual ao subtotal até a próxima pré-conta
