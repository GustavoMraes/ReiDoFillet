const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

export class ErroApi extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message)
  }
}

export async function getJson<T>(caminho: string): Promise<T> {
  let resposta: Response
  try {
    resposta = await fetch(`${API_URL}${caminho}`)
  } catch {
    throw new ErroApi('Servidor indisponível')
  }
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => null)
    throw new ErroApi(corpo?.detalhe ?? `Erro ${resposta.status}`, resposta.status)
  }
  return resposta.json() as Promise<T>
}
