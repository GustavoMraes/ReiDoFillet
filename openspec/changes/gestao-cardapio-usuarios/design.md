# Design

## Context

Motivação em `proposal.md`. Estado atual relevante:

- Tabelas prontas: `categoria` (`nome` único com diferença de maiúsculas, `ordem`), `produto` (`ativo`, `disponivel`, `preco > 0`) e `funcionario` (`login` único, `perfil`, `bloqueado`, `senha_hash`).
- `ItemComanda.preco_unitario` já guarda o preço do lançamento; `ComandaService.registrar_item` já recusa produto inativo ou indisponível ("Item indisponível").
- `usuario_atual` recarrega o funcionário do banco a cada requisição: bloqueio e mudança de perfil já valem na requisição seguinte. `FuncionarioService.definir_senha` aplica o mínimo de 8 caracteres, gera o hash em thread e audita `DEFINIR_SENHA` sem dados.
- Auditoria por snapshots explícitos (`FuncionarioSnapshot` já existe e não tem a senha).
- A tela da comanda carrega o cardápio uma única vez, ao abrir.

## Goals / Non-Goals

**Goals:**
- Cardápio e usuários mantidos inteiramente pela interface, com regras validadas no servidor e auditoria.
- Nenhuma operação apaga funcionário ou produto (histórico preservado).

**Non-Goals:**
- Invalidar sessões abertas na troca de senha (o bloqueio é o remédio imediato), troca obrigatória de senha no primeiro acesso, foto/estoque de produtos, permissões finas além dos três perfis.

## Decisions

### D1. Rotas

| Rota | Perfis | Uso |
|---|---|---|
| `GET /admin/cardapio` | Admin | categorias em ordem, cada uma com todos os produtos (inclusive inativos) |
| `POST /admin/categorias`, `PATCH /admin/categorias/{id}`, `DELETE /admin/categorias/{id}` | Admin | criar, renomear, excluir vazia |
| `POST /admin/categorias/{id}/mover` `{direcao: "acima"\|"abaixo"}` | Admin | troca a posição com a vizinha |
| `POST /admin/produtos`, `PATCH /admin/produtos/{id}` | Admin | cadastrar; editar nome, descrição, preço, categoria e `ativo` |
| `PATCH /produtos/{id}/disponibilidade` `{disponivel}` | Funcionário, Admin | esgotado no dia (só produto ativo) |
| `GET /usuarios`, `POST /usuarios`, `PATCH /usuarios/{id}` `{nome?, perfil?, bloqueado?}` | Admin | lista, cadastro, alteração e bloqueio |
| `POST /usuarios/{id}/senha` `{senha}` | Admin | redefinição |
| `POST /auth/senha` `{senha_atual, nova_senha}` | todos | troca da própria senha |

Respostas devolvem o recurso atualizado (o `GET /admin/cardapio` completo nas operações de cardápio, para a tela não precisar recarregar). Erros no formato `{"detalhe": ...}`: 404, 409 (conflitos de nome, categoria com produtos, último administrador, produto inativo na disponibilidade), 422 (validação).

### D2. Nomes únicos sem diferenciar maiúsculas

Migração `0003` cria índices únicos em `lower(nome)` de `produto` e `categoria` (o índice atual de `categoria.nome` diferencia maiúsculas). O serviço verifica antes para dar a mensagem certa e trata `IntegrityError` da corrida com a mesma mensagem. O login é normalizado para minúsculas no servidor, e o índice único existente basta.

### D3. Ordem das categorias

"Mover" troca o `ordem` da categoria com a vizinha na ordem atual, dentro de uma transação com as categorias bloqueadas (`FOR UPDATE`), e renumera de 0 a n−1 para eliminar empates herdados do seed. Categoria nova entra no fim. Alternativa considerada: enviar a lista inteira reordenada — descartada por permitir sobrescrever uma mudança concorrente sem perceber.

### D4. Ao menos um administrador ativo

Em toda alteração de perfil ou bloqueio, o serviço bloqueia (`FOR UPDATE`, em ordem de id) as linhas dos administradores ativos e só então conta quantos restariam. Isso impede que dois administradores se rebaixem simultaneamente e deixem o sistema sem nenhum. A regra "não pode bloquear nem rebaixar a si mesmo" é verificada antes, com mensagem própria.

### D5. Senhas

Cadastro, redefinição e troca reutilizam a regra e o hash de `FuncionarioService.definir_senha` (refatorado para receber o funcionário, não só o login). A troca própria confere a senha atual com `verificar_senha` em thread e responde 422 "Senha atual incorreta" (não 401, para a interface não tratar como sessão expirada). Auditoria `DEFINIR_SENHA` sem dados; cadastro e alterações com `FuncionarioSnapshot`.

### D6. Auditoria do cardápio

Novos `ProdutoSnapshot` (id, categoria_id, nome, preço, ativo, disponível) e `CategoriaSnapshot` (id, nome, ordem); ações `CRIAR`, `ALTERAR` e `EXCLUIR`. Mover registra `ALTERAR` das categorias cujo `ordem` mudou.

### D7. Interface

- Abas por perfil: Administrador ganha **Cardápio** e **Usuários**; Funcionário ganha **Cardápio** (só esgotado). Contabilidade continua sem abas operacionais.
- **Cardápio (admin):** categorias em ordem com ações renomear, ↑, ↓ e excluir; produtos com preço, selos "Inativo"/"Indisponível" e ações editar (diálogo com nome, descrição, preço e categoria), ativar/desativar e esgotado/disponível; botões "Nova categoria" e "Novo produto". **Cardápio (funcionário):** a mesma lista sem inativos, só com esgotado/disponível.
- **Usuários:** lista com selo de perfil e "Bloqueado", "Novo usuário" e, por usuário, editar (nome e perfil), bloquear/desbloquear (com confirmação) e redefinir senha (senha digitada duas vezes).
- **Trocar senha:** botão no cabeçalho, ao lado de "Sair", disponível a todos os perfis.
- A tela da comanda passa a recarregar o cardápio a cada 10 s (o servidor já recusa produto indisponível; a recarga só mantém a exibição correta).
- Ninguém altera o próprio perfil (D4); para os demais, a mudança vale no servidor na hora e, nas abas da interface deles, no próximo login.

## Risks / Trade-offs

- [Senha redefinida não derruba a sessão aberta (até 12 h)] → em caso de acesso indevido, o administrador bloqueia o usuário, o que vale na hora.
- [Interface de outro usuário mostra abas antigas após mudança de perfil] → o servidor recusa o que o perfil novo não permite; as abas se ajustam no próximo login.
- [Migração 0003 falharia se já houvesse nomes iguais diferindo só em maiúsculas] → o seed e a produção atual não têm; a migração é validada no banco de testes com os dados do seed antes do deploy.

## Migration Plan

Push na `main`: o Render roda `alembic upgrade head` (aplica a `0003`) e sobe a API; a Vercel publica a interface. Rollback: redeploy do commit anterior e `alembic downgrade 0002` remove os índices; dados cadastrados continuam válidos.
