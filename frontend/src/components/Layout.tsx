import type { ReactNode } from 'react'

import { useAuth } from '../auth/AuthContext'
import { ROTULOS_PERFIL } from '../auth/sessao'

export type Aba = 'Mapa de Mesas' | 'Comanda' | 'Cozinha' | 'Pagamento'

const ABAS: Aba[] = ['Mapa de Mesas', 'Comanda', 'Cozinha', 'Pagamento']

interface Props {
  abaAtiva?: Aba
  /** Abas clicáveis; as demais aparecem desabilitadas. */
  abasDisponiveis?: Aba[]
  onNavegar?: (aba: Aba) => void
  children: ReactNode
}

export default function Layout({ abaAtiva, abasDisponiveis = [], onNavegar, children }: Props) {
  const { usuario, sair } = useAuth()

  return (
    <>
      <header className="topo">
        <div className="marca">
          <strong>
            REI DO <span>FILET</span>
          </strong>
          <small>Sistema de Atendimento e Comandas</small>
        </div>
        {abaAtiva && (
          <nav className="abas">
            {ABAS.map((aba) => (
              <button
                key={aba}
                className={aba === abaAtiva ? 'ativa' : ''}
                disabled={aba !== abaAtiva && !abasDisponiveis.includes(aba)}
                onClick={() => aba !== abaAtiva && onNavegar?.(aba)}
              >
                {aba}
              </button>
            ))}
          </nav>
        )}
        {usuario && (
          <div className="usuario">
            <span>
              <span className="ponto" aria-hidden="true" />
              {usuario.nome} · {ROTULOS_PERFIL[usuario.perfil]}
            </span>
            <button className="sair" onClick={sair}>
              Sair
            </button>
          </div>
        )}
      </header>
      <main className="conteudo">{children}</main>
    </>
  )
}
