# Tasks

## 1. Cálculo financeiro e resposta da comanda

- [x] 1.1 Implementar a função de cálculo financeiro (subtotal, taxa com `ROUND_HALF_UP`, total, pago, restante) e estender `ComandaOut` com subtotal, taxa de serviço, pago, restante, `pre_conta_em` e pagamentos (D1, D4); testes unitários do cálculo, incluindo "Total com taxa de serviço" (R$ 33,90 → taxa R$ 3,39, total R$ 37,29), comanda ABERTA sem taxa e taxa desligada, e teste de integração de "Resumo financeiro da comanda"

## 2. Pré-conta e ciclo da comanda

- [x] 2.1 Adicionar as ações `PRE_CONTA`, `PAGAR` e `REMOVER_PAGAMENTO`, estender `ComandaSnapshot` e criar `PagamentoSnapshot` (D5); implementar `ComandaService.gerar_pre_conta` com cópia da taxa padrão só na primeira pré-conta e aviso de itens não entregues (D2), e `POST /comandas/{id}/pre-conta`; testes de integração de todos os cenários de "Geração da pré-conta", "Taxa padrão na pré-conta" e "Nova pré-conta mantém a escolha"
- [x] 2.2 Permitir incluir, alterar e cancelar itens em PRE_CONTA devolvendo a comanda para ABERTA na mesma transação (D2); testes de integração de "Alteração devolve a comanda para ABERTA", do cenário modificado "Comanda que não está aberta" (FECHADA/CANCELADA), de "Taxa não se aplica a comanda aberta" e de que o envio à cozinha continua exigindo ABERTA
- [x] 2.3 Implementar `cancelar_comanda` e `POST /comandas/{id}/cancelar`; testes de integração de todos os cenários de "Cancelamento de comanda sem itens ativos", incluindo a mesa Livre no mapa e a auditoria

## 3. Taxa de serviço e pagamentos

- [x] 3.1 Implementar `alterar_taxa_servico` e `PATCH /comandas/{id}/taxa-servico` com bloqueio e validações (D3); testes de integração de "Cliente recusa a taxa", "Percentual ajustado", "Percentual inválido", "Taxa abaixo do já pago" e "Comanda fora da pré-conta"
- [x] 3.2 Implementar `registrar_pagamento` com fechamento automático e `POST /comandas/{id}/pagamentos` (D3); testes de integração de todos os cenários de "Registro de pagamento" e "Fechamento ao quitar o total", da auditoria e do acesso por perfil, e teste de concorrência em que dois pagamentos simultâneos não ultrapassam o total
- [x] 3.3 Implementar `remover_pagamento` e `DELETE /comandas/{id}/pagamentos/{pagamento_id}`; testes de integração de "Remover pagamento parcial" (com auditoria contendo o pagamento removido), "Comanda já fechada" e pagamento inexistente; verificar as novas rotas no Swagger

## 4. Interface

- [x] 4.1 Criar as funções de API, generalizar a regra de impressão para uma classe comum e adicionar a aba Pagamento à navegação (disponível com a comanda em PRE_CONTA); verificar com `npm run build` sem erros de tipo
- [x] 4.2 Na tela da comanda, implementar "Gerar pré-conta", aviso de itens não entregues, pré-conta imprimível, faixa "Aguardando pagamento" com acesso ao pagamento e "Cancelar comanda"; verificar no navegador contra o backend local "Pré-conta imprimível" (incluindo a visualização de impressão), "Ir para o pagamento", "Mesa aberta por engano" e o retorno a ABERTA ao incluir item
- [x] 4.3 Implementar a tela de Pagamento (resumo, controle da taxa, formas, valor, lista com remover, confirmar, voltar); verificar no navegador "Forma não escolhida", pagamento parcial, remoção, "Quitação pela tela" (mapa com a mesa Livre), "Voltar para a comanda" e, em largura de celular, coluna única sem rolagem horizontal

## 5. Implantação e verificação

- [x] 5.1 Rodar `pytest` completo e `npm run build` e verificar que tudo passa
- [x] 5.2 Publicar (push na `main`) e verificar na URL pública o ciclo completo: abrir comanda, lançar e enviar itens, marcar entregues, gerar e imprimir a pré-conta, desligar e religar a taxa, pagar em duas formas e confirmar a mesa Livre; verificar também o cancelamento de uma comanda vazia

## Workflow follow-up

- Arquivar o change após revisão do grupo (`/opsx:archive`), criando a spec `pagamentos` e aplicando a delta de `comandas`.
- Discutir com o grupo a questão aberta do design (itens não entregues em comanda fechada).
- Próximos changes: `reservas`, `transferencia`, `gestao-cardapio-usuarios`, `relatorios`.
