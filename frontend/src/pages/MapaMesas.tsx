import { listarMesas, type MesaMapa, type StatusMesa } from '../api/mesas'
import { usePolling } from '../hooks/usePolling'

const INTERVALO_ATUALIZACAO_MS = 5000

const ROTULOS: Record<StatusMesa, string> = {
  LIVRE: 'Livre',
  OCUPADA: 'Ocupada',
  RESERVADA: 'Reservada',
  AGUARDANDO_PAGAMENTO: 'Aguardando pagamento',
  MANUTENCAO: 'Manutenção',
}

const formatoHora = new Intl.DateTimeFormat('pt-BR', {
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'America/Sao_Paulo',
})

function informacaoComplementar(mesa: MesaMapa): string | null {
  if (mesa.minutos_atendimento !== null) return `${mesa.minutos_atendimento} min de atendimento`
  if (mesa.reserva_inicio !== null) return `Reserva às ${formatoHora.format(new Date(mesa.reserva_inicio)).replace(':', 'h')}`
  return null
}

function CartaoMesa({ mesa }: { mesa: MesaMapa }) {
  const info = informacaoComplementar(mesa)
  return (
    <article className={`cartao-mesa status-${mesa.status.toLowerCase()}`}>
      <span className="localizacao">{mesa.localizacao}</span>
      <h3>Mesa {mesa.numero}</h3>
      <p className="capacidade">{mesa.capacidade} lugares</p>
      <span className="selo">{ROTULOS[mesa.status]}</span>
      {info && <p className="info">{info}</p>}
    </article>
  )
}

export default function MapaMesas() {
  const { dados: mesas, carregando, desatualizado } = usePolling(listarMesas, INTERVALO_ATUALIZACAO_MS)

  return (
    <section>
      <h1>Mapa de Mesas</h1>
      <p className="subtitulo">Toque em uma mesa para abrir ou continuar o atendimento.</p>

      <ul className="legenda">
        {Object.entries(ROTULOS).map(([status, rotulo]) => (
          <li key={status} className={`status-${status.toLowerCase()}`}>
            {rotulo}
          </li>
        ))}
      </ul>

      {desatualizado && (
        <p className="aviso" role="alert">
          {mesas
            ? 'Não foi possível atualizar o mapa. Os dados exibidos podem estar desatualizados; tentando novamente…'
            : 'Não foi possível carregar o mapa de mesas; tentando novamente…'}
        </p>
      )}

      {carregando && !mesas && <p className="vazio">Carregando mesas…</p>}
      {mesas && mesas.length === 0 && <p className="vazio">Nenhuma mesa cadastrada.</p>}
      {mesas && mesas.length > 0 && (
        <div className="grade-mesas">
          {mesas.map((mesa) => (
            <CartaoMesa key={mesa.id} mesa={mesa} />
          ))}
        </div>
      )}
    </section>
  )
}
