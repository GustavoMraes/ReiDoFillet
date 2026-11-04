# Design

## Context

Motivação em `proposal.md`. Estado atual relevante:

- `main.tsx` monta `StrictMode > AuthProvider > MensagensProvider > App`, sem nenhum limite de erro: qualquer exceção lançada durante a renderização desmonta tudo.
- `App` escolhe a tela pelo estado `tela` (e `comandaId`) e a renderiza dentro de `Layout` (cabeçalho e abas). A Contabilidade usa um `Layout` com a única aba Relatórios.
- Erros de chamadas à API e de ações do usuário já são capturados nas páginas e exibidos com `useMensagens`; o polling marca dados "desatualizados" em vez de lançar.
- A sessão fica no `sessionStorage`: recarregar a página mantém o usuário conectado.
- O frontend não tem executor de testes automatizados; a verificação é feita no navegador.

## Goals / Non-Goals

**Goals:**
- Nenhuma falha de renderização resulta em página em branco.
- Falha de uma tela não afeta o cabeçalho, a sessão nem as outras telas.

**Non-Goals:**
- Serviço de monitoramento de erros, captura de erros em eventos e promessas (já tratados com mensagens), novas dependências.

## Decisions

### D1. Componente `LimiteDeErro`

Componente de classe (único jeito de capturar erros de renderização no React 18) com `getDerivedStateFromError` e `componentDidCatch` (registra no `console.error` o erro e a pilha de componentes). Recebe `variante: 'tela' | 'geral'` e, na variante de tela, `onIrParaInicio`. "Tentar novamente" zera o erro: como os filhos foram desmontados na falha, eles montam de novo e refazem suas consultas. Alternativa considerada: a biblioteca `react-error-boundary` — descartada para não adicionar dependência por um componente de poucas linhas.

### D2. Onde ficam os limites

- **Por tela:** no `App`, em volta do conteúdo passado ao `Layout`, com `key` igual à tela atual (e ao `comandaId`), de modo que trocar de aba crie um limite novo, sem o erro anterior. Vale também para a Contabilidade.
- **Geral:** no `main.tsx`, por fora de `AuthProvider` e `MensagensProvider`, para capturar falhas no cabeçalho e nos provedores. A página de erro geral não depende de nenhum contexto e o botão "Recarregar" usa `window.location.reload()`.

### D3. "Ir para o início"

O `App` passa ao limite de tela uma função que muda a tela para a inicial do perfil (Mapa de Mesas ou Relatórios). Como a tela inicial pode ser a mesma que falhou, o limite também zera o próprio erro ao executar a ação.

### D4. Conteúdo do aviso

Título e texto em português, ações em botões e um `<details>` "Detalhes técnicos" com `nome: mensagem` do erro (a pilha completa fica só no console). O aviso não lê nem exibe dados da sessão.

### D5. Verificação sem gatilho no código

Para não deixar no código um "botão de quebrar", as falhas são provocadas no navegador durante a verificação: interceptando `fetch` para devolver um item malformado (falha numa tela) e alterando o nome do usuário na sessão guardada para um objeto (falha no cabeçalho, pois o React não renderiza objetos).

## Risks / Trade-offs

- [Em desenvolvimento o `StrictMode` e o overlay do Vite mostram o erro duas vezes] → comportamento só de desenvolvimento; no build de produção aparece apenas o aviso.
- [Erro que se repete a cada tentativa] → "Tentar novamente" mostra o aviso de novo; "Ir para o início" e as abas continuam disponíveis.

## Migration Plan

Só frontend: push na `main` e publicação na Vercel. Rollback: redeploy do commit anterior.
