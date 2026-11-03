# Design

## Context

Motivação em `proposal.md`. Estado atual relevante:

- `comanda` já tem `pre_conta_em`, `fechada_em`, `taxa_servico_pct` (nulo até a primeira pré-conta) e `taxa_servico_aplicada`; `pagamento` tem forma, valor, responsável e horário; `parametro('taxa_servico_padrao') = '10.00'` vem do seed. Nenhuma migração é necessária.
- O índice único parcial considera ABERTA e PRE_CONTA como "ativa", e o mapa de mesas já calcula AGUARDANDO_PAGAMENTO a partir de PRE_CONTA; FECHADA e CANCELADA já liberam a mesa.
- `ComandaService` concentra as regras de comanda e item, com o bloqueio `obter_para_atualizar` (FOR UPDATE) na comanda; `_comanda_aberta_bloqueada` hoje exige ABERTA.
- `detalhar` monta `ComandaOut` com itens e total; a cozinha (`CozinhaService`) já aceita comandas em PRE_CONTA.
- O cupom do envio já usa uma tela sobreposta com `@media print`.

## Goals / Non-Goals

**Goals:**
- Dinheiro sempre em `Decimal`, com uma única regra de arredondamento.
- Todas as operações de pagamento sob o mesmo bloqueio da comanda, para que pagamentos simultâneos não ultrapassem o total.
- Fechamento sem passo manual: a comanda fecha no pagamento que quita o total.

**Non-Goals:**
- RN03 (alteração de comanda fechada por administrador), troco, desconto/cortesia, nota fiscal, integração com maquininha.

## Decisions

### D1. Cálculo financeiro centralizado

Uma função pura calcula, a partir dos itens, da comanda e dos pagamentos: `subtotal` (itens não cancelados), `taxa` (`subtotal × pct / 100`, só em PRE_CONTA ou FECHADA com taxa aplicada), `total`, `pago` e `restante`. Arredondamento `ROUND_HALF_UP` para centavos, aplicado na taxa (o subtotal já é exato). É usada tanto em `detalhar` quanto nas validações de pagamento e de taxa, garantindo que a tela e as regras usem os mesmos números.

### D2. Estados da comanda

```
ABERTA --pré-conta--> PRE_CONTA --pagamentos = total--> FECHADA
  ^                       |
  +---- item incluído / alterado / cancelado (retrato invalidado)
ABERTA ou PRE_CONTA, sem itens ativos e sem pagamentos --cancelar--> CANCELADA
```

- `_comanda_aberta_bloqueada` passa a aceitar ABERTA ou PRE_CONTA nas operações de item; quando a comanda estava em PRE_CONTA, o mesmo serviço a devolve para ABERTA e zera `pre_conta_em`, na mesma transação.
- O envio à cozinha continua exigindo ABERTA (sem mudança): incluir um item na pré-conta já devolve a comanda para ABERTA, permitindo o envio em seguida.
- Na pré-conta, `taxa_servico_pct` só é preenchido se ainda for nulo (primeira pré-conta), lendo o parâmetro; nas seguintes, a escolha anterior é mantida.

### D3. Pagamentos sob o bloqueio da comanda

Registrar e remover pagamento e alterar a taxa bloqueiam a comanda (`FOR UPDATE`), recalculam com D1 e validam: valor > 0, valor ≤ restante, taxa nova não deixa o total abaixo do pago. Se o pagamento zera o restante, a comanda passa a FECHADA com `fechada_em` na mesma transação. Dois garçons registrando ao mesmo tempo são serializados: o segundo vê o restante atualizado.

A remoção é uma exclusão física do `pagamento`, permitida só em PRE_CONTA, com o pagamento completo registrado em `dados_antes` da auditoria (RN05). Alternativa considerada: status "estornado" no pagamento — descartada por exigir migração e por não haver estorno real (o dinheiro nunca passou pelo sistema).

### D4. Contrato da API

