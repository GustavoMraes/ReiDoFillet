# Spec Delta

## Purpose

Garantir que apenas funcionários cadastrados e não bloqueados acessem o sistema, identificando quem realiza cada operação e liberando as funcionalidades conforme o perfil de acesso (Funcionário, Administrador ou Contabilidade).

## ADDED Requirements

### Requirement: Login com usuário e senha
O sistema SHALL autenticar o usuário a partir do login e da senha cadastrados e, em caso de sucesso, iniciar uma sessão válida por 12 horas, informando o nome e o perfil do usuário.

#### Scenario: Credenciais corretas
- **WHEN** um usuário ativo informa login e senha corretos
- **THEN** o sistema inicia uma sessão e informa o nome e o perfil do usuário

#### Scenario: Sessão com validade limitada
- **WHEN** uma sessão foi iniciada há mais de 12 horas
- **THEN** o sistema não aceita mais essa sessão e exige um novo login

### Requirement: Recusa de credenciais inválidas
Quando o login não existir, a senha estiver incorreta ou o usuário ainda não tiver senha definida, o sistema MUST recusar o acesso com a mesma mensagem "Usuário ou senha incorretos", sem revelar qual dado está errado.

#### Scenario: Senha incorreta
- **WHEN** o usuário informa um login existente com a senha errada
- **THEN** o acesso é recusado com a mensagem "Usuário ou senha incorretos"

#### Scenario: Login inexistente
- **WHEN** o usuário informa um login que não está cadastrado
- **THEN** o acesso é recusado com a mesma mensagem "Usuário ou senha incorretos"

#### Scenario: Usuário sem senha definida
- **WHEN** o usuário informa o login de um funcionário cuja senha ainda não foi definida
- **THEN** o acesso é recusado com a mensagem "Usuário ou senha incorretos"

### Requirement: Usuário bloqueado não acessa o sistema
O sistema MUST impedir o acesso de usuários marcados como bloqueados, informando "Usuário bloqueado" somente após credenciais corretas. O bloqueio MUST valer também para sessões já iniciadas, a partir da requisição seguinte.

#### Scenario: Login de usuário bloqueado
- **WHEN** um usuário bloqueado informa login e senha corretos
- **THEN** o acesso é recusado com a mensagem "Usuário bloqueado" e nenhuma sessão é iniciada

#### Scenario: Bloqueio durante uma sessão aberta
- **WHEN** um usuário com sessão ativa é bloqueado e faz uma nova requisição
- **THEN** a requisição é recusada e o usuário precisa sair do sistema

### Requirement: Acesso a recursos protegidos exige sessão válida
Toda funcionalidade do sistema, exceto o login e a verificação de disponibilidade do serviço, MUST exigir uma sessão válida. Requisições sem sessão, com sessão expirada ou adulterada MUST ser recusadas como não autenticadas.

#### Scenario: Requisição sem sessão
- **WHEN** uma funcionalidade protegida é chamada sem sessão
- **THEN** a requisição é recusada como não autenticada

#### Scenario: Sessão adulterada
- **WHEN** uma funcionalidade protegida é chamada com uma sessão cujo conteúdo foi alterado
- **THEN** a requisição é recusada como não autenticada

#### Scenario: Verificação de disponibilidade sem sessão
- **WHEN** a verificação de disponibilidade do serviço é chamada sem sessão
- **THEN** o sistema responde normalmente

### Requirement: Controle de acesso por perfil
Cada funcionalidade protegida MUST declarar os perfis autorizados. Um usuário autenticado cujo perfil não esteja autorizado MUST ter a requisição recusada como sem permissão, distinta de não autenticada.

#### Scenario: Perfil autorizado
- **WHEN** um usuário autenticado acessa uma funcionalidade liberada para o seu perfil
- **THEN** a requisição é atendida

#### Scenario: Perfil não autorizado
- **WHEN** um usuário autenticado acessa uma funcionalidade que não é liberada para o seu perfil
- **THEN** a requisição é recusada como sem permissão

