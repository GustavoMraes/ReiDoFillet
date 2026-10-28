import type { ReactNode } from 'react'

const ABAS = ['Mapa de Mesas', 'Comanda', 'Cozinha', 'Pagamento'] as const

export default function Layout({ abaAtiva, children }: { abaAtiva: (typeof ABAS)[number]; children: ReactNode }) {
  return (
    <>
      <header className="topo">
        <div className="marca">
          <strong>
            REI DO <span>FILET</span>
          </strong>
          <small>Sistema de Atendimento e Comandas</small>
        </div>
        <nav className="abas">
          {ABAS.map((aba) => (
            <button key={aba} className={aba === abaAtiva ? 'ativa' : ''} disabled={aba !== abaAtiva}>
              {aba}
            </button>
          ))}
        </nav>
        <div className="usuario" />
      </header>
      <main className="conteudo">{children}</main>
    </>
  )
}
