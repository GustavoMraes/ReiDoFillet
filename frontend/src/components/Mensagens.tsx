import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react'

type Tipo = 'sucesso' | 'erro'

interface Mensagem {
  id: number
  texto: string
  tipo: Tipo
}

const DURACAO_MS = 3500

const MensagensContext = createContext<(texto: string, tipo?: Tipo) => void>(() => {})

/** Mensagens temporárias de confirmação ou erro (Projeto de Interface, seção 1.1). */
export function MensagensProvider({ children }: { children: ReactNode }) {
  const [mensagens, setMensagens] = useState<Mensagem[]>([])
  const proximoId = useRef(0)

  const mostrar = useCallback((texto: string, tipo: Tipo = 'sucesso') => {
    const id = ++proximoId.current
    setMensagens((atuais) => [...atuais.slice(-2), { id, texto, tipo }])
    setTimeout(() => setMensagens((atuais) => atuais.filter((m) => m.id !== id)), DURACAO_MS)
  }, [])

  return (
    <MensagensContext.Provider value={mostrar}>
      {children}
      <div className="mensagens" aria-live="polite">
        {mensagens.map((m) => (
          <p key={m.id} className={`mensagem ${m.tipo}`} role={m.tipo === 'erro' ? 'alert' : 'status'}>
            {m.texto}
          </p>
        ))}
      </div>
    </MensagensContext.Provider>
  )
}

export function useMensagens() {
  return useContext(MensagensContext)
}
