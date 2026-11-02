# Tasks

## 1. Dependências e configuração

- [x] 1.1 Adicionar PyJWT e bcrypt com versões fixadas ao `backend/requirements.txt`; verificar com `pip install -r requirements.txt` no venv e import das duas bibliotecas
- [x] 1.2 Adicionar `JWT_SECRET` e `JWT_EXPIRACAO_HORAS` (padrão 12) ao `Settings` e ao `.env.example`, e fazer `create_app` falhar sem `JWT_SECRET` com 32+ caracteres (D2); testes unitários de configuração cobrindo chave ausente, curta e válida, e ajuste dos testes existentes que criam o app

## 2. Núcleo de segurança

- [x] 2.1 Implementar `core/seguranca.py` com geração e verificação de hash bcrypt (retornando falso para hash inválido como `"!"`) e criação/decodificação de token JWT com `sub`, `perfil`, `iat` e `exp`; testes unitários de ida e volta, token expirado, token adulterado, chave errada e hash inutilizável

## 3. Autenticação no backend

- [x] 3.1 Adicionar as ações `LOGIN`, `LOGIN_FALHA` e `DEFINIR_SENHA` em `Acao` e o snapshot da tentativa de login (`login`, `motivo`); teste unitário garantindo que o snapshot não aceita campo de senha
- [x] 3.2 Implementar `FuncionarioRepository` (busca por id e por login) e `AuthService.login` com verificação contra hash fixo quando o login não existe e auditoria da falha confirmada antes da recusa (D5, D6); testes de integração dos cenários "Credenciais corretas", "Senha incorreta", "Login inexistente", "Usuário sem senha definida", "Login de usuário bloqueado", "Login bem-sucedido" e "Login malsucedido" (auditoria sem a senha)
- [x] 3.3 Implementar as dependências `usuario_atual` e `exigir_perfis` com esquema HTTP Bearer (D4); testes de integração com uma rota de teste cobrindo "Requisição sem sessão", "Sessão adulterada", sessão expirada, "Bloqueio durante uma sessão aberta", "Perfil autorizado" e "Perfil não autorizado"
- [x] 3.4 Implementar o router `/auth` com `POST /auth/login` e `GET /auth/me`; testes de integração do login pela API, do cenário "Consulta com sessão válida" (sem dados de senha) e de "Verificação de disponibilidade sem sessão" no `/health`; verificar no Swagger o botão *Authorize* e as duas rotas documentadas

## 4. Mapa de mesas protegido

- [x] 4.1 Proteger `GET /mesas` com `exigir_perfis(FUNCIONARIO, ADMIN)` e atualizar `test_mesas_api.py` para autenticar; testes de integração dos cenários "Funcionário consulta o mapa", "Administrador consulta o mapa", "Contabilidade não consulta o mapa" e "Consulta sem sessão"

## 5. Definição de senha

- [x] 5.1 Implementar `FuncionarioService.definir_senha` e o script `scripts/definir_senha.py` (login como argumento, senha via `getpass` com confirmação); testes de integração dos cenários "Senha válida" (login funciona depois e a auditoria `DEFINIR_SENHA` não contém senha nem hash), "Senha curta" e "Funcionário inexistente"

## 6. Interface

- [x] 6.1 Implementar o `AuthContext` com sessão em `sessionStorage` e o cliente HTTP anexando o token e disparando a saída global em 401, exceto na chamada de login (D3, D8); verificar com `npm run build` sem erros de tipo
- [x] 6.2 Implementar a página de login com exibição da mensagem do servidor, mantendo o login digitado e limpando a senha; verificar no navegador contra o backend local os cenários "Acesso sem sessão" e "Erro de login na interface" (senha errada e usuário bloqueado)
- [x] 6.3 Mostrar "Nome · Perfil" e o botão Sair na barra superior, exibir o Mapa de Mesas para Funcionário e Administrador e o aviso para Contabilidade; verificar no navegador os cenários "Entrada de funcionário", "Entrada da contabilidade" e "Sair do sistema"
- [x] 6.4 Verificar no navegador o cenário "Sessão expirada durante o uso" (token adulterado ou expirado na `sessionStorage` com o Mapa de Mesas aberto) e que o aviso de dados desatualizados não aparece nesse caso; e verificar em largura de celular que a barra superior não gera rolagem horizontal

## 7. Documentação e implantação

- [x] 7.1 Documentar no `README.md` a variável `JWT_SECRET` (com o comando de geração), o script de definição de senha e o uso do *Authorize* no Swagger; verificar executando os comandos documentados localmente
- [x] 7.2 Com `JWT_SECRET` configurado no Render, publicar o change e definir pelo script as senhas dos funcionários no Neon; verificar `POST /auth/login` e `GET /mesas` autenticado pela URL pública, e `GET /mesas` sem token retornando 401

## 8. Verificação integrada

- [x] 8.1 Rodar `pytest` completo (unitários e integração) e verificar que todos passam
- [x] 8.2 No site publicado, entrar com cada perfil, confirmar a tela correta de cada um, sair, e bloquear temporariamente um funcionário no banco para confirmar o bloqueio no login e em uma sessão aberta; desfazer o bloqueio ao final

## Workflow follow-up

- Arquivar o change após revisão do grupo (`/opsx:archive`), sincronizando a spec nova `autenticacao` e a delta de `mesas`.
- Próximo change: `abrir-comanda-registrar-itens`, que passa a gravar o funcionário autenticado na comanda (RF10).
