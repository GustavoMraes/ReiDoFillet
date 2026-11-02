# Proposal

## Why

Hoje o sistema publicado é acessível por qualquer pessoa: `GET /mesas` é público e não existe login. Todos os casos de uso da Especificação têm como pré-condição "usuário autenticado" (UC 7.1 a 7.8), e os próximos changes precisam saber **quem** opera — a comanda registra o funcionário responsável (RF10) e a auditoria registra o autor de cada operação (RN05). A autenticação vem antes da comanda para que os fluxos seguintes já nasçam com o usuário real, sem retrabalho.

## What Changes

- Login com usuário e senha (UC 7.9, RF13, RNF03), emitindo um token de sessão com validade limitada.
- Recusa de acesso para usuário bloqueado, com efeito imediato inclusive sobre sessões já abertas (decisão do grupo: bloqueio apenas por flag definida pelo administrador).
- Controle de acesso por perfil (RF14): Funcionário, Administrador e Contabilidade.
- Consulta do usuário autenticado (nome e perfil) e logout.
- Registro na auditoria das tentativas de login, bem-sucedidas e malsucedidas.
- Script de linha de comando para definir a senha de um funcionário, já que o cadastro de usuários (UC 7.5) só chega no change `gestao-cardapio-usuarios`.
- **BREAKING**: `GET /mesas` passa a exigir autenticação e perfil Funcionário ou Administrador.
- Interface: tela de login como ponto de entrada, nome e perfil do usuário na barra superior, botão Sair e retorno ao login quando a sessão expira.

Fora do escopo: cadastro, edição e bloqueio de usuários pela interface (UC 7.5), recuperação de senha, bloqueio automático por tentativas e limitação de taxa de requisições.

## Capabilities

### New Capabilities

- `autenticacao`: login, sessão, bloqueio de usuário, perfis de acesso, logout, auditoria de tentativas de login e definição de senha.

### Modified Capabilities

- `mesas`: o mapa de mesas passa a exigir usuário autenticado com perfil Funcionário ou Administrador, e a interface só o exibe após o login.

## Impact

- **Backend:** novos módulos de segurança (hash de senha e token), rotas `POST /auth/login` e `GET /auth/me`, dependência de autorização aplicada a `GET /mesas`, novas ações de auditoria, script `scripts/definir_senha.py`.
- **Dependências novas:** biblioteca de JWT e de hash bcrypt (ver `design.md`).
- **Configuração:** nova variável `JWT_SECRET` (obrigatória) no `.env` local e no Render; `JWT_EXPIRACAO_HORAS` opcional.
- **Frontend:** página de login, contexto de sessão, cabeçalho `Authorization` nas chamadas à API, cabeçalho com usuário e botão Sair.
- **Dados:** nenhuma migração; `Funcionario` já possui `login`, `senha_hash`, `perfil` e `bloqueado`. As senhas dos funcionários do seed precisam ser definidas pelo script antes do primeiro login.
- **Desvio da Pesquisa do Estilo Arquitetural:** substitui `python-jose` e `passlib` por bibliotecas mantidas (ver `design.md`).
