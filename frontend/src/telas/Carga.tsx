import { useState, type FormEvent } from 'react'
import { api, mensagemDeErro, type Modo, type ResultadoCarga } from '../api'
import { Alerta, Cartao, Segmentado } from '../componentes'
import { formatarMs, formatarNumero } from '../formato'

const CLIENTES = [1, 5, 10, 20, 50].map((n) => ({ valor: n, rotulo: String(n) }))
const MODOS: { valor: Modo; rotulo: string }[] = [
  { valor: 'sequencial', rotulo: 'Sequencial' },
  { valor: 'concorrente', rotulo: 'Concorrente' },
]

/** Distribuição dos tempos de resposta do teste de carga em faixas iguais. */
function Histograma({ tempos, faixas = 8 }: { tempos: number[]; faixas?: number }) {
  if (tempos.length === 0) return null
  const minimo = Math.min(...tempos)
  const maximo = Math.max(...tempos)
  const largura = Math.max((maximo - minimo) / faixas, 0.01)
  const contagens = new Array<number>(faixas).fill(0)
  for (const t of tempos) {
    contagens[Math.min(Math.floor((t - minimo) / largura), faixas - 1)] += 1
  }
  const maior = Math.max(...contagens)
  const inicios = contagens.map((_, i) => minimo + i * largura)
  const descricao = contagens
    .map((n, i) => `${n} entre ${formatarNumero(inicios[i])} e ${formatarNumero(inicios[i] + largura)} ms`)
    .join('; ')

  return (
    <div>
      <div className="histograma" role="img" aria-label={`Histograma dos tempos: ${descricao}`}>
        {contagens.map((n, i) => (
          <div key={i} className="histograma-coluna">
            <span className="histograma-contagem">{n}</span>
            <div className={`histograma-barra ${n === maior ? 'maior' : ''}`} style={{ height: `${(n / maior) * 100}%` }} />
          </div>
        ))}
      </div>
      <div className="histograma-eixo" aria-hidden="true">
        {inicios.map((inicio, i) => (
          <span key={i}>{formatarNumero(inicio, 0)}{i === faixas - 1 ? ' ms' : ''}</span>
        ))}
      </div>
    </div>
  )
}

export function Carga() {
  const [clientes, setClientes] = useState(50)
  const [modo, setModo] = useState<Modo>('concorrente')
  const [produto, setProduto] = useState('notebook')
  const [atraso, setAtraso] = useState(100)
  const [resultado, setResultado] = useState<ResultadoCarga | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [carregando, setCarregando] = useState(false)

  async function disparar(evento: FormEvent) {
    evento.preventDefault()
    setCarregando(true)
    setErro(null)
    try {
      setResultado(await api.carga({ clientes, modo, produto, atraso_ms: atraso }))
    } catch (e) {
      setErro(mensagemDeErro(e))
    } finally {
      setCarregando(false)
    }
  }

  return (
    <>
      <div className="intro">
        <h1>Vários clientes ao mesmo tempo</h1>
        <p>
          O gateway cria N clientes TCP que disparam a mesma pesquisa no mesmo instante (barreira de threads).
          O agregador atende cada conexão numa thread própria.
        </p>
      </div>

      <form className="formulario" onSubmit={disparar}>
        <div className="linha-campos">
          <Segmentado legenda="Clientes simultâneos" opcoes={CLIENTES} valor={clientes} aoMudar={setClientes} />
          <Segmentado legenda="Modo do agregador" opcoes={MODOS} valor={modo} aoMudar={setModo} />
          <div className="campo campo-cresce" style={{ flexBasis: 180 }}>
            <label htmlFor="produto-carga" className="rotulo">Produto</label>
            <input id="produto-carga" className="entrada" value={produto} required onChange={(e) => setProduto(e.target.value)} />
          </div>
          <div className="campo" style={{ width: 150 }}>
            <label htmlFor="atraso-carga" className="rotulo">Latência (ms)</label>
            <input id="atraso-carga" className="entrada mono" type="number" min={0} max={2000} step={10} value={atraso}
              onChange={(e) => setAtraso(Math.max(0, Math.min(2000, Math.round(Number(e.target.value) || 0))))} />
          </div>
          <button type="submit" className="botao botao-principal" disabled={carregando || !produto.trim()}>
            {carregando ? 'Executando…' : `Disparar ${clientes} ${clientes === 1 ? 'cliente' : 'clientes'}`}
          </button>
        </div>
      </form>

      {erro && <Alerta tipo="erro" titulo="O teste de carga falhou">{erro}</Alerta>}

      {resultado && (
        <>
          <section aria-label="Resultado" className="grade-metricas">
            <Cartao tipo="metrica" rotulo="Tempo médio" valor={formatarMs(resultado.media_ms)} detalhe={`desvio ${formatarMs(resultado.desvio_ms)}`} />
            <Cartao tipo="metrica" rotulo="p95" valor={formatarMs(resultado.p95_ms)} />
            <Cartao tipo="metrica" rotulo="Mais lento" valor={formatarMs(resultado.max_ms)} detalhe={`mais rápido ${formatarMs(resultado.min_ms)}`} />
            <Cartao tipo="metrica" rotulo="Vazão" valor={resultado.vazao_req_s === null ? '—' : `${formatarNumero(resultado.vazao_req_s, 0)} req/s`} />
            <Cartao tipo="metrica" variante="escura" rotulo="Falhas" valor={`${resultado.falhas} de ${resultado.clientes}`} />
          </section>

          <section className="painel" aria-labelledby="t-hist">
            <div className="painel-topo">
              <h2 id="t-hist">Distribuição dos {resultado.clientes} tempos de resposta</h2>
              <span className="nota">
                lote inteiro em {formatarMs(resultado.tempo_total_ms)} · modo {resultado.modo}
                {resultado.atraso_ms !== null ? ` · latência das lojas ${resultado.atraso_ms} ms` : ''}
              </span>
            </div>
            <Histograma tempos={resultado.tempos_ms} />
            {resultado.falhas === 0 ? (
              <Alerta tipo="sucesso" titulo={`${resultado.clientes} ${resultado.clientes === 1 ? 'cliente atendido' : 'clientes simultâneos atendidos'} sem nenhuma falha.`}>
                {resultado.clientes >= 50 ? 'RNF03 atendido (pelo menos 50 clientes simultâneos sem falhas).' : undefined}
              </Alerta>
            ) : (
              <Alerta tipo="aviso" titulo={`${resultado.falhas} de ${resultado.clientes} clientes falharam.`}>
                <ul>
                  {resultado.detalhes_falhas.slice(0, 5).map((f) => (
                    <li key={f.cliente}>cliente {f.cliente}: {f.detalhe}</li>
                  ))}
                </ul>
              </Alerta>
            )}
          </section>
        </>
      )}
    </>
  )
}
