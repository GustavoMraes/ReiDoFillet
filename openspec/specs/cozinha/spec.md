# cozinha Specification

## Purpose

Apresentar à cozinha os itens enviados pelo salão, organizados por estágio de preparo, e registrar quando cada item fica pronto e quando é entregue à mesa.

## Requirements

### Requirement: Fila da cozinha por estágio
O sistema SHALL apresentar os itens enviados à cozinha agrupados em Em preparo e Pronto, cada grupo em ordem de envio (o mais antigo primeiro), informando para cada item: número da mesa, quantidade, produto, observação, horário do envio e minutos decorridos desde o envio. Itens PENDENTES, ENTREGUES ou CANCELADOS MUST NOT aparecer.

#### Scenario: Itens em estágios diferentes
- **WHEN** existem dois itens em preparo, enviados às 20h00 e às 20h05, e um item pronto
- **THEN** o painel mostra os dois itens em preparo na ordem 20h00, 20h05 e o item pronto no grupo Pronto, cada um com mesa, quantidade, produto e observação

#### Scenario: Itens que não pertencem à fila
- **WHEN** uma comanda tem um item pendente, um entregue e um cancelado
- **THEN** nenhum desses itens aparece no painel

#### Scenario: Tempo desde o envio
- **WHEN** um item foi enviado há 12 minutos e 30 segundos
- **THEN** o painel informa 12 minutos para esse item

### Requirement: Marcar item como pronto
O sistema SHALL permitir mudar um item de EM_PREPARO para PRONTO, registrando o horário. Item em qualquer outro estágio MUST NOT ser marcado como pronto, com a mensagem "Somente itens em preparo podem ser marcados como prontos".

#### Scenario: Item em preparo
- **WHEN** a cozinha marca como pronto um item em preparo
- **THEN** o item passa a PRONTO, com o horário registrado, e aparece no grupo Pronto

#### Scenario: Item que não está em preparo
- **WHEN** é solicitado marcar como pronto um item já entregue
- **THEN** nada é alterado e o sistema informa "Somente itens em preparo podem ser marcados como prontos"

### Requirement: Marcar item como entregue
O sistema SHALL permitir mudar um item de PRONTO para ENTREGUE, registrando o horário; o item sai do painel. Item em qualquer outro estágio MUST NOT ser marcado como entregue, com a mensagem "Somente itens prontos podem ser marcados como entregues".

#### Scenario: Item pronto
- **WHEN** um funcionário marca como entregue um item pronto
- **THEN** o item passa a ENTREGUE, com o horário registrado, e deixa de aparecer no painel

#### Scenario: Item ainda em preparo
- **WHEN** é solicitado marcar como entregue um item em preparo
- **THEN** nada é alterado e o sistema informa "Somente itens prontos podem ser marcados como entregues"

### Requirement: Item cancelado deixa a fila
Um item em preparo ou pronto cancelado por um administrador (RN02) MUST deixar o painel e MUST NOT poder ser marcado como pronto ou entregue.

#### Scenario: Cancelamento durante o preparo
- **WHEN** um administrador cancela um item que estava em preparo
- **THEN** o item deixa de aparecer no painel e tentativas de marcá-lo como pronto são recusadas

### Requirement: Auditoria das mudanças de estágio
Cada mudança de estágio feita pelo painel MUST gerar um registro de auditoria com o usuário responsável e o item antes e depois da mudança.

#### Scenario: Item marcado como pronto
- **WHEN** um funcionário marca um item como pronto
- **THEN** é gravado um registro de auditoria com o funcionário e o status anterior EM_PREPARO e posterior PRONTO

### Requirement: Acesso ao painel restrito por perfil
O painel e as mudanças de estágio MUST exigir sessão válida e MUST ser liberados apenas para os perfis Funcionário e Administrador.

#### Scenario: Contabilidade consulta o painel
- **WHEN** um usuário com perfil Contabilidade consulta o painel da cozinha
- **THEN** a requisição é recusada como sem permissão

### Requirement: Tela do Painel da Cozinha
A interface SHALL exibir o painel na aba Cozinha, com uma coluna por estágio e a contagem de itens de cada uma, o botão "Marcar como pronto" nos itens em preparo e "Marcar como entregue" nos itens prontos. A tela MUST atualizar automaticamente em no máximo 10 segundos e confirmar cada ação com uma mensagem temporária.

#### Scenario: Itens recém-enviados
- **WHEN** um garçom envia itens à cozinha enquanto o painel está aberto em outro dispositivo
- **THEN** os itens aparecem na coluna Em preparo em no máximo 10 segundos, sem ação do usuário

#### Scenario: Marcar pela tela
- **WHEN** o funcionário clica em "Marcar como pronto" em um item
- **THEN** o item passa para a coluna Pronto e é exibida uma mensagem de confirmação

#### Scenario: Painel vazio
- **WHEN** não há itens em preparo nem prontos
- **THEN** cada coluna informa que não há itens
