import type { Usuario } from '../auth/sessao'
import { postJson } from './cliente'

interface RespostaLogin {
  token: string
  tipo: 'bearer'
  expira_em: string
  usuario: Usuario
}

export function autenticar(login: string, senha: string): Promise<RespostaLogin> {
  return postJson<RespostaLogin>('/auth/login', { login, senha }, { semSessao: true })
}

export function trocarSenha(senhaAtual: string, novaSenha: string): Promise<void> {
  return postJson<void>('/auth/senha', { senha_atual: senhaAtual, nova_senha: novaSenha })
}
