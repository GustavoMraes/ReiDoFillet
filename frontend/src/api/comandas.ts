import { getJson, patchJson, postJson } from './cliente'

export type StatusItem = 'PENDENTE' | 'EM_PREPARO' | 'PRONTO' | 'ENTREGUE' | 'CANCELADO'

export interface ItemComanda {
  id: number
  produto_id: number
  produto_nome: string
  quantidade: number
  observacao: string
  preco_unitario: string
  subtotal: string
  status: StatusItem
}

export interface Comanda {
  id: number
  mesa: { id: number; numero: number }
  responsavel: { id: number; nome: string } | null
  status: 'ABERTA' | 'PRE_CONTA' | 'FECHADA' | 'CANCELADA'
  aberta_em: string
  itens: ItemComanda[]
  total: string
}

export function abrirComanda(mesaId: number): Promise<Comanda> {
  return postJson<Comanda>(`/mesas/${mesaId}/comanda`)
}

export function obterComanda(comandaId: number): Promise<Comanda> {
  return getJson<Comanda>(`/comandas/${comandaId}`)
}

export function adicionarItem(comandaId: number, produtoId: number, observacao = '', quantidade = 1): Promise<Comanda> {
  return postJson<Comanda>(`/comandas/${comandaId}/itens`, { produto_id: produtoId, quantidade, observacao })
}

export function alterarItem(comandaId: number, itemId: number, alteracao: { quantidade?: number; observacao?: string }) {
  return patchJson<Comanda>(`/comandas/${comandaId}/itens/${itemId}`, alteracao)
}

export function cancelarItem(comandaId: number, itemId: number): Promise<Comanda> {
  return postJson<Comanda>(`/comandas/${comandaId}/itens/${itemId}/cancelar`)
}