### Requirement: Consulta do usuário autenticado
O sistema SHALL informar, para a sessão atual, o identificador, o nome, o login e o perfil do usuário. A senha, em qualquer forma, MUST NOT ser retornada.

#### Scenario: Consulta com sessão válida
- **WHEN** um usuário autenticado consulta seus próprios dados
- **THEN** o sistema retorna identificador, nome, login e perfil, sem nenhum dado de senha

### Requirement: Encerramento da sessão na interface
A interface SHALL oferecer a opção Sair, que descarta a sessão no dispositivo e retorna à tela de login. Sem um novo login, nenhuma tela protegida pode ser exibida.

#### Scenario: Sair do sistema
- **WHEN** o usuário clica em Sair
- **THEN** a interface volta à tela de login e não exibe mais dados protegidos

#### Scenario: Sessão expirada durante o uso
- **WHEN** a sessão expira enquanto o usuário está em uma tela protegida
- **THEN** a interface volta à tela de login com a mensagem "Sua sessão expirou. Entre novamente."

### Requirement: Auditoria das tentativas de login
Toda tentativa de login MUST gerar um registro de auditoria: com o usuário identificado em caso de sucesso, e com o login informado em caso de falha. A senha informada MUST NOT aparecer em nenhum registro.

#### Scenario: Login bem-sucedido
- **WHEN** um usuário entra no sistema com sucesso
- **THEN** é gravado um registro de auditoria de login associado a esse usuário

#### Scenario: Login malsucedido
- **WHEN** uma tentativa de login é recusada por credenciais inválidas ou usuário bloqueado
- **THEN** é gravado um registro de auditoria de falha de login contendo o login informado e o motivo, sem a senha

### Requirement: Definição de senha de funcionário
O sistema SHALL permitir que um responsável técnico defina a senha de um funcionário existente por meio de uma ferramenta administrativa fora da interface web. A senha MUST ter no mínimo 8 caracteres e MUST ser armazenada apenas como hash irreversível.

#### Scenario: Senha válida
- **WHEN** é definida uma senha com 8 ou mais caracteres para um funcionário existente
- **THEN** o funcionário passa a conseguir entrar com essa senha e a alteração é registrada na auditoria, sem a senha nem o hash

#### Scenario: Senha curta
- **WHEN** é informada uma senha com menos de 8 caracteres
- **THEN** a senha não é alterada e é exibida a mensagem "A senha deve ter no mínimo 8 caracteres"

#### Scenario: Funcionário inexistente
- **WHEN** é informado um login que não está cadastrado
- **THEN** nenhuma senha é alterada e é exibida a mensagem "Funcionário não encontrado"

### Requirement: Tela de login como ponto de entrada
A interface SHALL exibir a tela de login enquanto não houver sessão válida. Após o login, Funcionário e Administrador MUST ver o Mapa de Mesas, e Contabilidade MUST ver um aviso de que ainda não há telas disponíveis para o seu perfil. A barra superior MUST mostrar o nome e o perfil do usuário.

#### Scenario: Acesso sem sessão
- **WHEN** a aplicação é aberta sem sessão válida
- **THEN** a tela de login é exibida

#### Scenario: Erro de login na interface
- **WHEN** o login é recusado
- **THEN** a tela de login exibe a mensagem recebida e mantém o login digitado, limpando apenas a senha

#### Scenario: Entrada de funcionário
- **WHEN** um Funcionário ou Administrador entra no sistema
- **THEN** o Mapa de Mesas é exibido e a barra superior mostra o nome e o perfil do usuário

#### Scenario: Entrada da contabilidade
- **WHEN** um usuário com perfil Contabilidade entra no sistema
- **THEN** é exibido o aviso "Ainda não há telas disponíveis para o perfil Contabilidade" e a barra superior mostra o nome e o perfil do usuário
