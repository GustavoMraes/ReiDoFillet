# Spec Delta

## MODIFIED Requirements

### Requirement: Abertura da comanda pelo mapa de mesas
Na interface, clicar em uma mesa Livre, Ocupada ou Aguardando pagamento MUST abrir ou retomar a comanda e exibir a tela da comanda. Em mesa Livre com reserva próxima informada no mapa, a abertura MUST ser precedida de um aviso com o horário da reserva, que o funcionário confirma ou desiste. Clicar em uma mesa Reservada MUST oferecer o check-in da reserva que a bloqueia, mostrando cliente, pessoas e horário. Clicar em uma mesa em Manutenção MUST exibir a mensagem correspondente e manter o mapa.

#### Scenario: Clique em mesa livre
- **WHEN** o funcionário clica em uma mesa Livre sem reserva próxima no mapa
- **THEN** a comanda é aberta e a tela da comanda é exibida

#### Scenario: Clique em mesa ocupada
- **WHEN** o funcionário clica em uma mesa Ocupada no mapa
- **THEN** a tela da comanda existente é exibida

#### Scenario: Clique em mesa reservada
- **WHEN** o funcionário clica em uma mesa Reservada no mapa
- **THEN** são exibidos o cliente, as pessoas e o horário da reserva, com a opção de fazer o check-in; ao confirmar, a reserva é concluída e a tela da comanda é exibida

#### Scenario: Mesa livre com reserva próxima
- **WHEN** o funcionário clica em uma mesa Livre com reserva às 20h30 informada no mapa
- **THEN** é exibido o aviso "Esta mesa tem reserva às 20h30. Abrir a comanda mesmo assim?"; se confirmar, a comanda é aberta; se desistir, o mapa continua na tela
