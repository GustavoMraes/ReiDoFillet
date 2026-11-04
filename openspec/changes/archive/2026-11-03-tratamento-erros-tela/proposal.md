# Proposal

## Why

Quando um componente da interface falha ao ser desenhado (por exemplo, por um dado em formato inesperado vindo da API), o React desmonta a aplicação inteira e o usuário fica com uma página em branco, sem mensagem nem forma de continuar além de recarregar e perder o contexto. Os erros de chamadas à API já são tratados com mensagens; falta proteger a renderização. Era um ponto em aberto registrado desde os primeiros changes.

## What Changes

- Uma falha ao exibir uma tela passa a mostrar, no lugar dela, um aviso "Não foi possível exibir esta tela" com as ações "Tentar novamente" e "Ir para o início"; o cabeçalho, as abas, a sessão e as demais telas continuam funcionando.
- Trocar de aba descarta o erro da tela anterior.
- Uma falha fora das telas (cabeçalho ou estrutura geral) mostra uma página de erro com "Recarregar", em vez da página em branco.
- O detalhe técnico do erro fica disponível num bloco recolhido "Detalhes técnicos" e no console do navegador, para quem for dar suporte.

## Capabilities

### New Capabilities

- `interface`: comportamento geral da interface diante de falhas de exibição (isolamento por tela, recuperação e página de erro geral).

### Modified Capabilities

(nenhuma)

## Impact

- **Frontend:** novo componente de limite de erro (`ErrorBoundary` do React, por classe, sem dependência nova) usado em volta de cada tela no `App` e em volta da aplicação no `main.tsx`; estilos do aviso.
- **Backend:** nenhum.
- Fora do escopo: envio dos erros para um serviço de monitoramento e erros em ações assíncronas (cliques e chamadas à API), que já são tratados com mensagens temporárias.
