# Proposal

## Why

O sistema publicado já autentica os usuários e mostra o mapa de mesas, mas ainda não permite o núcleo do atendimento: abrir uma comanda e lançar os pedidos. Hoje os garçons anotam em papel (Especificação, seção 2), e o UC 7.1 é a primeira funcionalidade que substitui esse processo. É também a base dos changes seguintes — o envio à cozinha (UC 7.2) e a pré-conta (UC 7.3) operam sobre os itens registrados aqui.

## What Changes

- Consulta do cardápio por categoria, com os produtos ativos e a indicação dos indisponíveis no momento.
- Abertura de comanda a partir de uma mesa livre, registrando o funcionário autenticado como responsável (RF01, RF10, HU01). Uma mesa ocupada retoma a comanda existente; mesas em manutenção ou reservadas não abrem comanda.
- Registro de itens com quantidade e observação (RF02, HU02), com preço unitário congelado no momento do lançamento e recusa de produtos indisponíveis ou inativos (fluxo alternativo do UC 7.1).
- Itens idênticos (mesmo produto e mesma observação) ainda pendentes somam quantidade em vez de criar nova linha.
- Manutenção dos itens (RF04): alterar quantidade e observação de itens pendentes; cancelar itens pendentes; cancelar itens já enviados à cozinha apenas por administrador (RN02). Itens nunca são excluídos — passam a CANCELADO.
- Cálculo automático do total da comanda, sem itens cancelados.
- Registro de todas essas operações na auditoria (RN05).
- Interface: clicar em uma mesa no mapa abre ou retoma a comanda; aba Comanda com cardápio, itens lançados, status de cada item e total, atualizada automaticamente.

Fora do escopo: envio à cozinha (`enviar-itens-cozinha`), pré-conta e pagamento (`pre-conta-pagamento`), check-in de reserva e aviso de reserva próxima ao abrir uma mesa livre (`reservas`), transferência (`transferencia`) e cadastro de produtos (`gestao-cardapio-usuarios`).

## Capabilities

### New Capabilities

- `cardapio`: consulta do cardápio para lançamento de pedidos (categorias, produtos ativos, preço e disponibilidade).
- `comandas`: abertura e retomada de comanda por mesa, registro e manutenção de itens, cancelamento conforme RN02 e cálculo do total.

### Modified Capabilities

(nenhuma — o mapa de mesas já calcula OCUPADA a partir da comanda ABERTA; a ação de abrir a comanda pelo mapa é especificada em `comandas`)

## Impact

- **Backend:** novos routers `/cardapio` e de comandas, serviços e repositórios de comanda e cardápio; sem migração (as tabelas `comanda`, `item_comanda` e `produto` já existem desde `estrutura-base`).
- **API:** `GET /cardapio`, `POST /mesas/{id}/comanda`, `GET /comandas/{id}`, `POST /comandas/{id}/itens`, `PATCH /comandas/{id}/itens/{item_id}`, `POST /comandas/{id}/itens/{item_id}/cancelar`; todas restritas a Funcionário e Administrador.
- **Frontend:** navegação entre Mapa de Mesas e Comanda, página da comanda com cardápio e itens.
- **Dados:** produção passa a receber comandas reais; nenhuma alteração de esquema.
