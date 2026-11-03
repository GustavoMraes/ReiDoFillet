import { getJson } from './cliente'

export type StatusMesa = 'LIVRE' | 'OCUPADA' | 'RESERVADA' | 'AGUARDANDO_PAGAMENTO' | 'MANUTENCAO'

export interface MesaMapa {
  id: number
  numero: number
  capacidade: number
  localizacao: string
  status: StatusMesa
  minutos_atendimento: number | null
  reserva_inicio: string | null
  /** Mesa livre com reserva começando em até 2h. */
  proxima_reserva_inicio: string | null
}

export function listarMesas(): Promise<MesaMapa[]> {
  return getJson<MesaMapa[]>('/mesas')
}
