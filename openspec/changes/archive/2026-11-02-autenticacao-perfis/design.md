# Design

## Context

Motivação em `proposal.md`. Estado atual relevante:

- `Funcionario` já tem `login` (único), `senha_hash`, `perfil` (FUNCIONARIO, ADMIN, CONTABILIDADE) e `bloqueado`; não há migração neste change.
- O seed grava `senha_hash = "!"` (senha inutilizável) nos três funcionários de exemplo.
- Frontend na Vercel (`reidofilet.vercel.app`) e API no Render (`reidofilet-api.onrender.com`): domínios diferentes, portanto chamadas *cross-site*.
- Auditoria transacional já existe (`AuditoriaService` + `transacao()`), com snapshots explícitos que excluem `senha_hash`.

## Goals / Non-Goals

**Goals:**
- Um mecanismo único de autenticação e autorização que todos os routers futuros reutilizem com uma linha (`Depends(exigir_perfis(...))`).
- Bloqueio com efeito imediato, sem depender da expiração do token.
- Nenhum segredo (senha, hash, chave do token) em respostas, logs de auditoria ou repositório.

**Non-Goals:**
- Telas de cadastro e bloqueio de usuários (UC 7.5, change `gestao-cardapio-usuarios`).
- Refresh token, "lembrar de mim", recuperação de senha, bloqueio automático por tentativas e rate limiting.
- Revogação individual de tokens no servidor (lista de tokens revogados).

## Decisions

### D1. Bibliotecas: PyJWT e bcrypt

Token com **PyJWT** e hash com **bcrypt** (uso direto da biblioteca), versões fixadas no `requirements.txt` durante a implementação.

Alternativa considerada: `python-jose` e `passlib[bcrypt]`, citadas na Pesquisa do Estilo Arquitetural. Descartadas: ambas estão sem manutenção ativa, o `python-jose` acumula vulnerabilidades conhecidas e o `passlib` quebra com versões recentes do `bcrypt`. Registrado como desvio da Pesquisa.

### D2. Token JWT no cabeçalho `Authorization`

JWT assinado com HS256, chave em `JWT_SECRET` (variável de ambiente, mínimo de 32 caracteres), com as claims `sub` (id do funcionário), `perfil`, `iat` e `exp`. Validade padrão de 12 horas (um turno), configurável por `JWT_EXPIRACAO_HORAS`. Enviado como `Authorization: Bearer <token>`.

A aplicação **não sobe** sem `JWT_SECRET` válido (falha na criação do app), para que um deploy mal configurado falhe no Render em vez de emitir tokens com chave vazia.

Alternativa considerada: cookie `httpOnly`. Descartada: frontend e API estão em domínios diferentes, então seria um cookie de terceiros, cada vez mais bloqueado pelos navegadores (Safari, Chrome), além de exigir proteção contra CSRF.

### D3. Sessão no frontend em `sessionStorage`

Token e dados do usuário ficam em `sessionStorage`: fechar a aba encerra a sessão, o que é adequado a tablets compartilhados no salão.

Trade-off aceito: `sessionStorage` é legível por JavaScript (risco de XSS). Mitigação: o React escapa o conteúdo renderizado, a aplicação não carrega scripts de terceiros e o token expira em 12 horas.

### D4. Usuário carregado do banco a cada requisição

A dependência `usuario_atual` valida o token e carrega o `Funcionario` pelo `sub`. Recusa com **401** se o token estiver ausente, inválido, expirado, se o funcionário não existir mais ou se estiver bloqueado (detalhe "Usuário bloqueado", para o frontend voltar ao login). A fábrica `exigir_perfis(*perfis)` compõe essa dependência e recusa com **403** ("Sem permissão para esta funcionalidade") quando o perfil não está autorizado.

O perfil usado na autorização é o do banco, não o da claim do token: uma mudança de perfil vale na requisição seguinte.

Custo: uma consulta por chave primária a cada requisição protegida, desprezível frente às demais.

Alternativa considerada: confiar só nas claims do token. Descartada porque o bloqueio só valeria após a expiração, contrariando a spec.

