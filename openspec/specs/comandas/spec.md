# comandas Specification

## Purpose

Permitir que funcionários e administradores abram a comanda de uma mesa e registrem e mantenham os itens pedidos pelos consumidores, com o total calculado automaticamente, substituindo as anotações em papel.

## Requirements

### Requirement: Abertura de comanda em mesa livre
O sistema SHALL abrir uma comanda no estado ABERTA para uma mesa sem comanda ativa, fora de manutenção e não reservada, registrando o usuário autenticado como funcionário responsável (RF10) e gerando um identificador único para o atendimento.

#### Scenario: Mesa livre
- **WHEN** um funcionário abre a comanda de uma mesa livre
- **THEN** é criada uma comanda ABERTA para a mesa, com o funcionário como responsável, e a mesa passa a ser exibida como Ocupada no mapa

#### Scenario: Identificador único
- **WHEN** duas mesas diferentes têm comandas abertas
- **THEN** cada comanda possui um identificador próprio, que nunca é reutilizado

### Requirement: Retomada da comanda ativa
Quando a mesa já possui uma comanda ativa (ABERTA ou PRE_CONTA), a abertura MUST retornar essa comanda em vez de criar outra. Pedidos simultâneos de abertura para a mesma mesa MUST resultar em uma única comanda.

#### Scenario: Mesa ocupada
- **WHEN** um funcionário abre a comanda de uma mesa que já tem uma comanda ABERTA
- **THEN** o sistema retorna a comanda existente, sem criar uma nova, mantendo o responsável original

#### Scenario: Abertura simultânea
- **WHEN** dois funcionários abrem a comanda da mesma mesa livre ao mesmo tempo
- **THEN** apenas uma comanda é criada e os dois recebem a mesma comanda

### Requirement: Mesas que não podem abrir comanda
O sistema MUST recusar a abertura de comanda em mesa em manutenção, com a mensagem "Mesa em manutenção", e em mesa reservada, com a mensagem "Mesa reservada: aguarde o check-in do cliente". Mesa inexistente MUST resultar em "Mesa não encontrada".

#### Scenario: Mesa em manutenção
- **WHEN** um funcionário tenta abrir a comanda de uma mesa em manutenção
- **THEN** nenhuma comanda é criada e é exibida a mensagem "Mesa em manutenção"

#### Scenario: Mesa reservada
- **WHEN** um funcionário tenta abrir a comanda de uma mesa dentro da janela de bloqueio de uma reserva
- **THEN** nenhuma comanda é criada e é exibida a mensagem "Mesa reservada: aguarde o check-in do cliente"

#### Scenario: Mesa inexistente
- **WHEN** é solicitada a abertura de comanda para uma mesa que não existe
- **THEN** nenhuma comanda é criada e o sistema informa "Mesa não encontrada"

### Requirement: Consulta da comanda
O sistema SHALL apresentar a comanda com o número da mesa, o nome do funcionário responsável, a data e hora de abertura, o status e os itens em ordem de lançamento. Cada item MUST informar produto, quantidade, observação, preço unitário, subtotal e status.

#### Scenario: Comanda com itens
- **WHEN** um funcionário consulta uma comanda com três itens lançados
- **THEN** o sistema apresenta a mesa, o responsável, a abertura, o status e os três itens na ordem em que foram lançados, cada um com seu subtotal e status

#### Scenario: Comanda inexistente
- **WHEN** é consultada uma comanda que não existe
- **THEN** o sistema informa "Comanda não encontrada"

### Requirement: Registro de item na comanda
O sistema SHALL registrar um item em uma comanda ABERTA a partir de um produto ativo e disponível, com quantidade entre 1 e 99 e observação opcional de até 200 caracteres. O item MUST iniciar como PENDENTE e MUST guardar o preço do produto no momento do lançamento.

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
- **WHEN** um funcionário tenta registrar um item em uma comanda que não está ABERTA
- **THEN** o item não é registrado e é exibida a mensagem "A comanda não está aberta para novos itens"

### Requirement: Recusa de item indisponível
O sistema MUST recusar o registro de produto inativo ou indisponível no momento com a mensagem "Item indisponível", sem alterar a comanda (fluxo alternativo do UC 7.1).

#### Scenario: Produto esgotado
- **WHEN** um funcionário tenta registrar um produto marcado como indisponível
- **THEN** o item não é registrado e é exibida a mensagem "Item indisponível"

#### Scenario: Produto inativo
- **WHEN** um funcionário tenta registrar um produto inativo
- **THEN** o item não é registrado e é exibida a mensagem "Item indisponível"

### Requirement: Itens idênticos somam quantidade
Ao registrar um item, se a comanda já tiver um item PENDENTE do mesmo produto, com a mesma observação (ignorando espaços nas pontas e diferença entre maiúsculas e minúsculas) e o mesmo preço unitário, o sistema MUST somar a quantidade nesse item em vez de criar outro, respeitando o máximo de 99.

#### Scenario: Mesmo produto e mesma observação
- **WHEN** a comanda tem 1 "Refrigerante Lata" pendente sem observação e o funcionário registra mais 2 iguais
- **THEN** a comanda passa a ter um único item "Refrigerante Lata" pendente com quantidade 3

#### Scenario: Observação diferente
- **WHEN** a comanda tem 1 "Filet Mignon 300g" pendente sem observação e o funcionário registra 1 com a observação "sem sal"
- **THEN** a comanda passa a ter dois itens separados desse produto

#### Scenario: Item igual já enviado à cozinha
- **WHEN** a comanda tem 1 "Batata Rústica" em preparo e o funcionário registra mais 1 igual
- **THEN** é criado um novo item PENDENTE, sem alterar o item em preparo

