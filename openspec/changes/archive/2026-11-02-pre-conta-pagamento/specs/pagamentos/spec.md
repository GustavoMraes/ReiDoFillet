# Spec Delta

## Purpose

Encerrar o atendimento registrando a taxa de serviço e os pagamentos feitos nas máquinas do estabelecimento, fechando a comanda e liberando a mesa quando o total é quitado, sem integração com meios de pagamento nem emissão de nota fiscal.

## ADDED Requirements

### Requirement: Taxa de serviço opcional
Na primeira pré-conta, a comanda MUST receber o percentual do parâmetro de taxa de serviço padrão, aplicado sobre o subtotal; pré-contas seguintes mantêm a escolha anterior. Em PRE_CONTA, o funcionário SHALL poder desligar ou religar a taxa e ajustar o percentual entre 0 e 100. A taxa MUST NOT tornar o total menor que o valor já pago.

#### Scenario: Taxa padrão na pré-conta
- **WHEN** é gerada a pré-conta de uma comanda com subtotal de R$ 100,00 e o parâmetro de taxa padrão é 10
- **THEN** a comanda passa a ter taxa de 10% aplicada, taxa de R$ 10,00 e total de R$ 110,00

#### Scenario: Nova pré-conta mantém a escolha
- **WHEN** o cliente recusou a taxa, um item novo devolveu a comanda para ABERTA e uma nova pré-conta é gerada
- **THEN** a comanda continua sem taxa de serviço

#### Scenario: Cliente recusa a taxa
- **WHEN** o funcionário desliga a taxa de uma comanda em pré-conta com subtotal de R$ 100,00
- **THEN** o total passa a R$ 100,00 e a mudança é registrada na auditoria

#### Scenario: Percentual ajustado
- **WHEN** o funcionário ajusta o percentual de uma comanda em pré-conta com subtotal de R$ 100,00 para 12
- **THEN** a taxa passa a R$ 12,00 e o total a R$ 112,00

#### Scenario: Percentual inválido
- **WHEN** o funcionário informa um percentual menor que 0 ou maior que 100
- **THEN** nada é alterado e o sistema informa a faixa permitida

#### Scenario: Taxa abaixo do já pago
- **WHEN** uma comanda de total R$ 110,00 já tem R$ 105,00 pagos e o funcionário tenta desligar a taxa
- **THEN** nada é alterado e o sistema informa que o total não pode ficar menor que o valor já pago

#### Scenario: Comanda fora da pré-conta
- **WHEN** é solicitada alteração da taxa em uma comanda que não está em PRE_CONTA
- **THEN** nada é alterado e o sistema informa "A taxa de serviço só pode ser alterada na pré-conta"

### Requirement: Registro de pagamento
O sistema SHALL registrar pagamentos em uma comanda em PRE_CONTA, cada um com forma (PIX, Crédito, Débito ou Dinheiro), valor maior que zero, o funcionário que registrou e o horário. A soma dos pagamentos MUST NOT ultrapassar o total da comanda. Não há integração com maquininha nem emissão de nota fiscal: o pagamento é feito nas máquinas do estabelecimento e apenas registrado no sistema.

#### Scenario: Pagamento parcial
- **WHEN** o funcionário registra R$ 50,00 em PIX em uma comanda de total R$ 110,00
- **THEN** o pagamento é registrado, a comanda continua em PRE_CONTA e o restante passa a R$ 60,00

#### Scenario: Valor acima do restante
- **WHEN** o restante a pagar é R$ 60,00 e o funcionário tenta registrar R$ 70,00
- **THEN** nada é registrado e o sistema informa o valor restante

#### Scenario: Valor inválido
- **WHEN** o funcionário tenta registrar um pagamento de valor zero ou negativo
- **THEN** nada é registrado e o sistema informa que o valor deve ser maior que zero

#### Scenario: Comanda sem pré-conta
- **WHEN** é solicitado um pagamento em uma comanda ABERTA
- **THEN** nada é registrado e o sistema informa "Gere a pré-conta antes de registrar pagamentos"

