import type { Comanda } from './comandas'
import { getJson, postJson } from './cliente'

export type StatusReserva = 'CONFIRMADA' | 'CONCLUIDA' | 'CANCELADA'
export type SituacaoReserva = StatusReserva | 'NAO_COMPARECEU'

export interface Reserva {
  id: number
  mesa: { id: number; numero: number }
  nome_cliente: string
  telefone: string
  qtd_pessoas: number
  inicio: string
  fim: string
  status: StatusReserva
  situacao: SituacaoReserva
}

export interface NovaReserva {
  mesa_id: number
  nome_cliente: string
  telefone: string
  qtd_pessoas: number
  /** Data e hora locais, sem fuso ("2026-11-10T20:30:00"): o servidor interpreta no fuso de São Paulo. */
  inicio: string
}

export const ROTULOS_SITUACAO: Record<SituacaoReserva, string> = {
  CONFIRMADA: 'Confirmada',
  CONCLUIDA: 'Concluída',
  CANCELADA: 'Cancelada',
  NAO_COMPARECEU: 'Não compareceu',
}

const formatoHora = new Intl.DateTimeFormat('pt-BR', {
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'America/Sao_Paulo',
})

/** "20h30", no fuso do restaurante. */
export function horaCurta(instante: string): string {
  return formatoHora.format(new Date(instante)).replace(':', 'h')
}

/** Data de hoje no fuso do restaurante, no formato do campo de data ("2026-11-10"). */
export function hojeLocal(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo' }).format(new Date())
}

export function listarReservas(data?: string): Promise<Reserva[]> {
  return getJson<Reserva[]>(data ? `/reservas?data=${data}` : '/reservas')
}

export function criarReserva(dados: NovaReserva): Promise<{ reserva: Reserva; aviso: string | null }> {
  return postJson('/reservas', dados)
}

export function cancelarReserva(reservaId: number): Promise<Reserva> {
  return postJson<Reserva>(`/reservas/${reservaId}/cancelar`)
}

export function fazerCheckIn(reservaId: number): Promise<{ reserva: Reserva; comanda: Comanda }> {
  return postJson(`/reservas/${reservaId}/check-in`)
}
