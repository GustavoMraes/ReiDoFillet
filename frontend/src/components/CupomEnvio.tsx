import type { Cupom } from '../api/comandas'

const formatoDataHora = new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'short',
  timeStyle: 'short',
  timeZone: 'America/Sao_Paulo',
})

/** Cupom do envio à cozinha (RF12). Na impressão, só este conteúdo aparece (ver @media print). */
export default function CupomEnvio({ cupom, onFechar }: { cupom: Cupom; onFechar: () => void }) {
  return (
    <div className="sobreposicao" role="dialog" aria-modal="true" aria-label="Cupom do envio à cozinha">
      <div className="cupom-moldura">
        <article className="cupom">
          <header>
            <strong>REI DO FILET</strong>
            <span>Pedido para a cozinha</span>
          </header>
          <p className="cupom-mesa">MESA {cupom.mesa_numero}</p>
          <p>
            Garçom: {cupom.garcom}
            <br />
            {formatoDataHora.format(new Date(cupom.enviado_em))}
          </p>
          <ul>
            {cupom.itens.map((item, indice) => (
              <li key={indice}>
                <strong>
                  {item.quantidade}× {item.produto_nome}
                </strong>
                {item.observacao && <span>Obs.: {item.observacao}</span>}
              </li>
            ))}
          </ul>
        </article>
        <div className="cupom-acoes">
          <button className="primario" onClick={() => window.print()}>
            Imprimir cupom
          </button>
          <button className="secundario" onClick={onFechar}>
            Fechar
          </button>
        </div>
      </div>
    </div>
  )
}
