# Design

## Context

Motivação em `proposal.md`. Estado atual relevante:

- `item_comanda` já tem `enviado_em`, `pronto_em` e `entregue_em`; o enum de status já tem EM_PREPARO, PRONTO e ENTREGUE. Nenhuma migração é necessária.
- `ComandaService` concentra as regras de item e usa `SELECT ... FOR UPDATE` na comanda (`obter_para_atualizar`) para serializar operações na mesma comanda; o cancelamento por administrador de item enviado (RN02) já existe.
- A tela da comanda já exibe o status de cada item e atualiza por polling de 5 s; o botão "Enviar itens para a cozinha" existe, desabilitado.
- O `App` navega entre Mapa e Comanda por estado, sem biblioteca de rotas.

## Goals / Non-Goals

**Goals:**
- Um protocolo de bloqueio único para tudo que muda itens: sempre a linha da comanda primeiro.
- Painel da cozinha legível à distância em um tablet, com ação de um toque por item.
- Cupom imprimível sem dependência de impressora específica.

**Non-Goals:**
- Alertas de tempo de espera, separação cozinha/bar, reimpressão de cupons antigos e tempo médio (UC 7.6).

## Decisions

### D1. Envio em lote no `ComandaService`

`enviar(comanda_id, usuario)` bloqueia a comanda, exige status ABERTA, seleciona os itens PENDENTES e, se houver, muda todos para EM_PREPARO com um único `enviado_em = relogio.agora()`. O mesmo instante identifica o lote: é o que permite montar o cupom e, no futuro, reimprimir um envio. Sem pendentes, 409 "Não há itens pendentes para enviar".

O bloqueio da comanda faz o segundo de dois envios simultâneos esperar o primeiro terminar e então não encontrar pendentes — nenhum item é enviado duas vezes.

### D2. Cupom calculado na resposta, não persistido

`POST /comandas/{id}/enviar` devolve `{comanda, cupom}`, com `cupom = {mesa_numero, garcom, enviado_em, itens: [{quantidade, produto_nome, observacao}]}`, onde `garcom` é quem enviou. Não há tabela de cupom: o lote é recuperável pelos itens com o mesmo `enviado_em`.

Alternativa considerada: entidade Cupom. Descartada por não haver impressão real nem reimpressão no escopo.

### D3. Mudanças de estágio na cozinha com o mesmo bloqueio

`CozinhaService.marcar_pronto/marcar_entregue(item_id, usuario)` carrega o item, bloqueia a comanda dele com `obter_para_atualizar`, recarrega o item e só então valida o status. Assim, "marcar pronto" e o cancelamento por administrador nunca se cruzam: quem chegar depois vê o status final do outro. Dois toques simultâneos em "pronto" resultam em um sucesso e um 409.

A comanda precisa estar ativa (ABERTA ou PRE_CONTA): itens continuam sendo preparados e entregues durante a pré-conta.

### D4. Consulta do painel

`GET /cozinha` devolve `{em_preparo: [...], pronto: [...]}`, cada item com `{id, comanda_id, mesa_numero, quantidade, produto_nome, observacao, enviado_em, minutos_desde_envio}`, em ordem de `enviado_em` e `id`. Uma única consulta com junção de item, comanda, mesa e produto, filtrando por status do item. Os minutos são calculados no servidor com o relógio injetável, como no mapa de mesas.

`POST /cozinha/itens/{id}/pronto` e `.../entregue` devolvem o painel atualizado, para a tela trocar o item de coluna em uma ida ao servidor.

### D5. Auditoria

Novas ações `ENVIAR`, `PRONTO` e `ENTREGAR`, cada uma com `ItemComandaSnapshot` antes e depois (um registro por item no envio).

### D6. Interface

- **Navegação:** o `App` ganha a tela Cozinha. A aba Cozinha fica sempre disponível para Funcionário e Administrador; a aba Comanda fica disponível quando alguma comanda foi aberta na sessão (o `App` lembra a última). Pagamento continua desabilitado.
- **Envio:** o botão fica habilitado quando há item PENDENTE. Após o envio, a comanda é atualizada com a resposta e o cupom abre em uma sobreposição com "Imprimir" e "Fechar".
- **Impressão:** `window.print()` com uma folha de estilo `@media print` que esconde a aplicação e mostra só o cupom, em coluna estreita (cerca de 80 mm), compatível com impressoras térmicas instaladas no sistema operacional. Sem integração direta com impressora (decisão do grupo).
- **Painel:** duas colunas (Em preparo, Pronto) com contagem, cartões com mesa em destaque, quantidade × produto, observação e "há N min"; botão de ação em cada cartão; uma coluna em telas estreitas; polling de 5 s; mensagens temporárias.

## Risks / Trade-offs

- [Impressão depende da configuração do navegador e da impressora] → a tela do cupom é legível também sem imprimir; a impressão é opcional e o envio não depende dela.
- [Painel sem distinção cozinha/bar] → um único painel atende o restaurante; separação fica para evolução.
- [Polling de 5 s em tablets da cozinha durante todo o turno] → consulta única e indexada por status; volume pequeno.
- [Um toque errado em "Marcar como entregue" não tem desfazer] → a auditoria registra quem fez; correção por administrador fica para evolução, se necessária.

## Migration Plan

Sem migração de banco. Deploy pelo push na `main` (Render e Vercel). Rollback: redeploy do commit anterior; itens já enviados continuam válidos e aparecem com seu status na tela da comanda.
