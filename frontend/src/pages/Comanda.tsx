import { useCallback, useEffect, useState } from 'react'

import { obterCardapio, type CategoriaCardapio, type ProdutoCardapio } from '../api/cardapio'
import { ErroApi, emReais } from '../api/cliente'
import {
  adicionarItem,
  alterarItem,
  cancelarItem,
  obterComanda,
  type Comanda,
  type ItemComanda,
  type StatusItem,
} from '../api/comandas'
import { useMensagens } from '../components/Mensagens'
import { usePolling } from '../hooks/usePolling'

const INTERVALO_ATUALIZACAO_MS = 5000

const ROTULOS_ITEM: Record<StatusItem, string> = {
  PENDENTE: 'Pendente',
  EM_PREPARO: 'Em preparo',
  PRONTO: 'Pronto',
  ENTREGUE: 'Entregue',
  CANCELADO: 'Cancelado',
}

function minutosDesde(iso: string): number {
  return Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 60000))
}

function mensagemDeErro(erro: unknown): string {
  return erro instanceof ErroApi ? erro.message : 'Não foi possível concluir a operação'
}

function ProdutoLinha({ produto, onAdicionar }: { produto: ProdutoCardapio; onAdicionar: (obs: string) => Promise<boolean> }) {
  const [comObservacao, setComObservacao] = useState(false)
  const [observacao, setObservacao] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function adicionar() {
    setEnviando(true)
    if (await onAdicionar(observacao)) {
      setObservacao('')
      setComObservacao(false)
    }
    setEnviando(false)
  }

  return (
    <li className={`produto ${produto.disponivel ? '' : 'indisponivel'}`}>
      <div className="produto-info">
        <strong>{produto.nome}</strong>
        {produto.descricao && <small>{produto.descricao}</small>}
        {comObservacao && (
          <input
            className="observacao"
            value={observacao}
            maxLength={200}
            placeholder="Observação (ex.: sem sal)"
            onChange={(e) => setObservacao(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && adicionar()}
            autoFocus
          />
        )}
      </div>
      <span className="preco">{emReais(produto.preco)}</span>
      {produto.disponivel ? (
        <div className="produto-acoes">
          <button className="link" onClick={() => setComObservacao(!comObservacao)} aria-label={`Observação para ${produto.nome}`}>
            Obs.
          </button>
          <button className="adicionar" onClick={adicionar} disabled={enviando} aria-label={`Adicionar ${produto.nome}`}>
            + Adicionar
          </button>
        </div>
      ) : (
        <span className="selo-indisponivel">Indisponível</span>
      )}
    </li>
  )
}

function ItemLinha({ item, onAlterar, onCancelar }: {
  item: ItemComanda
  onAlterar: (quantidade: number) => void
  onCancelar: () => void
}) {
  const pendente = item.status === 'PENDENTE'
  const cancelado = item.status === 'CANCELADO'
  return (
    <li className={`item item-${item.status.toLowerCase()}`}>
      <div className="item-quantidade">
        {pendente ? (
          <>
            <button onClick={() => onAlterar(item.quantidade - 1)} disabled={item.quantidade <= 1} aria-label="Diminuir">
              −
            </button>
            <span>{item.quantidade}</span>
            <button onClick={() => onAlterar(item.quantidade + 1)} disabled={item.quantidade >= 99} aria-label="Aumentar">
              +
            </button>
          </>
        ) : (
          <span>{item.quantidade}×</span>
        )}
      </div>
      <div className="item-info">
        <strong>{item.produto_nome}</strong>
        {item.observacao && <small className="obs">{item.observacao}</small>}
        <small className={`status-item status-item-${item.status.toLowerCase()}`}>{ROTULOS_ITEM[item.status]}</small>
      </div>
      <span className="subtotal">{emReais(item.subtotal)}</span>
      {!cancelado && (
        <button className="cancelar" onClick={onCancelar} aria-label={`Cancelar ${item.produto_nome}`} title="Cancelar item">
          ×
        </button>
      )}
    </li>
  )
}

export default function ComandaPage({ comandaId, onVoltar }: { comandaId: number; onVoltar: () => void }) {
  const mostrar = useMensagens()
  const buscarComanda = useCallback(() => obterComanda(comandaId), [comandaId])
  const { dados: comanda, desatualizado, definir } = usePolling<Comanda>(buscarComanda, INTERVALO_ATUALIZACAO_MS)
  const [cardapio, setCardapio] = useState<CategoriaCardapio[] | null>(null)

  const carregarCardapio = useCallback(() => {
    obterCardapio()
      .then(setCardapio)
      .catch((erro) => mostrar(mensagemDeErro(erro), 'erro'))
  }, [mostrar])

  useEffect(carregarCardapio, [carregarCardapio])

  async function executar(acao: () => Promise<Comanda>, sucesso: string): Promise<boolean> {
    try {
      definir(await acao())
      mostrar(sucesso)
      return true
    } catch (erro) {
      mostrar(mensagemDeErro(erro), 'erro')
      if (erro instanceof ErroApi && erro.message === 'Item indisponível') carregarCardapio()
      return false
    }
  }

  if (!comanda) {
    return <p className="vazio">{desatualizado ? 'Não foi possível carregar a comanda; tentando novamente…' : 'Carregando comanda…'}</p>
  }

  const ativos = comanda.itens.filter((item) => item.status !== 'CANCELADO')

  return (
    <section className="tela-comanda">
      <div className="cabecalho-comanda">
        <div>
          <h1>Comanda — Mesa {comanda.mesa.numero}</h1>
          <p className="subtitulo">Selecione itens do cardápio para adicionar à comanda.</p>
        </div>
        <button className="secundario" onClick={onVoltar}>
          ← Mapa de mesas
        </button>
      </div>

      {desatualizado && (
        <p className="aviso" role="alert">
          Não foi possível atualizar a comanda. Os dados exibidos podem estar desatualizados; tentando novamente…
        </p>
      )}

      <div className="colunas-comanda">
        <div className="cardapio">
          {!cardapio && <p className="vazio">Carregando cardápio…</p>}
          {cardapio?.map((categoria) => (
            <section key={categoria.id} className="categoria">
              <h2>{categoria.nome}</h2>
              <ul>
                {categoria.produtos.map((produto) => (
                  <ProdutoLinha
                    key={produto.id}
                    produto={produto}
                    onAdicionar={(obs) => executar(() => adicionarItem(comanda.id, produto.id, obs), `${produto.nome} adicionado`)}
                  />
                ))}
              </ul>
            </section>
          ))}
        </div>

        <aside className="painel-comanda">
          <h2>Comanda ativa</h2>
          <p className="meta">
            Aberta há {minutosDesde(comanda.aberta_em)} min
            {comanda.responsavel && ` · Garçom: ${comanda.responsavel.nome}`}
          </p>

          {comanda.itens.length === 0 ? (
            <p className="vazio">Nenhum item lançado.</p>
          ) : (
            <ul className="itens">
              {comanda.itens.map((item) => (
                <ItemLinha
                  key={item.id}
                  item={item}
                  onAlterar={(quantidade) =>
                    executar(() => alterarItem(comanda.id, item.id, { quantidade }), 'Quantidade atualizada')
                  }
                  onCancelar={() => executar(() => cancelarItem(comanda.id, item.id), `${item.produto_nome} cancelado`)}
                />
              ))}
            </ul>
          )}

          <div className="total">
            <span>Total{ativos.length > 0 && ` (${ativos.reduce((soma, item) => soma + item.quantidade, 0)} itens)`}</span>
            <strong>{emReais(comanda.total)}</strong>
          </div>
          <button className="primario" disabled title="Disponível no próximo incremento">
            Enviar itens para a cozinha
          </button>
          <button className="secundario" disabled title="Disponível em um próximo incremento">
            Gerar pré-conta
          </button>
        </aside>
      </div>
    </section>
  )
}
