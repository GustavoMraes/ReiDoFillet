import { useState } from 'react'

import { ErroApi } from '../api/cliente'
import { abrirComanda } from '../api/comandas'
import { listarMesas, type MesaMapa, type StatusMesa } from '../api/mesas'
import { fazerCheckIn, horaCurta, listarReservas, type Reserva } from '../api/reservas'
import Dialogo from '../components/Dialogo'
import { useMensagens } from '../components/Mensagens'
import { usePolling } from '../hooks/usePolling'

const INTERVALO_ATUALIZACAO_MS = 5000

const ROTULOS: Record<StatusMesa, string> = {
  LIVRE: 'Livre',
  OCUPADA: 'Ocupada',
  RESERVADA: 'Reservada',
  AGUARDANDO_PAGAMENTO: 'Aguardando pagamento',
  MANUTENCAO: 'Manutenção',
}

function informacaoComplementar(mesa: MesaMapa): string | null {
  if (mesa.minutos_atendimento !== null) return `${mesa.minutos_atendimento} min de atendimento`
  if (mesa.reserva_inicio !== null) return `Reserva às ${horaCurta(mesa.reserva_inicio)}`
  if (mesa.proxima_reserva_inicio !== null) return `Reserva às ${horaCurta(mesa.proxima_reserva_inicio)}`
  return null
}

function mensagemDeErro(erro: unknown, padrao: string): string {
  return erro instanceof ErroApi ? erro.message : padrao
}

/** Diálogo aberto no mapa: check-in de mesa reservada ou confirmação em mesa livre com reserva próxima. */
type Pendente =
  | { tipo: 'check-in'; mesa: MesaMapa; reserva: Reserva | null }
  | { tipo: 'reserva-proxima'; mesa: MesaMapa; inicio: string }

function CartaoMesa({ mesa, ocupado, onClick }: { mesa: MesaMapa; ocupado: boolean; onClick: () => void }) {
  const info = informacaoComplementar(mesa)
  return (
    <button
      className={`cartao-mesa status-${mesa.status.toLowerCase()}`}
      onClick={onClick}
      disabled={ocupado}
      aria-label={`Mesa ${mesa.numero}, ${ROTULOS[mesa.status]}`}
    >
      <span className="localizacao">{mesa.localizacao}</span>
      <h3>Mesa {mesa.numero}</h3>
      <p className="capacidade">{mesa.capacidade} lugares</p>
      <span className="selo">{ROTULOS[mesa.status]}</span>
      {info && <p className="info">{info}</p>}
    </button>
  )
}

export default function MapaMesas({ onAbrirComanda }: { onAbrirComanda: (comandaId: number) => void }) {
  const { dados: mesas, carregando, desatualizado } = usePolling(listarMesas, INTERVALO_ATUALIZACAO_MS)
  const mostrar = useMensagens()
  const [abrindo, setAbrindo] = useState(false)
  const [pendente, setPendente] = useState<Pendente | null>(null)

  async function abrir(mesa: MesaMapa) {
    setAbrindo(true)
    try {
      // Livre abre, Ocupada/Aguardando retoma; Manutenção volta com a mensagem do servidor.
      const comanda = await abrirComanda(mesa.id)
      onAbrirComanda(comanda.id)
    } catch (erro) {
      mostrar(mensagemDeErro(erro, 'Não foi possível abrir a comanda'), 'erro')
      setAbrindo(false)
    }
  }

  async function verReserva(mesa: MesaMapa, inicio: string) {
    setAbrindo(true)
    try {
      // A reserva que bloqueia a mesa é a confirmada que começa no horário informado pelo mapa.
      const reservas = await listarReservas(inicio.slice(0, 10))
      const reserva = reservas.find((r) => r.mesa.id === mesa.id && r.status === 'CONFIRMADA' && r.inicio === inicio)
      setPendente({ tipo: 'check-in', mesa, reserva: reserva ?? null })
    } catch (erro) {
      mostrar(mensagemDeErro(erro, 'Não foi possível carregar a reserva'), 'erro')
    } finally {
      setAbrindo(false)
    }
  }

  function clicar(mesa: MesaMapa) {
    if (mesa.status === 'RESERVADA' && mesa.reserva_inicio !== null) verReserva(mesa, mesa.reserva_inicio)
    else if (mesa.status === 'LIVRE' && mesa.proxima_reserva_inicio !== null)
      setPendente({ tipo: 'reserva-proxima', mesa, inicio: mesa.proxima_reserva_inicio })
    else abrir(mesa)
  }

  async function checkIn(reserva: Reserva) {
    setAbrindo(true)
    try {
      const { comanda } = await fazerCheckIn(reserva.id)
      mostrar(`Check-in feito: comanda da mesa ${reserva.mesa.numero} aberta`)
      onAbrirComanda(comanda.id)
    } catch (erro) {
      mostrar(mensagemDeErro(erro, 'Não foi possível fazer o check-in'), 'erro')
      setAbrindo(false)
      setPendente(null)
    }
  }

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
            <CartaoMesa key={mesa.id} mesa={mesa} ocupado={abrindo} onClick={() => clicar(mesa)} />
          ))}
        </div>
      )}

      {pendente?.tipo === 'check-in' && (
        <Dialogo
          titulo={`Mesa ${pendente.mesa.numero} — Reservada`}
          acoes={
            <>
              <button className="secundario" disabled={abrindo} onClick={() => setPendente(null)}>
                Fechar
              </button>
              {pendente.reserva && (
                <button
                  className="primario"
                  disabled={abrindo}
                  onClick={() => pendente.reserva && checkIn(pendente.reserva)}
                >
                  Fazer check-in
                </button>
              )}
            </>
          }
        >
          {pendente.reserva ? (
            <dl className="dados-reserva">
              <dt>Cliente</dt>
              <dd>{pendente.reserva.nome_cliente}</dd>
              <dt>Telefone</dt>
              <dd>{pendente.reserva.telefone}</dd>
              <dt>Pessoas</dt>
              <dd>{pendente.reserva.qtd_pessoas}</dd>
              <dt>Horário</dt>
              <dd>
                {horaCurta(pendente.reserva.inicio)} às {horaCurta(pendente.reserva.fim)}
              </dd>
            </dl>
          ) : (
            <p>A reserva desta mesa não foi encontrada. Atualize o mapa e tente novamente.</p>
          )}
        </Dialogo>
      )}

      {pendente?.tipo === 'reserva-proxima' && (
        <Dialogo
          titulo={`Mesa ${pendente.mesa.numero}`}
          acoes={
            <>
              <button className="secundario" onClick={() => setPendente(null)}>
                Cancelar
              </button>
              <button
                className="primario"
                onClick={() => {
                  setPendente(null)
                  abrir(pendente.mesa)
                }}
              >
                Abrir comanda
              </button>
            </>
          }
        >
          <p>Esta mesa tem reserva às {horaCurta(pendente.inicio)}. Abrir a comanda mesmo assim?</p>
        </Dialogo>
      )}
    </section>
  )
}