| Rota | Corpo | Resposta |
|---|---|---|
| `POST /comandas/{id}/pre-conta` | — | `{comanda, aviso}` (`aviso` nulo ou o texto sobre itens não entregues) |
| `PATCH /comandas/{id}/taxa-servico` | `{aplicada?, percentual?}` | comanda |
| `POST /comandas/{id}/pagamentos` | `{forma, valor}` | comanda (com status FECHADA quando quitada) |
| `DELETE /comandas/{id}/pagamentos/{pagamento_id}` | — | comanda |
| `POST /comandas/{id}/cancelar` | — | comanda |

`ComandaOut` ganha `subtotal`, `taxa_servico: {aplicada, percentual, valor}`, `pago`, `restante`, `pre_conta_em` e `pagamentos: [{id, forma, valor, registrado_por, registrado_em}]`; `total` passa a incluir a taxa (D1). Valores monetários seguem como texto decimal. Erros no formato `{"detalhe": ...}`: 409 para estado (comanda fora do status exigido, valor acima do restante, taxa abaixo do pago, comanda com itens ou pagamentos), 422 para valor ≤ 0 ou percentual fora de 0–100, 404 para pagamento inexistente.

### D5. Auditoria

Novas ações `PRE_CONTA`, `PAGAR` e `REMOVER_PAGAMENTO`; alteração de taxa usa `ALTERAR` com `ComandaSnapshot` estendido (status, `taxa_servico_pct`, `taxa_servico_aplicada`); cancelamento de comanda usa `CANCELAR`; fechamento e retorno a ABERTA são registrados como `ALTERAR` da comanda. Novo `PagamentoSnapshot` (id, comanda_id, forma, valor, registrado_por_id).

### D6. Interface

- **Comanda:** "Gerar pré-conta" (com itens não cancelados) e "Cancelar comanda" (sem itens ativos). Em PRE_CONTA, uma faixa indica "Aguardando pagamento" com o botão "Ir para o pagamento".
- **Pré-conta imprimível:** sobreposição no mesmo padrão do cupom, reaproveitando a regra `@media print` (generalizada para uma classe comum `.impressao`), com mesa, garçom, itens com quantidade e subtotal, subtotal, taxa e total.
- **Pagamento:** aba Pagamento disponível quando a comanda aberta na tela está em PRE_CONTA. Duas colunas como no Projeto de Interface: resumo à esquerda (itens, subtotal, taxa com liga/desliga e percentual, total, pago, restante, pagamentos com remover) e forma de pagamento à direita (quatro botões, valor iniciando no restante, "Confirmar pagamento" desabilitado sem forma escolhida, "Voltar para a comanda").
- Ao quitar, mensagem "Pagamento em <forma> registrado. Mesa <n> liberada." e volta ao Mapa de Mesas; a aba Comanda deixa de estar disponível.

## Risks / Trade-offs

- [Remoção física de pagamento] → o registro completo fica na auditoria imutável; só é possível antes do fechamento.
- [Fechamento automático no pagamento exato] → evita um passo esquecido; o garçom confere o restante antes de confirmar, e a tela mostra o valor que será registrado.
- [Itens podem continuar EM_PREPARO/PRONTO depois do fechamento] → a pré-conta avisa; itens de comanda fechada deixam de poder avançar na cozinha (regra já existente: comanda precisa estar ativa) e continuam no painel até serem cancelados por um administrador — limitação documentada; a cozinha costuma entregar antes da conta.
- [`total` muda de significado na API] → na comanda ABERTA o valor é idêntico; só muda em PRE_CONTA, estado que não existia antes.

## Migration Plan

Sem migração de banco. Deploy pelo push na `main` (Render e Vercel). Rollback: redeploy do commit anterior; comandas em PRE_CONTA continuam válidas e aparecem como Aguardando pagamento no mapa da versão anterior.

## Open Questions

- Itens EM_PREPARO/PRONTO de comandas fechadas: avaliar com o grupo se o fechamento deve marcá-los como entregues automaticamente. A decisão não muda as specs deste change (a pré-conta já avisa) e pode entrar em um change futuro.
