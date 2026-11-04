# Tasks

## 1. Base

- [x] 1.1 Mover `fuso_local` e `intervalo_do_dia` para `core/tempo.py` (reservas continuam passando), criar o utilitário de período (D1) com testes unitários de "Período padrão", "Período invertido", "Período longo demais" (366 aceito, 367 recusado) e limites do dia em São Paulo, e a migração `0004` com os índices (D5), verificada pelo teste de correspondência com os models e por downgrade/upgrade
- [x] 1.2 Criar a ação `CONSULTAR` e o `ConsultaSnapshot` (D4); teste unitário do snapshot com os filtros

## 2. Relatórios no backend

- [x] 2.1 Implementar o relatório operacional e `GET /relatorios/operacional` (D2, D3); testes de integração de "Dia de movimento", "Período sem comandas fechadas", "Ranking do período" (com cancelados fora e limite de 10), "Preço alterado no período", "Horário de pico", faturamento por dia, comanda aberta antes do período fora do conjunto e consulta auditada
- [x] 2.2 Implementar o relatório financeiro e `GET /relatorios/financeiro`; testes de integração de "Fechamento do dia" (totais e formas, inclusive com zero), "Comandas abertas ou canceladas" fora, comanda aberta antes e fechada dentro do período incluída, consulta auditada e os acessos "Contabilidade tenta o operacional" e "Funcionário tenta o financeiro"; conferir que os totais batem com `GET /comandas/{id}` de cada comanda
- [x] 2.3 Implementar `GET /auditoria` e `GET /auditoria/opcoes`; testes de integração de "Quem cancelou o item", "Muitos registros" (paginação de 120), filtro por usuário (inclusive "Sistema"), "Consulta registrada" (sem aparecer na própria página) e "Funcionário tenta consultar a auditoria"

## 3. Interface

- [x] 3.1 Criar `api/relatorios.ts`, a aba Relatórios por perfil (Contabilidade entra nela após o login) e o filtro de período com atalhos (D6); verificar com `npm run build` sem erros de tipo
- [x] 3.2 Implementar as seções Operacional, Financeiro e Auditoria, o CSV e a impressão; verificar no navegador contra o backend local com dados de teste: indicadores e ranking conferidos com as comandas criadas, "Contabilidade confere o mês", CSV aberto como texto com `;`, BOM e vírgula decimal, prévia de impressão só com o relatório, paginação e detalhes da auditoria e largura de celular sem rolagem horizontal da página

## 4. Implantação e verificação

- [x] 4.1 Rodar `pytest` completo e `npm run build` e verificar que tudo passa
- [ ] 4.2 Publicar (push na `main`), confirmar a migração `0004` aplicada e verificar na URL pública: como admin, o operacional e o financeiro de hoje batendo com as comandas do dia; como contabilidade, o financeiro do mês, o CSV e a auditoria filtrada

## Workflow follow-up

- Arquivar o change após revisão do grupo (`/opsx:archive`), criando a spec `relatorios` e aplicando as deltas de `auditoria` e `autenticacao`.
- Pendência registrada: tratamento de erros de renderização (página em branco).
