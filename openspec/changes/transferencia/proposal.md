# Proposal

## Why

Clientes trocam de mesa durante o atendimento (vão para a varanda, o grupo cresce, a mesa tem problema), e hoje a comanda fica presa à mesa em que foi aberta: o garçom precisaria cancelar e relançar tudo, perdendo o histórico de envios e pagamentos. O RF08 e o caso de uso 7.8 da especificação preveem a transferência; o grupo decidiu manter só a transferência da comanda inteira, sem transferência parcial de itens.

## What Changes

- Transferência da comanda ativa (ABERTA ou em PRÉ-CONTA) inteira para outra mesa, com itens, horários de envio, pré-conta e pagamentos preservados; a mesa de origem fica livre e a de destino passa a mostrar o atendimento.
- O destino MUST ser uma mesa livre: mesa ocupada, aguardando pagamento, reservada (dentro da janela de bloqueio) ou em manutenção recusa a transferência. Não há junção de comandas nem transferência de itens isolados.
- Destino livre com reserva próxima é aceito; a interface avisa o horário da reserva antes de confirmar (mesma regra da abertura de comanda).
- Registro de auditoria da transferência com a comanda antes (mesa de origem) e depois (mesa de destino).
- Na tela da comanda, ação "Trocar de mesa" com a escolha da mesa de destino entre as livres; a cozinha e o mapa passam a mostrar o novo número da mesa.

## Capabilities

### New Capabilities

(nenhuma)

### Modified Capabilities

- `comandas`: novos requisitos de transferência da comanda para outra mesa (regras do destino, preservação dos dados, concorrência, auditoria e ação na tela da comanda).

## Impact

- **Backend:** `ComandaService.transferir`, rota `POST /comandas/{id}/transferir`, nova ação de auditoria `TRANSFERIR`, bloqueio da linha da mesa de destino (`MesaRepository.obter_para_atualizar`, já existente) e testes de integração, incluindo transferências simultâneas para a mesma mesa.
- **Frontend:** função `transferirComanda` em `api/comandas.ts` e diálogo de troca de mesa na página da comanda (reutilizando `Dialogo`).
- **Banco:** sem migração; o índice único de comanda ativa por mesa continua garantindo uma comanda por mesa.
- Cozinha e mapa não mudam de código: já obtêm o número da mesa pela comanda.
