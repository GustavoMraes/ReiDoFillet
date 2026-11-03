import { getJson, postJson } from './cliente'

export interface ItemCozinha {
  id: number
  comanda_id: number
  mesa_numero: number
  quantidade: number
  produto_nome: string
  observacao: string
  enviado_em: string
  minutos_desde_envio: number
}

export interface PainelCozinha {
  em_preparo: ItemCozinha[]
  pronto: ItemCozinha[]
}

export function obterPainel(): Promise<PainelCozinha> {
  return getJson<PainelCozinha>('/cozinha')
}

export function marcarPronto(itemId: number): Promise<PainelCozinha> {
  return postJson<PainelCozinha>(`/cozinha/itens/${itemId}/pronto`)
}

export function marcarEntregue(itemId: number): Promise<PainelCozinha> {
  return postJson<PainelCozinha>(`/cozinha/itens/${itemId}/entregue`)
}
