import { useState } from 'react'

import { ErroApi } from '../api/cliente'
import { marcarEntregue, marcarPronto, obterPainel, type ItemCozinha, type PainelCozinha } from '../api/cozinha'
import { useMensagens } from '../components/Mensagens'
import { usePolling } from '../hooks/usePolling'

const INTERVALO_ATUALIZACAO_MS = 5000

function CartaoCozinha({ item, acao, ocupado, onAcao }: {
  item: ItemCozinha
  acao: string
  ocupado: boolean
  onAcao: () => void
}) {
  return (
    <li className="cartao-cozinha">
      <div className="cartao-cozinha-topo">
        <strong>Mesa {item.mesa_numero}</strong>
        <span>há {item.minutos_desde_envio} min</span>
      </div>
      <p className="cartao-cozinha-item">
        {item.quantidade}× {item.produto_nome}
      </p>
      {item.observacao && <p className="cartao-cozinha-obs">{item.observacao}</p>}
      <button className="secundario" onClick={onAcao} disabled={ocupado}>
        {acao}
      </button>
    </li>
  )
}

function Coluna({ titulo, itens, vazio, acao, ocupado, onAcao }: {
  titulo: string
  itens: ItemCozinha[]
  vazio: string
  acao: string
  ocupado: number | null
  onAcao: (item: ItemCozinha) => void
}) {
  return (
    <section className="coluna-cozinha">
      <h2>
        {titulo} <span className="contagem">{itens.length}</span>
      </h2>
      {itens.length === 0 ? (
        <p className="vazio">{vazio}</p>
      ) : (
        <ul>
          {itens.map((item) => (
            <CartaoCozinha key={item.id} item={item} acao={acao} ocupado={ocupado === item.id} onAcao={() => onAcao(item)} />
          ))}
        </ul>
      )}
    </section>
  )
}

export default function Cozinha() {
  const { dados: painel, desatualizado, definir } = usePolling<PainelCozinha>(obterPainel, INTERVALO_ATUALIZACAO_MS)
  const mostrar = useMensagens()
  const [ocupado, setOcupado] = useState<number | null>(null)

  async function executar(item: ItemCozinha, acao: (id: number) => Promise<PainelCozinha>, sucesso: string) {
    setOcupado(item.id)
    try {
      definir(await acao(item.id))
      mostrar(`${item.produto_nome} (mesa ${item.mesa_numero}) ${sucesso}`)
    } catch (erro) {
      mostrar(erro instanceof ErroApi ? erro.message : 'Não foi possível atualizar o item', 'erro')
    } finally {
      setOcupado(null)
    }
  }

  return (
    <section>
      <h1>Painel da Cozinha</h1>
      <p className="subtitulo">Itens enviados pelo salão, organizados por status de preparo.</p>

      {desatualizado && (
        <p className="aviso" role="alert">
          {painel
            ? 'Não foi possível atualizar o painel. Os dados exibidos podem estar desatualizados; tentando novamente…'
            : 'Não foi possível carregar o painel; tentando novamente…'}
        </p>
      )}
      {!painel && !desatualizado && <p className="vazio">Carregando painel…</p>}

      {painel && (
        <div className="colunas-cozinha">
          <Coluna
            titulo="Em preparo"
            itens={painel.em_preparo}
            vazio="Nenhum item em preparo. Os itens aparecem aqui assim que o garçom envia o pedido."
            acao="Marcar como pronto"
            ocupado={ocupado}
            onAcao={(item) => executar(item, marcarPronto, 'pronto')}
          />
          <Coluna
            titulo="Pronto"
            itens={painel.pronto}
            vazio="Nenhum item aguardando entrega."
            acao="Marcar como entregue"
            ocupado={ocupado}
            onAcao={(item) => executar(item, marcarEntregue, 'entregue')}
          />
        </div>
      )}
    </section>
  )
}
