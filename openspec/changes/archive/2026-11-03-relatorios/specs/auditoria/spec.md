# Spec Delta

## ADDED Requirements

### Requirement: Consulta do histórico de auditoria
O sistema SHALL permitir consultar, somente para leitura, os registros de auditoria de um período (mesmas regras de período dos relatórios), com filtros opcionais por usuário, ação e tipo de entidade, do mais recente para o mais antigo, em páginas de 50 registros. Cada registro MUST mostrar data e hora em São Paulo, usuário (ou "Sistema"), ação, entidade, identificador e os estados anterior e posterior.

#### Scenario: Quem cancelou o item
- **WHEN** o administrador consulta a auditoria de hoje filtrando a ação "CANCELAR" e a entidade "ItemComanda"
- **THEN** são exibidos os cancelamentos de itens do dia com quem cancelou e o item antes e depois

#### Scenario: Muitos registros
- **WHEN** o período tem 120 registros
- **THEN** a primeira página mostra os 50 mais recentes e o total de 120, e as páginas seguintes mostram os demais

### Requirement: Rastro da consulta da auditoria
Cada consulta do histórico de auditoria MUST gerar ela própria um registro de auditoria com o usuário e os filtros usados.

#### Scenario: Consulta registrada
- **WHEN** a contabilidade consulta a auditoria da semana filtrando a ação "PAGAR"
- **THEN** é gravado um registro de auditoria com o usuário, a consulta da auditoria e os filtros de período e ação

### Requirement: Acesso ao histórico de auditoria restrito por perfil
A consulta do histórico de auditoria MUST ser liberada apenas para Administrador e Contabilidade.

#### Scenario: Funcionário tenta consultar a auditoria
- **WHEN** um usuário com perfil Funcionário consulta a auditoria
- **THEN** a requisição é recusada como sem permissão
