import { useCallback, useEffect, useRef, useState } from 'react'

interface EstadoPolling<T> {
  dados: T | null
  carregando: boolean
  /** true quando a última atualização falhou; `dados` continua com o último valor recebido. */
  desatualizado: boolean
}

interface ResultadoPolling<T> extends EstadoPolling<T> {
  /** Substitui os dados na hora, com a resposta de uma ação (sem esperar o próximo ciclo). */
  definir: (dados: T) => void
}

/** Busca os dados ao montar e repete a cada `intervaloMs`, sem sobrepor requisições. */
export function usePolling<T>(buscar: () => Promise<T>, intervaloMs: number): ResultadoPolling<T> {
  const [estado, setEstado] = useState<EstadoPolling<T>>({ dados: null, carregando: true, desatualizado: false })
  const buscarRef = useRef(buscar)
  buscarRef.current = buscar

  useEffect(() => {
    let ativo = true
    let timer: ReturnType<typeof setTimeout>

    async function ciclo() {
      try {
        const dados = await buscarRef.current()
        if (ativo) setEstado({ dados, carregando: false, desatualizado: false })
      } catch {
        if (ativo) setEstado((anterior) => ({ ...anterior, carregando: false, desatualizado: true }))
      } finally {
        if (ativo) timer = setTimeout(ciclo, intervaloMs)
      }
    }

    ciclo()
    return () => {
      ativo = false
      clearTimeout(timer)
    }
  }, [intervaloMs])

  const definir = useCallback((dados: T) => setEstado({ dados, carregando: false, desatualizado: false }), [])

  return { ...estado, definir }
}
