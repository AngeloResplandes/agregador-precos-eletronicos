// Tipos que espelham as respostas do agregador (docs/03_protocolo.md) e as chamadas ao gateway HTTP
// (backend/gateway_http.py). Erros viram ErroApi com mensagem amigável.

export type Modo = 'sequencial' | 'concorrente'
export type ModoInterface = Modo | 'comparar'
export type Criterio = 'preco' | 'custo_beneficio'
export type AcaoLoja = 'derrubar' | 'subir'
export type LinhaCsv = Record<string, string>

export interface Oferta {
  fonte: string
  produto: string
  specs: string
  preco: number
  frete: number
  preco_total: number
  avaliacao: number
  garantia_meses: number
  tempo_loja_ms: number
  score_custo_beneficio: number
  status: string
}

/** Loja que falhou (conexão recusada, queda, timeout, resposta inválida). */
export interface Ocorrencia {
  fonte: string
  status: string
  detalhe?: string
  tempo_loja_ms: number
}

export interface RespostaConsulta {
  status: 'sucesso' | 'nao_encontrado'
  produto_pesquisado: string
  modo_execucao: Modo
  criterio_ordenacao: Criterio
  tempo_total_ms: number
  tempos_lojas_ms: Record<string, number>
  total_lojas_consultadas: number
  total_lojas_responderam: number
  total_ofertas: number
  menor_preco: Oferta | null
  melhor_custo_beneficio: Oferta | null
  ofertas_ordenadas: Oferta[]
  lojas_sem_produto: string[]
  ocorrencias_ou_falhas: Ocorrencia[]
}

export interface RespostaComparacao {
  status: 'sucesso' | 'nao_encontrado'
  modo_execucao: 'comparar'
  sequencial: RespostaConsulta
  concorrente: RespostaConsulta
  speedup: number | null
}

export type RespostaPesquisa = RespostaConsulta | RespostaComparacao

export interface Saude {
  agregador_online: boolean
  agregador: string
  gerencia_processos: boolean
}

export interface StatusLoja {
  nome: string
  host: string
  porta: number
  latencia_ms: number | null
  online: boolean
}

export interface ResultadoCarga {
  clientes: number
  produto: string
  modo: Modo
  atraso_ms: number | null
  media_ms: number
  desvio_ms: number
  min_ms: number
  max_ms: number
  p95_ms: number
  tempo_total_ms: number
  vazao_req_s: number | null
  falhas: number
  detalhes_falhas: { cliente: number; detalhe: string }[]
  tempos_ms: number[]
}

export interface TabelaCsv {
  arquivo: string
  colunas: string[]
  linhas: LinhaCsv[]
}

export interface RespostaLog {
  colunas: string[]
  linhas: LinhaCsv[]
  total: number
}

export function ehComparacao(resposta: RespostaPesquisa): resposta is RespostaComparacao {
  return resposta.modo_execucao === 'comparar'
}

// ---------------------------------------------------------------- chamadas HTTP

export class ErroApi extends Error {}

const GATEWAY_FORA =
  'não foi possível falar com o gateway HTTP. Ele está rodando? (python3 backend/gateway_http.py)'

/** GET sem corpo; POST com corpo JSON. Respostas de erro do gateway têm a forma {status, detalhe}. */
async function requisitar<T>(caminho: string, corpo?: unknown): Promise<T> {
  let resposta: Response
  let dados: { detalhe?: string }
  try {
    resposta = await fetch('/api' + caminho, corpo === undefined ? undefined : {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(corpo),
    })
    dados = await resposta.json()
  } catch {
    // fetch falhou, ou o proxy do Vite devolveu um 5xx sem JSON: o gateway está fora do ar
    throw new ErroApi(GATEWAY_FORA)
  }
  if (!resposta.ok) throw new ErroApi(dados.detalhe ?? `HTTP ${resposta.status}`)
  return dados as T
}

export const api = {
  saude: () => requisitar<Saude>('/saude'),
  lojas: () => requisitar<{ lojas: StatusLoja[]; gerencia_processos: boolean }>('/lojas'),
  controlarLoja: (nome: string, acao: AcaoLoja) =>
    requisitar<StatusLoja>(`/lojas/${encodeURIComponent(nome)}/${acao}`, {}),
  produtos: () => requisitar<{ produtos: string[] }>('/produtos'),
  pesquisar: (pedido: { produto: string; modo: ModoInterface; criterio: Criterio; atraso_ms?: number }) =>
    requisitar<RespostaPesquisa>('/consultar', pedido),
  carga: (pedido: { clientes: number; produto: string; modo: Modo; atraso_ms?: number }) =>
    requisitar<ResultadoCarga>('/carga', pedido),
  experimentos: () => requisitar<{ tabelas: TabelaCsv[]; graficos: string[] }>('/experimentos'),
  log: (limite: number) => requisitar<RespostaLog>(`/log?limite=${limite}`),
  urlGrafico: (nome: string) => `/api/resultados/${encodeURIComponent(nome)}`,
}

export function mensagemDeErro(erro: unknown): string {
  return erro instanceof Error ? erro.message : 'erro inesperado'
}
