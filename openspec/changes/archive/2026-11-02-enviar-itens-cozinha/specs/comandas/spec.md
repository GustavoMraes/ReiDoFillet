# Spec Delta

## ADDED Requirements

### Requirement: Envio dos itens pendentes à cozinha
O sistema SHALL enviar à cozinha todos os itens PENDENTES de uma comanda ABERTA, de uma só vez, mudando-os para EM_PREPARO com o mesmo horário de envio. Itens em outros status MUST NOT ser alterados. Sem itens pendentes, MUST ser informado "Não há itens pendentes para enviar" (UC 7.2, RF03).

#### Scenario: Envio de itens pendentes
- **WHEN** um funcionário envia uma comanda com dois itens pendentes e um item já em preparo
- **THEN** os dois itens pendentes passam a EM_PREPARO com o mesmo horário de envio e o item que já estava em preparo não é alterado

#### Scenario: Nada a enviar
- **WHEN** um funcionário envia uma comanda sem itens pendentes
- **THEN** nada é alterado e o sistema informa "Não há itens pendentes para enviar"

#### Scenario: Comanda que não está aberta
- **WHEN** é solicitado o envio de uma comanda que não está ABERTA
- **THEN** nada é alterado e o sistema informa "A comanda não está aberta para envio"

#### Scenario: Envios simultâneos
- **WHEN** dois funcionários enviam a mesma comanda ao mesmo tempo
- **THEN** cada item pendente é enviado uma única vez e o segundo envio informa "Não há itens pendentes para enviar"

### Requirement: Cupom do envio
O envio MUST disponibilizar o cupom com o número da mesa, o nome do garçom que enviou, o horário do envio e os itens enviados nesse envio, com quantidade, produto e observação. A interface SHALL exibir o cupom em uma tela própria para impressão pelo navegador.

#### Scenario: Cupom após o envio
- **WHEN** um funcionário envia dois itens, um deles com a observação "sem sal"
- **THEN** o cupom lista os dois itens com quantidade, produto e a observação "sem sal", além da mesa, do garçom e do horário do envio

#### Scenario: Imprimir o cupom
- **WHEN** o funcionário escolhe imprimir o cupom
- **THEN** o navegador abre a impressão apenas com o conteúdo do cupom, sem menus nem botões da aplicação

### Requirement: Auditoria do envio
Cada envio MUST gerar um registro de auditoria por item enviado, com o funcionário responsável e o item antes e depois do envio.

#### Scenario: Envio auditado
- **WHEN** um funcionário envia dois itens
- **THEN** são gravados dois registros de auditoria de envio, um por item, com status anterior PENDENTE e posterior EM_PREPARO

### Requirement: Envio pela tela da comanda
A tela da comanda SHALL oferecer o botão "Enviar itens para a cozinha", habilitado somente quando houver itens pendentes. Após o envio, MUST exibir uma mensagem de confirmação, mostrar os itens com o status "Em preparo" e oferecer a impressão do cupom.

#### Scenario: Botão sem itens pendentes
- **WHEN** a comanda não tem itens pendentes
- **THEN** o botão "Enviar itens para a cozinha" aparece desabilitado

#### Scenario: Envio pela tela
- **WHEN** o funcionário clica em "Enviar itens para a cozinha" com itens pendentes
- **THEN** é exibida a mensagem de confirmação, os itens passam a "Em preparo" na lista e é oferecida a impressão do cupom
