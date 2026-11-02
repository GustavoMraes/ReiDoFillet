import { useAuth } from './auth/AuthContext'
import Layout from './components/Layout'
import AvisoContabilidade from './pages/AvisoContabilidade'
import Login from './pages/Login'
import MapaMesas from './pages/MapaMesas'

export default function App() {
  const { usuario } = useAuth()

  if (!usuario) return <Login />

  if (usuario.perfil === 'CONTABILIDADE') {
    return (
      <Layout>
        <AvisoContabilidade />
      </Layout>
    )
  }

  return (
    <Layout abaAtiva="Mapa de Mesas">
      <MapaMesas />
    </Layout>
  )
}
