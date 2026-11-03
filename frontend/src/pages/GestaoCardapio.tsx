import { useCallback, useState, type FormEvent } from 'react'

import {
  alterarProduto,
  criarCategoria,
  criarProduto,
  excluirCategoria,
  moverCategoria,
  obterCardapioCompleto,
  renomearCategoria,
  type CategoriaAdmin,
  type ProdutoAdmin,
} from '../api/admin'
import { definirDisponibilidade, obterCardapio } from '../api/cardapio'
import { ErroApi, emReais, paraDecimal } from '../api/cliente'
import Dialogo from '../components/Dialogo'
import { useMensagens } from '../components/Mensagens'
import { usePolling } from '../hooks/usePolling'

const INTERVALO_ATUALIZACAO_MS = 10000

function mensagemDeErro(erro: unknown): string {
  return erro instanceof ErroApi ? erro.message : 'Não foi possível concluir a operação'
}

/** O funcionário vê o cardápio de pedidos (só produtos ativos), no mesmo formato da visão do administrador. */
async function cardapioDoFuncionario(): Promise<CategoriaAdmin[]> {
  return (await obterCardapio()).map((categoria, ordem) => ({
    id: categoria.id,
    nome: categoria.nome,
    ordem,
    produtos: categoria.produtos.map((p) => ({ ...p, categoria_id: categoria.id, ativo: true })),
  }))
}

type Edicao =
  | { tipo: 'produto'; produto: ProdutoAdmin | null }
  | { tipo: 'categoria'; categoria: CategoriaAdmin | null }
  | { tipo: 'excluir-categoria'; categoria: CategoriaAdmin }

