import { useEffect, useState, type FormEvent } from 'react'
import {
  api, ehComparacao, mensagemDeErro, type Criterio, type ModoInterface, type RespostaConsulta, type RespostaPesquisa,
} from '../api'
import { Alerta, AlertasConsulta, BarrasTempo, Cartao, Segmentado } from '../componentes'
import { formatarMoeda, formatarMs, formatarNumero } from '../formato'

const ATRASO_MAXIMO_INTERFACE = 2000
const ATRASO_PADRAO = 150

const MODOS: { valor: ModoInterface; rotulo: string }[] = [
  { valor: 'sequencial', rotulo: 'Sequencial' },
  { valor: 'concorrente', rotulo: 'Concorrente' },
  { valor: 'comparar', rotulo: 'Comparar os dois' },
]

const CRITERIOS: { valor: Criterio; rotulo: string }[] = [
  { valor: 'preco', rotulo: 'Preço total' },
  { valor: 'custo_beneficio', rotulo: 'Custo-benefício' },
]

function Destaques({ resposta, comparacao }: { resposta: RespostaConsulta; comparacao: RespostaPesquisa }) {
  const menor = resposta.menor_preco
  const melhor = resposta.melhor_custo_beneficio
  return (
    <section aria-label="Destaques" className="grade-cartoes">
      {menor && (
        <Cartao tipo="destaque" rotulo="Menor preço total" valor={formatarMoeda(menor.preco_total)}
          texto={`${menor.fonte} · ${menor.produto}`}
          detalhe={`${formatarMoeda(menor.preco)} + ${menor.frete === 0 ? 'frete grátis' : `${formatarMoeda(menor.frete)} de frete`}`} />
      )}
      {melhor && (
        <Cartao tipo="destaque" variante="laranja" rotulo="Melhor custo-benefício" valor={melhor.fonte}
          texto={`${melhor.produto} · ${formatarMoeda(melhor.preco_total)}`}
          detalhe={`score ${formatarNumero(melhor.score_custo_beneficio, 2)} · nota ${formatarNumero(melhor.avaliacao)} · garantia ${melhor.garantia_meses} meses`} />
      )}
      {ehComparacao(comparacao) ? (
        <Cartao tipo="destaque" variante="escuro" rotulo="Speedup da concorrência"
          valor={comparacao.speedup === null ? '—' : `${formatarNumero(comparacao.speedup, 2)}×`}
          texto={`${formatarMs(comparacao.sequencial.tempo_total_ms)} sequencial → ${formatarMs(comparacao.concorrente.tempo_total_ms)} concorrente`} />
      ) : (
        <Cartao tipo="destaque" variante="escuro" rotulo={`Tempo total · ${resposta.modo_execucao}`}
          valor={formatarMs(resposta.tempo_total_ms)} texto="Use “Comparar os dois” para ver o speedup." />
      )}
    </section>
  )
}