### D5. Login sem enumeração de usuários

`POST /auth/login` (JSON `{login, senha}`) responde:
- **200** com `{token, expira_em, usuario: {id, nome, login, perfil}}`;
- **401** "Usuário ou senha incorretos" para login inexistente, senha errada ou senha inutilizável (`"!"`, que o bcrypt rejeita como hash inválido);
- **403** "Usuário bloqueado" apenas quando a senha está correta.

Quando o login não existe, a senha ainda é verificada contra um hash fixo, para que o tempo de resposta não revele quais logins existem.

`GET /auth/me` devolve `{id, nome, login, perfil}`. O Swagger passa a ter o botão *Authorize* (esquema HTTP Bearer) para testar rotas protegidas.

### D6. Auditoria de login e de definição de senha

Novas ações em `Acao`: `LOGIN`, `LOGIN_FALHA` e `DEFINIR_SENHA`.

| Evento | usuario_id | entidade / entidade_id | dados_depois |
|---|---|---|---|
| Login com sucesso | o próprio funcionário | `Funcionario` / id | — |
| Falha (credenciais) | id, se o login existir; senão nulo | `Funcionario` / id ou `-` | `{login, motivo: CREDENCIAIS_INVALIDAS}` |
| Falha (bloqueado) | id do funcionário | `Funcionario` / id | `{login, motivo: USUARIO_BLOQUEADO}` |
| Definição de senha | nulo (sistema) | `Funcionario` / id | — |

O registro de falha é **confirmado antes** de a requisição ser recusada: a falha de login não pode desfazer a própria auditoria. A senha informada nunca é passada ao serviço de auditoria.

### D7. Definição de senha por script

`python -m scripts.definir_senha <login>` pede a senha duas vezes (sem eco, via `getpass`), valida o mínimo de 8 caracteres, grava o hash bcrypt e registra `DEFINIR_SENHA`. Usa o `DATABASE_URL` do `.env`; em produção, é executado da máquina de um integrante apontando para o Neon.

Alternativa considerada: senhas padrão no seed. Descartada: o seed é versionado e o repositório é público.

### D8. Interface

- `AuthContext` guarda a sessão e expõe `entrar`, `sair` e o usuário atual.
- O cliente HTTP anexa o token e, ao receber **401**, dispara a saída global com a mensagem "Sua sessão expirou. Entre novamente." (exceto na própria chamada de login, cuja mensagem é exibida no formulário). Assim, o polling do mapa não mostra o aviso de "dados desatualizados" quando o problema é a sessão.
- Sem biblioteca de rotas: o `App` decide entre Login, Mapa de Mesas (Funcionário/Administrador) e o aviso da Contabilidade.
- A barra superior mostra "Nome · Perfil" e o botão Sair.

## Risks / Trade-offs

- [Sem limite de tentativas, senhas fracas podem ser descobertas por força bruta] → mínimo de 8 caracteres, bcrypt (custo alto por tentativa) e falhas registradas na auditoria; rate limiting fica para evolução futura.
- [Sair não invalida o token no servidor; um token copiado vale até expirar] → validade de 12 horas e bloqueio com efeito imediato (D4).
- [Trocar o `JWT_SECRET` derruba todas as sessões] → comportamento aceitável e útil em caso de vazamento; documentado no README.
- [Tentativas de login por robôs aumentam o volume da auditoria] → volume pequeno frente aos 0,5 GB do Neon; monitorar pelo painel.
- [Deploy sem `JWT_SECRET` no Render] → o app falha ao subir (D2) e o Render mantém a versão anterior no ar.

## Migration Plan

1. Gerar a chave: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
2. Adicionar `JWT_SECRET` no `.env` local e no Render **antes** do push.
3. Fazer o deploy (push na `main`); nenhuma migração de banco.
4. Definir as senhas dos funcionários com `scripts/definir_senha.py` apontando para o Neon.
5. Rollback: redeploy do commit anterior no Render e na Vercel; as senhas definidas permanecem e não afetam a versão anterior.
