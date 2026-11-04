import type { FormaPagamento } from './comandas'
import { getJson } from './cliente'

export interface Periodo {
  /** "AAAA-MM-DD" (datas locais de São Paulo, ambas inclusivas). */
  inicio: string
  fim: string
}

export interface RelatorioOperacional {
  periodo: Periodo
  comandas: { em_aberto: number; fechadas: number; canceladas: number; total: number }
  faturamento: string
  ticket_medio: string | null
  tempo_medio_minutos: number | null
  produtos: { produto_id: number; nome: string; quantidade: number; valor: string }[]
  por_dia: { data: string; comandas: number; faturamento: string }[]
  por_hora: { hora: number; comandas: number }[]
}

export interface ValorPorForma {
  forma: FormaPagamento
  valor: string
}

export interface ComandaFechada {
  id: number
  mesa_numero: number
  responsavel: string | null
  aberta_em: string
  fechada_em: string
  subtotal: string
  taxa_servico: string
  total: string
  pagamentos: ValorPorForma[]
}

export interface RelatorioFinanceiro {
  periodo: Periodo
  totais: { comandas: number; subtotal: string; taxa_servico: string; total: string; por_forma: ValorPorForma[] }
  comandas: ComandaFechada[]
}

export interface RegistroAuditoria {
  id: number
  criado_em: string
  usuario_id: number | null
  /** null = operação do sistema. */
  usuario: string | null
  acao: string
  entidade: string
  entidade_id: string
  dados_antes: Record<string, unknown> | null
  dados_depois: Record<string, unknown> | null
}

export interface PaginaAuditoria {
  registros: RegistroAuditoria[]
  total: number
  pagina: number
  paginas: number
}

export interface OpcoesAuditoria {
  usuarios: { id: number; nome: string }[]
  acoes: string[]
  entidades: string[]
}

export interface FiltrosAuditoria {
  /** 0 = operações do sistema. */
  usuario_id?: number
  acao?: string
  entidade?: string
  pagina?: number
}

/** Sistema (sem usuário) no filtro de usuário da auditoria. */
export const USUARIO_SISTEMA = 0

function consulta(parametros: Record<string, string | number | undefined>): string {
  const busca = new URLSearchParams()
  for (const [chave, valor] of Object.entries(parametros)) {
    if (valor !== undefined && valor !== '') busca.set(chave, String(valor))
  }
  return busca.toString()
}

export function obterOperacional(periodo: Periodo): Promise<RelatorioOperacional> {
  return getJson<RelatorioOperacional>(`/relatorios/operacional?${consulta({ ...periodo })}`)
}

export function obterFinanceiro(periodo: Periodo): Promise<RelatorioFinanceiro> {
  return getJson<RelatorioFinanceiro>(`/relatorios/financeiro?${consulta({ ...periodo })}`)
}

export function consultarAuditoria(periodo: Periodo, filtros: FiltrosAuditoria): Promise<PaginaAuditoria> {
  return getJson<PaginaAuditoria>(`/auditoria?${consulta({ ...periodo, ...filtros })}`)
}

export function obterOpcoesAuditoria(): Promise<OpcoesAuditoria> {
  return getJson<OpcoesAuditoria>('/auditoria/opcoes')
}
