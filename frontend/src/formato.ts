// Formatação no padrão brasileiro.

const moeda = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

export function formatarMoeda(valor: number): string {
  return moeda.format(valor)
}

export function formatarNumero(valor: number, casas = 1): string {
  return valor.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })
}

export function formatarMs(valor: number, casas = 1): string {
  return `${formatarNumero(valor, casas)} ms`
}

/** "MagaluTechSim" -> "Magalu" (rótulo curto para barras estreitas). */
export function nomeCurto(loja: string): string {
  return loja.replace(/(Tech)?Sim$/, '')
}

/** Converte texto numérico do CSV ("156.5") para o padrão brasileiro; mantém o resto como está. */
export function formatarCelula(texto: string): string {
  if (/^-?\d+\.\d+$/.test(texto)) {
    const casas = texto.split('.')[1].length
    return formatarNumero(Number(texto), Math.min(casas, 2))
  }
  return texto
}

/** "KabumSim=2.59;PichauSim=0.47" -> "Kabum 2,59 · Pichau 0,47" */
export function formatarTemposLojas(texto: string): string {
  if (!texto) return ''
  return texto
    .split(';')
    .map((par) => {
      const [loja, ms] = par.split('=')
      return `${nomeCurto(loja)} ${formatarCelula(ms ?? '')}`
    })
    .join(' · ')
}
