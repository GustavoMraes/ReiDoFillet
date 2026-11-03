# Design

## Context

Motivação em `proposal.md`. Estado atual relevante:

- A tabela `reserva` existe desde `estrutura-base` (mesa, nome, telefone, pessoas, `inicio`, `fim`, status CONFIRMADA/CONCLUIDA/CANCELADA, `criado_por_id`, `cancelado_por_id`), com índice `(mesa_id, status, inicio)` e `CHECK fim > inicio`. Nenhuma migração é necessária.
- `MesaRepository.reservas_na_janela` busca reservas confirmadas com `inicio` em `[agora − 30min, agora + 30min]`; `calcular_mapa` marca a mesa como RESERVADA e informa `reserva_inicio`.
- `ComandaService.abrir` recusa mesa RESERVADA ("aguarde o check-in") e trata a corrida pelo índice único de comanda ativa; a operação faz commit próprio.
- O frontend tem as abas Mapa, Comanda, Cozinha e Pagamento, e o clique em mesa reservada hoje só mostra a mensagem do servidor.

## Goals / Non-Goals

**Goals:**
- Uma única regra de tempo (relógio injetável, fuso de São Paulo) para janela, conflito e "não compareceu".
- Check-in atômico: reserva concluída e comanda aberta juntas, ou nada.
- Nenhuma tarefa agendada (o Render hiberna).

**Non-Goals:**
- Reserva de várias mesas, cadastro de clientes, lembretes, anonimização automática.

## Decisions

### D1. Horários e fuso

`inicio` chega como data e hora ISO 8601; sem fuso, é interpretado como America/Sao_Paulo (a interface envia a hora local da tela). `fim = inicio + 2h` é calculado no servidor. A consulta por data usa o dia em São Paulo: `inicio` em `[data 00:00, data+1 00:00)` no fuso local, convertido para UTC.

### D2. Conflito de horário com bloqueio da mesa

Antes de verificar sobreposição, o serviço bloqueia a linha da mesa (`SELECT ... FOR UPDATE`). Duas criações simultâneas para a mesma mesa são serializadas: a segunda enxerga a primeira e é recusada. Sobreposição: reserva CONFIRMADA da mesma mesa com `inicio < novo_fim` e `fim > novo_inicio` (intervalos semiabertos, então reservas encostadas são aceitas).

Alternativa considerada: restrição de exclusão do PostgreSQL (`EXCLUDE USING gist`). Descartada por exigir migração e a extensão `btree_gist`, e por gerar erro genérico em vez da mensagem com o horário existente.

### D3. Situação calculada

`situacao(reserva, agora)`: CONFIRMADA com `agora > inicio + 30min` → NAO_COMPARECEU; demais, o próprio status. Função pura, usada na listagem. O status gravado não muda, e uma reserva "não compareceu" ainda pode receber check-in (cliente muito atrasado com mesa livre) ou ser cancelada.

### D4. Check-in reutilizando a abertura de comanda

A criação da comanda é extraída de `ComandaService.abrir` para um método que trabalha dentro de uma transação já aberta (adiciona, faz flush e registra a auditoria, sem commit). `abrir` passa a usá-lo, e `ReservaService.check_in` também:

1. bloqueia a reserva (`FOR UPDATE`) e exige CONFIRMADA;
2. recusa mesa em manutenção ou com comanda ativa;
3. marca a reserva CONCLUIDA e cria a comanda (responsável: quem fez o check-in) na mesma transação.

A janela de reserva não é verificada: o check-in é justamente o que libera a mesa reservada. Se outra abertura vencer a corrida pelo índice único, a transação é desfeita e o check-in recusado com a mensagem de mesa ocupada.

### D5. Próxima reserva no mapa

`reservas_na_janela` passa a buscar `inicio` em `[agora − 30min, agora + 2h]` (continua uma consulta). `calcular_mapa` usa as que estão em `±30min` para RESERVADA, como hoje, e as entre `agora + 30min` e `agora + 2h` para preencher `proxima_reserva_inicio` de mesas LIVRE. O mapa continua com três consultas.

### D6. Contrato da API

| Rota | Resposta |
|---|---|
| `GET /reservas?data=AAAA-MM-DD` (padrão: hoje) | lista `{id, mesa: {id, numero}, nome_cliente, telefone, qtd_pessoas, inicio, fim, status, situacao}` |
| `POST /reservas` `{mesa_id, nome_cliente, telefone, qtd_pessoas, inicio}` | 201 `{reserva, aviso}` (`aviso` sobre capacidade) |
| `POST /reservas/{id}/cancelar` | reserva |
| `POST /reservas/{id}/check-in` | `{reserva, comanda}` |

`MesaMapaOut` ganha `proxima_reserva_inicio`. Erros no formato `{"detalhe": ...}`: 404 (mesa/reserva), 409 (conflito, manutenção, status, mesa ocupada), 422 (dados inválidos, horário no passado). Datas devolvidas no fuso de São Paulo.

### D7. Auditoria

`CRIAR` e `CANCELAR` da reserva e nova ação `CHECK_IN`, com `ReservaSnapshot` (id, mesa_id, status, inicio, qtd_pessoas, nome_cliente). O telefone não entra na auditoria (dado pessoal desnecessário para o rastro). A comanda aberta no check-in gera seu próprio `CRIAR`.

### D8. Interface

- Nova aba **Reservas**, sempre disponível para Funcionário e Administrador: seletor de data (hoje por padrão), lista em ordem de horário com selo de situação, "Check-in" e "Cancelar" nas confirmadas, e formulário "Nova reserva" (mesa por número e capacidade, cliente, telefone, pessoas, data e hora).
- **Mapa:** mesa Reservada abre um diálogo com cliente, pessoas e horário (a partir de `GET /reservas` do dia) e o botão de check-in; mesa Livre com `proxima_reserva_inicio` mostra "Reserva às HHhMM" no cartão e pede confirmação antes de abrir a comanda.
- Check-in, pelo mapa ou pela lista, leva à tela da comanda aberta.

## Risks / Trade-offs

- [Nome e telefone de clientes em produção (LGPD)] → apenas os dados necessários, acesso restrito por perfil, telefone fora da auditoria; anonimização de reservas antigas fica como evolução registrada.
- [Mesa ocupada além do horário de uma reserva] → o mapa mantém OCUPADA (prioridade) e o check-in é recusado até a mesa liberar; a reserva continua visível na lista.
- [Abertura de comanda sem passar pela interface ignora o aviso de reserva próxima] → o aviso é de interface por decisão do grupo (permitir com aviso); a API só bloqueia dentro da janela.
- [Reservas "não compareceu" não liberam nada por si] → como a janela termina em `inicio + 30min`, a mesa já volta a Livre no mapa sem intervenção.

## Migration Plan

Sem migração de banco. Deploy pelo push na `main`. Rollback: redeploy do commit anterior; reservas criadas continuam válidas e o mapa da versão anterior já as respeita.
