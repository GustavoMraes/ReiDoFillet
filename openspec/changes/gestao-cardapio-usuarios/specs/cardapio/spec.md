# Spec Delta

## ADDED Requirements

### Requirement: Cadastro de produto
O administrador SHALL cadastrar e editar produtos com nome (obrigatório, até 100 caracteres, único sem diferenciar maiúsculas), descrição opcional (até 300 caracteres), preço (maior que zero e até R$ 99.999,99, com no máximo duas casas decimais) e categoria existente. Produto novo MUST nascer ativo e disponível.

#### Scenario: Novo prato
- **WHEN** o administrador cadastra "Filet à Parmegiana" na categoria Pratos por R$ 79,90
- **THEN** o produto passa a aparecer no cardápio dos funcionários, ativo e disponível

#### Scenario: Preço inválido
- **WHEN** o administrador informa preço zero, negativo ou com mais de duas casas decimais
- **THEN** o produto não é salvo e o sistema informa "Informe um preço maior que zero, com até duas casas decimais"

#### Scenario: Nome repetido
- **WHEN** o administrador cadastra um produto com o nome de outro já existente
- **THEN** nada é salvo e o sistema informa "Já existe um produto com este nome"

### Requirement: Mudança de preço não altera comandas
A alteração do preço de um produto MUST valer apenas para itens lançados depois dela; itens já registrados em comandas MUST manter o preço do momento do lançamento.

#### Scenario: Aumento de preço com comanda aberta
- **WHEN** uma comanda aberta tem "Filet Mignon 300g" a R$ 89,90 e o administrador muda o preço para R$ 95,00
- **THEN** o item já lançado continua a R$ 89,90 e um novo lançamento do produto sai a R$ 95,00

### Requirement: Ativação e desativação de produto
O administrador SHALL desativar e reativar produtos. Produto desativado MUST sair do cardápio de novos pedidos, mas itens já lançados com ele MUST continuar nas comandas e no histórico; produtos MUST NOT ser apagados.

#### Scenario: Prato retirado do cardápio
- **WHEN** o administrador desativa um produto que está em uma comanda aberta
- **THEN** o produto deixa de aparecer para novos pedidos e o item já lançado continua na comanda

### Requirement: Produto esgotado no dia
Funcionários e administradores SHALL marcar um produto ativo como indisponível (esgotado) ou disponível novamente. A mudança MUST valer para novos lançamentos a partir da próxima atualização do cardápio, sem alterar itens já lançados.

#### Scenario: Acabou o petit gâteau
- **WHEN** um funcionário marca "Petit Gâteau" como indisponível
- **THEN** o produto aparece no cardápio identificado como "Indisponível" e não pode ser adicionado a comandas até ser marcado como disponível

### Requirement: Gestão de categorias
O administrador SHALL criar e renomear categorias (nome obrigatório, até 50 caracteres, único sem diferenciar maiúsculas) e definir a ordem em que aparecem no cardápio. Uma categoria MUST só poder ser excluída quando não tiver nenhum produto, ativo ou inativo.

#### Scenario: Nova categoria
- **WHEN** o administrador cria a categoria "Porções" e a coloca antes de "Sobremesas"
- **THEN** os produtos de "Porções" aparecem no cardápio antes dos de "Sobremesas"

#### Scenario: Categoria com produtos
- **WHEN** o administrador tenta excluir uma categoria que tem produtos
- **THEN** a categoria não é excluída e o sistema informa "Mova os produtos para outra categoria antes de excluí-la"

### Requirement: Auditoria da gestão do cardápio
Cadastro, alteração, ativação, desativação e mudança de disponibilidade de produtos e criação, alteração e exclusão de categorias MUST gerar registros de auditoria com o usuário responsável e os dados antes e depois.

#### Scenario: Mudança de preço auditada
- **WHEN** o administrador altera o preço de um produto
- **THEN** é gravado um registro de auditoria com o administrador e o produto com o preço antigo e o novo

### Requirement: Acesso à gestão do cardápio restrito por perfil
O cadastro e a edição de produtos e categorias, inclusive ativação, MUST ser liberados apenas para o perfil Administrador. A mudança de disponibilidade MUST ser liberada para Funcionário e Administrador. Contabilidade MUST NOT acessar nenhuma dessas funções.

#### Scenario: Funcionário tenta mudar preço
- **WHEN** um usuário com perfil Funcionário tenta alterar o preço de um produto
- **THEN** a requisição é recusada como sem permissão

#### Scenario: Funcionário marca esgotado
- **WHEN** um usuário com perfil Funcionário marca um produto como indisponível
- **THEN** a mudança é aceita

### Requirement: Tela de gestão do cardápio
A interface SHALL oferecer a aba Cardápio. Para o administrador, ela MUST listar categorias e produtos, inclusive inativos, com cadastro e edição de produtos, ativação, disponibilidade e gestão de categorias. Para o funcionário, ela MUST listar os produtos ativos com apenas a ação de marcar como esgotado ou disponível.

#### Scenario: Funcionário marca esgotado pela tela
- **WHEN** o funcionário abre a aba Cardápio e marca um produto como esgotado
- **THEN** o produto aparece como "Indisponível" no cardápio da tela da comanda em no máximo 10 segundos

#### Scenario: Administrador edita preço pela tela
- **WHEN** o administrador altera o preço de um produto e salva
- **THEN** o novo preço aparece na lista e é exibida uma mensagem de confirmação
