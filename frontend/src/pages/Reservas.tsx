import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { ErroApi } from '../api/cliente'
import { listarMesas, type MesaMapa } from '../api/mesas'
import {
  cancelarReserva,
  criarReserva,
  fazerCheckIn,
  hojeLocal,
  horaCurta,
  listarReservas,
  ROTULOS_SITUACAO,
  type Reserva,
} from '../api/reservas'
import Dialogo from '../components/Dialogo'
import { useMensagens } from '../components/Mensagens'
import { usePolling } from '../hooks/usePolling'

const INTERVALO_ATUALIZACAO_MS = 15000

function mensagemDeErro(erro: unknown): string {
  return erro instanceof ErroApi ? erro.message : 'Não foi possível concluir a operação'
}

const formatoData = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'full', timeZone: 'UTC' })

/** "terça-feira, 10 de novembro de 2026" a partir de "2026-11-10". */
function dataPorExtenso(data: string): string {
  return formatoData.format(new Date(`${data}T00:00:00Z`))
}

interface Formulario {
  mesaId: string
  nome: string
  telefone: string
  pessoas: string
  data: string
  hora: string
}

const FORMULARIO_VAZIO: Omit<Formulario, 'data'> = { mesaId: '', nome: '', telefone: '', pessoas: '2', hora: '' }

function NovaReservaForm({
  dataInicial,
  onCriada,
  onFechar,
}: {
  dataInicial: string
  onCriada: (reserva: Reserva, aviso: string | null) => void
  onFechar: () => void
}) {
  const mostrar = useMensagens()
  const [mesas, setMesas] = useState<MesaMapa[] | null>(null)
  const [form, setForm] = useState<Formulario>({ ...FORMULARIO_VAZIO, data: dataInicial })
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    listarMesas()
      .then(setMesas)
      .catch((erro) => mostrar(mensagemDeErro(erro), 'erro'))
  }, [mostrar])

  const alterar = (campo: keyof Formulario) => (evento: { target: { value: string } }) =>
    setForm((atual) => ({ ...atual, [campo]: evento.target.value }))

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setEnviando(true)
    try {
      const { reserva, aviso } = await criarReserva({
        mesa_id: Number(form.mesaId),
        nome_cliente: form.nome,
        telefone: form.telefone,
        qtd_pessoas: Number(form.pessoas),
        inicio: `${form.data}T${form.hora}:00`,
      })
      onCriada(reserva, aviso)
      setForm((atual) => ({ ...FORMULARIO_VAZIO, data: atual.data }))
    } catch (erro) {
      mostrar(mensagemDeErro(erro), 'erro')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="painel-comanda form-reserva" onSubmit={enviar}>
      <h2>Nova reserva</h2>
      <label className="campo">
        Mesa
        <select required value={form.mesaId} onChange={alterar('mesaId')}>
          <option value="" disabled>
            {mesas ? 'Selecione' : 'Carregando…'}
          </option>
          {mesas?.map((mesa) => (
            <option key={mesa.id} value={mesa.id} disabled={mesa.status === 'MANUTENCAO'}>
              Mesa {mesa.numero} · {mesa.capacidade} lugares · {mesa.localizacao}
              {mesa.status === 'MANUTENCAO' ? ' (manutenção)' : ''}
            </option>
          ))}
        </select>
      </label>
      <label className="campo">
        Cliente
        <input required maxLength={100} value={form.nome} onChange={alterar('nome')} autoComplete="off" />
      </label>
      <div className="campos-lado">
        <label className="campo">
          Telefone
          <input
            required
            type="tel"
            minLength={8}
            maxLength={20}
            value={form.telefone}
            onChange={alterar('telefone')}
            autoComplete="off"
          />
        </label>
        <label className="campo">
          Pessoas
          <input required type="number" min={1} max={50} value={form.pessoas} onChange={alterar('pessoas')} />
        </label>
      </div>
      <div className="campos-lado">
        <label className="campo">
          Data
          <input required type="date" min={hojeLocal()} value={form.data} onChange={alterar('data')} />
        </label>
        <label className="campo">
          Hora
          <input required type="time" value={form.hora} onChange={alterar('hora')} />
        </label>
      </div>
      <p className="meta">A reserva ocupa a mesa por 2 horas.</p>
      <div className="dialogo-acoes">
        <button type="button" className="secundario" onClick={onFechar}>
          Fechar
        </button>
        <button type="submit" className="primario" disabled={enviando}>
          {enviando ? 'Salvando…' : 'Reservar'}
        </button>
      </div>
    </form>
  )
}

