# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

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
