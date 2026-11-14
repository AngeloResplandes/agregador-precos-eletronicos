import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { api, mensagemDeErro, type Saude, type StatusLoja } from './api'
import { Carga } from './telas/Carga'
import { Experimentos } from './telas/Experimentos'
import { Lojas } from './telas/Lojas'
import { Pesquisa } from './telas/Pesquisa'

const ABAS = [
  { id: 'pesquisa', rotulo: 'Pesquisa' },
  { id: 'lojas', rotulo: 'Lojas e falhas' },
  { id: 'carga', rotulo: 'Teste de carga' },
  { id: 'experimentos', rotulo: 'Experimentos e log' },
]

// ---------------------------------------------------------------- status do sistema
export interface StatusSistema {
  saude: Saude | null
  lojas: StatusLoja[]
  gerenciaProcessos: boolean
  /** Erro ao falar com o gateway (null quando ele respondeu). */
  erro: string | null
  carregado: boolean
  atualizar: () => Promise<void>
}

const SEM_STATUS = { saude: null, lojas: [], gerenciaProcessos: false, erro: null, carregado: false }

/** Consulta o status do agregador e das lojas (ping TCP feito pelo gateway) a cada `intervaloMs`. */
function useStatusSistema(intervaloMs = 2000): StatusSistema {
  const [estado, setEstado] = useState<Omit<StatusSistema, 'atualizar'>>(SEM_STATUS)
  const emAndamento = useRef(false)

  const atualizar = useCallback(async () => {
    if (emAndamento.current) return
    emAndamento.current = true
    try {
      const [saude, status] = await Promise.all([api.saude(), api.lojas()])
      setEstado({ saude, lojas: status.lojas, gerenciaProcessos: status.gerencia_processos, erro: null, carregado: true })
    } catch (e) {
      // Sem gateway não há status confiável: não mostrar lojas (nem botões) desatualizados.
      setEstado({ ...SEM_STATUS, erro: mensagemDeErro(e), carregado: true })
    } finally {
      emAndamento.current = false
    }
  }, [])

  useEffect(() => {
    void atualizar()
    const id = window.setInterval(() => void atualizar(), intervaloMs)
    return () => window.clearInterval(id)
  }, [atualizar, intervaloMs])

  return { ...estado, atualizar }
}

// ---------------------------------------------------------------- cabeçalho
function PilulasStatus({ status }: { status: StatusSistema }) {
  if (!status.carregado) {
    return <span className="pilula"><span className="ponto desligado" />Verificando…</span>
  }
  if (status.erro) {
    return <span className="pilula"><span className="ponto alerta" />Gateway HTTP fora do ar</span>
  }
  const noAr = status.lojas.filter((loja) => loja.online).length
  const total = status.lojas.length
  const agregadorOk = status.saude?.agregador_online ?? false
  const porta = status.saude?.agregador.split(':').pop()
  return (
    <>
      <span className="pilula">
        <span className={`ponto ${agregadorOk ? 'ok' : 'alerta'}`} />
        {agregadorOk ? `Agregador :${porta}` : 'Agregador fora do ar'}
      </span>
      <span className="pilula">
        <span className={`ponto ${noAr === total ? 'ok' : 'alerta'}`} />
        {noAr}/{total} lojas no ar
      </span>
    </>
  )
}

function Cabecalho({ abaAtual, aoTrocarAba, status }: { abaAtual: string; aoTrocarAba: (id: string) => void; status: StatusSistema }) {
  return (
    <header className="cabecalho">
      <div className="cabecalho-interno">
        <div className="cabecalho-topo">
          <div className="marca">
            <span className="marca-nome">Agregador de Eletrônicos</span>
            <span className="marca-sub">Trabalho 1 · Sistemas Distribuídos · sockets TCP + threads</span>
          </div>
          <div className="pilulas" aria-live="polite">
            <PilulasStatus status={status} />
          </div>
        </div>
        <nav aria-label="Telas">
          <div className="abas" role="tablist">
            {ABAS.map((aba) => (
              <button key={aba.id} type="button" role="tab" id={`aba-${aba.id}`} aria-controls={`painel-${aba.id}`}
                aria-selected={aba.id === abaAtual} className="aba" onClick={() => aoTrocarAba(aba.id)}>
                {aba.rotulo}
              </button>
            ))}
          </div>
        </nav>
      </div>
    </header>
  )
}

// ---------------------------------------------------------------- aplicação
function abaDoEndereco(): string {
  const id = window.location.hash.replace('#', '')
  return ABAS.some((aba) => aba.id === id) ? id : ABAS[0].id
}

export default function App() {
  const [aba, setAba] = useState(abaDoEndereco)
  const status = useStatusSistema()

  useEffect(() => {
    const aoMudarEndereco = () => setAba(abaDoEndereco())
    window.addEventListener('hashchange', aoMudarEndereco)
    return () => window.removeEventListener('hashchange', aoMudarEndereco)
  }, [])

  function trocarAba(id: string) {
    window.location.hash = id
    setAba(id)
  }

  // As telas ficam montadas (apenas ocultas) para não perder a última pesquisa ao trocar de aba.
  const paineis: Record<string, ReactNode> = {
    pesquisa: <Pesquisa />,
    lojas: <Lojas status={status} />,
    carga: <Carga />,
    experimentos: <Experimentos ativa={aba === 'experimentos'} />,
  }

  return (
    <>
      <Cabecalho abaAtual={aba} aoTrocarAba={trocarAba} status={status} />
      {ABAS.map(({ id }) => (
        <main key={id} id={`painel-${id}`} role="tabpanel" aria-labelledby={`aba-${id}`} hidden={id !== aba}
          className="conteudo">
          {paineis[id]}
        </main>
      ))}
    </>
  )
}
