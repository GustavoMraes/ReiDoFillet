# Tasks

## 1. Transferência no backend

- [x] 1.1 Implementar `ComandaService.transferir` (D1, D2, D3), a ação `TRANSFERIR` com `ComandaSnapshot` (D5) e `POST /comandas/{id}/transferir` com `TransferenciaIn` (D4); testes de integração de "Cliente troca de mesa" (mapa com origem Livre e destino Ocupada, itens e status preservados), "Transferência com pré-conta e pagamento parcial" (destino Aguardando pagamento, total e restante iguais), "Cozinha mostra a nova mesa" e "Transferência auditada"
- [x] 1.2 Testes de integração das recusas sem alteração: mesma mesa, "Destino ocupado", destino aguardando pagamento, "Destino reservado", mesa em manutenção, mesa inexistente, "Comanda encerrada" (fechada e cancelada), comanda inexistente, "Contabilidade não transfere" e transferência para mesa livre com reserva próxima aceita
- [x] 1.3 Testes de concorrência com sessões próprias: "Transferências simultâneas para a mesma mesa" (uma conclui, a outra recebe 409) e transferência disputando com a abertura comum de comanda no destino (uma comanda ativa no destino, a outra operação recusada); rodar a suíte completa de comandas sem regressões

## 2. Interface

- [x] 2.1 Adicionar `transferirComanda` em `api/comandas.ts` e, na página da comanda, o botão "Trocar de mesa" (ABERTA ou PRE_CONTA) com o diálogo de mesas livres, aviso de reserva próxima e confirmação (D6); verificar com `npm run build` sem erros de tipo
- [x] 2.2 Verificar no navegador contra o backend local: "Troca de mesa pela tela" (título e mensagem), o mapa com origem Livre e destino Ocupada, o painel da cozinha com o novo número, a troca em pré-conta, o aviso de reserva próxima, "Nenhuma mesa livre" e o erro quando o destino é ocupado por outro dispositivo antes da confirmação; conferir em largura de celular sem rolagem horizontal

## 3. Implantação e verificação

- [x] 3.1 Rodar `pytest` completo e `npm run build` e verificar que tudo passa
- [x] 3.2 Publicar (push na `main`) e verificar na URL pública: abrir uma comanda, lançar e enviar um item, trocar de mesa, conferir mapa e cozinha e, ao final, encerrar pelo próprio sistema a comanda de teste

## Workflow follow-up

- Arquivar o change após revisão do grupo (`/opsx:archive`), aplicando a delta de `comandas`.
- Próximos changes: `gestao-cardapio-usuarios`, `relatorios`.
