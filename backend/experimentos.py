#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo: experimentos.py (Execução automatizada dos 5 experimentos obrigatórios)

Sobe as 4 lojas e o agregador como PROCESSOS independentes, executa os
experimentos através do cliente TCP real e grava as tabelas em resultados/*.csv
e resultados/tabelas.md. Os gráficos são gerados depois por graficos.py.

Uso:
    python experimentos.py            # bateria completa (~2-3 min)
    python experimentos.py --rapido   # menos repetições (para testar)
"""
import argparse
import csv
import os
import platform
import statistics
import subprocess
import sys
import threading
import time
from datetime import datetime

import protocolo
from cliente import ErroCliente, disparar_clientes_simultaneos, requisitar_agregador
from config import DIRETORIO_RESULTADOS, LOJAS, TIMEOUT_LOJA
from iniciar_servicos import Ambiente, tratar_sinais_de_encerramento

SEQ, CONC = protocolo.MODO_SEQUENCIAL, protocolo.MODO_CONCORRENTE
MODOS = (SEQ, CONC)
PRODUTO = "notebook"
LOJA_ALVO = LOJAS[-1]  # loja usada no experimento de indisponibilidade

tabelas_md = []


# ---------------------------------------------------------------------- utilitários
def resumo(valores: list) -> dict:
    return {
        "n": len(valores),
        "media_ms": round(statistics.mean(valores), 2),
        "desvio_ms": round(statistics.stdev(valores), 2) if len(valores) > 1 else 0.0,
        "min_ms": round(min(valores), 2),
        "max_ms": round(max(valores), 2),
    }


def percentil(valores: list, p: int) -> float:
    if len(valores) == 1:
        return valores[0]
    return statistics.quantiles(valores, n=100, method="inclusive")[p - 1]


def gravar_csv(nome: str, linhas: list) -> None:
    with open(os.path.join(DIRETORIO_RESULTADOS, nome), "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0].keys()))
        escritor.writeheader()
        escritor.writerows(linhas)


def salvar(nome_csv: str, titulo: str, linhas: list) -> None:
    """Grava resultados/<nome_csv>, imprime a tabela no console e acumula a versão Markdown."""
    gravar_csv(nome_csv, linhas)
    colunas = list(linhas[0].keys())
    larguras = [max(len(str(c)), *(len(str(l[c])) for l in linhas)) for c in colunas]
    print(f"\n{titulo}")
    print("  ".join(str(c).ljust(w) for c, w in zip(colunas, larguras)))
    print("  ".join("-" * w for w in larguras))
    for l in linhas:
        print("  ".join(str(l[c]).ljust(w) for c, w in zip(colunas, larguras)))
    md = [f"### {titulo}", "", "| " + " | ".join(colunas) + " |",
          "|" + "|".join("---" for _ in colunas) + "|"]
    md += ["| " + " | ".join(str(l[c]) for c in colunas) + " |" for l in linhas]
    tabelas_md.append("\n".join(md) + "\n")


def cabecalho(texto: str) -> None:
    print("\n" + "=" * 90 + f"\n {texto}\n" + "=" * 90, flush=True)


def medir(modo: str, atraso_ms=None, produto: str = PRODUTO) -> dict:
    """Uma pesquisa completa pelo cliente TCP. Devolve a resposta do agregador."""
    return requisitar_agregador(produto, modo, protocolo.CRITERIO_PRECO, atraso_ms)


def aquecer():
    for modo in MODOS:
        medir(modo, atraso_ms=0)


# ---------------------------------------------------------------------- experimentos
def experimentos_1_e_2(repeticoes: int) -> None:
    cabecalho(f"EXPERIMENTOS 1 e 2 - SEQUENCIAL x CONCORRENTE ({repeticoes} repetições, latência 150 ms)")
    brutos, tempos = [], {SEQ: [], CONC: []}
    for rep in range(1, repeticoes + 1):
        for modo in MODOS:
            t = medir(modo)["tempo_total_ms"]
            tempos[modo].append(t)
            brutos.append({"repeticao": rep, "modo": modo, "tempo_total_ms": t})
    gravar_csv("exp1_2_bruto.csv", brutos)

    linhas = [{"modo": modo, **resumo(tempos[modo])} for modo in MODOS]
    speedup = round(linhas[0]["media_ms"] / linhas[1]["media_ms"], 2)
    for l in linhas:
        l["speedup"] = speedup if l["modo"] == CONC else 1.0
    salvar("exp1_2_resumo.csv", "Exp. 1 e 2 - Tempo total da pesquisa (4 lojas, 150 ms cada)", linhas)


def experimento_3a(repeticoes: int) -> None:
    cabecalho(f"EXPERIMENTO 3a - LATÊNCIA UNIFORME VARIÁVEL ({repeticoes} repetições por ponto)")
    linhas = []
    for latencia in (0, 50, 100, 200, 350, 500):
        medias = {}
        for modo in MODOS:
            r = resumo([medir(modo, latencia)["tempo_total_ms"] for _ in range(repeticoes)])
            medias[modo] = r["media_ms"]
            linhas.append({"latencia_ms": latencia, "modo": modo, **r})
        speedup = round(medias[SEQ] / medias[CONC], 2) if medias[CONC] > 0 else ""
        linhas[-1]["speedup"] = speedup
        linhas[-2]["speedup"] = 1.0
    salvar("exp3a_latencia_uniforme.csv",
           "Exp. 3a - Tempo total x latência artificial (igual em todas as lojas)", linhas)


def experimento_3b(repeticoes: int, ambiente_args: dict) -> None:
    latencias = [100, 200, 300, 400]
    cabecalho(f"EXPERIMENTO 3b - LATÊNCIAS HETEROGÊNEAS {latencias} ms ({repeticoes} repetições)")
    with Ambiente(latencias=latencias, **ambiente_args):
        aquecer()
        linhas = []
        for modo in MODOS:
            # sem atraso_ms na requisição: cada loja usa a sua própria latência
            r = resumo([medir(modo)["tempo_total_ms"] for _ in range(repeticoes)])
            teorico = sum(latencias) if modo == SEQ else max(latencias)
            linhas.append({"modo": modo, **r, "previsto_ms": teorico,
                           "regra": "soma das latências" if modo == SEQ else "maior latência"})
    salvar("exp3b_latencia_heterogenea.csv",
           "Exp. 3b - Lojas com latências diferentes (100/200/300/400 ms)", linhas)


def experimento_4(rodadas: int) -> None:
    cabecalho(f"EXPERIMENTO 4 - MÚLTIPLOS CLIENTES SIMULTÂNEOS (latência 100 ms, {rodadas} rodadas)")
    linhas = []
    for n in (1, 5, 10, 20, 50):
        for modo in MODOS:
            lotes = [disparar_clientes_simultaneos(n, PRODUTO, modo, atraso_ms=100) for _ in range(rodadas)]
            tempos = [t for lote in lotes for t in lote["tempos_ms"]]
            lote_medio = statistics.mean(lote["tempo_total_ms"] for lote in lotes)
            linhas.append({
                "clientes": n, "modo": modo,
                "latencia_media_ms": round(statistics.mean(tempos), 2),
                "latencia_p95_ms": round(percentil(tempos, 95), 2),
                "latencia_max_ms": round(max(tempos), 2),
                "tempo_lote_ms": round(lote_medio, 2),
                "vazao_req_s": round(n / (lote_medio / 1000.0), 2),
                "falhas": sum(f is not None for lote in lotes for f in lote["falhas"]),
            })
    salvar("exp4_multiplos_clientes.csv", "Exp. 4 - Clientes simultâneos (tempo medido no cliente)", linhas)


def _registrar_falha(cenario: str, modo: str, resp: dict) -> dict:
    alvo = next((f for f in resp.get("ocorrencias_ou_falhas", []) if f.get("fonte") == LOJA_ALVO["nome"]), {})
    return {
        "cenario": cenario, "modo": modo,
        "tempo_total_ms": resp.get("tempo_total_ms"),
        "lojas_ok": f"{resp.get('total_ofertas')}/{resp.get('total_lojas_consultadas')}",
        "status_loja_afetada": alvo.get("status", "sucesso"),
        "detalhe": (alvo.get("detalhe") or "-").split(":")[0],
        "menor_preco": resp["menor_preco"]["fonte"] if resp.get("menor_preco") else "-",
    }


def experimento_5(ambiente: Ambiente) -> None:
    cabecalho(f"EXPERIMENTO 5 - INDISPONIBILIDADE DA LOJA {LOJA_ALVO['nome']} (timeout da loja: {TIMEOUT_LOJA}s)")
    nome = LOJA_ALVO["nome"]
    linhas = []

    def rodada(cenario):
        linhas.extend(_registrar_falha(cenario, modo, medir(modo)) for modo in MODOS)

    rodada("0) todas as lojas ativas")  # referência: todas as lojas no ar

    ambiente.derrubar_loja(nome)  # (a) loja desligada antes da pesquisa -> conexão recusada
    rodada("a) loja desligada antes")

    # (b) Loja derrubada DURANTE a pesquisa -> conexão encerrada sem resposta
    for modo, espera in ((CONC, 0.3), (SEQ, 0.75)):
        ambiente.subir_loja(LOJA_ALVO, 2000)  # a loja demora 2 s para responder
        resposta = {}
        t = threading.Thread(target=lambda: resposta.update(medir(modo)))
        t.start()
        time.sleep(espera)  # a consulta à loja já está em andamento
        ambiente.derrubar_loja(nome)
        t.join()
        linhas.append(_registrar_falha("b) loja derrubada durante", modo, resposta))

    # (c) Loja travada / lenta demais -> timeout do agregador
    ambiente.subir_loja(LOJA_ALVO, int(TIMEOUT_LOJA * 1000) + 3000)
    rodada("c) loja lenta (timeout)")

    # (d) Recuperação: a loja volta e passa a ser consultada normalmente
    ambiente.derrubar_loja(nome)
    ambiente.subir_loja(LOJA_ALVO, LOJA_ALVO["latencia_ms"])
    rodada("d) loja recuperada")

    salvar("exp5_indisponibilidade.csv", "Exp. 5 - Comportamento diante da indisponibilidade de uma loja", linhas)


# ---------------------------------------------------------------------- main
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Executa os 5 experimentos obrigatórios.")
    parser.add_argument("--rapido", action="store_true", help="menos repetições")
    parser.add_argument("--verboso", action="store_true", help="mostra a saída dos servidores")
    args = parser.parse_args(argv)

    rep_12, rep_3, rodadas_4 = (5, 3, 1) if args.rapido else (30, 10, 3)
    os.makedirs(DIRETORIO_RESULTADOS, exist_ok=True)
    ambiente_args = {"saida": None if args.verboso else subprocess.DEVNULL}

    cabecalho("BATERIA DOS 5 EXPERIMENTOS - TEMA 6 (AGREGADOR DE ELETRÔNICOS)")
    print(f" Início: {datetime.now():%d/%m/%Y %H:%M:%S} | Python {platform.python_version()} | "
          f"{platform.system()} {platform.machine()} | {os.cpu_count()} CPUs")
    print(" Subindo 4 lojas (portas 9001-9004) e o agregador (porta 8000) como processos...", flush=True)

    tratar_sinais_de_encerramento()
    inicio = time.perf_counter()
    try:
        with Ambiente(**ambiente_args):
            aquecer()
            experimentos_1_e_2(rep_12)
            experimento_3a(rep_3)
        experimento_3b(rep_3, ambiente_args)  # sobe um ambiente próprio, com latências diferentes
        with Ambiente(**ambiente_args) as ambiente:
            aquecer()
            experimento_4(rodadas_4)
            experimento_5(ambiente)
    except (RuntimeError, ErroCliente) as exc:
        print(f"\n[ERRO] {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n[!] Experimentos interrompidos; processos encerrados.", file=sys.stderr)
        return 1

    with open(os.path.join(DIRETORIO_RESULTADOS, "tabelas.md"), "w", encoding="utf-8") as arquivo:
        arquivo.write(f"# Resultados dos experimentos\n\nGerado em {datetime.now():%d/%m/%Y %H:%M} — "
                      f"Python {platform.python_version()}, {platform.system()} {platform.machine()}, "
                      f"{os.cpu_count()} CPUs.\n\n")
        arquivo.write("\n".join(tabelas_md))

    cabecalho(f"BATERIA CONCLUÍDA em {time.perf_counter() - inicio:.1f}s")
    print(f" CSVs e tabelas.md em: {DIRETORIO_RESULTADOS}")
    print(" Para gerar os gráficos: python graficos.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
