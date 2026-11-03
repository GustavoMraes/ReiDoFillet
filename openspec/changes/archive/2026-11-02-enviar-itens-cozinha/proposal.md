# Proposal

## Why

Os itens já são registrados na comanda, mas continuam PENDENTES para sempre: não há como encaminhá-los à cozinha nem acompanhar o preparo. Hoje o pedido em papel é entregue na cozinha (Especificação, seção 2); o UC 7.2 e o Painel da Cozinha do Projeto de Interface substituem esse passo e fecham o ciclo do item até a entrega à mesa, permitindo ao garçom informar o consumidor sobre o andamento (HU03, RF05) e registrando os tempos de preparo (RF19).

## What Changes

- Envio dos itens à cozinha a partir da comanda (UC 7.2, RF03, RF18): somente os itens PENDENTES passam a EM_PREPARO, com o horário do envio; sem itens pendentes, o sistema informa que não há o que enviar.
- Cupom do envio em tela imprimível (RF06, RF12), com mesa, garçom, horário e os itens enviados com quantidade e observação.
- Painel da Cozinha (KDS) com duas colunas, Em preparo e Pronto, em ordem de envio, mostrando mesa, quantidade, produto, observação e tempo desde o envio, com atualização automática.
- Mudança de estágio pelo painel: EM_PREPARO → PRONTO → ENTREGUE, com registro do horário de cada etapa; itens entregues ou cancelados saem do painel.
- Auditoria do envio e de cada mudança de estágio (RN05).
- Interface: botão "Enviar itens para a cozinha" habilitado na tela da comanda e aba Cozinha liberada para Funcionário e Administrador.

Desvios dos documentos de origem: o fluxo alternativo do UC 7.2 ("sistema de impressão indisponível") não se aplica, pois o cupom é uma tela imprimível e não há integração com impressora; o Painel tem duas colunas, e não as três (Pendente, Em preparo, Pronto) do Projeto de Interface, porque o UC 7.2 define que o envio já coloca o item em preparo (decisão do grupo).

Fora do escopo: alertas de tempo de espera (decisão do grupo), divisão entre cozinha e bar, tempo médio de atendimento (change `relatorios`), pré-conta e pagamento.

## Capabilities

### New Capabilities

- `cozinha`: Painel da Cozinha — fila dos itens enviados por estágio e mudança de EM_PREPARO para PRONTO e de PRONTO para ENTREGUE.

### Modified Capabilities

- `comandas`: passa a enviar os itens pendentes à cozinha e a oferecer o cupom do envio; a tela da comanda ganha a ação de envio.

## Impact

- **Backend:** `POST /comandas/{id}/enviar`, `GET /cozinha`, `POST /cozinha/itens/{id}/pronto` e `POST /cozinha/itens/{id}/entregue`; novas regras no serviço de comandas e um serviço de cozinha; sem migração (`enviado_em`, `pronto_em` e `entregue_em` já existem em `item_comanda`).
- **Frontend:** botão de envio e tela de cupom imprimível na comanda; nova página Cozinha; navegação entre Mapa, Comanda e Cozinha.
- **Dados:** os horários de envio, pronto e entrega passam a ser preenchidos, base para o tempo médio da UC 7.6.
