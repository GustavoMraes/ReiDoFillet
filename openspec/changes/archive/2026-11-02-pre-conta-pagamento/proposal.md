# Proposal

## Why

O atendimento ainda não termina no sistema: depois de lançar e servir os itens, não há como conferir a conta, registrar o pagamento nem liberar a mesa — nos testes em produção, comandas precisaram ser encerradas diretamente no banco. Os módulos de Comandas e Pagamento são a prioridade apontada no estudo de viabilidade, e este change fecha o ciclo do atendimento (UC 7.3 e 7.4, RF01, RF09) usando as máquinas de cartão e PIX que o restaurante já tem.

## What Changes

- Geração da pré-conta (UC 7.3, RF09): a comanda passa a PRE_CONTA, com o resumo dos itens, subtotal, taxa de serviço e total; exige ao menos um item não cancelado; itens ainda em preparo ou prontos geram aviso, sem bloquear. A mesa passa a "Aguardando pagamento".
- Pré-conta é um retrato: incluir, alterar ou cancelar item em uma comanda em PRE_CONTA a devolve para ABERTA.
- Taxa de serviço opcional: o percentual padrão (parâmetro `taxa_servico_padrao`, 10%) é copiado na pré-conta e pode ser desligado ou ajustado até o fechamento, com auditoria.
- Registro de pagamentos (UC 7.4, RF01): um ou mais pagamentos por comanda, cada um com forma (PIX, Crédito, Débito, Dinheiro) e valor, sem integração com maquininha; a soma não pode passar do total.
- Remoção de pagamento registrado por engano, antes do fechamento (decisão do grupo).
- Fechamento automático: quando os pagamentos somam o total, a comanda passa a FECHADA e a mesa volta a Livre.
- Cancelamento de comanda sem itens ativos (decisão do grupo), liberando mesas abertas por engano.
- Pré-conta em tela imprimível e tela de Pagamento conforme o Projeto de Interface.
- Auditoria de todas essas operações (RN05).

Desvios dos documentos de origem: sem emissão de Nota Fiscal e sem integração com maquininha (UC 7.4 — decisão do grupo); o pagamento é apenas registrado.

Fora do escopo: alteração de comanda já fechada por administrador (RN03), desconto e cortesia, troco, alteração do percentual padrão pela interface (change `gestao-cardapio-usuarios`), relatórios financeiros (change `relatorios`).

## Capabilities

### New Capabilities

- `pagamentos`: taxa de serviço, registro e remoção de pagamentos, fechamento da comanda e tela de pagamento.

### Modified Capabilities

- `comandas`: pré-conta, retorno a ABERTA quando a pré-conta é alterada, cancelamento de comanda sem itens ativos e total com taxa de serviço; itens passam a poder ser incluídos e alterados também em comandas em PRE_CONTA.

## Impact

- **Backend:** `POST /comandas/{id}/pre-conta`, `PATCH /comandas/{id}/taxa-servico`, `POST /comandas/{id}/pagamentos`, `DELETE /comandas/{id}/pagamentos/{pagamento_id}`, `POST /comandas/{id}/cancelar`; a resposta da comanda ganha subtotal, taxa, total, valor pago, restante e pagamentos.
- **Sem migração:** `pagamento`, `parametro`, `taxa_servico_pct`, `taxa_servico_aplicada`, `pre_conta_em` e `fechada_em` já existem desde `estrutura-base`.
- **Frontend:** botão "Gerar pré-conta", pré-conta imprimível, aba e tela de Pagamento, cancelamento de comanda vazia.
- **Compatibilidade:** o campo `total` da comanda passa a incluir a taxa de serviço quando aplicada; enquanto a comanda está ABERTA, o valor não muda.