function FormProduto({
  produto,
  categorias,
  onSalvar,
  onFechar,
}: {
  produto: ProdutoAdmin | null
  categorias: CategoriaAdmin[]
  onSalvar: (dados: { categoria_id: number; nome: string; descricao: string | null; preco: string }) => Promise<void>
  onFechar: () => void
}) {
  const [categoriaId, setCategoriaId] = useState(String(produto?.categoria_id ?? categorias[0]?.id ?? ''))
  const [nome, setNome] = useState(produto?.nome ?? '')
  const [descricao, setDescricao] = useState(produto?.descricao ?? '')
  const [preco, setPreco] = useState(produto ? produto.preco.replace('.', ',') : '')
  const [enviando, setEnviando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setEnviando(true)
    try {
      await onSalvar({ categoria_id: Number(categoriaId), nome, descricao: descricao || null, preco: paraDecimal(preco) })
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Dialogo
      titulo={produto ? `Editar ${produto.nome}` : 'Novo produto'}
      acoes={
        <>
          <button type="button" className="secundario" disabled={enviando} onClick={onFechar}>
            Cancelar
          </button>
          <button type="submit" form="form-produto" className="primario" disabled={enviando}>
            {enviando ? 'Salvando…' : 'Salvar'}
          </button>
        </>
      }
    >
      <form id="form-produto" className="form-dialogo" onSubmit={enviar}>
        <label className="campo">
          Categoria
          <select required value={categoriaId} onChange={(e) => setCategoriaId(e.target.value)}>
            {categorias.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
        </label>
        <label className="campo">
          Nome
          <input required maxLength={100} value={nome} onChange={(e) => setNome(e.target.value)} />
        </label>
        <label className="campo">
          Descrição (opcional)
          <textarea maxLength={300} rows={2} value={descricao} onChange={(e) => setDescricao(e.target.value)} />
        </label>
        <label className="campo">
          Preço (R$)
          <input required inputMode="decimal" placeholder="0,00" value={preco} onChange={(e) => setPreco(e.target.value)} />
        </label>
        {produto && (
          <p className="meta">Itens já lançados em comandas mantêm o preço do momento do lançamento.</p>
        )}
      </form>
    </Dialogo>
  )
}

function FormCategoria({
  categoria,
  onSalvar,
  onFechar,
}: {
  categoria: CategoriaAdmin | null
  onSalvar: (nome: string) => Promise<void>
  onFechar: () => void
}) {
  const [nome, setNome] = useState(categoria?.nome ?? '')
  const [enviando, setEnviando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setEnviando(true)
    try {
      await onSalvar(nome)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Dialogo
      titulo={categoria ? `Renomear ${categoria.nome}` : 'Nova categoria'}
      acoes={
        <>
          <button type="button" className="secundario" disabled={enviando} onClick={onFechar}>
            Cancelar
          </button>
          <button type="submit" form="form-categoria" className="primario" disabled={enviando}>
            {enviando ? 'Salvando…' : 'Salvar'}
          </button>
        </>
      }
    >
      <form id="form-categoria" className="form-dialogo" onSubmit={enviar}>
        <label className="campo">
          Nome da categoria
          <input required maxLength={50} value={nome} onChange={(e) => setNome(e.target.value)} />
        </label>
        {!categoria && <p className="meta">A nova categoria entra no fim do cardápio; use as setas para reordenar.</p>}
      </form>
    </Dialogo>
  )
}

export default function GestaoCardapio({ administrador }: { administrador: boolean }) {
  const mostrar = useMensagens()
  const buscar = useCallback(() => (administrador ? obterCardapioCompleto() : cardapioDoFuncionario()), [administrador])
  const { dados: categorias, desatualizado, definir } = usePolling<CategoriaAdmin[]>(buscar, INTERVALO_ATUALIZACAO_MS)
  const [edicao, setEdicao] = useState<Edicao | null>(null)
  const [ocupado, setOcupado] = useState(false)

  /** Executa uma operação de administrador que devolve o cardápio completo atualizado. */
  async function executar(operacao: () => Promise<CategoriaAdmin[]>, sucesso: string): Promise<boolean> {
    setOcupado(true)
    try {
      definir(await operacao())
      mostrar(sucesso)
      return true
    } catch (erro) {
      mostrar(mensagemDeErro(erro), 'erro')
      return false
    } finally {
      setOcupado(false)
    }
  }

  async function alternarDisponibilidade(produto: ProdutoAdmin) {
    setOcupado(true)
    try {
      const atualizado = await definirDisponibilidade(produto.id, !produto.disponivel)
      definir(
        (categorias ?? []).map((c) => ({
          ...c,
          produtos: c.produtos.map((p) => (p.id === produto.id ? { ...p, disponivel: atualizado.disponivel } : p)),
        })),
      )
      mostrar(atualizado.disponivel ? `${produto.nome} disponível novamente` : `${produto.nome} marcado como esgotado`)
    } catch (erro) {
      mostrar(mensagemDeErro(erro), 'erro')
    } finally {
      setOcupado(false)
    }
  }

  async function salvarProduto(produto: ProdutoAdmin | null, dados: Parameters<typeof criarProduto>[0]) {
    const ok = await executar(
      () => (produto ? alterarProduto(produto.id, dados) : criarProduto(dados)),
      produto ? `${dados.nome.trim()} atualizado` : `${dados.nome.trim()} cadastrado`,
    )
    if (ok) setEdicao(null)
  }

  async function salvarCategoria(categoria: CategoriaAdmin | null, nome: string) {
    const ok = await executar(
      () => (categoria ? renomearCategoria(categoria.id, nome) : criarCategoria(nome)),
      categoria ? 'Categoria renomeada' : `Categoria ${nome.trim()} criada`,
    )
    if (ok) setEdicao(null)
  }

  if (!categorias) {
    return <p className="vazio">{desatualizado ? 'Não foi possível carregar o cardápio; tentando novamente…' : 'Carregando…'}</p>
  }

  return (
    <section>
      <div className="cabecalho-comanda">
        <div>
          <h1>Cardápio</h1>
          <p className="subtitulo">
            {administrador
              ? 'Cadastre produtos e categorias, ajuste preços e marque o que está esgotado no dia.'
              : 'Marque os produtos que acabaram hoje; eles ficam indisponíveis para novos pedidos.'}
          </p>
        </div>
        {administrador && (
          <div className="acoes-cabecalho">
            <button className="secundario" onClick={() => setEdicao({ tipo: 'categoria', categoria: null })}>
              Nova categoria
            </button>
            <button
              className="primario"
              disabled={categorias.length === 0}
              onClick={() => setEdicao({ tipo: 'produto', produto: null })}
            >
              Novo produto
            </button>
          </div>
        )}
      </div>

      {desatualizado && (
        <p className="aviso" role="alert">
          Não foi possível atualizar o cardápio. Os dados exibidos podem estar desatualizados; tentando novamente…
        </p>
      )}
      {categorias.length === 0 && <p className="vazio">Nenhuma categoria cadastrada.</p>}

      {categorias.map((categoria, posicao) => (
        <section key={categoria.id} className="grupo-cardapio">
          <div className="titulo-categoria">
            <h2>{categoria.nome}</h2>
            {administrador && (
              <div className="acoes-categoria">
                <button
                  className="link"
                  aria-label={`Mover ${categoria.nome} para cima`}
                  disabled={ocupado || posicao === 0}
                  onClick={() => executar(() => moverCategoria(categoria.id, 'acima'), 'Ordem atualizada')}
                >
                  ↑
                </button>
                <button
                  className="link"
                  aria-label={`Mover ${categoria.nome} para baixo`}
                  disabled={ocupado || posicao === categorias.length - 1}
                  onClick={() => executar(() => moverCategoria(categoria.id, 'abaixo'), 'Ordem atualizada')}
                >
                  ↓
                </button>
                <button className="link" onClick={() => setEdicao({ tipo: 'categoria', categoria })}>
                  Renomear
                </button>
                <button className="link" onClick={() => setEdicao({ tipo: 'excluir-categoria', categoria })}>
                  Excluir
                </button>
              </div>
            )}
          </div>

          {categoria.produtos.length === 0 && <p className="vazio">Nenhum produto nesta categoria.</p>}
          <ul className="lista-produtos">
            {categoria.produtos.map((produto) => (
              <li key={produto.id} className={produto.ativo ? 'produto-gestao' : 'produto-gestao inativo'}>
                <div className="produto-gestao-info">
                  <strong>{produto.nome}</strong>
                  {produto.descricao && <small>{produto.descricao}</small>}
                </div>
                <span className="produto-gestao-preco">{emReais(produto.preco)}</span>
                <div className="produto-gestao-selos">
                  {!produto.ativo && <span className="selo-indisponivel">Inativo</span>}
                  {produto.ativo && !produto.disponivel && <span className="selo-indisponivel">Indisponível</span>}
                </div>
                <div className="produto-gestao-acoes">
                  {produto.ativo && (
                    <button className="secundario" disabled={ocupado} onClick={() => alternarDisponibilidade(produto)}>
                      {produto.disponivel ? 'Marcar esgotado' : 'Marcar disponível'}
                    </button>
                  )}
                  {administrador && (
                    <>
                      <button className="secundario" disabled={ocupado} onClick={() => setEdicao({ tipo: 'produto', produto })}>
                        Editar
                      </button>
                      <button
                        className="secundario"
                        disabled={ocupado}
                        onClick={() =>
                          executar(
                            () => alterarProduto(produto.id, { ativo: !produto.ativo }),
                            produto.ativo ? `${produto.nome} retirado do cardápio` : `${produto.nome} de volta ao cardápio`,
                          )
                        }
                      >
                        {produto.ativo ? 'Desativar' : 'Reativar'}
                      </button>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}

      {edicao?.tipo === 'produto' && (
        <FormProduto
          produto={edicao.produto}
          categorias={categorias}
          onSalvar={(dados) => salvarProduto(edicao.produto, dados)}
          onFechar={() => setEdicao(null)}
        />
      )}
      {edicao?.tipo === 'categoria' && (
        <FormCategoria
          categoria={edicao.categoria}
          onSalvar={(nome) => salvarCategoria(edicao.categoria, nome)}
          onFechar={() => setEdicao(null)}
        />
      )}
      {edicao?.tipo === 'excluir-categoria' && (
        <Dialogo
          titulo="Excluir categoria"
          acoes={
            <>
              <button className="secundario" disabled={ocupado} onClick={() => setEdicao(null)}>
                Voltar
              </button>
              <button
                className="primario"
                disabled={ocupado}
                onClick={async () => {
                  const nome = edicao.categoria.nome
                  if (await executar(() => excluirCategoria(edicao.categoria.id), `Categoria ${nome} excluída`)) {
                    setEdicao(null)
                  }
                }}
              >
                Excluir
              </button>
            </>
          }
        >
          <p>
            Excluir a categoria <strong>{edicao.categoria.nome}</strong>? Só é possível excluir categorias sem
            produtos.
          </p>
        </Dialogo>
      )}
    </section>
  )
}
