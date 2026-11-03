# Tasks

## 1. Cardápio

- [x] 1.1 Implementar `CardapioRepository`, `CardapioService` e `GET /cardapio` (categorias na ordem definida, produtos ativos em ordem alfabética, indisponíveis identificados, categorias vazias omitidas, perfis Funcionário e Administrador); testes de integração de todos os cenários da spec `cardapio`

## 2. Abertura e consulta de comanda

- [x] 2.1 Adicionar a ação `CANCELAR` e os snapshots `ComandaSnapshot` e `ItemComandaSnapshot` (D7); teste unitário garantindo que os snapshots serializam valores monetários como texto decimal
- [x] 2.2 Implementar `ComandaRepository` (comanda ativa por mesa, comanda com itens e nomes de produto, bloqueio `FOR UPDATE`) e o cálculo de status de uma única mesa reutilizando `calcular_mapa` (D2); teste de integração do status de uma mesa livre, ocupada, em manutenção e reservada
- [x] 2.3 Implementar `ComandaService.abrir` com responsável, recusas de manutenção, reserva e mesa inexistente, retomada da comanda ativa e tratamento da corrida pelo índice único (D2); testes de integração dos cenários "Mesa livre", "Identificador único", "Mesa ocupada", "Abertura simultânea", "Mesa em manutenção", "Mesa reservada" e "Mesa inexistente", incluindo a auditoria da abertura
- [x] 2.4 Implementar a montagem da comanda para resposta (itens em ordem de lançamento, subtotais e total sem cancelados) e os endpoints `POST /mesas/{id}/comanda` e `GET /comandas/{id}` (D6); testes de integração de "Comanda com itens", "Comanda inexistente", "Total com item cancelado", códigos 201/200 e "Contabilidade tenta abrir comanda"

## 3. Itens da comanda

- [x] 3.1 Implementar o registro de item com bloqueio da comanda (D3), validação de faixa, preço congelado, recusa de indisponível/inativo, comanda não aberta e soma de itens idênticos (D4); testes de integração de todos os cenários de "Registro de item na comanda", "Recusa de item indisponível" e "Itens idênticos somam quantidade", incluindo auditoria
- [x] 3.2 Implementar a alteração de item pendente e o cancelamento com a regra RN02 (D6, D7); testes de integração de todos os cenários de "Alteração de item pendente" e "Cancelamento de item", incluindo a auditoria do cancelamento
- [x] 3.3 Expor `POST /comandas/{id}/itens`, `PATCH /comandas/{id}/itens/{item_id}` e `POST /comandas/{id}/itens/{item_id}/cancelar`; testes de integração da API cobrindo resposta com a comanda atualizada, 404, 409, 403 e 422, e verificação das rotas no Swagger
- [x] 3.4 Teste de integração de concorrência: duas adições simultâneas do mesmo produto na mesma comanda resultam em um único item com a quantidade somada

## 4. Interface

- [x] 4.1 Criar os clientes `api/cardapio.ts` e `api/comandas.ts`, um componente de mensagem temporária e o estado de navegação mapa/comanda no `App`, com a aba Comanda ativa quando houver comanda na tela; verificar com `npm run build` sem erros de tipo
- [x] 4.2 Tornar os cartões do mapa clicáveis com abertura ou retomada da comanda e mensagens para mesa reservada ou em manutenção; verificar no navegador contra o backend local os cenários "Clique em mesa livre", "Clique em mesa ocupada" e "Clique em mesa reservada"
- [x] 4.3 Implementar a tela da comanda (cabeçalho com mesa, responsável e abertura; cardápio por categoria com adicionar e observação; indisponíveis desabilitados; itens com status, subtotal, − / + e cancelar; total; botões futuros desabilitados; voltar ao mapa); verificar no navegador "Adicionar produto", "Produto indisponível na tela", soma de itens idênticos, cancelamento e "Voltar ao mapa"
- [x] 4.4 Implementar o polling de 5 s da comanda e as mensagens temporárias de sucesso e erro; verificar no navegador "Atualização por outro dispositivo" (item inserido pela API) e a mensagem "Item indisponível"; verificar em largura de celular a coluna única sem rolagem horizontal

## 5. Implantação e verificação

- [x] 5.1 Rodar `pytest` completo e `npm run build` e verificar que tudo passa
- [x] 5.2 Publicar (push na `main`) e verificar na URL pública: abrir a comanda de uma mesa, registrar itens, somar idêntico, cancelar um item, conferir o total e a mesa como Ocupada no mapa; ao final, cancelar os itens e encerrar a comanda de teste diretamente no banco, deixando a mesa livre

## Workflow follow-up

- Arquivar o change após revisão do grupo (`/opsx:archive`), criando as specs `cardapio` e `comandas`.
- Próximo change: `enviar-itens-cozinha` (UC 7.2 e Painel da Cozinha).
