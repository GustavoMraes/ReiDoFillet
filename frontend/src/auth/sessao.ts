export type Perfil = 'FUNCIONARIO' | 'ADMIN' | 'CONTABILIDADE'

export interface Usuario {
  id: number
  nome: string
  login: string
  perfil: Perfil
}

export interface Sessao {
  token: string
  usuario: Usuario
}

export const ROTULOS_PERFIL: Record<Perfil, string> = {
  FUNCIONARIO: 'Funcionário',
  ADMIN: 'Administrador',
  CONTABILIDADE: 'Contabilidade',
}

/** Disparado pelo cliente HTTP quando a API recusa a sessão (401). */
export const EVENTO_SESSAO_EXPIRADA = 'sessao-expirada'

// sessionStorage: fechar a aba encerra a sessão (tablets compartilhados no salão).
const CHAVE = 'reidofilet.sessao'

export function lerSessao(): Sessao | null {
  try {
    const bruto = sessionStorage.getItem(CHAVE)
    return bruto ? (JSON.parse(bruto) as Sessao) : null
  } catch {
    return null
  }
}

export function salvarSessao(sessao: Sessao): void {
  try {
    sessionStorage.setItem(CHAVE, JSON.stringify(sessao))
  } catch {
    // Sem storage disponível a sessão vale só enquanto a página estiver aberta.
  }
}

export function limparSessao(): void {
  try {
    sessionStorage.removeItem(CHAVE)
  } catch {
    // nada a limpar
  }
}
