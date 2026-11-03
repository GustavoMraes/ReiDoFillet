import type { ReactNode } from 'react'

interface Props {
  titulo: string
  children: ReactNode
  /** Botões do rodapé, já com seus estilos. */
  acoes: ReactNode
}

/** Janela sobre a tela atual, para confirmações e detalhes rápidos. */
export default function Dialogo({ titulo, children, acoes }: Props) {
  return (
    <div className="sobreposicao">
      <div className="dialogo" role="dialog" aria-modal="true" aria-label={titulo}>
        <h2>{titulo}</h2>
        <div className="dialogo-corpo">{children}</div>
        <div className="dialogo-acoes">{acoes}</div>
      </div>
    </div>
  )
}
