# mesas Specification

## Purpose

Permitir que funcionários e administradores visualizem o mapa de mesas do restaurante com a situação atual de cada mesa, calculada a partir de manutenção, comanda ativa e reservas.

## Requirements

### Requirement: Listagem do mapa de mesas
O sistema SHALL disponibilizar a listagem de todas as mesas cadastradas, ordenadas pelo número, contendo para cada mesa: número, capacidade, localização e status atual.

#### Scenario: Consulta do mapa com mesas cadastradas
- **WHEN** o mapa de mesas é consultado e existem 8 mesas cadastradas
- **THEN** o sistema retorna as 8 mesas ordenadas por número crescente, cada uma com número, capacidade, localização e status

#### Scenario: Consulta do mapa sem mesas cadastradas
- **WHEN** o mapa de mesas é consultado e não existe nenhuma mesa cadastrada
- **THEN** o sistema retorna uma lista vazia, sem erro

### Requirement: Status da mesa calculado na leitura
O status da mesa MUST ser calculado no momento da consulta, nunca armazenado, assumindo exatamente um dos valores: MANUTENCAO, OCUPADA, AGUARDANDO_PAGAMENTO, RESERVADA ou LIVRE. Quando mais de uma condição se aplica, prevalece a de maior prioridade, nesta ordem: MANUTENCAO > OCUPADA > AGUARDANDO_PAGAMENTO > RESERVADA > LIVRE.

#### Scenario: Mesa marcada como em manutenção
- **WHEN** a mesa está marcada como em manutenção
- **THEN** o status calculado é MANUTENCAO, independentemente de reservas existentes

#### Scenario: Mesa com comanda aberta
- **WHEN** a mesa não está em manutenção e possui uma comanda no estado ABERTA
- **THEN** o status calculado é OCUPADA

#### Scenario: Mesa com comanda em pré-conta
- **WHEN** a mesa não está em manutenção e possui uma comanda no estado PRE_CONTA
- **THEN** o status calculado é AGUARDANDO_PAGAMENTO

#### Scenario: Mesa ocupada dentro da janela de uma reserva
- **WHEN** a mesa possui comanda ABERTA e o horário atual está dentro da janela de bloqueio de uma reserva confirmada da mesma mesa
- **THEN** o status calculado é OCUPADA

#### Scenario: Mesa sem comanda ativa, sem manutenção e sem reserva na janela
- **WHEN** a mesa não está em manutenção, não possui comanda ABERTA nem PRE_CONTA e não há reserva confirmada cuja janela inclua o horário atual
- **THEN** o status calculado é LIVRE

#### Scenario: Comanda fechada não ocupa a mesa
- **WHEN** a única comanda associada à mesa está no estado FECHADA ou CANCELADA
- **THEN** essa comanda não influencia o status, e a mesa é calculada como LIVRE se nenhuma outra condição se aplicar

### Requirement: Janela de bloqueio por reserva
Uma reserva no estado CONFIRMADA MUST tornar a mesa RESERVADA somente enquanto o horário atual estiver entre 30 minutos antes e 30 minutos depois do horário de início da reserva, inclusive nos limites. Reservas CANCELADA ou CONCLUIDA MUST NOT influenciar o status.

#### Scenario: Antes da janela
- **WHEN** existe reserva confirmada para as 20h30 e o horário atual é 19h59
- **THEN** a mesa não é calculada como RESERVADA por essa reserva

#### Scenario: Início da janela
- **WHEN** existe reserva confirmada para as 20h30 e o horário atual é 20h00
- **THEN** o status calculado é RESERVADA

#### Scenario: Fim da janela
- **WHEN** existe reserva confirmada para as 20h30 e o horário atual é 21h00
- **THEN** o status calculado é RESERVADA

#### Scenario: Após a tolerância
- **WHEN** existe reserva confirmada para as 20h30 e o horário atual é 21h01
- **THEN** a mesa não é calculada como RESERVADA por essa reserva

#### Scenario: Reserva cancelada
- **WHEN** a única reserva da mesa está no estado CANCELADA e o horário atual está dentro da janela que ela teria
- **THEN** a mesa não é calculada como RESERVADA

### Requirement: Informações complementares do atendimento
Para mesas OCUPADA ou AGUARDANDO_PAGAMENTO, o mapa MUST informar o tempo decorrido, em minutos inteiros, desde a abertura da comanda ativa. Para mesas RESERVADA, o mapa MUST informar o horário de início da reserva que causou o bloqueio.

#### Scenario: Tempo de atendimento de mesa ocupada
- **WHEN** a comanda ativa da mesa foi aberta há 18 minutos e 40 segundos
- **THEN** o mapa informa 18 minutos de atendimento para essa mesa

#### Scenario: Horário da reserva em mesa reservada
- **WHEN** a mesa está RESERVADA por uma reserva confirmada para as 20h30
- **THEN** o mapa informa o horário 20h30 para essa mesa

#### Scenario: Mesa livre sem informação complementar
- **WHEN** a mesa está LIVRE
- **THEN** o mapa não informa tempo de atendimento nem horário de reserva

### Requirement: Exibição do mapa de mesas na interface
A interface SHALL exibir o Mapa de Mesas como primeira tela após o login de um Funcionário ou Administrador, com um cartão por mesa contendo número, capacidade, localização, status com cor própria e a informação complementar, além de uma legenda dos cinco status. A tela MUST atualizar os dados automaticamente em no máximo 10 segundos, sem recarregar a página.

#### Scenario: Exibição inicial
- **WHEN** um Funcionário ou Administrador entra no sistema
- **THEN** o Mapa de Mesas é exibido com um cartão por mesa e a legenda Livre, Ocupada, Reservada, Aguardando pagamento e Manutenção

#### Scenario: Atualização automática
- **WHEN** o status de uma mesa muda no servidor enquanto o Mapa de Mesas está aberto
- **THEN** o cartão da mesa reflete o novo status em no máximo 10 segundos, sem ação do usuário

#### Scenario: Falha temporária de comunicação
- **WHEN** uma atualização automática falha por indisponibilidade do servidor
- **THEN** a interface mantém os últimos dados exibidos, informa que os dados podem estar desatualizados e tenta novamente na próxima atualização

### Requirement: Acesso ao mapa de mesas restrito por perfil
A consulta do mapa de mesas MUST exigir sessão válida e MUST ser liberada apenas para os perfis Funcionário e Administrador, que são os atores da UC 7.6.

#### Scenario: Funcionário consulta o mapa
- **WHEN** um usuário com perfil Funcionário consulta o mapa de mesas
- **THEN** o sistema retorna as mesas com seus status

#### Scenario: Administrador consulta o mapa
- **WHEN** um usuário com perfil Administrador consulta o mapa de mesas
- **THEN** o sistema retorna as mesas com seus status

#### Scenario: Contabilidade não consulta o mapa
- **WHEN** um usuário com perfil Contabilidade consulta o mapa de mesas
- **THEN** a requisição é recusada como sem permissão

#### Scenario: Consulta sem sessão
- **WHEN** o mapa de mesas é consultado sem sessão válida
- **THEN** a requisição é recusada como não autenticada
