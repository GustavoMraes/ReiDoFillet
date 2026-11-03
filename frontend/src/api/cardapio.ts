import { getJson } from './cliente'

export interface ProdutoCardapio {
  id: number
  nome: string
  descricao: string | null
  preco: string
  disponivel: boolean
}

export interface CategoriaCardapio {
  id: number
  nome: string
  produtos: ProdutoCardapio[]
}

export function obterCardapio(): Promise<CategoriaCardapio[]> {
  return getJson<CategoriaCardapio[]>('/cardapio')
}
