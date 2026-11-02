# Spec Delta

## Purpose

Manter um histórico auditável e imutável das operações realizadas no sistema, atendendo à RN05 (histórico auditável), ao RF16 (logs de operações) e às consultas de conferência da HU07.

## ADDED Requirements

### Requirement: Registro de operações de escrita
Toda operação que cria, altera ou exclui dados de negócio MUST gerar um registro de auditoria contendo: usuário responsável (ou indicação de operação do sistema), ação realizada, tipo da entidade, identificador da entidade, estado anterior, estado posterior e data/hora da operação.

#### Scenario: Criação de registro
- **WHEN** uma operação de negócio cria uma nova entidade
- **THEN** é gravado um registro de auditoria com a ação de criação, o tipo e o identificador da entidade, estado anterior vazio e estado posterior com os dados criados

#### Scenario: Alteração de registro
- **WHEN** uma operação de negócio altera uma entidade existente
- **THEN** é gravado um registro de auditoria com o estado anterior e o estado posterior da entidade

#### Scenario: Exclusão de registro
- **WHEN** uma operação de negócio exclui uma entidade
- **THEN** é gravado um registro de auditoria com o estado anterior da entidade e estado posterior vazio

#### Scenario: Operação sem usuário autenticado
- **WHEN** uma operação é executada pelo próprio sistema, sem usuário associado
- **THEN** o registro de auditoria identifica a operação como executada pelo sistema

### Requirement: Atomicidade entre operação e auditoria
A operação de negócio e seu registro de auditoria MUST ser confirmados ou desfeitos em conjunto. Não pode existir operação confirmada sem registro, nem registro de uma operação que não foi confirmada.

#### Scenario: Falha na operação de negócio
- **WHEN** uma operação de negócio falha após o registro de auditoria ter sido preparado
- **THEN** nem a operação nem o registro de auditoria são persistidos

#### Scenario: Falha na gravação da auditoria
- **WHEN** a gravação do registro de auditoria falha
- **THEN** a operação de negócio correspondente é desfeita e o erro é informado

### Requirement: Imutabilidade dos registros de auditoria
Os registros de auditoria MUST NOT ser alterados nem excluídos por nenhuma funcionalidade do sistema, para nenhum perfil de usuário.

#### Scenario: Tentativa de alteração via API
- **WHEN** qualquer cliente tenta alterar ou excluir um registro de auditoria pela API
- **THEN** o sistema não oferece essa operação e nenhum registro é modificado

### Requirement: Registro de data e hora em fuso padronizado
A data/hora de cada registro de auditoria MUST ser armazenada com fuso horário, e exibida no fuso America/Sao_Paulo.

#### Scenario: Consistência do horário
- **WHEN** uma operação é realizada às 20h15 no horário de São Paulo
- **THEN** o registro de auditoria correspondente é exibido com o horário 20h15, independentemente do fuso do servidor
