# Spec Delta

## MODIFIED Requirements

### Requirement: Tela de login como ponto de entrada
A interface SHALL exibir a tela de login enquanto não houver sessão válida. Após o login, Funcionário e Administrador MUST ver o Mapa de Mesas, e Contabilidade MUST ver a tela de Relatórios. A barra superior MUST mostrar o nome e o perfil do usuário.

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
- **THEN** a tela de Relatórios é exibida com o relatório financeiro e a barra superior mostra o nome e o perfil do usuário
