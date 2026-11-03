import { useState, type FormEvent } from 'react'

import { alterarUsuario, criarUsuario, listarUsuarios, redefinirSenha, type UsuarioAdmin } from '../api/admin'
import { ErroApi } from '../api/cliente'
import { useAuth } from '../auth/AuthContext'
import { ROTULOS_PERFIL, type Perfil } from '../auth/sessao'
import Dialogo from '../components/Dialogo'
import { useMensagens } from '../components/Mensagens'
import { usePolling } from '../hooks/usePolling'

const INTERVALO_ATUALIZACAO_MS = 15000
const PERFIS: Perfil[] = ['FUNCIONARIO', 'ADMIN', 'CONTABILIDADE']
const TAMANHO_MINIMO_SENHA = 8

function mensagemDeErro(erro: unknown): string {
  return erro instanceof ErroApi ? erro.message : 'Não foi possível concluir a operação'
}

type Edicao =
  | { tipo: 'novo' }
  | { tipo: 'editar'; usuario: UsuarioAdmin }
  | { tipo: 'bloqueio'; usuario: UsuarioAdmin }
  | { tipo: 'senha'; usuario: UsuarioAdmin }

/** Campos de senha com confirmação; devolve a senha só quando as duas conferem. */
function CamposSenha({ rotulo, onMudar }: { rotulo: string; onMudar: (senha: string | null) => void }) {
  const [senha, setSenha] = useState('')
  const [confirmacao, setConfirmacao] = useState('')
  const atualizar = (nova: string, conf: string) => onMudar(nova && nova === conf ? nova : null)
  return (
    <>
      <label className="campo">
        {rotulo} (mínimo de {TAMANHO_MINIMO_SENHA} caracteres)
        <input
          type="password"
          required
          minLength={TAMANHO_MINIMO_SENHA}
          autoComplete="new-password"
          value={senha}
          onChange={(e) => {
            setSenha(e.target.value)
            atualizar(e.target.value, confirmacao)
          }}
        />
      </label>
      <label className="campo">
        Confirme a senha
        <input
          type="password"
          required
          autoComplete="new-password"
          value={confirmacao}
          onChange={(e) => {
            setConfirmacao(e.target.value)
            atualizar(senha, e.target.value)
          }}
        />
      </label>
    </>
  )
}

function FormUsuario({
  usuario,
  proprio,
  onSalvar,
  onFechar,
}: {
  usuario: UsuarioAdmin | null
  proprio: boolean
  onSalvar: (dados: { nome: string; login: string; perfil: Perfil; senha: string | null }) => Promise<void>
  onFechar: () => void
}) {
  const [nome, setNome] = useState(usuario?.nome ?? '')
  const [login, setLogin] = useState(usuario?.login ?? '')
  const [perfil, setPerfil] = useState<Perfil>(usuario?.perfil ?? 'FUNCIONARIO')
  const [senha, setSenha] = useState<string | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    if (!usuario && senha === null) {
      setErro('A confirmação não confere com a senha')
      return
    }
    setErro(null)
    setEnviando(true)
    try {
      await onSalvar({ nome, login, perfil, senha })
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Dialogo
      titulo={usuario ? `Editar ${usuario.nome}` : 'Novo usuário'}
      acoes={
        <>
          <button type="button" className="secundario" disabled={enviando} onClick={onFechar}>
            Cancelar
          </button>
          <button type="submit" form="form-usuario" className="primario" disabled={enviando}>
            {enviando ? 'Salvando…' : 'Salvar'}
          </button>
        </>
      }
    >
      <form id="form-usuario" className="form-dialogo" onSubmit={enviar}>
        <label className="campo">
          Nome
          <input required maxLength={100} value={nome} onChange={(e) => setNome(e.target.value)} />
        </label>
        <label className="campo">
          Login {usuario && '(não pode ser alterado)'}
          <input
            required
            disabled={!!usuario}
            minLength={3}
            maxLength={50}
            autoCapitalize="none"
            autoComplete="off"
            value={login}
            onChange={(e) => setLogin(e.target.value)}
          />
        </label>
        <label className="campo">
          Perfil {proprio && '(você não pode alterar o próprio perfil)'}
          <select disabled={proprio} value={perfil} onChange={(e) => setPerfil(e.target.value as Perfil)}>
            {PERFIS.map((p) => (
              <option key={p} value={p}>
                {ROTULOS_PERFIL[p]}
              </option>
            ))}
          </select>
        </label>
        {!usuario && <CamposSenha rotulo="Senha inicial" onMudar={setSenha} />}
        {erro && (
          <p className="erro" role="alert">
            {erro}
          </p>
        )}
      </form>
    </Dialogo>
  )
}

function FormSenha({
  usuario,
  onSalvar,
  onFechar,
}: {
  usuario: UsuarioAdmin
  onSalvar: (senha: string) => Promise<void>
  onFechar: () => void
}) {
  const [senha, setSenha] = useState<string | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    if (senha === null) {
      setErro('A confirmação não confere com a senha')
      return
    }
    setErro(null)
    setEnviando(true)
    try {
      await onSalvar(senha)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Dialogo
      titulo={`Redefinir a senha de ${usuario.nome}`}
      acoes={
        <>
          <button type="button" className="secundario" disabled={enviando} onClick={onFechar}>
            Cancelar
          </button>
          <button type="submit" form="form-senha" className="primario" disabled={enviando}>
            {enviando ? 'Salvando…' : 'Redefinir senha'}
          </button>
        </>
      }
    >
      <form id="form-senha" className="form-dialogo" onSubmit={enviar}>
        <CamposSenha rotulo="Nova senha" onMudar={setSenha} />
        {erro && (
          <p className="erro" role="alert">
            {erro}
          </p>
        )}
      </form>
    </Dialogo>
  )
}

