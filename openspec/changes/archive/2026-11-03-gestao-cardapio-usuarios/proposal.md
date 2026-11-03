# Proposal

## Why

Hoje cardápio e usuários só mudam pelo seed ou por scripts no servidor: um novo garçom, um prato novo, um aumento de preço ou um item que acabou exigem acesso técnico ao banco. A especificação prevê essas funções na interface (RF11, RF14, RF15; UC 7.5 Gerenciar Usuários e 7.7 Cadastrar Item no Cardápio; HU04 e HU05), e elas são pré-requisito para o restaurante operar sem o grupo.

## What Changes

- **Cardápio (Administrador):** cadastrar e editar produtos (nome, descrição, preço, categoria), ativar/desativar produtos e gerenciar categorias (criar, renomear, ordenar e excluir só quando vazia). Mudança de preço não altera itens já lançados em comandas.
- **Esgotado no dia (Funcionário e Administrador):** marcar um produto ativo como indisponível ou disponível, sem acesso ao restante do cadastro.
- **Usuários (Administrador):** listar, cadastrar (nome, login, perfil, senha inicial), alterar nome e perfil, bloquear e desbloquear e redefinir a senha. "Remover" um usuário é bloqueá-lo: ninguém é apagado, pois comandas, pagamentos e auditoria apontam para ele. O administrador não pode bloquear nem rebaixar a si mesmo, e o sistema sempre mantém ao menos um administrador ativo.
- **Troca da própria senha (todos os perfis):** informando a senha atual e a nova.
- Auditoria de todas essas operações, sem senhas nem hashes.
- Interface: abas **Cardápio** (edição completa para o Administrador; só o esgotado para o Funcionário) e **Usuários** (Administrador), e a opção "Trocar senha" no cabeçalho.

## Capabilities

### New Capabilities

- `usuarios`: gestão de funcionários pelo administrador (cadastro, alteração, bloqueio, redefinição de senha, proteção do último administrador) e troca da própria senha.

### Modified Capabilities

- `cardapio`: novos requisitos de cadastro de produtos e categorias, ativação, disponibilidade no dia e tela de gestão do cardápio.
- `autenticacao`: o requisito "Definição de senha de funcionário" passa a valer também para senhas definidas pela interface (mesma regra de tamanho e armazenamento só como hash); o script administrativo continua para emergências.

## Impact

- **Backend:** serviços e rotas novos de gestão de cardápio (`/admin/cardapio`, `/produtos/{id}/disponibilidade`) e de usuários (`/usuarios`, `/auth/senha`); snapshots de auditoria de produto e categoria; regras de último administrador. Sem migração: as tabelas `categoria`, `produto` e `funcionario` já têm os campos necessários.
- **Frontend:** páginas Cardápio e Usuários, diálogo de troca de senha e novas abas conforme o perfil.
- **Operação:** depois do deploy, o administrador passa a criar e manter usuários pela tela; `scripts/definir_senha.py` fica para recuperação de acesso.
