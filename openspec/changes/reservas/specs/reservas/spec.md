# Spec Delta

## Purpose

Permitir que o restaurante registre e acompanhe reservas de mesas, guardando o contato do cliente na própria reserva, bloqueando a mesa no horário reservado e abrindo o atendimento no check-in.

## ADDED Requirements

### Requirement: Criação de reserva
O sistema SHALL criar uma reserva CONFIRMADA para uma mesa com nome do cliente (obrigatório, até 100 caracteres), telefone (de 8 a 20 caracteres), quantidade de pessoas (de 1 a 50) e horário de início, que MUST ser futuro. A reserva ocupa a mesa por 2 horas a partir do início. O funcionário que registrou MUST ser gravado.

#### Scenario: Reserva válida
- **WHEN** um funcionário reserva a mesa 4 para "Ana Souza", telefone "11 99999-0000", 2 pessoas, hoje às 20h30
- **THEN** é criada uma reserva CONFIRMADA das 20h30 às 22h30, com o funcionário registrado

#### Scenario: Horário no passado
- **WHEN** um funcionário tenta reservar com início anterior ao horário atual
- **THEN** a reserva não é criada e o sistema informa "O horário da reserva deve ser no futuro"

#### Scenario: Dados obrigatórios ausentes
- **WHEN** um funcionário tenta reservar sem nome do cliente ou com telefone muito curto
- **THEN** a reserva não é criada e o sistema informa qual dado está inválido

### Requirement: Reservas sobrepostas na mesma mesa
O sistema MUST recusar uma reserva cujo período de 2 horas se sobreponha ao de outra reserva CONFIRMADA da mesma mesa, informando o horário da reserva existente. Reservas em mesas diferentes, ou que apenas se encostam (uma termina quando a outra começa), MUST ser aceitas.

#### Scenario: Horários sobrepostos
- **WHEN** a mesa 4 tem reserva das 20h00 às 22h00 e é solicitada outra para as 21h00
- **THEN** a reserva não é criada e o sistema informa "A mesa já tem reserva às 20h00 neste período"

#### Scenario: Horários encostados
- **WHEN** a mesa 4 tem reserva das 20h00 às 22h00 e é solicitada outra para as 22h00
- **THEN** a reserva é criada

#### Scenario: Reserva cancelada não conflita
- **WHEN** a única reserva das 20h00 da mesa 4 está cancelada e é solicitada outra para as 20h30
- **THEN** a reserva é criada

#### Scenario: Reservas simultâneas
- **WHEN** dois funcionários reservam ao mesmo tempo a mesma mesa para horários sobrepostos
- **THEN** apenas uma reserva é criada

### Requirement: Restrições da mesa na reserva
O sistema MUST recusar reserva em mesa em manutenção, com a mensagem "Mesa em manutenção", e em mesa inexistente. Quando a quantidade de pessoas passar da capacidade da mesa, a reserva MUST ser criada com o aviso de que excede a capacidade.

#### Scenario: Mesa em manutenção
- **WHEN** um funcionário tenta reservar uma mesa em manutenção
- **THEN** a reserva não é criada e o sistema informa "Mesa em manutenção"

#### Scenario: Acima da capacidade
- **WHEN** um funcionário reserva para 6 pessoas uma mesa de 4 lugares
- **THEN** a reserva é criada e o sistema avisa que a quantidade excede a capacidade da mesa

### Requirement: Situação da reserva
Cada reserva MUST ser apresentada com uma situação: Confirmada, Concluída, Cancelada ou Não compareceu. "Não compareceu" MUST ser calculada na leitura para reservas confirmadas cujo início foi há mais de 30 minutos, sem tarefa agendada nem alteração no banco.

#### Scenario: Cliente não apareceu
- **WHEN** uma reserva confirmada para as 20h30 é consultada às 21h01
- **THEN** a situação apresentada é Não compareceu

