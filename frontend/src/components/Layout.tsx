import type { ReactNode } from 'react'

import { useAuth } from '../auth/AuthContext'
import { ROTULOS_PERFIL } from '../auth/sessao'

const ABAS = ['Mapa de Mesas', 'Comanda', 'Cozinha', 'Pagamento'] as const

export default function Layout({ abaAtiva, children }: { abaAtiva?: (typeof ABAS)[number]; children: ReactNode }) {
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
              <button key={aba} className={aba === abaAtiva ? 'ativa' : ''} disabled={aba !== abaAtiva}>
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
