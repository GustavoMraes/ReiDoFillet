import { emReais } from '../api/cliente'
import type { Comanda } from '../api/comandas'

const formatoDataHora = new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'short',
  timeStyle: 'short',
  timeZone: 'America/Sao_Paulo',
})

/** Pré-conta para conferência do consumidor (RF09). Na impressão, só este conteúdo aparece. */
export default function PreContaImpressao({ comanda, onFechar }: { comanda: Comanda; onFechar: () => void }) {
  const itens = comanda.itens.filter((item) => item.status !== 'CANCELADO')
  const { taxa_servico: taxa } = comanda
  return (
    <div className="sobreposicao" role="dialog" aria-modal="true" aria-label="Pré-conta">
      <div className="cupom-moldura">
        <article className="cupom impressao">
          <header>
            <strong>REI DO FILET</strong>
            <span>Pré-conta — confira antes de pagar</span>
          </header>
          <p className="cupom-mesa">MESA {comanda.mesa.numero}</p>
          <p>
            {comanda.responsavel && <>Garçom: {comanda.responsavel.nome}<br /></>}
            {comanda.pre_conta_em && formatoDataHora.format(new Date(comanda.pre_conta_em))}
          </p>
          <ul>
            {itens.map((item) => (
              <li key={item.id} className="linha-valor">
                <span>
                  {item.quantidade}× {item.produto_nome}
                </span>
                <span>{emReais(item.subtotal)}</span>
              </li>
            ))}
          </ul>
          <div className="cupom-totais">
            <p className="linha-valor">
              <span>Subtotal</span>
              <span>{emReais(comanda.subtotal)}</span>
            </p>
            <p className="linha-valor">
              <span>
                Taxa de serviço{taxa.aplicada && taxa.percentual ? ` (${Number(taxa.percentual)}%)` : ' (não incluída)'}
              </span>
              <span>{emReais(taxa.valor)}</span>
            </p>
            <p className="linha-valor cupom-total">
              <span>TOTAL</span>
              <span>{emReais(comanda.total)}</span>
            </p>
          </div>
        </article>
        <div className="cupom-acoes">
          <button className="primario" onClick={() => window.print()}>
            Imprimir pré-conta
          </button>
          <button className="secundario" onClick={onFechar}>
            Fechar
          </button>
        </div>
      </div>
    </div>
  )
}