/** Todas as informações exigidas pelo RF05, na ordem escolhida pelo usuário (RF06). */
function TabelaOfertas({ resposta }: { resposta: RespostaConsulta }) {
  const menor = resposta.menor_preco?.fonte
  const melhor = resposta.melhor_custo_beneficio?.fonte
  const ordem = resposta.criterio_ordenacao === 'preco' ? 'preço total' : 'custo-benefício'
  const falhas = resposta.ocorrencias_ou_falhas.length

  return (
    <section className="painel" aria-labelledby="t-ofertas">
      <div className="painel-topo">
        <h2 id="t-ofertas">Ofertas ordenadas por {ordem}</h2>
        <span className="nota">
          {resposta.total_lojas_responderam}/{resposta.total_lojas_consultadas} lojas responderam ·{' '}
          {resposta.total_ofertas} {resposta.total_ofertas === 1 ? 'oferta' : 'ofertas'} ·{' '}
          {falhas} {falhas === 1 ? 'falha' : 'falhas'}
        </span>
      </div>
      <div className="tabela-caixa">
        <table className="tabela" style={{ minWidth: 980 }}>
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">Loja</th>
              <th scope="col">Produto</th>
              {['Preço', 'Frete', 'Total', 'Nota', 'Garantia', 'Tempo', 'Score'].map((titulo) => (
                <th key={titulo} scope="col" className="num">{titulo}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {resposta.ofertas_ordenadas.map((oferta, i) => {
              const score = formatarNumero(oferta.score_custo_beneficio, 2)
              return (
                <tr key={oferta.fonte} className={oferta.fonte === menor ? 'menor-preco' : oferta.fonte === melhor ? 'melhor-cb' : ''}>
                  <td>{i + 1}</td>
                  <td><b>{oferta.fonte}</b></td>
                  <td style={{ minWidth: 240 }}>
                    {oferta.produto}
                    <span className="specs">{oferta.specs}</span>
                  </td>
                  <td className="num">{formatarMoeda(oferta.preco)}</td>
                  <td className="num">{oferta.frete === 0 ? 'grátis' : formatarMoeda(oferta.frete)}</td>
                  <td className="num"><b>{formatarMoeda(oferta.preco_total)}</b></td>
                  <td className="num">{formatarNumero(oferta.avaliacao)}</td>
                  <td className="num">{oferta.garantia_meses} m</td>
                  <td className="num">{formatarMs(oferta.tempo_loja_ms)}</td>
                  <td className="num">{oferta.fonte === melhor ? <b>{score}</b> : score}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div className="legenda">
        <span><span className="amostra azul" />menor preço total</span>
        <span><span className="amostra laranja" />melhor custo-benefício</span>
      </div>
    </section>
  )
}

export function Pesquisa() {
  const [produto, setProduto] = useState('rtx 4060')
  const [modo, setModo] = useState<ModoInterface>('comparar')
  const [criterio, setCriterio] = useState<Criterio>('preco')
  const [atraso, setAtraso] = useState(ATRASO_PADRAO)
  const [latenciaPropria, setLatenciaPropria] = useState(false)
  const [catalogo, setCatalogo] = useState<string[]>([])
  const [resposta, setResposta] = useState<RespostaPesquisa | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [carregando, setCarregando] = useState(false)

  useEffect(() => {
    api.produtos().then((r) => setCatalogo(r.produtos)).catch(() => setCatalogo([]))
  }, [])

  async function pesquisar(evento: FormEvent) {
    evento.preventDefault()
    setCarregando(true)
    setErro(null)
    try {
      setResposta(await api.pesquisar({ produto, modo, criterio, ...(latenciaPropria ? {} : { atraso_ms: atraso }) }))
    } catch (e) {
      setErro(mensagemDeErro(e))
    } finally {
      setCarregando(false)
    }
  }

  const respostas = resposta ? (ehComparacao(resposta) ? [resposta.sequencial, resposta.concorrente] : [resposta]) : []
  const principal = respostas.at(-1) // no modo comparar, o resultado mostrado é o concorrente

  return (
    <>
      <form className="formulario" onSubmit={pesquisar}>
        <div className="linha-campos">
          <div className="campo campo-cresce">
            <label htmlFor="produto" className="rotulo">Produto</label>
            <input id="produto" className="entrada" value={produto} required
              onChange={(e) => setProduto(e.target.value)} autoComplete="off" />
            {catalogo.length > 0 && (
              <div className="chips">
                <span className="nota">Catálogo:</span>
                {catalogo.map((item) => (
                  <button key={item} type="button" className="chip" aria-pressed={item === produto}
                    onClick={() => setProduto(item)}>
                    {item}
                  </button>
                ))}
              </div>
            )}
          </div>
          <Segmentado legenda="Modo de consulta" opcoes={MODOS} valor={modo} aoMudar={setModo} />
          <Segmentado legenda="Ordenar por" opcoes={CRITERIOS} valor={criterio} aoMudar={setCriterio} />
        </div>
        <div className="linha-campos" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="campo controle-latencia">
            <label htmlFor="atraso" className="rotulo">
              Latência simulada por loja:{' '}
              <span className="mono" style={{ color: 'var(--azul-texto)' }}>
                {latenciaPropria ? 'a de cada loja' : `${atraso} ms`}
              </span>
            </label>
            <input id="atraso" type="range" min={0} max={ATRASO_MAXIMO_INTERFACE} step={10} value={atraso}
              disabled={latenciaPropria} onChange={(e) => setAtraso(Number(e.target.value))} />
            <label className="marcar">
              <input type="checkbox" checked={latenciaPropria} onChange={(e) => setLatenciaPropria(e.target.checked)} />
              <span>Usar a latência configurada em cada loja (sem <span className="mono">atraso_ms</span>)</span>
            </label>
          </div>
          <button type="submit" className="botao botao-principal" disabled={carregando || !produto.trim()}>
            {carregando ? 'Pesquisando…' : 'Pesquisar nas lojas'}
          </button>
        </div>
      </form>

      {erro && <Alerta tipo="erro" titulo="Não foi possível pesquisar">{erro}</Alerta>}

      {resposta && principal && (
        <>
          <AlertasConsulta resposta={principal} />
          {principal.total_ofertas > 0 && <Destaques resposta={principal} comparacao={resposta} />}
          <section className="painel" aria-labelledby="t-tempos">
            <div className="painel-topo">
              <h2 id="t-tempos">{respostas.length > 1 ? 'Tempo de resposta: soma × máximo' : 'Tempo de resposta por loja'}</h2>
              <span className="nota">cada bloco é uma loja (ms medidos pelo agregador)</span>
            </div>
            <BarrasTempo respostas={respostas} />
          </section>
          {principal.total_ofertas > 0 && <TabelaOfertas resposta={principal} />}
        </>
      )}
    </>
  )
}
