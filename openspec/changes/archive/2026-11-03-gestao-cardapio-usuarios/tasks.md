# Tasks

## 1. Cardápio no backend

- [x] 1.1 Criar a migração `0003` com os índices únicos em `lower(nome)` de `produto` e `categoria` (D2); verificar com o teste de correspondência entre migrações e models e com downgrade/upgrade completos
- [x] 1.2 Implementar `ProdutoSnapshot`, `CategoriaSnapshot` e o serviço de gestão do cardápio com `GET /admin/cardapio`, cadastro e edição de produtos (incluindo `ativo`) e `PATCH /produtos/{id}/disponibilidade` (D1, D6); testes de integração de "Novo prato", "Preço inválido" (zero, negativo, três casas, acima do limite), "Nome repetido" (com outra caixa), "Aumento de preço com comanda aberta", "Prato retirado do cardápio", "Acabou o petit gâteau" (inclusive recusa de produto inativo), "Mudança de preço auditada" e os acessos "Funcionário tenta mudar preço", "Funcionário marca esgotado" e Contabilidade recusada
- [x] 1.3 Implementar categorias: criar, renomear, mover (D3) e excluir vazia; testes de integração de "Nova categoria" (ordem no `GET /cardapio`), nome repetido, renumeração após mover, mover nas pontas sem efeito, "Categoria com produtos" (inclusive só com inativos) e auditoria

## 2. Usuários no backend

- [x] 2.1 Refatorar `FuncionarioService.definir_senha` para reutilização (D5) mantendo o script `definir_senha` e seus testes; implementar `GET/POST /usuarios`, `PATCH /usuarios/{id}` e `POST /usuarios/{id}/senha`; testes de integração de "Administrador consulta os usuários" (sem hash na resposta), "Novo garçom" (login funciona), "Login repetido" (inclusive com maiúsculas), "Dados inválidos", "Funcionário promovido", "Funcionário desligado" (sessão aberta recusada, nome mantido na comanda), "Desbloqueio", "Funcionário esqueceu a senha", "Bloqueio auditado" e "Funcionário tenta gerenciar usuários"
- [x] 2.2 Implementar a regra do administrador ativo (D4); testes de "Administrador tenta se bloquear" (bloqueio e rebaixamento), "Último administrador" e dois administradores se rebaixando ao mesmo tempo com sessões próprias (sobra um administrador ativo)
- [x] 2.3 Implementar `POST /auth/senha` (D5); testes de "Troca bem-sucedida" (login com a nova, não com a antiga), "Senha atual incorreta" (422, sem alteração), senha nova curta, auditoria sem senha e acesso pelos três perfis

## 3. Interface

- [x] 3.1 Criar `api/admin.ts` (cardápio e usuários) e a troca de senha em `api/auth.ts`; abas Cardápio e Usuários conforme o perfil e o botão "Trocar senha" no cabeçalho (D7); verificar com `npm run build` sem erros de tipo
- [x] 3.2 Implementar a página Cardápio (visão de administrador e de funcionário) e a recarga do cardápio a cada 10 s na tela da comanda; verificar no navegador contra o backend local "Administrador edita preço pela tela", novo produto, nova categoria e mover, desativar produto, "Funcionário marca esgotado pela tela" (refletindo na tela da comanda aberta em outra aba) e mensagens de erro do servidor
- [x] 3.3 Implementar a página Usuários e o diálogo "Trocar senha"; verificar no navegador "Cadastro pela tela" (e login com o novo usuário), editar perfil, bloquear e desbloquear, redefinir senha, a recusa de bloquear a si mesmo e "Trocar senha pelo cabeçalho" com Contabilidade; conferir as duas páginas em largura de celular sem rolagem horizontal

## 4. Implantação e verificação

- [x] 4.1 Rodar `pytest` completo e `npm run build` e verificar que tudo passa
- [x] 4.2 Publicar (push na `main`), confirmar a migração `0003` aplicada e verificar na URL pública: cadastrar um usuário de teste e entrar com ele, trocar a senha dele pelo cabeçalho, bloqueá-lo; criar um produto de teste, mudar o preço, marcar esgotado como funcionário e desativá-lo ao final

## Workflow follow-up

- Arquivar o change após revisão do grupo (`/opsx:archive`), criando a spec `usuarios` e aplicando as deltas de `cardapio` e `autenticacao`.
- Próximo change: `relatorios`.
