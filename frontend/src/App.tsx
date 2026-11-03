import { useEffect, useState } from 'react'

import { useAuth } from './auth/AuthContext'
import Layout from './components/Layout'
import AvisoContabilidade from './pages/AvisoContabilidade'
import ComandaPage from './pages/Comanda'
import Login from './pages/Login'
import MapaMesas from './pages/MapaMesas'

type Tela = { tipo: 'mapa' } | { tipo: 'comanda'; comandaId: number }

export default function App() {
  const { usuario } = useAuth()
  const [tela, setTela] = useState<Tela>({ tipo: 'mapa' })

  // Cada login começa no mapa de mesas.
  useEffect(() => setTela({ tipo: 'mapa' }), [usuario?.id])

  if (!usuario) return <Login />

  if (usuario.perfil === 'CONTABILIDADE') {
    return (
      <Layout>
        <AvisoContabilidade />
      </Layout>
    )
  }

  const voltarAoMapa = () => setTela({ tipo: 'mapa' })

  if (tela.tipo === 'comanda') {
    return (
      <Layout abaAtiva="Comanda" abasDisponiveis={['Mapa de Mesas']} onNavegar={voltarAoMapa}>
        <ComandaPage comandaId={tela.comandaId} onVoltar={voltarAoMapa} />
      </Layout>
    )
  }

  return (
    <Layout abaAtiva="Mapa de Mesas">
      <MapaMesas onAbrirComanda={(comandaId) => setTela({ tipo: 'comanda', comandaId })} />
    </Layout>
  )
}
