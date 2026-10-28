import Layout from './components/Layout'
import MapaMesas from './pages/MapaMesas'

export default function App() {
  return (
    <Layout abaAtiva="Mapa de Mesas">
      <MapaMesas />
    </Layout>
  )
}
