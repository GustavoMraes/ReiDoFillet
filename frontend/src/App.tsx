import { useEffect, useState } from 'react'

import { useAuth } from './auth/AuthContext'
import Layout, { type Aba } from './components/Layout'
import AvisoContabilidade from './pages/AvisoContabilidade'
import ComandaPage from './pages/Comanda'
import Cozinha from './pages/Cozinha'
import Login from './pages/Login'
import MapaMesas from './pages/MapaMesas'

type Tela = 'Mapa de Mesas' | 'Comanda' | 'Cozinha'

export default function App() {
  const { usuario } = useAuth()
  const [tela, setTela] = useState<Tela>('Mapa de Mesas')
  // Última comanda aberta na sessão: mantém a aba Comanda disponível ao alternar com a Cozinha.
  const [comandaId, setComandaId] = useState<number | null>(null)

  // Cada login começa no mapa de mesas, sem comanda aberta.
  useEffect(() => {
    setTela('Mapa de Mesas')
    setComandaId(null)
  }, [usuario?.id])

  if (!usuario) return <Login />

  if (usuario.perfil === 'CONTABILIDADE') {
    return (
      <Layout>
        <AvisoContabilidade />
      </Layout>
    )
  }

  const disponiveis: Aba[] = ['Mapa de Mesas', 'Cozinha', ...(comandaId !== null ? (['Comanda'] as Aba[]) : [])]
  const navegar = (aba: Aba) => {
    if (aba === 'Mapa de Mesas' || aba === 'Cozinha' || (aba === 'Comanda' && comandaId !== null)) setTela(aba)
  }

  return (
    <Layout abaAtiva={tela} abasDisponiveis={disponiveis} onNavegar={navegar}>
      {tela === 'Mapa de Mesas' && (
        <MapaMesas
          onAbrirComanda={(id) => {
            setComandaId(id)
            setTela('Comanda')
          }}
        />
      )}
      {tela === 'Comanda' && comandaId !== null && (
        <ComandaPage comandaId={comandaId} onVoltar={() => setTela('Mapa de Mesas')} />
      )}
      {tela === 'Cozinha' && <Cozinha />}
    </Layout>
  )
}