export default function Reservas({ onAbrirComanda }: { onAbrirComanda: (comandaId: number) => void }) {
  const mostrar = useMensagens()
  const [data, setData] = useState(hojeLocal)
  const buscar = useCallback(() => listarReservas(data), [data])
  const { dados: reservas, desatualizado, definir } = usePolling(buscar, INTERVALO_ATUALIZACAO_MS)
  const [formAberto, setFormAberto] = useState(false)
  const [aviso, setAviso] = useState<string | null>(null)
  const [cancelando, setCancelando] = useState<Reserva | null>(null)
  const [ocupado, setOcupado] = useState(false)

  // O polling guarda a função de busca por referência: ao trocar a data, busca já a nova lista.
  const recarregar = useCallback(() => buscar().then(definir), [buscar, definir])
  useEffect(() => {
    recarregar().catch(() => {})
  }, [recarregar])

  function criada(reserva: Reserva, avisoCapacidade: string | null) {
    mostrar(`Reserva confirmada: mesa ${reserva.mesa.numero} às ${horaCurta(reserva.inicio)}`)
    setAviso(avisoCapacidade)
    const dia = reserva.inicio.slice(0, 10)
    if (dia !== data) setData(dia)
    else recarregar().catch(() => {})
  }

  async function checkIn(reserva: Reserva) {
    setOcupado(true)
    try {
      const { comanda } = await fazerCheckIn(reserva.id)
      mostrar(`Check-in feito: comanda da mesa ${reserva.mesa.numero} aberta`)
      onAbrirComanda(comanda.id)
    } catch (erro) {
      mostrar(mensagemDeErro(erro), 'erro')
      setOcupado(false)
      recarregar().catch(() => {})
    }
  }

  async function confirmarCancelamento() {
    if (!cancelando) return
    setOcupado(true)
    try {
      await cancelarReserva(cancelando.id)
      mostrar(`Reserva de ${cancelando.nome_cliente} cancelada`)
    } catch (erro) {
      mostrar(mensagemDeErro(erro), 'erro')
    } finally {
      setCancelando(null)
      setOcupado(false)
      recarregar().catch(() => {})
    }
  }

  return (
    <section>
      <h1>Reservas</h1>
      <p className="subtitulo">Reservas do dia, com check-in e cancelamento.</p>

      <div className="barra-reservas">
        <label className="campo campo-data">
          Data
          <input type="date" value={data} onChange={(e) => e.target.value && setData(e.target.value)} />
        </label>
        {data !== hojeLocal() && (
          <button className="secundario" onClick={() => setData(hojeLocal())}>
            Hoje
          </button>
        )}
        {!formAberto && (
          <button className="primario" onClick={() => setFormAberto(true)}>
            Nova reserva
          </button>
        )}
      </div>

      {aviso && (
        <p className="aviso" role="status">
          {aviso}
        </p>
      )}

      <div className={formAberto ? 'colunas-reservas' : undefined}>
        <div>
          <h2 className="titulo-dia">{dataPorExtenso(data)}</h2>
          {desatualizado && (
            <p className="aviso" role="alert">
              Não foi possível atualizar as reservas; tentando novamente…
            </p>
          )}
          {!reservas && !desatualizado && <p className="vazio">Carregando reservas…</p>}
          {reservas && reservas.length === 0 && <p className="vazio">Nenhuma reserva para este dia.</p>}
          {reservas && reservas.length > 0 && (
            <ul className="lista-reservas">
              {reservas.map((reserva) => (
                <li key={reserva.id} className={`reserva situacao-${reserva.situacao.toLowerCase()}`}>
                  <div className="reserva-horario">
                    <strong>{horaCurta(reserva.inicio)}</strong>
                    <small>até {horaCurta(reserva.fim)}</small>
                  </div>
                  <div className="reserva-info">
                    <strong>
                      Mesa {reserva.mesa.numero} · {reserva.nome_cliente}
                    </strong>
                    <small>
                      {reserva.qtd_pessoas} {reserva.qtd_pessoas === 1 ? 'pessoa' : 'pessoas'} · {reserva.telefone}
                    </small>
                  </div>
                  <span className="selo">{ROTULOS_SITUACAO[reserva.situacao]}</span>
                  {reserva.status === 'CONFIRMADA' && (
                    <div className="reserva-acoes">
                      <button className="secundario" disabled={ocupado} onClick={() => setCancelando(reserva)}>
                        Cancelar
                      </button>
                      <button className="primario" disabled={ocupado} onClick={() => checkIn(reserva)}>
                        Check-in
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
        {formAberto && (
          <NovaReservaForm
            dataInicial={data}
            onCriada={criada}
            onFechar={() => {
              setFormAberto(false)
              setAviso(null)
            }}
          />
        )}
      </div>

      {cancelando && (
        <Dialogo
          titulo="Cancelar reserva"
          acoes={
            <>
              <button className="secundario" disabled={ocupado} onClick={() => setCancelando(null)}>
                Voltar
              </button>
              <button className="primario" disabled={ocupado} onClick={confirmarCancelamento}>
                Cancelar reserva
              </button>
            </>
          }
        >
          <p>
            Cancelar a reserva de <strong>{cancelando.nome_cliente}</strong> na mesa {cancelando.mesa.numero} às{' '}
            {horaCurta(cancelando.inicio)}?
          </p>
        </Dialogo>
      )}
    </section>
  )
}
