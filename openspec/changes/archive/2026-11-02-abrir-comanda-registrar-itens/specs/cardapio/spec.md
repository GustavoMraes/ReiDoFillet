# Spec Delta

## Purpose

Disponibilizar aos funcionários o cardápio atualizado do restaurante, organizado por categoria, para o lançamento de pedidos nas comandas.

## ADDED Requirements

### Requirement: Consulta do cardápio por categoria
O sistema SHALL disponibilizar o cardápio agrupado por categoria, na ordem definida para as categorias e, dentro de cada uma, em ordem alfabética de produto, informando para cada produto: identificador, nome, descrição, preço e se está disponível no momento.

#### Scenario: Cardápio com produtos em várias categorias
- **WHEN** o cardápio é consultado e existem produtos ativos em quatro categorias
- **THEN** o sistema retorna as quatro categorias na ordem definida, cada uma com seus produtos em ordem alfabética, com nome, descrição, preço e disponibilidade

#### Scenario: Categoria sem produtos ativos
- **WHEN** uma categoria não possui nenhum produto ativo
- **THEN** essa categoria não aparece no cardápio

### Requirement: Produtos inativos não aparecem no cardápio
Produtos marcados como inativos MUST NOT aparecer no cardápio consultado para novos pedidos (HU05). Produtos ativos e indisponíveis no momento MUST aparecer, identificados como indisponíveis.

#### Scenario: Produto inativo
- **WHEN** um produto está marcado como inativo
- **THEN** ele não é retornado na consulta do cardápio

#### Scenario: Produto ativo e indisponível
- **WHEN** um produto está ativo, mas marcado como indisponível no momento
- **THEN** ele é retornado no cardápio identificado como indisponível

### Requirement: Acesso ao cardápio restrito por perfil
A consulta do cardápio MUST exigir sessão válida e MUST ser liberada apenas para os perfis Funcionário e Administrador.

#### Scenario: Funcionário consulta o cardápio
- **WHEN** um usuário com perfil Funcionário consulta o cardápio
- **THEN** o sistema retorna o cardápio

#### Scenario: Contabilidade não consulta o cardápio
- **WHEN** um usuário com perfil Contabilidade consulta o cardápio
- **THEN** a requisição é recusada como sem permissão
