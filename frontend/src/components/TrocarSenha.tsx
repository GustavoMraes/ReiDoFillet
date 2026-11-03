import { useState, type FormEvent } from 'react'

import { trocarSenha } from '../api/auth'
import { ErroApi } from '../api/cliente'
import Dialogo from './Dialogo'
import { useMensagens } from './Mensagens'

const TAMANHO_MINIMO = 8

/** Troca da própria senha, disponível a todos os perfis pelo cabeçalho. */
export default function TrocarSenha({ onFechar }: { onFechar: () => void }) {
  const mostrar = useMensagens()
  const [atual, setAtual] = useState('')
  const [nova, setNova] = useState('')
  const [confirmacao, setConfirmacao] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    if (nova !== confirmacao) {
      setErro('A confirmação não confere com a nova senha')
      return
    }
    setEnviando(true)
    setErro(null)
    try {
      await trocarSenha(atual, nova)
      mostrar('Senha alterada. Use a nova senha no próximo login.')
      onFechar()
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha.message : 'Não foi possível trocar a senha')
      setEnviando(false)
    }
  }

  return (
    <Dialogo
      titulo="Trocar senha"
      acoes={
        <>
          <button type="button" className="secundario" disabled={enviando} onClick={onFechar}>
            Cancelar
          </button>
          <button type="submit" form="form-trocar-senha" className="primario" disabled={enviando}>
            {enviando ? 'Salvando…' : 'Trocar senha'}
          </button>
        </>
      }
    >
      <form id="form-trocar-senha" className="form-dialogo" onSubmit={enviar}>
        <label className="campo">
          Senha atual
          <input type="password" required autoComplete="current-password" value={atual} onChange={(e) => setAtual(e.target.value)} />
        </label>
        <label className="campo">
          Nova senha (mínimo de {TAMANHO_MINIMO} caracteres)
          <input
            type="password"
            required
            minLength={TAMANHO_MINIMO}
            autoComplete="new-password"
            value={nova}
            onChange={(e) => setNova(e.target.value)}
          />
        </label>
        <label className="campo">
          Confirme a nova senha
          <input
            type="password"
            required
            autoComplete="new-password"
            value={confirmacao}
            onChange={(e) => setConfirmacao(e.target.value)}
          />
        </label>
        {erro && (
          <p className="erro" role="alert">
            {erro}
          </p>
        )}
      </form>
    </Dialogo>
  )
}
