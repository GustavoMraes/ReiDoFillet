import { Fragment, useEffect, useRef, useState } from 'react'

import { ErroApi, emReais } from '../api/cliente'
import { ROTULOS_FORMA } from '../api/comandas'
import {
  consultarAuditoria,
  obterFinanceiro,
  obterOperacional,
  obterOpcoesAuditoria,
  USUARIO_SISTEMA,
  type FiltrosAuditoria,
  type OpcoesAuditoria,
  type PaginaAuditoria,
  type Periodo,
  type RelatorioFinanceiro,
  type RelatorioOperacional,
} from '../api/relatorios'
import { hojeLocal } from '../api/reservas'
import { baixarArquivo, dataCurta, dataHora, decimalBr, gerarCsv } from '../utils/planilha'

export type SecaoRelatorio = 'Operacional' | 'Financeiro' | 'Auditoria'

/** Período pedido pelo usuário; `versao` muda a cada clique em "Consultar" (sem atualização automática). */
interface Pedido {
  periodo: Periodo
  versao: number
}

function mensagemDeErro(erro: unknown): string {
  return erro instanceof ErroApi ? erro.message : 'Não foi possível gerar o relatório'
}

function deslocarDias(data: string, dias: number): string {
  const d = new Date(`${data}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + dias)
  return d.toISOString().slice(0, 10)
}

const ATALHOS: { rotulo: string; periodo: () => Periodo }[] = [
  { rotulo: 'Hoje', periodo: () => ({ inicio: hojeLocal(), fim: hojeLocal() }) },
  { rotulo: 'Últimos 7 dias', periodo: () => ({ inicio: deslocarDias(hojeLocal(), -6), fim: hojeLocal() }) },
  { rotulo: 'Mês atual', periodo: () => ({ inicio: `${hojeLocal().slice(0, 8)}01`, fim: hojeLocal() }) },
]

function descricaoPeriodo(periodo: Periodo): string {
  return periodo.inicio === periodo.fim
    ? dataCurta(periodo.inicio)
    : `${dataCurta(periodo.inicio)} a ${dataCurta(periodo.fim)}`
}

function nomeArquivo(prefixo: string, periodo: Periodo): string {
  return `${prefixo}_${periodo.inicio}_a_${periodo.fim}.csv`
}

/** Busca o relatório a cada pedido do usuário (e ao abrir a seção, se já houver um pedido). */
function useRelatorio<T, P>(pedido: P | null, buscar: (pedido: P) => Promise<T>) {
  const [dados, setDados] = useState<T | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [carregando, setCarregando] = useState(false)
  // Só um novo pedido refaz a consulta; a função de busca vai por referência.
  const buscarRef = useRef(buscar)
  buscarRef.current = buscar

  useEffect(() => {
    if (!pedido) return
    let ativo = true
    setCarregando(true)
    setErro(null)
    buscarRef
      .current(pedido)
      .then((resultado) => {
        if (ativo) setDados(resultado)
      })
      .catch((falha) => {
        if (!ativo) return
        setDados(null)
        setErro(mensagemDeErro(falha))
      })
      .finally(() => {
        if (ativo) setCarregando(false)
      })
    return () => {
      ativo = false
    }
  }, [pedido])

  return { dados, erro, carregando }
}

const buscarOperacional = (pedido: Pedido) => obterOperacional(pedido.periodo)
const buscarFinanceiro = (pedido: Pedido) => obterFinanceiro(pedido.periodo)

function Estado({ pedido, erro, carregando }: { pedido: Pedido | null; erro: string | null; carregando: boolean }) {
  if (!pedido) return <p className="vazio">Escolha o período e clique em Consultar.</p>
  if (carregando) return <p className="vazio">Gerando relatório…</p>
  if (erro)
    return (
      <p className="erro" role="alert">
        {erro}
      </p>
    )
  return null
}

function Barra({ valor, maximo }: { valor: number; maximo: number }) {
  return (
    <span className="barra" aria-hidden="true">
      <span style={{ width: maximo > 0 ? `${(valor / maximo) * 100}%` : 0 }} />
    </span>
  )
}

// --- Operacional ---

function Operacional({ pedido }: { pedido: Pedido | null }) {
  const { dados: r, erro, carregando } = useRelatorio<RelatorioOperacional, Pedido>(pedido, buscarOperacional)
  if (!r || carregando || erro) return <Estado pedido={pedido} erro={erro} carregando={carregando} />

  const maxDia = Math.max(0, ...r.por_dia.map((d) => d.comandas))
  const maxHora = Math.max(0, ...r.por_hora.map((h) => h.comandas))
  const baixarProdutos = () =>
    baixarArquivo(
      nomeArquivo('produtos', r.periodo),
      gerarCsv(
        ['Posição', 'Produto', 'Quantidade', 'Valor vendido (R$)'],
        r.produtos.map((p, i) => [i + 1, p.nome, p.quantidade, decimalBr(p.valor)]),
      ),
    )
  const baixarMovimento = () =>
    baixarArquivo(
      nomeArquivo('movimento', r.periodo),
      gerarCsv(
        ['Data', 'Comandas abertas', 'Faturamento (R$)'],
        r.por_dia.map((d) => [dataCurta(d.data), d.comandas, decimalBr(d.faturamento)]),
      ),
    )

  return (
    <article className="impressao relatorio-impresso">
      <header className="relatorio-cabecalho">
        <div>
          <h2>Relatório operacional</h2>
          <p className="meta">
            {descricaoPeriodo(r.periodo)} · comandas abertas no período; valores, tempos e produtos das que já fecharam
          </p>
        </div>
        <div className="acoes-cabecalho nao-imprimir">
          <button className="secundario" onClick={baixarProdutos}>
            CSV de produtos
          </button>
          <button className="secundario" onClick={baixarMovimento}>
            CSV por dia
          </button>
          <button className="secundario" onClick={() => window.print()}>
            Imprimir
          </button>
        </div>
      </header>

      <div className="indicadores">
        <div className="indicador">
          <small>Comandas</small>
          <strong>{r.comandas.total}</strong>
          <span>
            {r.comandas.em_aberto} em aberto · {r.comandas.fechadas} fechadas · {r.comandas.canceladas} canceladas
          </span>
        </div>
        <div className="indicador">
          <small>Faturamento</small>
          <strong>{emReais(r.faturamento)}</strong>
          <span>com taxa de serviço</span>
        </div>
        <div className="indicador">
          <small>Ticket médio</small>
          <strong>{r.ticket_medio ? emReais(r.ticket_medio) : '—'}</strong>
          <span>por comanda fechada</span>
        </div>
        <div className="indicador">
          <small>Tempo médio de atendimento</small>
          <strong>{r.tempo_medio_minutos !== null ? `${r.tempo_medio_minutos} min` : '—'}</strong>
          <span>da abertura ao fechamento</span>
        </div>
      </div>

      <section className="bloco-relatorio">
        <h3>Produtos mais vendidos</h3>
        {r.produtos.length === 0 ? (
          <p className="vazio">Nenhum produto vendido em comandas fechadas no período.</p>
        ) : (
          <div className="tabela-rolavel">
            <table className="tabela">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Produto</th>
                  <th className="numero">Qtd.</th>
                  <th className="numero">Valor</th>
                </tr>
              </thead>
              <tbody>
                {r.produtos.map((p, i) => (
                  <tr key={p.produto_id}>
                    <td>{i + 1}</td>
                    <td>{p.nome}</td>
                    <td className="numero">{p.quantidade}</td>
                    <td className="numero">{emReais(p.valor)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <div className="colunas-relatorio">
        <section className="bloco-relatorio">
          <h3>Movimento por dia</h3>
          <ul className="grafico-barras">
            {r.por_dia.map((d) => (
              <li key={d.data}>
                <span className="rotulo">{dataCurta(d.data).slice(0, 5)}</span>
                <Barra valor={d.comandas} maximo={maxDia} />
                <span className="valor">
                  {d.comandas} · {emReais(d.faturamento)}
                </span>
              </li>
            ))}
          </ul>
        </section>
        <section className="bloco-relatorio">
          <h3>Comandas por horário de abertura</h3>
          <ul className="grafico-barras">
            {r.por_hora.map((h) => (
              <li key={h.hora}>
                <span className="rotulo">{String(h.hora).padStart(2, '0')}h</span>
                <Barra valor={h.comandas} maximo={maxHora} />
                <span className="valor">{h.comandas}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </article>
  )
}

// --- Financeiro ---

function Financeiro({ pedido }: { pedido: Pedido | null }) {
  const { dados: r, erro, carregando } = useRelatorio<RelatorioFinanceiro, Pedido>(pedido, buscarFinanceiro)
  if (!r || carregando || erro) return <Estado pedido={pedido} erro={erro} carregando={carregando} />

  const formas = r.totais.por_forma.map((f) => f.forma)
  const porForma = (pagamentos: RelatorioFinanceiro['comandas'][number]['pagamentos'], forma: string) =>
    pagamentos.filter((p) => p.forma === forma).reduce((soma, p) => soma + Number(p.valor), 0).toFixed(2)
  const baixar = () =>
    baixarArquivo(
      nomeArquivo('financeiro', r.periodo),
      gerarCsv(
        [
          'Comanda',
          'Mesa',
          'Abertura',
          'Fechamento',
          'Responsável',
          'Subtotal (R$)',
          'Taxa de serviço (R$)',
          'Total (R$)',
          ...formas.map((f) => `${ROTULOS_FORMA[f]} (R$)`),
        ],
        r.comandas.map((c) => [
          c.id,
          c.mesa_numero,
          dataHora(c.aberta_em),
          dataHora(c.fechada_em),
          c.responsavel,
          decimalBr(c.subtotal),
          decimalBr(c.taxa_servico),
          decimalBr(c.total),
          ...formas.map((f) => decimalBr(porForma(c.pagamentos, f))),
        ]),
      ),
    )

  return (
    <article className="impressao relatorio-impresso">
      <header className="relatorio-cabecalho">
        <div>
          <h2>Relatório financeiro</h2>
          <p className="meta">{descricaoPeriodo(r.periodo)} · comandas fechadas no período, pelo horário de fechamento</p>
        </div>
        <div className="acoes-cabecalho nao-imprimir">
          <button className="secundario" onClick={baixar} disabled={r.comandas.length === 0}>
            Baixar CSV
          </button>
          <button className="secundario" onClick={() => window.print()}>
            Imprimir
          </button>
        </div>
      </header>

      <div className="indicadores">
        <div className="indicador">
          <small>Total recebido</small>
          <strong>{emReais(r.totais.total)}</strong>
          <span>
            {r.totais.comandas} comanda(s) · subtotal {emReais(r.totais.subtotal)} · taxa {emReais(r.totais.taxa_servico)}
          </span>
        </div>
        {r.totais.por_forma.map((f) => (
          <div key={f.forma} className="indicador">
            <small>{ROTULOS_FORMA[f.forma]}</small>
            <strong>{emReais(f.valor)}</strong>
          </div>
        ))}
      </div>

      <section className="bloco-relatorio">
        <h3>Comandas fechadas</h3>
        {r.comandas.length === 0 ? (
          <p className="vazio">Nenhuma comanda fechada no período.</p>
        ) : (
          <div className="tabela-rolavel">
            <table className="tabela">
              <thead>
                <tr>
                  <th>Comanda</th>
                  <th>Mesa</th>
                  <th>Abertura</th>
                  <th>Fechamento</th>
                  <th>Responsável</th>
                  <th className="numero">Subtotal</th>
                  <th className="numero">Taxa</th>
                  <th className="numero">Total</th>
                  <th>Pagamentos</th>
                </tr>
              </thead>
              <tbody>
                {r.comandas.map((c) => (
                  <tr key={c.id}>
                    <td>#{c.id}</td>
                    <td>{c.mesa_numero}</td>
                    <td>{dataHora(c.aberta_em)}</td>
                    <td>{dataHora(c.fechada_em)}</td>
                    <td>{c.responsavel ?? '—'}</td>
                    <td className="numero">{emReais(c.subtotal)}</td>
                    <td className="numero">{emReais(c.taxa_servico)}</td>
                    <td className="numero">{emReais(c.total)}</td>
                    <td>{c.pagamentos.map((p) => `${ROTULOS_FORMA[p.forma]} ${emReais(p.valor)}`).join(' + ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </article>
  )
}

// --- Auditoria ---

function Auditoria({ pedido }: { pedido: Pedido | null }) {
  const [opcoes, setOpcoes] = useState<OpcoesAuditoria | null>(null)
  const [filtros, setFiltros] = useState<FiltrosAuditoria>({})
  const [aberto, setAberto] = useState<number | null>(null)
  // Os filtros escolhidos entram na próxima consulta: um novo período (pedido) volta à página 1.
  const [consulta, setConsulta] = useState<{ pedido: Pedido; pagina: number; filtros: FiltrosAuditoria } | null>(null)
  const filtrosRef = useRef(filtros)
  filtrosRef.current = filtros

  useEffect(() => {
    obterOpcoesAuditoria()
      .then(setOpcoes)
      .catch(() => setOpcoes({ usuarios: [], acoes: [], entidades: [] }))
  }, [])

  useEffect(() => {
    if (pedido) setConsulta({ pedido, pagina: 1, filtros: filtrosRef.current })
  }, [pedido])

  const { dados, erro, carregando } = useRelatorio<PaginaAuditoria, NonNullable<typeof consulta>>(consulta, (c) =>
    consultarAuditoria(c.pedido.periodo, { ...c.filtros, pagina: c.pagina }),
  )
  const irParaPagina = (pagina: number) => setConsulta((atual) => (atual ? { ...atual, pagina } : atual))

  const alterarFiltro = (campo: keyof FiltrosAuditoria, valor: string) =>
    setFiltros((atual) => ({ ...atual, [campo]: valor === '' ? undefined : campo === 'usuario_id' ? Number(valor) : valor }))

  return (
    <article>
      <div className="filtros-auditoria">
        <label className="campo">
          Usuário
          <select value={filtros.usuario_id ?? ''} onChange={(e) => alterarFiltro('usuario_id', e.target.value)}>
            <option value="">Todos</option>
            <option value={USUARIO_SISTEMA}>Sistema</option>
            {opcoes?.usuarios.map((u) => (
              <option key={u.id} value={u.id}>
                {u.nome}
              </option>
            ))}
          </select>
        </label>
        <label className="campo">
          Ação
          <select value={filtros.acao ?? ''} onChange={(e) => alterarFiltro('acao', e.target.value)}>
            <option value="">Todas</option>
            {opcoes?.acoes.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </label>
        <label className="campo">
          Entidade
          <select value={filtros.entidade ?? ''} onChange={(e) => alterarFiltro('entidade', e.target.value)}>
            <option value="">Todas</option>
            {opcoes?.entidades.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="meta">Os filtros valem na próxima consulta. Cada consulta também fica registrada na auditoria.</p>

      {!dados || carregando || erro ? (
        <Estado pedido={pedido} erro={erro} carregando={carregando} />
      ) : (
        <>
          <p className="meta">
            {dados.total} registro(s) · página {dados.pagina} de {dados.paginas}
          </p>
          {dados.registros.length === 0 ? (
            <p className="vazio">Nenhum registro no período com esses filtros.</p>
          ) : (
            <div className="tabela-rolavel">
              <table className="tabela">
                <thead>
                  <tr>
                    <th>Data e hora</th>
                    <th>Usuário</th>
                    <th>Ação</th>
                    <th>Entidade</th>
                    <th>Id</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {dados.registros.map((registro) => (
                    <Fragment key={registro.id}>
                      <tr>
                        <td>{dataHora(registro.criado_em)}</td>
                        <td>{registro.usuario ?? 'Sistema'}</td>
                        <td>{registro.acao}</td>
                        <td>{registro.entidade}</td>
                        <td>{registro.entidade_id}</td>
                        <td>
                          <button
                            className="link"
                            onClick={() => setAberto(aberto === registro.id ? null : registro.id)}
                            aria-expanded={aberto === registro.id}
                          >
                            {aberto === registro.id ? 'Ocultar' : 'Detalhes'}
                          </button>
                        </td>
                      </tr>
                      {aberto === registro.id && (
                        <tr className="detalhes-auditoria">
                          <td colSpan={6}>
                            <div>
                              <small>Antes</small>
                              <pre>{registro.dados_antes ? JSON.stringify(registro.dados_antes, null, 2) : '—'}</pre>
                            </div>
                            <div>
                              <small>Depois</small>
                              <pre>{registro.dados_depois ? JSON.stringify(registro.dados_depois, null, 2) : '—'}</pre>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="paginacao">
            <button className="secundario" disabled={dados.pagina <= 1} onClick={() => irParaPagina(dados.pagina - 1)}>
              ← Anterior
            </button>
            <button className="secundario" disabled={dados.pagina >= dados.paginas} onClick={() => irParaPagina(dados.pagina + 1)}>
              Próxima →
            </button>
          </div>
        </>
      )}
    </article>
  )
}

// --- Página ---

export default function Relatorios({ secoes }: { secoes: SecaoRelatorio[] }) {
  const [secao, setSecao] = useState<SecaoRelatorio>(secoes[0])
  const [periodo, setPeriodo] = useState<Periodo>(ATALHOS[0].periodo)
  const [pedido, setPedido] = useState<Pedido | null>(null)

  const consultar = (p: Periodo = periodo) => setPedido((atual) => ({ periodo: p, versao: (atual?.versao ?? 0) + 1 }))

  return (
    <section>
      <h1>Relatórios</h1>
      <p className="subtitulo">Consultas somente leitura; cada consulta fica registrada na auditoria.</p>

      <div className="secoes-relatorio" role="tablist">
        {secoes.map((s) => (
          <button
            key={s}
            role="tab"
            aria-selected={s === secao}
            className={s === secao ? 'forma selecionada' : 'forma'}
            onClick={() => setSecao(s)}
          >
            {s}
          </button>
        ))}
      </div>

      <form
        className="barra-relatorio"
        onSubmit={(evento) => {
          evento.preventDefault()
          consultar()
        }}
      >
        <label className="campo">
          De
          <input
            type="date"
            required
            value={periodo.inicio}
            onChange={(e) => setPeriodo((p) => ({ ...p, inicio: e.target.value }))}
          />
        </label>
        <label className="campo">
          Até
          <input
            type="date"
            required
            value={periodo.fim}
            onChange={(e) => setPeriodo((p) => ({ ...p, fim: e.target.value }))}
          />
        </label>
        <div className="atalhos-periodo">
          {ATALHOS.map((a) => (
            <button
              key={a.rotulo}
              type="button"
              className="link"
              onClick={() => {
                const novo = a.periodo()
                setPeriodo(novo)
                consultar(novo)
              }}
            >
              {a.rotulo}
            </button>
          ))}
        </div>
        <button type="submit" className="primario">
          Consultar
        </button>
      </form>

      {secao === 'Operacional' && <Operacional pedido={pedido} />}
      {secao === 'Financeiro' && <Financeiro pedido={pedido} />}
      {secao === 'Auditoria' && <Auditoria pedido={pedido} />}
    </section>
  )
}
