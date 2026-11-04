# Proposal

## Why

O sistema já registra todo o atendimento (comandas, itens, pagamentos e auditoria), mas ninguém consegue consultar esses dados: o administrador não tem visão do movimento do restaurante e o perfil Contabilidade entra numa tela vazia. A especificação prevê os relatórios operacionais (HU06, F13), financeiros e de auditoria (HU07, F14) e a Matriz de Informação define os indicadores do nível gerencial (volume de atendimentos e consumo, desempenho dos produtos, comandas abertas, encerradas e canceladas).

## What Changes

- **Relatório operacional (Administrador):** para um período escolhido, comandas por situação (em aberto, fechadas, canceladas), faturamento, ticket médio, tempo médio de atendimento, produtos mais vendidos (quantidade e valor) e movimento por dia e por faixa de horário.
- **Relatório financeiro (Contabilidade e Administrador):** comandas fechadas no período, cada uma com mesa, abertura e fechamento, responsável, subtotal, taxa de serviço, total e pagamentos; totais do período por forma de pagamento e da taxa de serviço. Somente leitura.
- **Consulta da auditoria (Contabilidade e Administrador):** registros por período, usuário e tipo de operação, com estados antes e depois, paginados. Somente leitura.
- **Rastro das consultas:** toda consulta de relatório ou da auditoria gera um registro de auditoria com o usuário e os filtros usados (HU07).
- **Exportação:** CSV das listas (abre no Excel) e versão para impressão de cada relatório.
- **Interface:** aba **Relatórios** com Operacional, Financeiro e Auditoria para o Administrador, e Financeiro e Auditoria para a Contabilidade, que passa a entrar nela em vez do aviso de "ainda não há telas".

## Capabilities

### New Capabilities

- `relatorios`: relatórios operacional e financeiro por período, regras de cálculo dos indicadores, exportação, rastro das consultas e tela de relatórios.

### Modified Capabilities

- `auditoria`: novo requisito de consulta somente leitura do histórico de auditoria, com filtros e paginação, para Administrador e Contabilidade.
- `autenticacao`: o requisito "Tela de login como ponto de entrada" passa a levar a Contabilidade à tela de relatórios.

## Impact

- **Backend:** serviço e rotas de relatórios (`/relatorios/operacional`, `/relatorios/financeiro`) e de consulta da auditoria (`/auditoria`), reutilizando o cálculo de `financeiro.calcular`; migração `0004` com índices em `comanda.aberta_em` e `comanda.fechada_em`.
- **Frontend:** página Relatórios com as três seções, filtros de período, gráficos de barras simples em CSS (sem biblioteca nova), CSV gerado no navegador e estilos de impressão.
- **Banco:** só índices novos; nenhuma tabela muda.
