# interface Specification

## Purpose

Garantir que uma falha ao exibir parte da interface nunca deixe o usuário diante de uma página em branco: a falha fica contida, é explicada e oferece um caminho para continuar o trabalho.

## Requirements

### Requirement: Falha ao exibir uma tela
Quando uma tela falhar ao ser exibida, a interface MUST mostrar no lugar dela o aviso "Não foi possível exibir esta tela", com as ações "Tentar novamente" (exibe a tela de novo) e "Ir para o início" (abre a tela inicial do perfil). O cabeçalho, as abas, a sessão e as demais telas MUST continuar funcionando.

#### Scenario: Dado inesperado no mapa
- **WHEN** o Mapa de Mesas recebe um dado em formato inesperado e falha ao ser desenhado
- **THEN** é exibido o aviso no lugar do mapa, com o cabeçalho e as abas funcionando, e a aba Cozinha abre normalmente

#### Scenario: Tentar novamente depois de corrigido
- **WHEN** o usuário clica em "Tentar novamente" e o dado já chega correto
- **THEN** a tela é exibida normalmente, sem recarregar a página nem perder a sessão

#### Scenario: Ir para o início
- **WHEN** o usuário clica em "Ir para o início" no aviso
- **THEN** é exibida a tela inicial do perfil (Mapa de Mesas para Funcionário e Administrador, Relatórios para Contabilidade)

### Requirement: Troca de aba descarta o erro
Ao trocar de aba, a interface MUST exibir a nova tela normalmente, e ao voltar à aba que falhou MUST tentar exibi-la de novo.

#### Scenario: Volta à aba que falhou
- **WHEN** o usuário sai da aba que falhou e volta a ela
- **THEN** a tela é exibida de novo, e o aviso só reaparece se a falha persistir

### Requirement: Falha geral da interface
Quando a falha ocorrer fora das telas (por exemplo, no cabeçalho), a interface MUST mostrar uma página de erro com a mensagem "Algo deu errado no sistema" e a ação "Recarregar", em vez de uma página em branco.

#### Scenario: Falha no cabeçalho
- **WHEN** o cabeçalho falha ao ser desenhado
- **THEN** é exibida a página de erro geral com o botão "Recarregar", que recarrega a aplicação mantendo a sessão aberta

### Requirement: Detalhe técnico do erro
Os avisos de falha MUST oferecer um bloco recolhido "Detalhes técnicos" com a mensagem do erro, e o erro MUST ser registrado no console do navegador. O aviso MUST NOT exibir dados da sessão, como o token de acesso.

#### Scenario: Suporte consulta o detalhe
- **WHEN** alguém abre "Detalhes técnicos" no aviso de falha
- **THEN** é exibida a mensagem técnica do erro, e o mesmo erro aparece no console do navegador
