import { useState, type ReactNode } from 'react'

import { useAuth } from '../auth/AuthContext'
import { ROTULOS_PERFIL } from '../auth/sessao'
import TrocarSenha from './TrocarSenha'

export type Aba =
  | 'Mapa de Mesas'
  | 'Reservas'
  | 'Comanda'
  | 'Cozinha'
  | 'Pagamento'
  | 'Cardápio'
  | 'Usuários'
  | 'Relatórios'

interface Props {
  abaAtiva?: Aba
  /** Abas exibidas para o perfil, em ordem. */
  abas?: Aba[]
  /** Abas clicáveis; as demais aparecem desabilitadas. */
  abasDisponiveis?: Aba[]
  onNavegar?: (aba: Aba) => void
  children: ReactNode
}

export default function Layout({ abaAtiva, abas = [], abasDisponiveis = [], onNavegar, children }: Props) {
  const { usuario, sair } = useAuth()
  const [trocandoSenha, setTrocandoSenha] = useState(false)

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
            {abas.map((aba) => (
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
            <button className="sair" onClick={() => setTrocandoSenha(true)}>
              Trocar senha
            </button>
            <button className="sair" onClick={sair}>
              Sair
            </button>
          </div>
        )}
      </header>
      <main className="conteudo">{children}</main>
      {trocandoSenha && <TrocarSenha onFechar={() => setTrocandoSenha(false)} />}
    </>
  )
}
