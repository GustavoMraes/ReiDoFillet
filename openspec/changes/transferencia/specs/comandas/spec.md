# Spec Delta

## ADDED Requirements

### Requirement: Transferência da comanda para outra mesa
O sistema SHALL transferir uma comanda ABERTA ou em PRE_CONTA, inteira, para outra mesa livre. A comanda MUST manter o mesmo identificador, status, responsável, itens (com status e horários), pré-conta, taxa de serviço e pagamentos; somente a mesa muda. Após a transferência, a mesa de origem MUST ficar livre e a de destino MUST exibir o atendimento. Não há transferência de itens isolados nem junção de comandas.

#### Scenario: Cliente troca de mesa
- **WHEN** um funcionário transfere para a mesa 7 (livre) a comanda aberta da mesa 3, que tem itens em preparo
- **THEN** a comanda passa a ser da mesa 7 com os mesmos itens e status, a mesa 3 aparece como Livre e a mesa 7 como Ocupada no mapa

#### Scenario: Transferência com pré-conta e pagamento parcial
- **WHEN** uma comanda em pré-conta com um pagamento registrado é transferida para outra mesa livre
- **THEN** a comanda continua em pré-conta, com o mesmo total, o mesmo pagamento e o mesmo valor restante, e a mesa de destino aparece como Aguardando pagamento

#### Scenario: Cozinha mostra a nova mesa
- **WHEN** uma comanda com itens em preparo é transferida da mesa 3 para a mesa 7
- **THEN** o painel da cozinha passa a identificar esses itens como da mesa 7

### Requirement: Destinos que não recebem transferência
O sistema MUST recusar a transferência, sem alterar nada, quando o destino não for uma mesa livre diferente da atual: a própria mesa, mesa com comanda ativa, em manutenção, reservada ou inexistente. Comandas FECHADA ou CANCELADA MUST NOT ser transferidas.

#### Scenario: Mesma mesa
- **WHEN** um funcionário tenta transferir uma comanda para a mesa em que ela já está
- **THEN** nada é alterado e o sistema informa "A comanda já está nesta mesa"

#### Scenario: Destino em manutenção ou inexistente
- **WHEN** um funcionário tenta transferir uma comanda para uma mesa em manutenção ou que não existe
- **THEN** nada é alterado e o sistema informa "Mesa em manutenção" ou "Mesa não encontrada", respectivamente

#### Scenario: Destino ocupado
- **WHEN** um funcionário tenta transferir uma comanda para uma mesa que já tem comanda aberta
- **THEN** nada é alterado e o sistema informa "A mesa de destino já está em atendimento"

#### Scenario: Destino reservado
- **WHEN** um funcionário tenta transferir uma comanda para uma mesa Reservada
- **THEN** nada é alterado e o sistema informa "A mesa de destino está reservada"

#### Scenario: Comanda encerrada
- **WHEN** é solicitada a transferência de uma comanda fechada
- **THEN** nada é alterado e o sistema informa "Somente comandas em atendimento podem ser transferidas"

#### Scenario: Transferências simultâneas para a mesma mesa
- **WHEN** duas comandas são transferidas ao mesmo tempo para a mesma mesa livre
- **THEN** apenas uma transferência é concluída e a outra é recusada com "A mesa de destino já está em atendimento"

### Requirement: Destino livre com reserva próxima
Uma mesa livre com reserva confirmada nas próximas 2 horas MUST aceitar a transferência. Na interface, a confirmação da transferência para essa mesa MUST mostrar o horário da reserva.

#### Scenario: Transferência para mesa com reserva mais tarde
- **WHEN** um funcionário escolhe como destino uma mesa livre com reserva às 20h30
- **THEN** a interface avisa "A mesa 7 tem reserva às 20h30" junto da confirmação e, se confirmada, a transferência é concluída

### Requirement: Auditoria da transferência
A transferência MUST gerar um registro de auditoria com o usuário responsável e a comanda antes (mesa de origem) e depois (mesa de destino).

#### Scenario: Transferência auditada
- **WHEN** um funcionário transfere a comanda da mesa 3 para a mesa 7
- **THEN** é gravado um registro de auditoria com o funcionário, a ação de transferência e a comanda com a mesa 3 antes e a mesa 7 depois

### Requirement: Troca de mesa pela tela da comanda
A tela da comanda SHALL oferecer a ação "Trocar de mesa" enquanto a comanda estiver aberta ou em pré-conta. A ação MUST listar somente as mesas livres como destino, pedir confirmação e, concluída a transferência, continuar na tela da comanda com o novo número da mesa e uma mensagem de confirmação. O acesso MUST seguir o das demais operações de comanda (Funcionário e Administrador).

#### Scenario: Troca de mesa pela tela
- **WHEN** o funcionário escolhe "Trocar de mesa", seleciona a mesa 7 e confirma
- **THEN** a tela mostra "Comanda — Mesa 7" e a mensagem "Comanda transferida da mesa 3 para a mesa 7"

#### Scenario: Nenhuma mesa livre
- **WHEN** o funcionário escolhe "Trocar de mesa" e não há mesa livre
- **THEN** a interface informa que não há mesas livres para a transferência

#### Scenario: Contabilidade não transfere
- **WHEN** um usuário com perfil Contabilidade solicita a transferência de uma comanda
- **THEN** a requisição é recusada como sem permissão
