# Design

## Context

Motivação em `proposal.md`. Estado atual relevante:

- `Comanda.mesa_id` é a única ligação entre comanda e mesa; itens, pagamentos e auditoria apontam para a comanda. Cozinha (`CozinhaRepository`), mapa (`MesaRepository.comandas_ativas`) e cabeçalho da comanda obtêm o número da mesa por junção, então trocar `mesa_id` basta para todos refletirem a nova mesa.
- O índice único parcial `uq_comanda_ativa_por_mesa` garante no máximo uma comanda ABERTA/PRE_CONTA por mesa.
- `ComandaService` já bloqueia a comanda (`obter_para_atualizar`, `SELECT ... FOR UPDATE`) em toda operação que a altera; `MesaRepository.obter_para_atualizar` e `MesaService.situacao` (status calculado da mesa, inclusive janela de reserva) já existem.
- A abertura comum de comanda não bloqueia a mesa: a corrida é resolvida pelo índice único (`IntegrityError`).

## Goals / Non-Goals

**Goals:**
- Transferência atômica: a comanda muda de mesa por inteiro ou nada muda.
- Mesmas regras de status de mesa do mapa (uma única fonte: `calcular_mapa`).

**Non-Goals:**
- Junção de comandas, transferência de itens, troca entre duas mesas ocupadas (decisão do grupo: destino somente livre).

## Decisions

### D1. Atualizar `mesa_id` em vez de recriar a comanda

A transferência altera apenas `mesa_id` da comanda existente. Alternativa considerada: fechar a comanda e abrir outra na mesa de destino copiando itens e pagamentos — descartada por duplicar dados, quebrar o identificador usado por outros dispositivos abertos na comanda e exigir regras de cópia para pagamentos e auditoria.

### D2. Ordem de bloqueio e validação

Em `ComandaService.transferir`, dentro de uma transação:

1. bloqueia a comanda (`FOR UPDATE`) e exige ABERTA ou PRE_CONTA;
2. recusa destino igual à mesa atual;
3. bloqueia a linha da mesa de destino (`MesaRepository.obter_para_atualizar`; inexistente → 404);
4. calcula o status do destino com `MesaService.situacao`: MANUTENCAO → "Mesa em manutenção"; OCUPADA/AGUARDANDO_PAGAMENTO → "A mesa de destino já está em atendimento"; RESERVADA → "A mesa de destino está reservada";
5. troca `mesa_id`, faz `flush` e registra a auditoria.

O bloqueio da mesa serializa transferências, check-ins e criações de reserva para o mesmo destino. Ele usa `FOR NO KEY UPDATE` (também em reservas e check-in), e não `FOR UPDATE`: o teste de concorrência mostrou deadlock entre a transferência e uma abertura comum no destino, porque a inserção da comanda confere a chave estrangeira com `FOR KEY SHARE` na mesa (bloqueado por `FOR UPDATE`) enquanto a transferência espera o índice único dessa inserção. `FOR NO KEY UPDATE` não conflita com `FOR KEY SHARE` e continua conflitando com outros bloqueios de atualização. A abertura comum de comanda, que não bloqueia a mesa, é coberta pelo índice único: se ela vencer a corrida, o `flush` da transferência gera `IntegrityError`, a transação é desfeita e a resposta é 409 com a mensagem de destino em atendimento. A ordem comanda → mesa não forma ciclo com o check-in (reserva → mesa → nova comanda) nem com a criação de reserva (mesa), pois nenhum deles bloqueia uma comanda existente.

### D3. Pré-conta e pagamentos preservados

A transferência não mexe em status, pré-conta, taxa ou pagamentos, nem invalida a pré-conta (os itens não mudaram). Uma comanda em PRE_CONTA leva o status AGUARDANDO_PAGAMENTO para a nova mesa no mapa.

### D4. API

`POST /comandas/{id}/transferir` com `{"mesa_id": <destino>}` → `ComandaOut` (já com o novo número da mesa). Erros no formato `{"detalhe": ...}`: 404 (comanda ou mesa), 409 (regras de destino ou status da comanda). Perfis Funcionário e Administrador, como as demais rotas de comanda.

### D5. Auditoria

Nova ação `TRANSFERIR`, entidade `Comanda`, com `ComandaSnapshot` antes e depois — o snapshot já contém `mesa_id`, então origem e destino ficam registrados sem novo schema.

### D6. Interface

Na página da comanda (ABERTA ou PRE_CONTA), botão "Trocar de mesa" abre um `Dialogo` com as mesas LIVRE do `GET /mesas` (número, lugares, localização e "Reserva às HHhMM" quando houver `proxima_reserva_inicio`). Escolhida a mesa, a confirmação repete a origem e o destino e, se houver reserva próxima, o aviso "A mesa N tem reserva às HHhMM". Após a resposta, a tela usa a comanda devolvida (`definir` do polling) e mostra "Comanda transferida da mesa X para a mesa Y". Sem mesas livres, o diálogo informa isso.

## Risks / Trade-offs

- [Outro dispositivo com a lista de mesas desatualizada escolhe um destino que acabou de ser ocupado] → o servidor revalida tudo sob bloqueio e recusa com a mensagem de destino em atendimento; a interface mostra o erro e recarrega a lista.
- [Cupom já impresso com o número antigo da mesa] → aceito: o painel da cozinha mostra o número atualizado; reimpressão não faz parte do escopo.
- [Garçom transfere para a mesa errada] → basta transferir de novo; a auditoria registra cada troca.

## Migration Plan

Sem migração de banco. Deploy pelo push na `main` (Render e Vercel). Rollback: redeploy do commit anterior; comandas transferidas continuam válidas, pois só `mesa_id` mudou.
