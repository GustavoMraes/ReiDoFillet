/** Exportação para planilha (CSV no padrão do Excel em português) e formatos de data dos relatórios. */

const FUSO = 'America/Sao_Paulo'

const formatoDataHora = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: FUSO,
})

/** "20/10/2026 12:05", no horário de São Paulo. */
export function dataHora(instante: string): string {
  return formatoDataHora.format(new Date(instante)).replace(',', '')
}

/** "20/10/2026" a partir de "2026-10-20" (data sem horário: não passa por fuso). */
export function dataCurta(data: string): string {
  const [ano, mes, dia] = data.split('-')
  return `${dia}/${mes}/${ano}`
}

/** "110.00" (formato da API) → "110,00" (planilha em português). */
export function decimalBr(valor: string): string {
  return valor.replace('.', ',')
}

type Celula = string | number | null

function celula(valor: Celula): string {
  const texto = valor === null ? '' : String(valor)
  // Aspas quando o texto tem separador, aspas ou quebra de linha.
  return /[;"\n\r]/.test(texto) ? `"${texto.replace(/"/g, '""')}"` : texto
}

/** CSV com separador ";" e BOM UTF-8: o Excel em português abre com acentos e colunas corretos. */
export function gerarCsv(cabecalho: string[], linhas: Celula[][]): string {
  return '﻿' + [cabecalho, ...linhas].map((linha) => linha.map(celula).join(';')).join('\r\n') + '\r\n'
}

export function baixarArquivo(nome: string, conteudo: string, tipo = 'text/csv;charset=utf-8'): void {
  const url = URL.createObjectURL(new Blob([conteudo], { type: tipo }))
  const link = document.createElement('a')
  link.href = url
  link.download = nome
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