export default function Usuarios() {
  const mostrar = useMensagens()
  const { usuario: logado } = useAuth()
  const { dados: usuarios, desatualizado, definir } = usePolling(listarUsuarios, INTERVALO_ATUALIZACAO_MS)
  const [edicao, setEdicao] = useState<Edicao | null>(null)
  const [ocupado, setOcupado] = useState(false)

  async function recarregar() {
    try {
      definir(await listarUsuarios())
    } catch {
      // o polling tenta de novo
    }
  }

  async function executar(operacao: () => Promise<unknown>, sucesso: string) {
    setOcupado(true)
    try {
      await operacao()
      mostrar(sucesso)
      setEdicao(null)
      await recarregar()
    } catch (erro) {
      mostrar(mensagemDeErro(erro), 'erro')
    } finally {
      setOcupado(false)
    }
  }

  if (!usuarios) {
    return <p className="vazio">{desatualizado ? 'Não foi possível carregar os usuários; tentando novamente…' : 'Carregando…'}</p>
  }

  return (
    <section>
      <div className="cabecalho-comanda">
        <div>
          <h1>Usuários</h1>
          <p className="subtitulo">Funcionários com acesso ao sistema. Para remover alguém, bloqueie o usuário.</p>
        </div>
        <button className="primario" onClick={() => setEdicao({ tipo: 'novo' })}>
          Novo usuário
        </button>
      </div>

      {desatualizado && (
        <p className="aviso" role="alert">
          Não foi possível atualizar a lista; tentando novamente…
        </p>
      )}

      <ul className="lista-usuarios">
        {usuarios.map((usuario) => {
          const proprio = usuario.id === logado?.id
          return (
            <li key={usuario.id} className={usuario.bloqueado ? 'usuario-gestao bloqueado' : 'usuario-gestao'}>
              <div className="usuario-gestao-info">
                <strong>
                  {usuario.nome}
                  {proprio && ' (você)'}
                </strong>
                <small>{usuario.login}</small>
              </div>
              <div className="produto-gestao-selos">
                <span className="selo selo-perfil">{ROTULOS_PERFIL[usuario.perfil]}</span>
                {usuario.bloqueado && <span className="selo-indisponivel">Bloqueado</span>}
              </div>
              <div className="produto-gestao-acoes">
                <button className="secundario" disabled={ocupado} onClick={() => setEdicao({ tipo: 'editar', usuario })}>
                  Editar
                </button>
                <button className="secundario" disabled={ocupado} onClick={() => setEdicao({ tipo: 'senha', usuario })}>
                  Redefinir senha
                </button>
                {!proprio && (
                  <button className="secundario" disabled={ocupado} onClick={() => setEdicao({ tipo: 'bloqueio', usuario })}>
                    {usuario.bloqueado ? 'Desbloquear' : 'Bloquear'}
                  </button>
                )}
              </div>
            </li>
          )
        })}
      </ul>

      {edicao?.tipo === 'novo' && (
        <FormUsuario
          usuario={null}
          proprio={false}
          onSalvar={({ nome, login, perfil, senha }) =>
            executar(() => criarUsuario({ nome, login, perfil, senha: senha ?? '' }), `Usuário ${login.trim().toLowerCase()} cadastrado`)
          }
          onFechar={() => setEdicao(null)}
        />
      )}
      {edicao?.tipo === 'editar' && (
        <FormUsuario
          usuario={edicao.usuario}
          proprio={edicao.usuario.id === logado?.id}
          onSalvar={({ nome, perfil }) =>
            executar(
              () => alterarUsuario(edicao.usuario.id, edicao.usuario.id === logado?.id ? { nome } : { nome, perfil }),
              `Usuário ${edicao.usuario.login} atualizado`,
            )
          }
          onFechar={() => setEdicao(null)}
        />
      )}
      {edicao?.tipo === 'senha' && (
        <FormSenha
          usuario={edicao.usuario}
          onSalvar={(senha) => executar(() => redefinirSenha(edicao.usuario.id, senha), `Senha de ${edicao.usuario.login} redefinida`)}
          onFechar={() => setEdicao(null)}
        />
      )}
      {edicao?.tipo === 'bloqueio' && (
        <Dialogo
          titulo={edicao.usuario.bloqueado ? 'Desbloquear usuário' : 'Bloquear usuário'}
          acoes={
            <>
              <button className="secundario" disabled={ocupado} onClick={() => setEdicao(null)}>
                Voltar
              </button>
              <button
                className="primario"
                disabled={ocupado}
                onClick={() =>
                  executar(
                    () => alterarUsuario(edicao.usuario.id, { bloqueado: !edicao.usuario.bloqueado }),
                    edicao.usuario.bloqueado
                      ? `${edicao.usuario.login} desbloqueado`
                      : `${edicao.usuario.login} bloqueado`,
                  )
                }
              >
                {edicao.usuario.bloqueado ? 'Desbloquear' : 'Bloquear'}
              </button>
            </>
          }
        >
          <p>
            {edicao.usuario.bloqueado
              ? `${edicao.usuario.nome} voltará a conseguir entrar com a mesma senha.`
              : `${edicao.usuario.nome} perde o acesso imediatamente, inclusive com o sistema já aberto. O histórico de atendimentos é mantido.`}
          </p>
        </Dialogo>
      )}
    </section>
  )
}
