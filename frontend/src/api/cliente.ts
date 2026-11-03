import { EVENTO_SESSAO_EXPIRADA, lerSessao } from '../auth/sessao'

const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

export class ErroApi extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message)
  }
}

interface Opcoes {
  metodo?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  corpo?: unknown
  /** Na chamada de login, um 401 é erro de credencial, não sessão expirada. */
  semSessao?: boolean
}

async function requisitar<T>(caminho: string, { metodo = 'GET', corpo, semSessao = false }: Opcoes = {}): Promise<T> {
  const cabecalhos: Record<string, string> = {}
  const token = semSessao ? null : lerSessao()?.token
  if (token) cabecalhos.Authorization = `Bearer ${token}`
  if (corpo !== undefined) cabecalhos['Content-Type'] = 'application/json'

  let resposta: Response
  try {
    resposta = await fetch(`${API_URL}${caminho}`, {
      method: metodo,
      headers: cabecalhos,
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    })
  } catch {
    throw new ErroApi('Servidor indisponível')
  }

  if (!resposta.ok) {
    const conteudo = await resposta.json().catch(() => null)
    if (resposta.status === 401 && !semSessao) window.dispatchEvent(new Event(EVENTO_SESSAO_EXPIRADA))
    const detalhe = typeof conteudo?.detalhe === 'string' ? conteudo.detalhe : `Erro ${resposta.status}`
    throw new ErroApi(detalhe, resposta.status)
  }
  if (resposta.status === 204) return undefined as T
  return resposta.json() as Promise<T>
}

export function getJson<T>(caminho: string): Promise<T> {
  return requisitar<T>(caminho)
}

export function postJson<T>(caminho: string, corpo?: unknown, opcoes: Omit<Opcoes, 'metodo' | 'corpo'> = {}): Promise<T> {
  return requisitar<T>(caminho, { ...opcoes, metodo: 'POST', corpo })
}

export function patchJson<T>(caminho: string, corpo: unknown): Promise<T> {
  return requisitar<T>(caminho, { metodo: 'PATCH', corpo })
}

export function deleteJson<T>(caminho: string): Promise<T> {
  return requisitar<T>(caminho, { metodo: 'DELETE' })
}

const formatoReal = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

/** Valores monetários chegam da API como texto decimal ("14.00"). */
export function emReais(valor: string): string {
  return formatoReal.format(Number(valor))
}

/** Converte o valor digitado ("60,50" ou "60.50") para o formato da API ("60.50"). */
export function paraDecimal(texto: string): string {
  const limpo = texto.trim()
  return limpo.includes(',') ? limpo.replace(/\./g, '').replace(',', '.') : limpo
}
