import type { Perfil } from '../auth/sessao'
import { deleteJson, getJson, patchJson, postJson } from './cliente'

// --- Cardápio (Administrador) ---

export interface ProdutoAdmin {
  id: number
  categoria_id: number
  nome: string
  descricao: string | null
  preco: string
  ativo: boolean
  disponivel: boolean
}

export interface CategoriaAdmin {
  id: number
  nome: string
  ordem: number
  produtos: ProdutoAdmin[]
}

export interface DadosProduto {
  categoria_id: number
  nome: string
  descricao: string | null
  /** Formato da API: "79.90". */
  preco: string
}

export function obterCardapioCompleto(): Promise<CategoriaAdmin[]> {
  return getJson<CategoriaAdmin[]>('/admin/cardapio')
}

export function criarProduto(dados: DadosProduto): Promise<CategoriaAdmin[]> {
  return postJson<CategoriaAdmin[]>('/admin/produtos', dados)
}

export function alterarProduto(
  produtoId: number,
  dados: Partial<DadosProduto> & { ativo?: boolean },
): Promise<CategoriaAdmin[]> {
  return patchJson<CategoriaAdmin[]>(`/admin/produtos/${produtoId}`, dados)
}

export function criarCategoria(nome: string): Promise<CategoriaAdmin[]> {
  return postJson<CategoriaAdmin[]>('/admin/categorias', { nome })
}

export function renomearCategoria(categoriaId: number, nome: string): Promise<CategoriaAdmin[]> {
  return patchJson<CategoriaAdmin[]>(`/admin/categorias/${categoriaId}`, { nome })
}

export function moverCategoria(categoriaId: number, direcao: 'acima' | 'abaixo'): Promise<CategoriaAdmin[]> {
  return postJson<CategoriaAdmin[]>(`/admin/categorias/${categoriaId}/mover`, { direcao })
}

export function excluirCategoria(categoriaId: number): Promise<CategoriaAdmin[]> {
  return deleteJson<CategoriaAdmin[]>(`/admin/categorias/${categoriaId}`)
}

// --- Usuários (Administrador) ---

export interface UsuarioAdmin {
  id: number
  nome: string
  login: string
  perfil: Perfil
  bloqueado: boolean
}

export function listarUsuarios(): Promise<UsuarioAdmin[]> {
  return getJson<UsuarioAdmin[]>('/usuarios')
}

export function criarUsuario(dados: { nome: string; login: string; perfil: Perfil; senha: string }): Promise<UsuarioAdmin> {
  return postJson<UsuarioAdmin>('/usuarios', dados)
}

export function alterarUsuario(
  usuarioId: number,
  dados: { nome?: string; perfil?: Perfil; bloqueado?: boolean },
): Promise<UsuarioAdmin> {
  return patchJson<UsuarioAdmin>(`/usuarios/${usuarioId}`, dados)
}

export function redefinirSenha(usuarioId: number, senha: string): Promise<void> {
  return postJson<void>(`/usuarios/${usuarioId}/senha`, { senha })
}