#### Scenario: Soma acima do máximo
- **WHEN** a soma com o item pendente idêntico ultrapassaria 99 unidades
- **THEN** nada é alterado e o sistema informa a quantidade máxima permitida

### Requirement: Alteração de item pendente
O sistema SHALL permitir alterar a quantidade (entre 1 e 99) e a observação de um item PENDENTE de uma comanda ABERTA. Itens em qualquer outro status MUST NOT ser alterados, com a mensagem "Apenas itens pendentes podem ser alterados".

#### Scenario: Alterar quantidade
- **WHEN** um funcionário altera a quantidade de um item pendente de 1 para 2
- **THEN** o item passa a ter quantidade 2 e o subtotal e o total são recalculados

#### Scenario: Item já enviado
- **WHEN** um funcionário tenta alterar um item em preparo
- **THEN** o item não é alterado e é exibida a mensagem "Apenas itens pendentes podem ser alterados"

### Requirement: Cancelamento de item
Itens MUST NOT ser excluídos: a remoção é a mudança para CANCELADO, registrando quem cancelou e quando. Item PENDENTE pode ser cancelado por Funcionário ou Administrador. Item já enviado à cozinha (EM_PREPARO, PRONTO ou ENTREGUE) MUST ser cancelado somente por Administrador (RN02).

#### Scenario: Cancelar item pendente
- **WHEN** um funcionário cancela um item pendente
- **THEN** o item passa a CANCELADO, com o funcionário e o horário do cancelamento, e deixa de compor o total

#### Scenario: Funcionário cancela item enviado
- **WHEN** um usuário com perfil Funcionário tenta cancelar um item em preparo
- **THEN** o item não é cancelado e a requisição é recusada com a mensagem "Itens enviados à cozinha só podem ser cancelados por um administrador"

#### Scenario: Administrador cancela item enviado
- **WHEN** um usuário com perfil Administrador cancela um item em preparo
- **THEN** o item passa a CANCELADO e deixa de compor o total

#### Scenario: Item já cancelado
- **WHEN** é solicitado o cancelamento de um item já cancelado
- **THEN** nada é alterado e o sistema informa "Item já cancelado"

### Requirement: Total da comanda
O total da comanda MUST ser a soma de quantidade vezes preço unitário de todos os itens não cancelados, com duas casas decimais, recalculado a cada consulta.

#### Scenario: Total com item cancelado
- **WHEN** a comanda tem 2 itens de R$ 7,00 e 1 item de R$ 89,90 cancelado
- **THEN** o total da comanda é R$ 14,00

### Requirement: Auditoria das operações da comanda
A abertura da comanda e o registro, a alteração e o cancelamento de itens MUST gerar registros de auditoria com o usuário responsável e os estados anterior e posterior.

#### Scenario: Registro de item auditado
- **WHEN** um funcionário registra um item
- **THEN** é gravado um registro de auditoria com o funcionário, a ação e os dados do item

#### Scenario: Cancelamento auditado
- **WHEN** um item é cancelado
- **THEN** é gravado um registro de auditoria com quem cancelou e o item antes e depois do cancelamento

### Requirement: Acesso às comandas restrito por perfil
Todas as operações de comanda MUST exigir sessão válida e MUST ser liberadas apenas para os perfis Funcionário e Administrador.

#### Scenario: Contabilidade tenta abrir comanda
- **WHEN** um usuário com perfil Contabilidade tenta abrir uma comanda
- **THEN** a requisição é recusada como sem permissão

### Requirement: Abertura da comanda pelo mapa de mesas
Na interface, clicar em uma mesa Livre, Ocupada ou Aguardando pagamento MUST abrir ou retomar a comanda e exibir a tela da comanda. Clicar em uma mesa em Manutenção ou Reservada MUST exibir a mensagem correspondente e manter o mapa.

#### Scenario: Clique em mesa livre
- **WHEN** o funcionário clica em uma mesa Livre no mapa
- **THEN** a comanda é aberta e a tela da comanda é exibida

#### Scenario: Clique em mesa ocupada
- **WHEN** o funcionário clica em uma mesa Ocupada no mapa
- **THEN** a tela da comanda existente é exibida

#### Scenario: Clique em mesa reservada
- **WHEN** o funcionário clica em uma mesa Reservada no mapa
- **THEN** é exibida a mensagem "Mesa reservada: aguarde o check-in do cliente" e o mapa continua na tela

### Requirement: Tela da comanda
A tela da comanda SHALL exibir o cardápio por categoria, com controle para adicionar cada produto com quantidade e observação, os produtos indisponíveis desabilitados e identificados, os itens lançados com status e subtotal, controles para alterar e cancelar itens e o total. A tela MUST atualizar automaticamente em no máximo 10 segundos e confirmar cada ação com uma mensagem temporária.

#### Scenario: Adicionar produto
- **WHEN** o funcionário adiciona um produto disponível pelo cardápio
- **THEN** o item aparece na lista da comanda, o total é atualizado e é exibida uma mensagem de confirmação

#### Scenario: Produto indisponível na tela
- **WHEN** a tela exibe um produto indisponível
- **THEN** o produto aparece identificado como "Indisponível" e sem a opção de adicionar

#### Scenario: Atualização por outro dispositivo
- **WHEN** outro funcionário registra um item na mesma comanda em outro dispositivo
- **THEN** o item aparece na tela em no máximo 10 segundos, sem ação do usuário

#### Scenario: Voltar ao mapa
- **WHEN** o funcionário escolhe voltar ao mapa de mesas
- **THEN** o mapa é exibido com a mesa como Ocupada
