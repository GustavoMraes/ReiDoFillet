# Spec Delta

## MODIFIED Requirements

### Requirement: Definição de senha de funcionário
O sistema SHALL permitir definir a senha de um funcionário existente pela interface (cadastro e redefinição pelo administrador, ou troca pelo próprio usuário) e, para recuperação de acesso, por uma ferramenta administrativa fora da interface web. Em todos os casos, a senha MUST ter no mínimo 8 caracteres e MUST ser armazenada apenas como hash irreversível.

#### Scenario: Senha válida
- **WHEN** é definida uma senha com 8 ou mais caracteres para um funcionário existente
- **THEN** o funcionário passa a conseguir entrar com essa senha e a alteração é registrada na auditoria, sem a senha nem o hash

#### Scenario: Senha curta
- **WHEN** é informada uma senha com menos de 8 caracteres
- **THEN** a senha não é alterada e é exibida a mensagem "A senha deve ter no mínimo 8 caracteres"

#### Scenario: Funcionário inexistente
- **WHEN** é informado um login que não está cadastrado
- **THEN** nenhuma senha é alterada e é exibida a mensagem "Funcionário não encontrado"
