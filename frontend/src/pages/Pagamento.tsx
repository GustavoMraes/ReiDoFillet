import { useCallback, useEffect, useState } from 'react'

import { ErroApi, emReais, paraDecimal } from '../api/cliente'
import {
  alterarTaxaServico,
  obterComanda,
  registrarPagamento,
  removerPagamento,
  ROTULOS_FORMA,
  type Comanda,
  type FormaPagamento,
} from '../api/comandas'
import { useMensagens } from '../components/Mensagens'
import PreContaImpressao from '../components/PreContaImpressao'
import { usePolling } from '../hooks/usePolling'

const INTERVALO_ATUALIZACAO_MS = 5000
const FORMAS: FormaPagamento[] = ['PIX', 'CREDITO', 'DEBITO', 'DINHEIRO']

const formatoHora = new Intl.DateTimeFormat('pt-BR', { timeStyle: 'short', timeZone: 'America/Sao_Paulo' })

function mensagemDeErro(erro: unknown): string {
  return erro instanceof ErroApi ? erro.message : 'Não foi possível concluir a operação'
}

interface Props {
  comandaId: number
  onStatus: (status: Comanda['status']) => void
  onVoltarParaComanda: () => void
  onEncerrada: () => void
}

export default function PagamentoPage({ comandaId, onStatus, onVoltarParaComanda, onEncerrada }: Props) {
  const mostrar = useMensagens()
  const buscar = useCallback(() => obterComanda(comandaId), [comandaId])
  const { dados: comanda, desatualizado, definir } = usePolling<Comanda>(buscar, INTERVALO_ATUALIZACAO_MS)
  const [forma, setForma] = useState<FormaPagamento | null>(null)
  const [valor, setValor] = useState('')
  const [percentual, setPercentual] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [preConta, setPreConta] = useState(false)

  const status = comanda?.status
  const restante = comanda?.restante
  useEffect(() => {
    if (status) onStatus(status)
  }, [status, onStatus])
  // O valor sugerido acompanha o restante (inclusive após pagamentos feitos em outro dispositivo).
  useEffect(() => {
    if (restante !== undefined) setValor(restante.replace('.', ','))
  }, [restante])
  useEffect(() => {
    if (comanda?.taxa_servico.percentual) setPercentual(String(Number(comanda.taxa_servico.percentual)))
  }, [comanda?.taxa_servico.percentual])

  if (!comanda) {
    return <p className="vazio">{desatualizado ? 'Não foi possível carregar a comanda; tentando novamente…' : 'Carregando…'}</p>
  }

  if (comanda.status !== 'PRE_CONTA') {
    return (
      <section>
        <h1>Fechamento — Mesa {comanda.mesa.numero}</h1>
        <p className="aviso">
          {comanda.status === 'ABERTA'
            ? 'A comanda voltou a ficar aberta (houve alteração nos itens). Gere a pré-conta novamente para receber.'
            : 'Esta comanda já foi encerrada.'}
        </p>
        <button className="secundario" onClick={comanda.status === 'ABERTA' ? onVoltarParaComanda : onEncerrada}>
          {comanda.status === 'ABERTA' ? 'Voltar para a comanda' : 'Voltar ao mapa de mesas'}
        </button>
      </section>
    )
  }

  async function executar(acao: () => Promise<Comanda>, sucesso: string) {
    setEnviando(true)
    try {
      definir(await acao())
      mostrar(sucesso)
    } catch (erro) {
      mostrar(mensagemDeErro(erro), 'erro')
    } finally {
      setEnviando(false)
    }
  }

  async function confirmar() {
    if (!comanda || !forma) return
    setEnviando(true)
    try {
      const atualizada = await registrarPagamento(comanda.id, forma, paraDecimal(valor))
      if (atualizada.status === 'FECHADA') {
        mostrar(`Pagamento em ${ROTULOS_FORMA[forma]} registrado. Mesa ${atualizada.mesa.numero} liberada.`)
        onEncerrada()
        return
      }
      definir(atualizada)
      setForma(null)
      mostrar(`Pagamento de ${emReais(paraDecimal(valor))} em ${ROTULOS_FORMA[forma]} registrado`)
    } catch (erro) {
      mostrar(mensagemDeErro(erro), 'erro')
    } finally {
      setEnviando(false)
    }
  }

  const taxa = comanda.taxa_servico
  const itens = comanda.itens.filter((item) => item.status !== 'CANCELADO')

  return (
    <section>
      <div className="cabecalho-comanda">
        <div>
          <h1>Fechamento — Mesa {comanda.mesa.numero}</h1>
          <p className="subtitulo">Confira a pré-conta e registre a forma de pagamento para encerrar a comanda.</p>
        </div>
        <button className="secundario" onClick={() => setPreConta(true)}>
          Imprimir pré-conta
        </button>
      </div>

      <div className="colunas-pagamento">
        <div className="painel-comanda">
          <h2>Resumo da comanda</h2>
          <ul className="resumo-itens">
            {itens.map((item) => (
              <li key={item.id} className="linha-valor">
                <span>
                  {item.quantidade}× {item.produto_nome}
                </span>
                <span>{emReais(item.subtotal)}</span>
              </li>
            ))}
          </ul>
          <p className="linha-valor">
            <span>Subtotal</span>
            <span>{emReais(comanda.subtotal)}</span>
          </p>
          <div className="linha-valor taxa">
            <label>
              <input
                type="checkbox"
                checked={taxa.aplicada}
                disabled={enviando}
                onChange={(e) =>
                  executar(
                    () => alterarTaxaServico(comanda.id, { aplicada: e.target.checked }),
                    e.target.checked ? 'Taxa de serviço incluída' : 'Taxa de serviço removida',
                  )
                }
              />
              Taxa de serviço
            </label>
            <span className="percentual">
              <input
                aria-label="Percentual da taxa de serviço"
                inputMode="decimal"
                value={percentual}
                disabled={!taxa.aplicada || enviando}
                onChange={(e) => setPercentual(e.target.value)}
                onBlur={() => {
                  if (paraDecimal(percentual) !== String(Number(taxa.percentual)))
                    executar(() => alterarTaxaServico(comanda.id, { percentual: paraDecimal(percentual) }), 'Percentual atualizado')
                }}
              />
              %
            </span>
            <span>{emReais(taxa.valor)}</span>
          </div>
          <div className="total">
            <span>Total a pagar</span>
            <strong>{emReais(comanda.total)}</strong>
          </div>
          <p className="linha-valor">
            <span>Pago</span>
            <span>{emReais(comanda.pago)}</span>
          </p>
          <p className="linha-valor restante">
            <span>Restante</span>
            <strong>{emReais(comanda.restante)}</strong>
          </p>

          {comanda.pagamentos.length > 0 && (
            <>
              <h2>Pagamentos registrados</h2>
              <ul className="itens">
                {comanda.pagamentos.map((pagamento) => (
                  <li key={pagamento.id} className="linha-valor">
                    <span>
                      {ROTULOS_FORMA[pagamento.forma]} · {formatoHora.format(new Date(pagamento.registrado_em))}
                      {pagamento.registrado_por && ` · ${pagamento.registrado_por}`}
                    </span>
                    <span>
                      {emReais(pagamento.valor)}{' '}
                      <button
                        className="cancelar"
                        aria-label={`Remover pagamento de ${emReais(pagamento.valor)}`}
                        title="Remover pagamento registrado por engano"
                        disabled={enviando}
                        onClick={() =>
                          window.confirm(`Remover o pagamento de ${emReais(pagamento.valor)} em ${ROTULOS_FORMA[pagamento.forma]}?`) &&
                          executar(() => removerPagamento(comanda.id, pagamento.id), 'Pagamento removido')
                        }
                      >
                        ×
                      </button>
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <aside className="painel-comanda">
          <h2>Forma de pagamento</h2>
          <div className="formas">
            {FORMAS.map((opcao) => (
              <button
                key={opcao}
                className={`forma ${forma === opcao ? 'selecionada' : ''}`}
                aria-pressed={forma === opcao}
                onClick={() => setForma(opcao)}
              >
                {ROTULOS_FORMA[opcao]}
              </button>
            ))}
          </div>
          <label className="campo-valor">
            Valor (R$)
            <input inputMode="decimal" value={valor} onChange={(e) => setValor(e.target.value)} />
          </label>
          <button className="primario" onClick={confirmar} disabled={!forma || enviando || !valor.trim()}>
            Confirmar pagamento
          </button>
          <button className="secundario" onClick={onVoltarParaComanda}>
            Voltar para a comanda
          </button>
        </aside>
      </div>

      {preConta && <PreContaImpressao comanda={comanda} onFechar={() => setPreConta(false)} />}
    </section>
  )
}
