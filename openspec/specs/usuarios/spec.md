# usuarios Specification

## Purpose

Permitir que o administrador gerencie os funcionários que acessam o sistema (cadastro, perfil, bloqueio e senha) e que cada usuário troque a própria senha, preservando o histórico de quem realizou cada operação.

## Requirements

### Requirement: Lista de usuários
O sistema SHALL listar para o administrador todos os funcionários cadastrados, bloqueados ou não, em ordem de nome, com nome, login, perfil e situação (ativo ou bloqueado). A lista MUST NOT expor senhas nem hashes.

#### Scenario: Administrador consulta os usuários
- **WHEN** o administrador abre a lista de usuários
- **THEN** são exibidos todos os funcionários em ordem de nome, com login, perfil e se estão bloqueados

### Requirement: Cadastro de usuário
O sistema SHALL cadastrar um funcionário com nome (obrigatório, até 100 caracteres), login, perfil (Funcionário, Administrador ou Contabilidade) e senha inicial com no mínimo 8 caracteres. O login MUST ter de 3 a 50 caracteres, apenas letras minúsculas sem acento, números, ponto, hífen ou sublinhado, e MUST ser único. O login MUST NOT mudar depois do cadastro.

#### Scenario: Novo garçom
- **WHEN** o administrador cadastra "Bruno Lima", login "bruno", perfil Funcionário e uma senha de 10 caracteres
- **THEN** o funcionário é criado ativo e consegue entrar com esse login e senha

#### Scenario: Login repetido
- **WHEN** o administrador tenta cadastrar um login que já existe
- **THEN** nada é criado e o sistema informa "Já existe um usuário com este login"

#### Scenario: Dados inválidos
- **WHEN** o administrador tenta cadastrar sem nome, com login fora do formato ou com senha de menos de 8 caracteres
- **THEN** nada é criado e o sistema informa qual dado está inválido

### Requirement: Alteração de nome e perfil
O sistema SHALL permitir ao administrador alterar o nome e o perfil de um funcionário. A mudança de perfil MUST valer a partir da próxima requisição do funcionário, sem novo login.

#### Scenario: Funcionário promovido
- **WHEN** o administrador muda o perfil de "bruno" de Funcionário para Administrador
- **THEN** na próxima requisição "bruno" já acessa as funções de administrador

### Requirement: Bloqueio no lugar de exclusão
Remover um usuário MUST significar bloqueá-lo: funcionários nunca são apagados, para preservar o histórico das operações. O administrador SHALL bloquear e desbloquear funcionários; o bloqueio MUST impedir o acesso a partir da próxima requisição, inclusive com sessão já aberta.

#### Scenario: Funcionário desligado
- **WHEN** o administrador bloqueia "bruno", que está com uma sessão aberta
- **THEN** a próxima requisição de "bruno" é recusada e ele não consegue mais entrar, mas as comandas que ele atendeu continuam mostrando seu nome

#### Scenario: Desbloqueio
- **WHEN** o administrador desbloqueia um funcionário
- **THEN** o funcionário volta a conseguir entrar com a mesma senha

### Requirement: Administrador ativo garantido
O administrador MUST NOT bloquear a si mesmo nem retirar o próprio perfil de administrador, e o sistema MUST recusar qualquer bloqueio ou mudança de perfil que deixe o sistema sem nenhum administrador ativo.

#### Scenario: Administrador tenta se bloquear
- **WHEN** o administrador tenta bloquear o próprio usuário ou mudar o próprio perfil
- **THEN** nada é alterado e o sistema informa "Você não pode bloquear nem rebaixar o próprio usuário"

#### Scenario: Último administrador
- **WHEN** uma alteração deixaria o sistema sem administrador ativo
- **THEN** nada é alterado e o sistema informa "O sistema precisa de ao menos um administrador ativo"

### Requirement: Redefinição de senha pelo administrador
O sistema SHALL permitir ao administrador definir uma nova senha (mínimo de 8 caracteres) para qualquer funcionário, sem conhecer a senha anterior. A senha MUST ser armazenada apenas como hash.

#### Scenario: Funcionário esqueceu a senha
- **WHEN** o administrador redefine a senha de "bruno"
- **THEN** "bruno" passa a entrar com a nova senha e a anterior deixa de funcionar

### Requirement: Troca da própria senha
Todo usuário autenticado, de qualquer perfil, SHALL poder trocar a própria senha informando a senha atual e a nova (mínimo de 8 caracteres). Senha atual incorreta MUST recusar a troca.

#### Scenario: Troca bem-sucedida
- **WHEN** um usuário informa a senha atual correta e uma nova senha válida
- **THEN** a nova senha passa a valer no próximo login e é exibida uma mensagem de confirmação

#### Scenario: Senha atual incorreta
- **WHEN** um usuário informa a senha atual errada
- **THEN** a senha não é alterada e o sistema informa "Senha atual incorreta"

### Requirement: Auditoria da gestão de usuários
Cadastro, alteração de nome ou perfil, bloqueio, desbloqueio, redefinição e troca de senha MUST gerar registros de auditoria com o usuário responsável e os dados do funcionário antes e depois; senhas e hashes MUST NOT aparecer na auditoria.

#### Scenario: Bloqueio auditado
- **WHEN** o administrador bloqueia um funcionário
- **THEN** é gravado um registro de auditoria com o administrador e o funcionário antes e depois, sem senha nem hash

### Requirement: Acesso à gestão de usuários restrito por perfil
A lista, o cadastro, a alteração, o bloqueio e a redefinição de senha MUST ser liberados apenas para o perfil Administrador. A troca da própria senha MUST ser liberada para qualquer usuário autenticado.

#### Scenario: Funcionário tenta gerenciar usuários
- **WHEN** um usuário com perfil Funcionário ou Contabilidade tenta listar ou cadastrar usuários
- **THEN** a requisição é recusada como sem permissão

### Requirement: Tela de usuários
A interface SHALL oferecer ao administrador a aba Usuários com a lista, o formulário de cadastro e, para cada funcionário, as ações de editar nome e perfil, bloquear ou desbloquear e redefinir senha. Todos os perfis SHALL ter no cabeçalho a opção "Trocar senha".

#### Scenario: Cadastro pela tela
- **WHEN** o administrador preenche o formulário de novo usuário e confirma
- **THEN** o usuário aparece na lista e é exibida uma mensagem de confirmação

#### Scenario: Trocar senha pelo cabeçalho
- **WHEN** um usuário escolhe "Trocar senha" no cabeçalho, informa a senha atual e a nova duas vezes e confirma
- **THEN** a senha é trocada e é exibida uma mensagem de confirmação
