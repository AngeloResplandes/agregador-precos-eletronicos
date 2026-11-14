import { useCallback, useEffect, useState } from 'react'
import { api, mensagemDeErro, type LinhaCsv, type RespostaLog, type TabelaCsv } from '../api'
import { Alerta, Cartao } from '../componentes'
import { formatarCelula, formatarNumero, formatarTemposLojas } from '../formato'

const LIMITE_LOG = 20

const NOMES_TABELAS: Record<string, string> = {
  'exp1_2_resumo.csv': 'Exp. 1–2 (resumo)',
  'exp1_2_bruto.csv': 'Exp. 1–2 (30 repetições)',
  'exp3a_latencia_uniforme.csv': 'Exp. 3a',
  'exp3b_latencia_heterogenea.csv': 'Exp. 3b',
  'exp4_multiplos_clientes.csv': 'Exp. 4',
  'exp5_indisponibilidade.csv': 'Exp. 5',
}

const LEGENDAS_GRAFICOS: Record<string, string> = {
  g1: 'G1 · Sequencial × concorrente',
  g2: 'G2 · Latência uniforme 0–500 ms',
  g3: 'G3 · Latências 100/200/300/400 ms',
  g4: 'G4 · Latência × clientes',
  g5: 'G5 · Vazão × clientes',
  g6: 'G6 · Indisponibilidade de uma loja',
}

function linha(tabelas: TabelaCsv[], arquivo: string, filtro: (l: LinhaCsv) => boolean) {
  return tabelas.find((t) => t.arquivo === arquivo)?.linhas.find(filtro)
}

function Resumo({ tabelas }: { tabelas: TabelaCsv[] }) {
  const seq = linha(tabelas, 'exp1_2_resumo.csv', (l) => l.modo === 'sequencial')
  const conc = linha(tabelas, 'exp1_2_resumo.csv', (l) => l.modo === 'concorrente')
  const carga = linha(tabelas, 'exp4_multiplos_clientes.csv', (l) => l.clientes === '50' && l.modo === 'concorrente')
  const lenta = linha(tabelas, 'exp5_indisponibilidade.csv', (l) => l.cenario.startsWith('c)') && l.modo === 'concorrente')
  if (!seq && !conc && !carga && !lenta) return null
  return (
    <section aria-label="Resumo" className="grade-metricas">
      {seq && conc && (
        <Cartao tipo="metrica" variante="escura" rotulo={`Exp. 1 e 2 · speedup (${conc.n} rep.)`}
          valor={`${formatarNumero(Number(conc.speedup), 2)}×`}
          detalhe={`${formatarCelula(seq.media_ms)} ms → ${formatarCelula(conc.media_ms)} ms`} />
      )}
      {carga && (
        <Cartao tipo="metrica" rotulo="Exp. 4 · 50 clientes" valor={`${formatarNumero(Number(carga.vazao_req_s))} req/s`}
          detalhe={`p95 ${formatarCelula(carga.latencia_p95_ms)} ms · ${carga.falhas} falhas`} />
      )}
      {lenta && (
        <Cartao tipo="metrica" rotulo="Exp. 5 · loja lenta" valor={`${formatarNumero(Number(lenta.tempo_total_ms), 0)} ms`}
          detalhe={`timeout, resposta com ${lenta.lojas_ok} lojas`} />
      )}
    </section>
  )
}

