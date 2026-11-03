# Design

## Context

Motivação em `proposal.md`. Estado atual relevante:

- As tabelas `comanda` e `item_comanda` existem desde `estrutura-base`, com o índice único parcial que garante uma comanda ativa (ABERTA ou PRE_CONTA) por mesa, `preco_unitario` no item e os campos de cancelamento.
- `MesaService.calcular_mapa` já calcula o status da mesa (manutenção, comanda ativa e janela de reserva) a partir de três consultas.
- `exigir_perfis`, `AuditoriaService` e `transacao()` já são o padrão de autorização, auditoria e unidade de trabalho.
- O frontend não usa biblioteca de rotas: o `App` escolhe a tela a partir do estado de autenticação.

## Goals / Non-Goals

**Goals:**
- Regras de comanda e item concentradas em um único serviço, que os changes de cozinha e pré-conta vão estender.
- Comportamento correto sob concorrência: dois garçons na mesma mesa ou na mesma comanda.
- Tela da comanda usável em tablet, alinhada ao Projeto de Interface.

**Non-Goals:**
- Envio à cozinha, pré-conta, pagamento, transferência, reservas e cadastro de produtos (outros changes).
- Lista de comandas ativas (RF20) — o mapa de mesas cumpre esse papel por enquanto.

## Decisions

### D1. Cada item é gravado no momento em que é adicionado

O UC 7.1 descreve "selecionar itens" e depois "confirmar os itens". Aqui cada adição já é persistida como PENDENTE, e a confirmação para a cozinha é a ação "Enviar itens para a cozinha" do change `enviar-itens-cozinha`. Assim nada se perde se o tablet fechar, outros dispositivos veem os itens e a tela segue o Projeto de Interface, em que o item entra na comanda ao ser selecionado.

Alternativa considerada: carrinho local com envio em lote. Descartada pela perda de dados ao fechar a aba e pela divergência entre dispositivos.

### D2. Abertura idempotente por mesa

`POST /mesas/{id}/comanda` devolve **201** com a comanda criada ou **200** com a comanda ativa já existente. A verificação de manutenção e reserva reutiliza `calcular_mapa` para uma única mesa, garantindo que o mapa e a abertura usem exatamente a mesma regra e o mesmo relógio.

Na corrida de duas aberturas simultâneas, o índice único parcial recusa a segunda inserção; o serviço captura o erro de integridade, desfaz a transação e devolve a comanda ativa (200). Nenhuma auditoria é gravada para a tentativa que perdeu a corrida.

### D3. Bloqueio da linha da comanda nas operações de item

Registrar, alterar e cancelar item começam com `SELECT ... FOR UPDATE` na comanda. Isso serializa as operações na mesma comanda: duas adições simultâneas do mesmo produto somam na mesma linha em vez de criar duas, e a verificação "comanda ABERTA" não muda no meio da operação. O change `enviar-itens-cozinha` usará o mesmo bloqueio.

### D4. Identidade de item para somar quantidade

Dois lançamentos somam quando coincidem: produto, observação normalizada (sem espaços nas pontas, comparação sem diferenciar maiúsculas e minúsculas), preço unitário e status PENDENTE. A observação é gravada como digitada, apenas sem os espaços nas pontas. O preço entra na identidade para que uma mudança de preço entre dois lançamentos não misture valores na mesma linha.

### D5. Total calculado, não armazenado

O total é somado em `Decimal` a partir dos itens não cancelados a cada consulta, como o status da mesa. Valores monetários trafegam na API como texto decimal (`"14.00"`), padrão do Pydantic para `Decimal`, e o frontend formata em reais com `Intl.NumberFormat`.

### D6. Contrato da API

| Rota | Resposta |
|---|---|
| `GET /cardapio` | categorias com produtos ativos `{id, nome, descricao, preco, disponivel}` |
| `POST /mesas/{id}/comanda` | comanda (201 criada, 200 existente) |
| `GET /comandas/{id}` | comanda |
| `POST /comandas/{id}/itens` `{produto_id, quantidade, observacao}` | comanda atualizada |
| `PATCH /comandas/{id}/itens/{item_id}` `{quantidade?, observacao?}` | comanda atualizada |
| `POST /comandas/{id}/itens/{item_id}/cancelar` | comanda atualizada |

A comanda é `{id, mesa: {id, numero}, responsavel: {id, nome}, status, aberta_em, itens: [{id, produto_id, produto_nome, quantidade, observacao, preco_unitario, subtotal, status}], total}`. As operações de item devolvem a comanda inteira, para a tela atualizar em uma única ida ao servidor.

Erros seguem o formato `{"detalhe": ...}`: 404 para mesa, comanda ou item inexistente; 409 para conflito de estado (mesa em manutenção ou reservada, comanda não aberta, item não pendente, item já cancelado, item indisponível, soma acima de 99); 403 para RN02; 422 para quantidade fora de 1–99 ou observação acima de 200 caracteres.

Cancelar é um `POST` em sub-recurso, e não `DELETE`, porque o item não é excluído (D7 da `estrutura-base`).

### D7. Auditoria

Snapshots explícitos novos: `ComandaSnapshot` (id, mesa_id, funcionario_id, status) e `ItemComandaSnapshot` (id, comanda_id, produto_id, quantidade, observacao, preco_unitario, status, cancelado_por_id). Nova ação `CANCELAR`. Abertura grava `CRIAR` da comanda; registro de item grava `CRIAR` do item ou `ALTERAR` quando soma em item existente; alteração grava `ALTERAR`; cancelamento grava `CANCELAR`.

### D8. Interface

- O `App` passa a ter um estado de navegação: mapa ou comanda (com o id). Sem biblioteca de rotas, mantendo o padrão atual; recarregar a página volta ao mapa.
- Os cartões do mapa viram botões. Clique em Livre, Ocupada ou Aguardando pagamento chama a abertura e navega; em Manutenção ou Reservada mostra a mensagem do servidor (o mesmo texto da API) sem navegar.
- A aba Comanda fica ativa enquanto uma comanda está aberta na tela; Cozinha e Pagamento continuam desabilitadas.
- Tela da comanda em duas colunas (cardápio à esquerda, comanda à direita; uma coluna no celular), seguindo o Projeto de Interface. Cada produto tem o botão de adicionar uma unidade e um campo opcional de observação; cada item pendente tem − / + e cancelar; itens enviados mostram o status.
- Os botões "Enviar itens para a cozinha" e "Gerar pré-conta" aparecem desabilitados, indicando que chegam nos próximos changes.
- Polling de 5 s na comanda (como no mapa); o cardápio é carregado ao abrir a tela e recarregado após um "Item indisponível".
- Mensagens temporárias (toast) confirmam cada ação ou mostram o erro do servidor.

## Risks / Trade-offs

- [Dois polls por tablet a cada 5 s (mapa ou comanda)] → só uma tela fica aberta por vez; consultas indexadas e volume de um restaurante.
- [O `FOR UPDATE` serializa operações na mesma comanda] → operações curtas; disputa só entre garçons da mesma mesa.
- [Itens adicionados por engano ficam no histórico como CANCELADO] → intencional (RN05); o total e a tela da cozinha ignoram cancelados.
- [Recarregar a página volta ao mapa] → a comanda continua acessível com um clique na mesa ocupada.
- [Mesa livre perto do horário de uma reserva abre comanda sem aviso] → o aviso decidido pelo grupo entra no change `reservas`.

## Migration Plan

Sem migração de banco. Deploy pelo push na `main` (Render e Vercel). Rollback: redeploy do commit anterior; comandas criadas permanecem válidas para a versão anterior, que só as exibe no mapa.
