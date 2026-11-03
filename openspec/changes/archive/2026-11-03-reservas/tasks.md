# Tasks

## 1. Reservas no backend

- [x] 1.1 Implementar a situação calculada (D3) e a conversão de horários (D1); testes unitários de "Cliente não apareceu" (21h01), "Ainda dentro da tolerância" (21h00), horário sem fuso interpretado em São Paulo e limites do dia na consulta por data
- [x] 1.2 Implementar `ReservaRepository`, `ReservaService.criar` com bloqueio da mesa e verificação de sobreposição (D2), validações e aviso de capacidade, `ReservaSnapshot` e `POST /reservas`; testes de integração de todos os cenários de "Criação de reserva", "Reservas sobrepostas na mesma mesa" (incluindo "Reservas simultâneas" com sessões concorrentes) e "Restrições da mesa na reserva", com auditoria
- [x] 1.3 Implementar `GET /reservas` (de hoje em diante) e `GET /reservas?data=` e `POST /reservas/{id}/cancelar`; testes de integração de "Reservas de hoje", "Cliente avisa que não vem" (mesa volta a Livre no mapa), "Reserva já concluída", auditoria do cancelamento e "Contabilidade consulta reservas"

## 2. Check-in e mapa

- [x] 2.1 Extrair a criação de comanda para uso dentro de transação e implementar `ReservaService.check_in` com a ação `CHECK_IN` e `POST /reservas/{id}/check-in` (D4); testes de integração de "Cliente chega no horário", check-in antecipado e atrasado, "Mesa ainda ocupada", mesa em manutenção, "Reserva não confirmada" e de que a abertura comum de comanda continua com todos os testes passando
- [x] 2.2 Ampliar a busca do mapa e preencher `proxima_reserva_inicio` (D5); testes unitários de "Mesa livre com reserva próxima" e "Reserva distante não aparece", teste de integração do campo no `GET /mesas` e de que o mapa continua com no máximo três consultas; verificar as novas rotas no Swagger

## 3. Interface

- [x] 3.1 Criar `api/reservas.ts`, adicionar a aba Reservas à navegação e o tipo `proxima_reserva_inicio` no mapa; verificar com `npm run build` sem erros de tipo
- [x] 3.2 Implementar a página Reservas (lista de hoje em diante agrupada por dia, filtro por data, situação, nova reserva, cancelar, check-in levando à comanda); verificar no navegador contra o backend local "Nova reserva pela tela", conflito de horário, aviso de capacidade, cancelamento e "Check-in pela tela"
- [x] 3.3 No mapa, implementar o diálogo de check-in da mesa reservada e o aviso de reserva próxima em mesa livre (cartão e confirmação); verificar no navegador "Clique em mesa reservada", "Mesa livre com reserva próxima" (confirmar e desistir) e, em largura de celular, a aba Reservas sem rolagem horizontal

## 4. Implantação e verificação

- [x] 4.1 Rodar `pytest` completo e `npm run build` e verificar que tudo passa
- [x] 4.2 Publicar (push na `main`) e verificar na URL pública: criar uma reserva para dentro de 20 minutos e confirmar a mesa Reservada no mapa, fazer o check-in pelo mapa, criar outra e cancelar; ao final, encerrar pelo próprio sistema a comanda aberta no check-in

## Workflow follow-up

- Arquivar o change após revisão do grupo (`/opsx:archive`), criando a spec `reservas` e aplicando as deltas de `mesas` e `comandas`.
- Próximos changes: `transferencia`, `gestao-cardapio-usuarios`, `relatorios`.
