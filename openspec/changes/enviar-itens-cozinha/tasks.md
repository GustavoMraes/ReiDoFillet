# Tasks

## 1. Envio à cozinha

- [x] 1.1 Adicionar as ações `ENVIAR`, `PRONTO` e `ENTREGAR` e implementar `ComandaService.enviar` com bloqueio da comanda, lote com um único horário de envio e montagem do cupom (D1, D2, D5); testes de integração de "Envio de itens pendentes", "Nada a enviar", "Comanda que não está aberta", "Cupom após o envio" e "Envio auditado"
- [x] 1.2 Expor `POST /comandas/{id}/enviar` (perfis Funcionário e Administrador) devolvendo comanda e cupom; testes de integração da API (200, 404, 409, 403) e de "Envios simultâneos" com sessões concorrentes, confirmando que cada item é enviado uma única vez

## 2. Painel da cozinha

- [x] 2.1 Implementar `CozinhaRepository`, `CozinhaService.painel` e `GET /cozinha` (D4); testes de integração de "Itens em estágios diferentes", "Itens que não pertencem à fila", "Tempo desde o envio" e "Contabilidade consulta o painel"
- [x] 2.2 Implementar `marcar_pronto` e `marcar_entregue` com o bloqueio da comanda (D3) e os endpoints `POST /cozinha/itens/{id}/pronto` e `.../entregue`; testes de integração de todos os cenários de "Marcar item como pronto", "Marcar item como entregue", "Item cancelado deixa a fila" e "Auditoria das mudanças de estágio", e verificação das rotas no Swagger

## 3. Interface

- [x] 3.1 Criar `api/cozinha.ts` e `enviarComanda` em `api/comandas.ts`, e a navegação com a tela Cozinha e a lembrança da última comanda no `App` (D6); verificar com `npm run build` sem erros de tipo
- [x] 3.2 Habilitar o envio na tela da comanda e criar a sobreposição do cupom com impressão (`@media print`); verificar no navegador contra o backend local "Botão sem itens pendentes", "Envio pela tela", o conteúdo do cupom e a visualização de impressão contendo só o cupom
- [x] 3.3 Implementar a página Cozinha (colunas com contagem, cartões, ações, estado vazio, polling e mensagens); verificar no navegador "Itens recém-enviados", "Marcar pela tela", entrega saindo do painel, "Painel vazio" e, em largura de celular, coluna única sem rolagem horizontal

## 4. Implantação e verificação

- [x] 4.1 Rodar `pytest` completo e `npm run build` e verificar que tudo passa
- [x] 4.2 Publicar (push na `main`) e verificar na URL pública: abrir uma comanda, enviar itens, imprimir (visualizar) o cupom, marcar pronto e entregue no painel e conferir os status na comanda; ao final, encerrar a comanda de teste diretamente no banco, deixando a mesa livre

## Workflow follow-up

- Arquivar o change após revisão do grupo (`/opsx:archive`), criando a spec `cozinha` e aplicando a delta de `comandas`.
- Próximo change: `pre-conta-pagamento` (UC 7.3 e 7.4).
