import { deleteJson, getJson, patchJson, postJson } from './cliente'

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

export type FormaPagamento = 'PIX' | 'CREDITO' | 'DEBITO' | 'DINHEIRO'

export interface Pagamento {
  id: number
  forma: FormaPagamento
  valor: string
  registrado_por: string | null
  registrado_em: string
}

export interface Comanda {
  id: number
  mesa: { id: number; numero: number }
  responsavel: { id: number; nome: string } | null
  status: 'ABERTA' | 'PRE_CONTA' | 'FECHADA' | 'CANCELADA'
  aberta_em: string
  pre_conta_em: string | null
  itens: ItemComanda[]
  subtotal: string
  taxa_servico: { aplicada: boolean; percentual: string | null; valor: string }
  total: string
  pago: string
  restante: string
  pagamentos: Pagamento[]
}

export const ROTULOS_FORMA: Record<FormaPagamento, string> = {
  PIX: 'PIX',
  CREDITO: 'Cartão de Crédito',
  DEBITO: 'Cartão de Débito',
  DINHEIRO: 'Dinheiro',
}

export function gerarPreConta(comandaId: number): Promise<{ comanda: Comanda; aviso: string | null }> {
  return postJson<{ comanda: Comanda; aviso: string | null }>(`/comandas/${comandaId}/pre-conta`)
}

export function alterarTaxaServico(comandaId: number, alteracao: { aplicada?: boolean; percentual?: string }) {
  return patchJson<Comanda>(`/comandas/${comandaId}/taxa-servico`, alteracao)
}

export function registrarPagamento(comandaId: number, forma: FormaPagamento, valor: string): Promise<Comanda> {
  return postJson<Comanda>(`/comandas/${comandaId}/pagamentos`, { forma, valor })
}

export function removerPagamento(comandaId: number, pagamentoId: number): Promise<Comanda> {
  return deleteJson<Comanda>(`/comandas/${comandaId}/pagamentos/${pagamentoId}`)
}

export function cancelarComanda(comandaId: number): Promise<Comanda> {
  return postJson<Comanda>(`/comandas/${comandaId}/cancelar`)
}

export interface Cupom {
  mesa_numero: number
  garcom: string
  enviado_em: string
  itens: { quantidade: number; produto_nome: string; observacao: string }[]
}

export function enviarComanda(comandaId: number): Promise<{ comanda: Comanda; cupom: Cupom }> {
  return postJson<{ comanda: Comanda; cupom: Cupom }>(`/comandas/${comandaId}/enviar`)
}

export function abrirComanda(mesaId: number): Promise<Comanda> {
  return postJson<Comanda>(`/mesas/${mesaId}/comanda`)
}

/** Leva a comanda inteira para uma mesa livre (a mesa de origem fica livre). */
export function transferirComanda(comandaId: number, mesaId: number): Promise<Comanda> {
  return postJson<Comanda>(`/comandas/${comandaId}/transferir`, { mesa_id: mesaId })
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
