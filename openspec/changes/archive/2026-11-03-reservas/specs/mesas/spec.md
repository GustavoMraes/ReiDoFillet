# Spec Delta

## MODIFIED Requirements

### Requirement: Informações complementares do atendimento
Para mesas OCUPADA ou AGUARDANDO_PAGAMENTO, o mapa MUST informar o tempo decorrido, em minutos inteiros, desde a abertura da comanda ativa. Para mesas RESERVADA, o mapa MUST informar o horário de início da reserva que causou o bloqueio. Para mesas LIVRE com reserva confirmada que comece nas próximas 2 horas, o mapa MUST informar o horário dessa próxima reserva.

#### Scenario: Tempo de atendimento de mesa ocupada
- **WHEN** a comanda ativa da mesa foi aberta há 18 minutos e 40 segundos
- **THEN** o mapa informa 18 minutos de atendimento para essa mesa

#### Scenario: Horário da reserva em mesa reservada
- **WHEN** a mesa está RESERVADA por uma reserva confirmada para as 20h30
- **THEN** o mapa informa o horário 20h30 para essa mesa

#### Scenario: Mesa livre sem informação complementar
- **WHEN** a mesa está LIVRE e não tem reserva confirmada nas próximas 2 horas
- **THEN** o mapa não informa tempo de atendimento nem horário de reserva

#### Scenario: Mesa livre com reserva próxima
- **WHEN** a mesa está LIVRE às 18h40 e tem reserva confirmada para as 20h30
- **THEN** o mapa informa a próxima reserva às 20h30 para essa mesa, que continua LIVRE

#### Scenario: Reserva distante não aparece
- **WHEN** a mesa está LIVRE às 18h00 e sua próxima reserva confirmada é às 20h30
- **THEN** o mapa não informa horário de reserva para essa mesa
