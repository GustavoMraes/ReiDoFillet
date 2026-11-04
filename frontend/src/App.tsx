import { useEffect, useState } from 'react'

import type { Comanda } from './api/comandas'
import { useAuth } from './auth/AuthContext'
import Layout, { type Aba } from './components/Layout'
import ComandaPage from './pages/Comanda'
import Cozinha from './pages/Cozinha'
import GestaoCardapio from './pages/GestaoCardapio'
import Login from './pages/Login'
import MapaMesas from './pages/MapaMesas'
import PagamentoPage from './pages/Pagamento'
import Relatorios from './pages/Relatorios'
import Reservas from './pages/Reservas'
import Usuarios from './pages/Usuarios'

type Tela = Aba

export default function App() {
  const { usuario } = useAuth()
  const [tela, setTela] = useState<Tela>('Mapa de Mesas')
  // Última comanda aberta na sessão: mantém as abas Comanda e Pagamento ao alternar com a Cozinha.
  const [comandaId, setComandaId] = useState<number | null>(null)
  const [statusComanda, setStatusComanda] = useState<Comanda['status'] | null>(null)

  // Cada login começa no mapa de mesas, sem comanda aberta.
  useEffect(() => {
    setTela('Mapa de Mesas')
    setComandaId(null)
    setStatusComanda(null)
  }, [usuario?.id])

  if (!usuario) return <Login />

  if (usuario.perfil === 'CONTABILIDADE') {
    return (
      <Layout abaAtiva="Relatórios" abas={['Relatórios']} abasDisponiveis={['Relatórios']}>
        <Relatorios secoes={['Financeiro', 'Auditoria']} />
      </Layout>
    )
  }

  const administrador = usuario.perfil === 'ADMIN'
  const exclusivasDoAdmin: Aba[] = administrador ? ['Usuários', 'Relatórios'] : []
  const abas: Aba[] = ['Mapa de Mesas', 'Reservas', 'Comanda', 'Cozinha', 'Pagamento', 'Cardápio', ...exclusivasDoAdmin]
  const comComanda = comandaId !== null
  const disponiveis: Aba[] = [
    'Mapa de Mesas',
    'Reservas',
    'Cozinha',
    'Cardápio',
    ...exclusivasDoAdmin,
    ...(comComanda ? (['Comanda'] as Aba[]) : []),
    ...(comComanda && statusComanda === 'PRE_CONTA' ? (['Pagamento'] as Aba[]) : []),
  ]
  const navegar = (aba: Aba) => {
    if (disponiveis.includes(aba)) setTela(aba)
  }
  const abrirComanda = (id: number) => {
    setComandaId(id)
    setStatusComanda(null)
    setTela('Comanda')
  }
  const encerrarComanda = () => {
    setComandaId(null)
    setStatusComanda(null)
    setTela('Mapa de Mesas')
  }

  return (
    <Layout abaAtiva={tela} abas={abas} abasDisponiveis={disponiveis} onNavegar={navegar}>
      {tela === 'Mapa de Mesas' && <MapaMesas onAbrirComanda={abrirComanda} />}
      {tela === 'Reservas' && <Reservas onAbrirComanda={abrirComanda} />}
      {tela === 'Comanda' && comandaId !== null && (
        <ComandaPage
          comandaId={comandaId}
          onVoltar={() => setTela('Mapa de Mesas')}
          onStatus={setStatusComanda}
          onIrParaPagamento={() => setTela('Pagamento')}
          onEncerrada={encerrarComanda}
        />
      )}
      {tela === 'Pagamento' && comandaId !== null && (
        <PagamentoPage
          comandaId={comandaId}
          onStatus={setStatusComanda}
          onVoltarParaComanda={() => setTela('Comanda')}
          onEncerrada={encerrarComanda}
        />
      )}
      {tela === 'Cozinha' && <Cozinha />}
      {tela === 'Cardápio' && <GestaoCardapio administrador={administrador} />}
      {tela === 'Usuários' && administrador && <Usuarios />}
      {tela === 'Relatórios' && administrador && <Relatorios secoes={['Operacional', 'Financeiro', 'Auditoria']} />}
    </Layout>
  )
}
