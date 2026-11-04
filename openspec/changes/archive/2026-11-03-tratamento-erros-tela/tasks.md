# Tasks

## 1. Limites de erro

- [x] 1.1 Criar o componente `LimiteDeErro` com as variantes de tela e geral, "Tentar novamente", "Ir para o início", "Recarregar", "Detalhes técnicos" e registro no console (D1, D4), com os estilos do aviso; verificar com `npm run build` sem erros de tipo
- [x] 1.2 Usar o limite de tela no `App` com `key` pela tela e comanda, inclusive na visão da Contabilidade, com "Ir para o início" levando à tela inicial do perfil (D2, D3), e o limite geral no `main.tsx`; verificar com `npm run build`

## 2. Verificação e implantação

- [x] 2.1 Verificar no navegador contra o backend local (D5): "Dado inesperado no mapa" (aviso no lugar do mapa, cabeçalho e aba Cozinha funcionando), "Tentar novamente depois de corrigido", "Ir para o início", "Volta à aba que falhou", "Falha no cabeçalho" (página geral e "Recarregar" mantendo a sessão) e "Suporte consulta o detalhe" (detalhes e console, sem token); conferir em largura de celular e que as telas sem falha continuam iguais
- [x] 2.2 Publicar (push na `main`) e verificar na URL pública que a navegação normal pelas abas de cada perfil continua igual

## Workflow follow-up

- Arquivar o change (`/opsx:archive`), criando a spec `interface`.
