import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  /** `tela`: falha de uma tela, dentro do layout. `geral`: falha fora das telas, página inteira. */
  variante: 'tela' | 'geral'
  /** Variante de tela: leva à tela inicial do perfil. */
  onIrParaInicio?: () => void
  children: ReactNode
}

interface Estado {
  erro: Error | null
}

/**
 * Limite de erro do React: uma falha ao desenhar os filhos mostra um aviso em vez de desmontar a aplicação
 * (que deixaria a página em branco). Só componentes de classe capturam erros de renderização no React 18.
 */
export default class LimiteDeErro extends Component<Props, Estado> {
  state: Estado = { erro: null }

  static getDerivedStateFromError(erro: Error): Estado {
    return { erro }
  }

  componentDidCatch(erro: Error, info: ErrorInfo): void {
    console.error('Falha ao exibir a interface:', erro, info.componentStack)
  }

  /** Os filhos foram desmontados na falha: ao zerar o erro, eles montam de novo e refazem suas consultas. */
  private tentarNovamente = () => this.setState({ erro: null })

  private irParaInicio = () => {
    this.props.onIrParaInicio?.()
    this.setState({ erro: null }) // a tela inicial pode ser a mesma que falhou
  }

  render() {
    const { erro } = this.state
    if (!erro) return this.props.children

    const detalhes = (
      <details className="detalhes-erro">
        <summary>Detalhes técnicos</summary>
        <code>{`${erro.name}: ${erro.message}`}</code>
      </details>
    )

    if (this.props.variante === 'geral') {
      return (
        <main className="erro-geral" role="alert">
          <h1>Algo deu errado no sistema</h1>
          <p>Recarregue a página para continuar. Sua sessão continua aberta.</p>
          <button className="primario" onClick={() => window.location.reload()}>
            Recarregar
          </button>
          {detalhes}
        </main>
      )
    }

    return (
      <section className="erro-tela" role="alert">
        <h1>Não foi possível exibir esta tela</h1>
        <p>Tente novamente ou volte para o início. As demais telas continuam funcionando.</p>
        <div className="acoes-cabecalho">
          <button className="secundario" onClick={this.irParaInicio}>
            Ir para o início
          </button>
          <button className="primario" onClick={this.tentarNovamente}>
            Tentar novamente
          </button>
        </div>
        {detalhes}
      </section>
    )
  }
}