function Tabelas({ tabelas }: { tabelas: TabelaCsv[] }) {
  const [selecionada, setSelecionada] = useState<string | null>(null)
  const atual = tabelas.find((t) => t.arquivo === selecionada) ?? tabelas[0]
  return (
    <section className="painel" aria-labelledby="t-tabelas">
      <div className="painel-topo">
        <h2 id="t-tabelas">Tabelas</h2>
        <div className="segmentado-opcoes" role="group" aria-label="Escolher tabela">
          {tabelas.map((t) => (
            <button key={t.arquivo} type="button" aria-pressed={t.arquivo === atual.arquivo}
              onClick={() => setSelecionada(t.arquivo)}>
              {NOMES_TABELAS[t.arquivo] ?? t.arquivo}
            </button>
          ))}
        </div>
      </div>
      <span className="nota mono">{atual.arquivo}</span>
      <div className="tabela-caixa" style={{ maxHeight: 520, overflowY: 'auto' }}>
        <table className="tabela compacta">
          <thead>
            <tr>{atual.colunas.map((c) => <th key={c} scope="col">{c}</th>)}</tr>
          </thead>
          <tbody>
            {atual.linhas.map((l, i) => (
              <tr key={i}>{atual.colunas.map((c) => <td key={c}>{formatarCelula(l[c] ?? '')}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function LogPesquisas({ log, aoAtualizar }: { log: RespostaLog | null; aoAtualizar: () => void }) {
  return (
    <section className="painel" aria-labelledby="t-log">
      <div className="painel-topo">
        <h2 id="t-log">Últimas pesquisas registradas pelo agregador</h2>
        <button type="button" className="botao botao-contorno" onClick={aoAtualizar}>Atualizar</button>
      </div>
      <span className="nota">
        <span className="mono">log_pesquisas.csv</span> · mais recentes primeiro
        {log ? ` · ${log.total} registros no total` : ''}
      </span>
      {log && log.linhas.length === 0 && <p className="vazio">Nenhuma pesquisa registrada ainda.</p>}
      {log && log.linhas.length > 0 && (
        <div className="tabela-caixa">
          <table className="tabela compacta">
            <thead>
              <tr>
                <th scope="col">Horário</th><th scope="col">Operação</th><th scope="col">Produto</th><th scope="col">Modo</th>
                <th scope="col" className="num">Total (ms)</th><th scope="col">Tempo por loja (ms)</th>
                <th scope="col">Lojas</th><th scope="col">Simult.</th><th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {log.linhas.map((l, i) => (
                <tr key={`${l.timestamp}-${i}`}>
                  <td className="mono">{(l.timestamp ?? '').split('T')[1] ?? l.timestamp}</td>
                  <td>{l.operacao}</td>
                  <td>{l.produto}</td>
                  <td>{l.modo}</td>
                  <td className="num">{formatarCelula(l.tempo_total_ms ?? '')}</td>
                  <td className="mono" style={{ fontSize: 13 }}>{formatarTemposLojas(l.tempos_lojas_ms ?? '')}</td>
                  <td>{l.lojas_responderam ? `${l.lojas_responderam}/${l.lojas_consultadas}` : ''}</td>
                  <td>{l.clientes_simultaneos}</td>
                  <td><span className="codigo-status">{l.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export function Experimentos({ ativa }: { ativa: boolean }) {
  const [dados, setDados] = useState<{ tabelas: TabelaCsv[]; graficos: string[] } | null>(null)
  const [log, setLog] = useState<RespostaLog | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  const carregar = useCallback(async () => {
    setErro(null)
    try {
      const [novosDados, novoLog] = await Promise.all([api.experimentos(), api.log(LIMITE_LOG)])
      setDados(novosDados)
      setLog(novoLog)
    } catch (e) {
      setErro(mensagemDeErro(e))
    }
  }, [])

  // Recarrega ao abrir a aba, para o log mostrar as pesquisas feitas nas outras telas.
  useEffect(() => {
    if (ativa) void carregar()
  }, [ativa, carregar])

  return (
    <>
      <div className="painel-topo">
        <div className="intro">
          <h1>Resultados dos 5 experimentos</h1>
          <p>Lidos de <span className="mono">backend/resultados/</span> · gerados por experimentos.py e graficos.py</p>
        </div>
        <span className="comando">python3 experimentos.py</span>
      </div>

      {erro && <Alerta tipo="erro" titulo="Não foi possível carregar os resultados">{erro}</Alerta>}
      {!dados && !erro && <p className="carregando">Carregando…</p>}

      {dados && (
        <>
          {dados.tabelas.length === 0 && (
            <Alerta tipo="info" titulo="Nenhum experimento encontrado">
              Rode <span className="mono">python3 experimentos.py</span> e <span className="mono">graficos.py</span> em backend/.
            </Alerta>
          )}
          <Resumo tabelas={dados.tabelas} />
          {dados.graficos.length > 0 && (
            <section className="painel" aria-labelledby="t-graficos">
              <h2 id="t-graficos" style={{ fontSize: 22 }}>Gráficos</h2>
              <div className="galeria">
                {dados.graficos.map((nome) => {
                  const legenda = LEGENDAS_GRAFICOS[nome.slice(0, 2)] ?? nome
                  return (
                    <figure key={nome}>
                      <a href={api.urlGrafico(nome)} target="_blank" rel="noreferrer">
                        <img src={api.urlGrafico(nome)} alt={legenda} loading="lazy" />
                      </a>
                      <figcaption>{legenda}</figcaption>
                    </figure>
                  )
                })}
              </div>
            </section>
          )}
          {dados.tabelas.length > 0 && <Tabelas tabelas={dados.tabelas} />}
        </>
      )}
      <LogPesquisas log={log} aoAtualizar={() => void carregar()} />
    </>
  )
}
