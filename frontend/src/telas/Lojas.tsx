import { useState } from 'react'
import { api, mensagemDeErro, type AcaoLoja, type RespostaConsulta, type StatusLoja } from '../api'
import type { StatusSistema } from '../App'
import { Alerta, AlertasConsulta, Cartao } from '../componentes'
import { formatarMoeda, formatarMs } from '../formato'

const PRODUTO_DEMO = 'rtx 4060'

const DETECCAO = [
  { situacao: 'Loja desligada antes da pesquisa', deteccao: 'ConnectionRefusedError', status: 'erro_comunicacao' },
  { situacao: 'Loja cai durante a consulta', deteccao: 'recv() vazio → ConexaoEncerrada', status: 'erro_comunicacao' },
  { situacao: 'Loja lenta além do limite', deteccao: 'socket.timeout após 2,5 s', status: 'timeout' },
  { situacao: 'Resposta malformada ou incompleta', deteccao: 'validar_resposta_loja → MensagemInvalida', status: 'erro_comunicacao' },
]

/** Status de uma loja (ping TCP) e o botão para derrubar ou subir o processo. */
function CartaoLoja({ loja, podeControlar, ocupado, aoAgir }:
  { loja: StatusLoja; podeControlar: boolean; ocupado: boolean; aoAgir: (acao: AcaoLoja) => void }) {
  return (
    <div className={`loja ${loja.online ? '' : 'fora'}`}>
      <div className="loja-topo">
        <span className="loja-nome">{loja.nome}</span>
        <span className={`selo ${loja.online ? 'no-ar' : 'fora-do-ar'}`}>
          <span className="ponto" />
          {loja.online ? 'No ar' : 'Fora do ar'}
        </span>
      </div>
      <span className="loja-endereco">
        {loja.host}:{loja.porta}
        {loja.latencia_ms !== null ? ` · ${loja.latencia_ms} ms` : ''}
      </span>
      {podeControlar && (
        <button type="button" className={`botao ${loja.online ? 'botao-contorno' : 'botao-principal'}`}
          style={{ minHeight: 44, fontSize: 15 }} disabled={ocupado} onClick={() => aoAgir(loja.online ? 'derrubar' : 'subir')}>
          {ocupado ? 'Aguarde…' : loja.online ? 'Derrubar loja' : 'Subir loja'}
        </button>
      )}
    </div>
  )
}

export function Lojas({ status }: { status: StatusSistema }) {
  const [ocupada, setOcupada] = useState<string | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [resposta, setResposta] = useState<RespostaConsulta | null>(null)
  const [pesquisando, setPesquisando] = useState(false)

  async function agir(nome: string, acao: AcaoLoja) {
    setOcupada(nome)
    setErro(null)
    try {
      await api.controlarLoja(nome, acao)
    } catch (e) {
      setErro(mensagemDeErro(e))
    } finally {
      await status.atualizar()
      setOcupada(null)
    }
  }

  async function pesquisarAgora() {
    setPesquisando(true)
    setErro(null)
    try {
      const r = await api.pesquisar({ produto: PRODUTO_DEMO, modo: 'concorrente', criterio: 'preco' })
      if (r.modo_execucao !== 'comparar') setResposta(r)
    } catch (e) {
      setErro(mensagemDeErro(e))
    } finally {
      setPesquisando(false)
    }
  }

  return (
    <>
      <div className="intro">
        <h1>Cada loja é um processo TCP independente</h1>
        <p>
          Derrube uma loja e pesquise de novo: o agregador continua respondendo com as demais e informa o
          motivo da falha. Status atualizado a cada 2 s por <span className="mono">ping</span>.
        </p>
      </div>

      {status.erro && <Alerta tipo="erro" titulo="Gateway HTTP fora do ar">{status.erro}</Alerta>}
      {!status.erro && status.carregado && !status.gerenciaProcessos && (
        <Alerta tipo="info" titulo="Controle de processos desativado">
          O gateway foi iniciado com <span className="mono">--externo</span>, então só mostra o status. Para
          derrubar uma loja, pressione Ctrl+C no terminal dela, ou reinicie o gateway sem essa opção.
        </Alerta>
      )}
      {erro && <Alerta tipo="erro" titulo="A operação falhou">{erro}</Alerta>}

      <section aria-label="Lojas" className="grade-cartoes">
        {status.lojas.map((loja) => (
          <CartaoLoja key={loja.nome} loja={loja} podeControlar={status.gerenciaProcessos}
            ocupado={ocupada === loja.nome} aoAgir={(acao) => void agir(loja.nome, acao)} />
        ))}
      </section>

      <section className="painel" aria-labelledby="t-ultima">
        <div className="painel-topo">
          <h2 id="t-ultima">Pesquisa com as lojas no estado atual</h2>
          <button type="button" className="botao botao-escuro" onClick={() => void pesquisarAgora()} disabled={pesquisando}>
            {pesquisando ? 'Pesquisando…' : `Pesquisar “${PRODUTO_DEMO}” agora`}
          </button>
        </div>
        {!resposta && <p className="vazio">Ainda não houve pesquisa nesta tela.</p>}
        {resposta && (
          <>
            {resposta.ocorrencias_ou_falhas.length === 0 && (
              <Alerta tipo="sucesso" titulo={`${resposta.total_lojas_responderam}/${resposta.total_lojas_consultadas} lojas responderam.`} />
            )}
            <AlertasConsulta resposta={resposta} />
            <div className="grade-metricas">
              <Cartao tipo="metrica" variante="suave" rotulo="Menor preço total"
                valor={resposta.menor_preco ? formatarMoeda(resposta.menor_preco.preco_total) : '—'}
                detalhe={resposta.menor_preco?.fonte} />
              <Cartao tipo="metrica" variante="suave" rotulo="Tempo total (concorrente)" valor={formatarMs(resposta.tempo_total_ms)}
                detalhe={resposta.ocorrencias_ou_falhas.some((f) => f.status === 'timeout') ? 'inclui a espera do timeout' : undefined} />
              <Cartao tipo="metrica" variante="suave" rotulo="Ofertas válidas" valor={String(resposta.total_ofertas)}
                detalhe={resposta.ofertas_ordenadas.map((o) => o.fonte.replace(/Sim$/, '')).join(', ')} />
            </div>
          </>
        )}
      </section>

      <section className="painel" aria-labelledby="t-deteccao">
        <h2 id="t-deteccao" style={{ fontSize: 22 }}>Como cada falha é detectada</h2>
        <div className="tabela-caixa">
          <table className="tabela" style={{ minWidth: 640 }}>
            <thead>
              <tr><th scope="col">Situação</th><th scope="col">Detecção no agregador</th><th scope="col">Status</th></tr>
            </thead>
            <tbody>
              {DETECCAO.map((linha) => (
                <tr key={linha.situacao}>
                  <td>{linha.situacao}</td>
                  <td>{linha.deteccao}</td>
                  <td><span className="codigo-status">{linha.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}