### Requirement: Fechamento ao quitar o total
Quando a soma dos pagamentos atingir o total da comanda, a comanda MUST passar a FECHADA, com o horário de fechamento, e a mesa MUST voltar a ser exibida como Livre.

#### Scenario: Pagamento que quita a conta
- **WHEN** o restante é R$ 60,00 e o funcionário registra R$ 60,00 no cartão de crédito
- **THEN** a comanda passa a FECHADA e a mesa aparece como Livre no mapa

#### Scenario: Pagamento único do total
- **WHEN** o funcionário registra em dinheiro o valor total de uma comanda em pré-conta
- **THEN** a comanda passa a FECHADA

### Requirement: Remoção de pagamento antes do fechamento
Um pagamento registrado por engano SHALL poder ser removido enquanto a comanda estiver em PRE_CONTA. Pagamentos de comandas fechadas MUST NOT ser removidos.

#### Scenario: Remover pagamento parcial
- **WHEN** o funcionário remove um pagamento de R$ 50,00 de uma comanda em pré-conta
- **THEN** o pagamento deixa de existir, o restante aumenta em R$ 50,00 e a remoção é registrada na auditoria com os dados do pagamento

#### Scenario: Comanda já fechada
- **WHEN** é solicitada a remoção de um pagamento de uma comanda FECHADA
- **THEN** nada é alterado e o sistema informa "Pagamentos de comanda fechada não podem ser removidos"

### Requirement: Resumo financeiro da comanda
A consulta da comanda MUST informar subtotal (itens não cancelados), situação e percentual da taxa de serviço, valor da taxa, total, valor pago, valor restante e a lista de pagamentos com forma, valor, responsável e horário.

#### Scenario: Comanda com pagamento parcial
- **WHEN** é consultada uma comanda em pré-conta com subtotal R$ 100,00, taxa de 10% e R$ 50,00 pagos em PIX
- **THEN** a consulta informa subtotal R$ 100,00, taxa R$ 10,00, total R$ 110,00, pago R$ 50,00, restante R$ 60,00 e o pagamento em PIX

### Requirement: Auditoria dos pagamentos
Registro e remoção de pagamento e alteração da taxa de serviço MUST gerar registros de auditoria com o usuário responsável e os estados anterior e posterior.

#### Scenario: Pagamento auditado
- **WHEN** um funcionário registra um pagamento
- **THEN** é gravado um registro de auditoria com o funcionário e os dados do pagamento

### Requirement: Acesso aos pagamentos restrito por perfil
Taxa de serviço e registro e remoção de pagamentos MUST exigir sessão válida e MUST ser liberados apenas para os perfis Funcionário e Administrador.

#### Scenario: Contabilidade registra pagamento
- **WHEN** um usuário com perfil Contabilidade tenta registrar um pagamento
- **THEN** a requisição é recusada como sem permissão

### Requirement: Tela de pagamento
A interface SHALL exibir, para a comanda em pré-conta, o resumo dos itens, subtotal, controle da taxa de serviço, total, pago e restante, as opções PIX, Cartão de Crédito, Cartão de Débito e Dinheiro, o valor a registrar (inicialmente o restante) e a lista de pagamentos com opção de remover. O botão de confirmação MUST ficar desabilitado até uma forma ser escolhida. Ao fechar a comanda, MUST informar a forma usada e voltar ao Mapa de Mesas.

#### Scenario: Forma não escolhida
- **WHEN** a tela de pagamento é aberta
- **THEN** o botão de confirmar pagamento fica desabilitado até o funcionário escolher uma forma de pagamento

#### Scenario: Quitação pela tela
- **WHEN** o funcionário escolhe PIX e confirma o valor restante
- **THEN** é exibida a mensagem de que o pagamento em PIX foi registrado e a mesa liberada, e o Mapa de Mesas é exibido com a mesa Livre

#### Scenario: Voltar para a comanda
- **WHEN** o funcionário escolhe voltar para a comanda na tela de pagamento
- **THEN** a tela da comanda é exibida
