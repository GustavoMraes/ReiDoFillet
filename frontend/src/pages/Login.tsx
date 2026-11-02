import { useState, type FormEvent } from 'react'

import { ErroApi } from '../api/cliente'
import { useAuth } from '../auth/AuthContext'

export default function Login() {
  const { entrar, aviso } = useAuth()
  const [login, setLogin] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setEnviando(true)
    setErro(null)
    try {
      await entrar(login, senha)
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha.message : 'Não foi possível entrar. Tente novamente.')
      setSenha('')
      setEnviando(false)
    }
  }

  const mensagem = erro ?? aviso

  return (
    <main className="tela-login">
      <form className="cartao-login" onSubmit={enviar}>
        <div className="marca">
          <strong>
            REI DO <span>FILET</span>
          </strong>
          <small>Sistema de Atendimento e Comandas</small>
        </div>
        <h1>Entrar</h1>

        {mensagem && (
          <p className={erro ? 'erro' : 'aviso'} role="alert">
            {mensagem}
          </p>
        )}

        <label>
          Usuário
          <input
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            autoComplete="username"
            autoCapitalize="none"
            autoFocus
            required
          />
        </label>
        <label>
          Senha
          <input
            type="password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        <button type="submit" disabled={enviando}>
          {enviando ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
    </main>
  )
}
