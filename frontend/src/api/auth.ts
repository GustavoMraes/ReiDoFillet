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
