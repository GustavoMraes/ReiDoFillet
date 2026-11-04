# Spec Delta

## Purpose

Disponibilizar ao administrador indicadores operacionais do atendimento e à contabilidade (e ao administrador) o histórico financeiro das comandas fechadas, por período, somente para consulta, com exportação e com registro de cada consulta.

## ADDED Requirements

### Requirement: Período dos relatórios
Os relatórios SHALL ser consultados por um período de data inicial e data final, ambas inclusivas e interpretadas no fuso de São Paulo, com hoje como padrão. A data final MUST ser igual ou posterior à inicial e o período MUST ter no máximo 366 dias.

#### Scenario: Período padrão
- **WHEN** um relatório é consultado sem datas
- **THEN** são considerados os dados de hoje, das 00h00 às 23h59 no horário de São Paulo

#### Scenario: Período invertido
- **WHEN** a data final é anterior à inicial
- **THEN** o relatório não é gerado e o sistema informa "A data final deve ser igual ou posterior à inicial"

#### Scenario: Período longo demais
- **WHEN** o período tem mais de 366 dias
- **THEN** o relatório não é gerado e o sistema informa "O período máximo é de 366 dias"

### Requirement: Relatório operacional
O relatório operacional SHALL considerar as comandas abertas no período e MUST apresentar: quantidade de comandas por situação (em aberto, fechadas e canceladas), faturamento (soma dos totais das comandas fechadas, com a taxa de serviço), ticket médio (faturamento dividido pelas comandas fechadas) e tempo médio de atendimento das comandas fechadas (da abertura ao fechamento, em minutos).

#### Scenario: Dia de movimento
- **WHEN** no período foram abertas 5 comandas, das quais 3 fecharam com totais de R$ 110,00, R$ 55,00 e R$ 35,00, 1 foi cancelada e 1 continua aberta
- **THEN** o relatório mostra 1 em aberto, 3 fechadas e 1 cancelada, faturamento de R$ 200,00 e ticket médio de R$ 66,67

#### Scenario: Período sem comandas fechadas
- **WHEN** nenhuma comanda aberta no período foi fechada
- **THEN** faturamento é R$ 0,00 e ticket médio e tempo médio aparecem como não disponíveis

### Requirement: Produtos mais vendidos
O relatório operacional MUST listar os 10 produtos mais vendidos nas comandas fechadas do período, com quantidade e valor vendido (preço de cada lançamento multiplicado pela quantidade), em ordem decrescente de quantidade e, no empate, de valor. Itens cancelados MUST NOT ser contados.

#### Scenario: Ranking do período
- **WHEN** foram vendidas 8 unidades de "Arroz Branco" e 5 de "Filet Mignon 300g", e 2 de "Picanha 400g" foram canceladas
- **THEN** o ranking começa por "Arroz Branco" (8) e "Filet Mignon 300g" (5) e não inclui as picanhas canceladas

#### Scenario: Preço alterado no período
- **WHEN** um produto foi vendido a R$ 89,90 e, após aumento, a R$ 95,00
- **THEN** o valor vendido soma cada lançamento pelo preço em que foi lançado

### Requirement: Movimento por dia e por horário
O relatório operacional MUST mostrar, para cada dia do período, a quantidade de comandas abertas e o faturamento das fechadas abertas naquele dia, e, para cada faixa de uma hora (0h a 23h, no horário de São Paulo), a quantidade de comandas abertas.

#### Scenario: Horário de pico
- **WHEN** no período foram abertas 4 comandas entre 20h00 e 20h59 e 1 entre 12h00 e 12h59
- **THEN** a faixa das 20h mostra 4 comandas e a das 12h mostra 1

### Requirement: Relatório financeiro
O relatório financeiro SHALL listar as comandas fechadas no período (pelo horário de fechamento), em ordem de fechamento, cada uma com número da comanda, mesa, horários de abertura e fechamento, responsável, subtotal, taxa de serviço, total e pagamentos (forma e valor). O relatório MUST apresentar os totais do período: quantidade de comandas, subtotal, taxa de serviço, total e total por forma de pagamento. O relatório MUST ser somente leitura.

#### Scenario: Fechamento do dia
- **WHEN** no dia foram fechadas duas comandas: uma de R$ 110,00 (R$ 100,00 + taxa de R$ 10,00) paga com R$ 60,00 em PIX e R$ 50,00 em crédito, e outra de R$ 35,00 sem taxa paga em dinheiro
- **THEN** o relatório mostra as duas comandas, subtotal de R$ 135,00, taxa de R$ 10,00, total de R$ 145,00 e, por forma, PIX R$ 60,00, crédito R$ 50,00, débito R$ 0,00 e dinheiro R$ 35,00

#### Scenario: Comandas abertas ou canceladas
- **WHEN** no período há comandas abertas, em pré-conta ou canceladas
- **THEN** elas não aparecem no relatório financeiro

### Requirement: Rastro das consultas
Toda consulta de relatório MUST gerar um registro de auditoria com o usuário, o tipo de relatório e os filtros usados.

#### Scenario: Consulta auditada
- **WHEN** a contabilidade consulta o relatório financeiro de 1º a 31 de outubro
- **THEN** é gravado um registro de auditoria com o usuário, o relatório financeiro e o período consultado

### Requirement: Exportação dos relatórios
A interface SHALL permitir baixar em CSV a lista exibida de cada relatório (comandas fechadas do financeiro e produtos e movimento do operacional), com separador ponto e vírgula, valores com vírgula decimal e acentuação legível no Excel, e SHALL oferecer uma versão para impressão de cada relatório.

#### Scenario: Planilha do financeiro
- **WHEN** a contabilidade baixa o CSV do relatório financeiro
- **THEN** o arquivo traz uma linha por comanda fechada, com os mesmos valores da tela, e abre no Excel com acentos e decimais corretos

### Requirement: Acesso aos relatórios restrito por perfil
O relatório operacional MUST ser liberado apenas para o perfil Administrador; o relatório financeiro, para Administrador e Contabilidade. O perfil Funcionário MUST NOT acessar relatórios.

#### Scenario: Contabilidade tenta o operacional
- **WHEN** um usuário com perfil Contabilidade consulta o relatório operacional
- **THEN** a requisição é recusada como sem permissão

#### Scenario: Funcionário tenta o financeiro
- **WHEN** um usuário com perfil Funcionário consulta o relatório financeiro
- **THEN** a requisição é recusada como sem permissão

### Requirement: Tela de relatórios
A interface SHALL oferecer a aba Relatórios com filtro de período (atalhos para hoje, últimos 7 dias e mês atual) e as seções Operacional, Financeiro e Auditoria para o Administrador, e Financeiro e Auditoria para a Contabilidade. O relatório só MUST ser consultado quando o usuário pedir, sem atualização automática.

#### Scenario: Contabilidade confere o mês
- **WHEN** a contabilidade escolhe "Mês atual" e consulta o financeiro
- **THEN** são exibidos os totais por forma de pagamento e a lista das comandas fechadas no mês, com as opções de baixar CSV e imprimir