#### Scenario: Ainda dentro da tolerância
- **WHEN** uma reserva confirmada para as 20h30 é consultada às 21h00
- **THEN** a situação apresentada é Confirmada

### Requirement: Consulta das reservas do dia
O sistema SHALL listar as reservas que começam em uma data (no fuso de São Paulo; padrão: hoje), em ordem de horário, com número da mesa, cliente, telefone, quantidade de pessoas, início, fim e situação.

#### Scenario: Reservas de hoje
- **WHEN** existem reservas hoje às 19h00 e às 20h30 e uma amanhã
- **THEN** a consulta de hoje retorna as duas reservas de hoje, na ordem 19h00 e 20h30

### Requirement: Cancelamento de reserva
O sistema SHALL cancelar uma reserva CONFIRMADA, registrando quem cancelou; a mesa deixa de ser bloqueada por ela. Reservas concluídas ou já canceladas MUST NOT ser canceladas.

#### Scenario: Cliente avisa que não vem
- **WHEN** um funcionário cancela uma reserva confirmada que bloqueava a mesa
- **THEN** a reserva passa a CANCELADA e a mesa volta a ser exibida como Livre

#### Scenario: Reserva já concluída
- **WHEN** é solicitado o cancelamento de uma reserva concluída
- **THEN** nada é alterado e o sistema informa "Somente reservas confirmadas podem ser canceladas"

### Requirement: Check-in da reserva
O check-in de uma reserva CONFIRMADA SHALL concluí-la e abrir a comanda da mesa, com o funcionário que fez o check-in como responsável, inclusive se o cliente chegar antes ou depois da janela de bloqueio. Se a mesa já tiver comanda ativa ou estiver em manutenção, o check-in MUST ser recusado e a reserva continuar confirmada.

#### Scenario: Cliente chega no horário
- **WHEN** um funcionário faz o check-in da reserva das 20h30 às 20h25
- **THEN** a reserva passa a CONCLUIDA, é aberta a comanda da mesa e a mesa aparece como Ocupada

#### Scenario: Mesa ainda ocupada
- **WHEN** um funcionário faz o check-in de uma reserva cuja mesa ainda tem comanda aberta
- **THEN** nada é alterado e o sistema informa "A mesa ainda está ocupada: encerre o atendimento anterior antes do check-in"

#### Scenario: Reserva não confirmada
- **WHEN** é solicitado o check-in de uma reserva cancelada
- **THEN** nada é alterado e o sistema informa "Somente reservas confirmadas podem fazer check-in"

### Requirement: Auditoria das reservas
Criação, cancelamento e check-in de reservas MUST gerar registros de auditoria com o usuário responsável e os estados anterior e posterior da reserva.

#### Scenario: Cancelamento auditado
- **WHEN** um funcionário cancela uma reserva
- **THEN** é gravado um registro de auditoria com o funcionário e a reserva antes e depois do cancelamento

### Requirement: Acesso às reservas restrito por perfil
Todas as operações de reserva MUST exigir sessão válida e MUST ser liberadas apenas para os perfis Funcionário e Administrador.

#### Scenario: Contabilidade consulta reservas
- **WHEN** um usuário com perfil Contabilidade consulta as reservas
- **THEN** a requisição é recusada como sem permissão

### Requirement: Tela de reservas
A interface SHALL oferecer a aba Reservas com a lista de um dia escolhido (inicialmente hoje), a situação de cada reserva, um formulário de nova reserva e as ações de cancelar e fazer check-in nas reservas confirmadas. O check-in MUST levar à tela da comanda aberta.

#### Scenario: Nova reserva pela tela
- **WHEN** o funcionário preenche o formulário com mesa, cliente, telefone, pessoas, data e hora e confirma
- **THEN** a reserva aparece na lista do dia e é exibida uma mensagem de confirmação

#### Scenario: Check-in pela tela
- **WHEN** o funcionário clica em "Check-in" em uma reserva confirmada
- **THEN** a tela da comanda da mesa é exibida
