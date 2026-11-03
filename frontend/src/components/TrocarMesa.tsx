import { useEffect, useState } from 'react'

import { ErroApi } from '../api/cliente'
import { transferirComanda, type Comanda } from '../api/comandas'
import { listarMesas, type MesaMapa } from '../api/mesas'
import { horaCurta } from '../api/reservas'
import Dialogo from './Dialogo'

interface Props {
  comanda: Comanda
  onTransferida: (comanda: Comanda, origem: number) => void
  onErro: (mensagem: string) => void
  onFechar: () => void
}

/** Escolha da mesa livre de destino e confirmação da transferência da comanda inteira. */
export default function TrocarMesa({ comanda, onTransferida, onErro, onFechar }: Props) {
  const [livres, setLivres] = useState<MesaMapa[] | null>(null)
  const [erroCarga, setErroCarga] = useState<string | null>(null)
  const [destino, setDestino] = useState<MesaMapa | null>(null)
  const [enviando, setEnviando] = useState(false)
  // Incrementar recarrega a lista de mesas livres.
  const [versao, setVersao] = useState(0)

  useEffect(() => {
    let ativo = true
    listarMesas()
      .then((mesas) => ativo && setLivres(mesas.filter((mesa) => mesa.status === 'LIVRE')))
      .catch((erro) => ativo && setErroCarga(erro instanceof ErroApi ? erro.message : 'Não foi possível carregar as mesas'))
    return () => {
      ativo = false
    }
  }, [versao])

  async function confirmar() {
    if (!destino) return
    setEnviando(true)
    try {
      onTransferida(await transferirComanda(comanda.id, destino.id), comanda.mesa.numero)
    } catch (erro) {
      // O destino pode ter sido ocupado por outro dispositivo: mostra o motivo e atualiza a lista.
      onErro(erro instanceof ErroApi ? erro.message : 'Não foi possível trocar de mesa')
      setDestino(null)
      setEnviando(false)
      setLivres(null)
      setVersao((v) => v + 1)
    }
  }

  if (destino) {
    return (
      <Dialogo
        titulo="Confirmar troca de mesa"
        acoes={
          <>
            <button className="secundario" disabled={enviando} onClick={() => setDestino(null)}>
              Voltar
            </button>
            <button className="primario" disabled={enviando} onClick={confirmar}>
              {enviando ? 'Transferindo…' : 'Trocar de mesa'}
            </button>
          </>
        }
      >
        <p>
          Levar a comanda da mesa <strong>{comanda.mesa.numero}</strong> para a mesa <strong>{destino.numero}</strong>?
          Itens, pré-conta e pagamentos vão junto, e a mesa {comanda.mesa.numero} fica livre.
        </p>
        {destino.proxima_reserva_inicio && (
          <p className="aviso">
            A mesa {destino.numero} tem reserva às {horaCurta(destino.proxima_reserva_inicio)}.
          </p>
        )}
      </Dialogo>
    )
  }

  return (
    <Dialogo
      titulo={`Trocar a mesa ${comanda.mesa.numero}`}
      acoes={
        <button className="secundario" onClick={onFechar}>
          Fechar
        </button>
      }
    >
      {erroCarga && <p className="aviso">{erroCarga}</p>}
      {!livres && !erroCarga && <p className="vazio">Carregando mesas…</p>}
      {livres && livres.length === 0 && <p className="vazio">Não há mesas livres para a transferência.</p>}
      {livres && livres.length > 0 && (
        <>
          <p>Escolha a mesa livre de destino:</p>
          <ul className="opcoes-mesa">
            {livres.map((mesa) => (
              <li key={mesa.id}>
                <button className="secundario" onClick={() => setDestino(mesa)}>
                  <strong>Mesa {mesa.numero}</strong>
                  <small>
                    {mesa.capacidade} lugares · {mesa.localizacao}
                    {mesa.proxima_reserva_inicio && ` · Reserva às ${horaCurta(mesa.proxima_reserva_inicio)}`}
                  </small>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </Dialogo>
  )
}
