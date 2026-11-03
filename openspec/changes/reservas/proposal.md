# Proposal

## Why

O mapa já mostra mesas como Reservadas e bloqueia a abertura de comanda nelas, mas não há como criar, cancelar ou concluir uma reserva pelo sistema — a mensagem "aguarde o check-in do cliente" aponta para uma ação que ainda não existe. O grupo decidiu trazer as reservas, previstas como integração futura na Especificação (RNF06), para o escopo atual, mantendo os dados de contato na própria reserva, sem cadastro de cliente.

## What Changes

- Criação de reserva para uma mesa, com nome e telefone do cliente, quantidade de pessoas e horário de início; duração padrão de 2 horas, usada para recusar reservas sobrepostas na mesma mesa.
- Recusa de reserva em mesa em manutenção ou com início no passado; aviso, sem bloqueio, quando a quantidade de pessoas passa da capacidade da mesa.
- Cancelamento da reserva quando o cliente avisa que não vem, desfazendo o bloqueio da mesa.
- Situação "Não compareceu" calculada na leitura para reservas confirmadas cujo horário passou da tolerância de 30 minutos, sem tarefa agendada.
- Check-in da reserva: conclui a reserva e abre a comanda da mesa com o funcionário responsável, quando a mesa não tem comanda ativa.
- Consulta das reservas de um dia, em ordem de horário.
- Aviso ao abrir comanda em mesa livre com reserva confirmada nas próximas 2 horas (decisão do grupo: permitir com aviso).
- Auditoria de criação, cancelamento e check-in (RN05).
- Interface: aba Reservas (lista do dia, nova reserva, cancelar, check-in) e, no mapa, check-in a partir da mesa reservada e horário da próxima reserva em mesa livre.

Fora do escopo: reserva de várias mesas para um grupo, cadastro de clientes e histórico de consumo (fidelidade), lembretes ao cliente, anonimização automática de reservas antigas (registrada como risco de LGPD no design).

## Capabilities

### New Capabilities

- `reservas`: criação, consulta, cancelamento e check-in de reservas, conflito de horário e situação de não comparecimento.

### Modified Capabilities

- `mesas`: o mapa passa a informar o horário da próxima reserva das próximas 2 horas também para mesas livres.
- `comandas`: clicar em mesa reservada passa a oferecer o check-in; abrir comanda em mesa livre com reserva próxima exige confirmação do aviso.

## Impact

- **Backend:** `GET /reservas?data=`, `POST /reservas`, `POST /reservas/{id}/cancelar`, `POST /reservas/{id}/check-in`; serviço e repositório de reservas; `GET /mesas` ganha o horário da próxima reserva; o check-in reutiliza a abertura de comanda.
- **Sem migração:** a tabela `reserva` existe desde `estrutura-base` com todos os campos necessários.
- **Frontend:** nova aba Reservas, formulário de reserva, ações de cancelar e check-in, confirmações no mapa.
- **Dados pessoais:** nome e telefone de clientes passam a ser gravados em produção.
