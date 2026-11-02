import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'

import { autenticar } from '../api/auth'
import { EVENTO_SESSAO_EXPIRADA, limparSessao, lerSessao, salvarSessao, type Usuario } from './sessao'

const MENSAGEM_SESSAO_EXPIRADA = 'Sua sessão expirou. Entre novamente.'

interface ValorAuth {
  usuario: Usuario | null
  /** Aviso a exibir na tela de login (ex.: sessão expirada). */
  aviso: string | null
  entrar: (login: string, senha: string) => Promise<void>
  sair: () => void
}

const AuthContext = createContext<ValorAuth | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(() => lerSessao()?.usuario ?? null)
  const [aviso, setAviso] = useState<string | null>(null)

  const sair = useCallback(() => {
    limparSessao()
    setUsuario(null)
    setAviso(null)
  }, [])

  const entrar = useCallback(async (login: string, senha: string) => {
    const resposta = await autenticar(login, senha)
    salvarSessao({ token: resposta.token, usuario: resposta.usuario })
    setAviso(null)
    setUsuario(resposta.usuario)
  }, [])

  useEffect(() => {
    function aoExpirar() {
      limparSessao()
      setUsuario(null)
      setAviso(MENSAGEM_SESSAO_EXPIRADA)
    }
    window.addEventListener(EVENTO_SESSAO_EXPIRADA, aoExpirar)
    return () => window.removeEventListener(EVENTO_SESSAO_EXPIRADA, aoExpirar)
  }, [])

  return <AuthContext.Provider value={{ usuario, aviso, entrar, sair }}>{children}</AuthContext.Provider>
}

export function useAuth(): ValorAuth {
  const valor = useContext(AuthContext)
  if (!valor) throw new Error('useAuth precisa estar dentro de <AuthProvider>')
  return valor
}
