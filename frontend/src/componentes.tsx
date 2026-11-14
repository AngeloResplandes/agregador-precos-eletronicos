// Componentes usados por mais de uma tela.
import type { ReactNode } from 'react'
import type { RespostaConsulta } from './api'
import { formatarMs, formatarNumero, nomeCurto } from './formato'

// ---------------------------------------------------------------- Alerta
type TipoAlerta = 'aviso' | 'erro' | 'sucesso' | 'info'

const ICONES: Record<TipoAlerta, { cor: string; caminhos: string[] }> = {
  aviso: { cor: '#B4461A', caminhos: ['M12 9v4', 'M12 17h.01', 'M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z'] },
  erro: { cor: '#B4461A', caminhos: ['M12 8v5', 'M12 16h.01', 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z'] },
  sucesso: { cor: '#1E6B43', caminhos: ['M20 6 9 17l-5-5'] },
  info: { cor: '#1F64B8', caminhos: ['M12 11v5', 'M12 8h.01', 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z'] },
}

export function Alerta({ tipo = 'aviso', titulo, children }: { tipo?: TipoAlerta; titulo: string; children?: ReactNode }) {
  const icone = ICONES[tipo]
  return (
    <div className={`alerta ${tipo}`} role={tipo === 'erro' || tipo === 'aviso' ? 'alert' : 'status'}>
      <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={icone.cor}
        strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        {icone.caminhos.map((d) => <path key={d} d={d} />)}
      </svg>
      <div className="alerta-corpo">
        <span className="alerta-titulo">{titulo}</span>
        {children && <div className="alerta-texto">{children}</div>}
      </div>
    </div>
  )
}

/** RF09: lojas sem o produto e lojas que falharam, com o motivo, sem esconder o resultado das demais. */
export function AlertasConsulta({ resposta }: { resposta: RespostaConsulta }) {
  const falhas = resposta.ocorrencias_ou_falhas
  return (
    <>
      {resposta.status === 'nao_encontrado' && (
        <Alerta tipo="info" titulo={`Nenhuma loja tem “${resposta.produto_pesquisado}”.`}>
          {falhas.length > 0
            ? 'Além disso, algumas lojas não responderam (veja abaixo).'
            : 'Tente um item do catálogo: iphone, monitor, notebook, rtx 4060 ou ssd.'}
        </Alerta>
      )}
      {falhas.length > 0 && (
        <Alerta
          tipo="aviso"
          titulo={`${resposta.total_lojas_responderam}/${resposta.total_lojas_consultadas} lojas responderam. A pesquisa continuou com as demais.`}
        >
          <ul>
            {falhas.map((falha) => (
              <li key={falha.fonte}>
                <b>{falha.fonte}</b> · <span className="codigo-status">{falha.status}</span>
                {falha.detalhe ? ` · ${falha.detalhe}` : ''}
              </li>
            ))}
          </ul>
        </Alerta>
      )}
      {resposta.lojas_sem_produto.length > 0 && resposta.status === 'sucesso' && (
        <Alerta tipo="info" titulo="Lojas sem este produto">
          {resposta.lojas_sem_produto.join(', ')}
        </Alerta>
      )}
    </>
  )
}

// ---------------------------------------------------------------- Cartao
interface PropsCartao {
  /** 'destaque' (menor preço, custo-benefício, speedup) ou 'metrica' (tempo médio, p95, vazão…). */
  tipo: 'destaque' | 'metrica'
  rotulo: string
  valor: string
  texto?: string
  detalhe?: string
  /** destaque: laranja | escuro; métrica: escura | suave. Sem variante = padrão. */
  variante?: 'laranja' | 'escuro' | 'escura' | 'suave'
}

export function Cartao({ tipo, rotulo, valor, texto, detalhe, variante }: PropsCartao) {
  return (
    <div className={`${tipo} ${variante ?? ''}`}>
      <span className={`${tipo}-rotulo`}>{rotulo}</span>
      <span className={`${tipo}-valor`}>{valor}</span>
      {texto && <span className={`${tipo}-texto`}>{texto}</span>}
      {detalhe && <span className={`${tipo}-detalhe`}>{detalhe}</span>}
    </div>
  )
}

// ---------------------------------------------------------------- Segmentado
interface PropsSegmentado<T extends string | number> {
  legenda: string
  opcoes: { valor: T; rotulo: string }[]
  valor: T
  aoMudar: (valor: T) => void
}

/** Grupo de botões exclusivos (modo, critério, nº de clientes). */
export function Segmentado<T extends string | number>({ legenda, opcoes, valor, aoMudar }: PropsSegmentado<T>) {
  return (
    <fieldset className="segmentado">
      <legend className="rotulo">{legenda}</legend>
      <div className="segmentado-opcoes">
        {opcoes.map((opcao) => (
          <button key={String(opcao.valor)} type="button" aria-pressed={opcao.valor === valor}
            onClick={() => aoMudar(opcao.valor)}>
            {opcao.rotulo}
          </button>
        ))}
      </div>
    </fieldset>
  )
}

// ---------------------------------------------------------------- BarrasTempo
/**
 * Tempo de cada loja medido pelo agregador, uma linha por resposta. No sequencial os blocos se
 * somam (uma loja depois da outra); no concorrente ficam empilhados e o total é o da loja mais
 * lenta. Todas as linhas usam a mesma escala para a diferença ficar visível.
 */
export function BarrasTempo({ respostas }: { respostas: RespostaConsulta[] }) {
  const escala = Math.max(...respostas.map((r) => r.tempo_total_ms), 1)
  return (
    <div className="barras">
      {respostas.map((resposta) => {
        const sequencial = resposta.modo_execucao === 'sequencial'
        const falharam = new Set(resposta.ocorrencias_ou_falhas.map((falha) => falha.fonte))
        return (
          <div key={resposta.modo_execucao} className="barra-linha">
            <span className="barra-rotulo">{sequencial ? 'Sequencial' : 'Concorrente'}</span>
            <div className="barra-trilho">
              <div className={sequencial ? 'barra-sequencial' : 'barra-concorrente'}
                style={sequencial ? { width: `${(resposta.tempo_total_ms / escala) * 100}%` } : undefined}>
                {Object.entries(resposta.tempos_lojas_ms).map(([loja, ms]) => (
                  <div
                    key={loja}
                    className={`bloco ${falharam.has(loja) ? 'falhou' : ''}`}
                    style={sequencial ? { flex: `${Math.max(ms, 1)} 1 0` } : { width: `${(ms / escala) * 100}%` }}
                    title={`${loja}: ${formatarMs(ms, 2)}`}
                  >
                    {nomeCurto(loja)}{sequencial && ` ${formatarNumero(ms)}`}
                  </div>
                ))}
              </div>
            </div>
            <span className="barra-total">{formatarMs(resposta.tempo_total_ms)}</span>
          </div>
        )
      })}
    </div>
  )
}
