#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo: graficos.py (Gera os gráficos PNG a partir dos CSVs de resultados/)

Requer matplotlib (pip install -r requirements.txt).
Uso:
    python experimentos.py && python graficos.py
"""
import csv
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from config import DIRETORIO_RESULTADOS  # noqa: E402

# Paleta (categorical slots 1 e 2) e tinta de texto/eixos
COR = {"sequencial": "#2a78d6", "concorrente": "#eb6834"}
NOME = {"sequencial": "Sequencial", "concorrente": "Concorrente (threads)"}
SUPERFICIE, TEXTO, TEXTO_2, GRADE = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
MODOS = ("sequencial", "concorrente")

plt.rcParams.update({
    "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE, "savefig.facecolor": SUPERFICIE,
    "axes.edgecolor": GRADE, "axes.labelcolor": TEXTO_2, "xtick.color": TEXTO_2, "ytick.color": TEXTO_2,
    "text.color": TEXTO, "axes.titleweight": "bold", "axes.titlesize": 13, "axes.titlelocation": "left",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.grid.axis": "y",
    "grid.color": GRADE, "grid.linewidth": 0.8, "axes.axisbelow": True, "font.size": 10.5,
    "legend.frameon": False, "lines.linewidth": 2, "figure.dpi": 110,
})


def ler(nome):
    with open(os.path.join(DIRETORIO_RESULTADOS, nome), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def salvar(fig, nome):
    caminho = os.path.join(DIRETORIO_RESULTADOS, nome)
    fig.tight_layout()
    fig.savefig(caminho, dpi=160)
    plt.close(fig)
    print(f"[OK] {caminho}")


def novo_grafico(tamanho, titulo, subtexto, ylabel, xlabel=None):
    """Figura com título, subtítulo e rótulos dos eixos no padrão visual do trabalho."""
    fig, ax = plt.subplots(figsize=tamanho)
    ax.set_title(titulo, pad=22)
    ax.text(0, 1.02, subtexto, transform=ax.transAxes, color=TEXTO_2, fontsize=9.5, va="bottom")
    if ylabel:
        ax.set_ylabel(ylabel)
    if xlabel:
        ax.set_xlabel(xlabel)
    return fig, ax


def linhas_por_modo(ax, dados, campo_x, campo_y, unidade):
    """Uma linha por modo, com o último valor anotado à direita."""
    for m in MODOS:
        x, y = zip(*[(int(l[campo_x]), float(l[campo_y])) for l in dados if l["modo"] == m])
        ax.plot(x, y, color=COR[m], marker="o", markersize=6, label=NOME[m])
        ax.annotate(f"{y[-1]:.0f} {unidade}", (x[-1], y[-1]), xytext=(8, 0), textcoords="offset points",
                    va="center", color=TEXTO)


def g1_seq_vs_conc():
    linhas = {l["modo"]: l for l in ler("exp1_2_resumo.csv")}
    fig, ax = novo_grafico((6.4, 4.4), "Exp. 1 e 2 — Sequencial × concorrente",
                           f"Média de {linhas['sequencial']['n']} pesquisas, 4 lojas com 150 ms de latência "
                           f"(speedup {linhas['concorrente']['speedup']}x)", "Tempo total da pesquisa (ms)")
    medias = [float(linhas[m]["media_ms"]) for m in MODOS]
    desvios = [float(linhas[m]["desvio_ms"]) for m in MODOS]
    barras = ax.bar([NOME[m] for m in MODOS], medias, yerr=desvios, width=0.5, capsize=5,
                    color=[COR[m] for m in MODOS], error_kw={"ecolor": TEXTO_2, "lw": 1})
    for b, v in zip(barras, medias):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.02 + 8, f"{v:.0f} ms", ha="center", color=TEXTO)
    ax.set_ylim(0, max(medias) * 1.18)
    salvar(fig, "g1_sequencial_vs_concorrente.png")


def g2_latencia_uniforme():
    dados = ler("exp3a_latencia_uniforme.csv")
    fig, ax = novo_grafico((7.2, 4.4), "Exp. 3a — Tempo total conforme a latência das lojas",
                           "Sequencial cresce ≈ 4 × latência; concorrente ≈ 1 × latência",
                           "Tempo total da pesquisa (ms)", "Latência artificial de cada loja (ms)")
    linhas_por_modo(ax, dados, "latencia_ms", "media_ms", "ms")
    ax.legend(loc="upper left")
    ax.set_xlim(-20, max(int(l["latencia_ms"]) for l in dados) * 1.15)
    salvar(fig, "g2_latencia_uniforme.png")


def g3_latencia_heterogenea():
    dados = {l["modo"]: l for l in ler("exp3b_latencia_heterogenea.csv")}
    fig, ax = novo_grafico((6.4, 4.4), "Exp. 3b — Lojas com latências 100/200/300/400 ms",
                           "Tracejado = previsto: soma (sequencial) e maior latência (concorrente)",
                           "Tempo total da pesquisa (ms)")
    medias = [float(dados[m]["media_ms"]) for m in MODOS]
    previstos = [float(dados[m]["previsto_ms"]) for m in MODOS]
    barras = ax.bar([NOME[m] for m in MODOS], medias, width=0.5, color=[COR[m] for m in MODOS])
    for b, v, p in zip(barras, medias, previstos):
        ax.hlines(p, b.get_x() - 0.06, b.get_x() + b.get_width() + 0.06, colors=TEXTO, linestyles="--", lw=1.2)
        ax.text(b.get_x() + b.get_width() / 2, v + 25, f"{v:.0f} ms (previsto {p:.0f})", ha="center", color=TEXTO)
    ax.set_ylim(0, max(medias) * 1.18)
    salvar(fig, "g3_latencia_heterogenea.png")


def g4_multiplos_clientes_latencia():
    dados = ler("exp4_multiplos_clientes.csv")
    fig, ax = novo_grafico((7.2, 4.4), "Exp. 4 — Tempo de resposta com vários clientes",
                           "Latência de 100 ms por loja; o agregador atende cada cliente em uma thread",
                           "Tempo de resposta por pesquisa (ms)", "Clientes simultâneos")
    for m in MODOS:
        do_modo = [l for l in dados if l["modo"] == m]
        x = [int(l["clientes"]) for l in do_modo]
        ax.plot(x, [float(l["latencia_media_ms"]) for l in do_modo], color=COR[m], marker="o", markersize=6,
                label=f"{NOME[m]} — média")
        ax.plot(x, [float(l["latencia_p95_ms"]) for l in do_modo], color=COR[m], linestyle="--", lw=1.5,
                label=f"{NOME[m]} — p95")
    ax.set_ylim(0, None)
    ax.legend(loc="center right", fontsize=9)
    salvar(fig, "g4_multiplos_clientes_latencia.png")


def g5_multiplos_clientes_vazao():
    dados = ler("exp4_multiplos_clientes.csv")
    fig, ax = novo_grafico((7.2, 4.4), "Exp. 4 — Vazão do agregador",
                           "Pesquisas concluídas por segundo em cada lote de clientes simultâneos",
                           "Vazão (pesquisas por segundo)", "Clientes simultâneos")
    linhas_por_modo(ax, dados, "clientes", "vazao_req_s", "req/s")
    ax.set_xlim(0, max(int(l["clientes"]) for l in dados) * 1.18)
    ax.legend(loc="upper left")
    salvar(fig, "g5_multiplos_clientes_vazao.png")


def g6_indisponibilidade():
    dados = ler("exp5_indisponibilidade.csv")
    cenarios = list(dict.fromkeys(l["cenario"] for l in dados))
    fig, ax = novo_grafico((8, 4.8), "Exp. 5 — Indisponibilidade da loja MagaluTechSim",
                           "A pesquisa sempre conclui com as lojas restantes; o timeout limita a espera",
                           None, "Tempo total da pesquisa (ms)")
    altura = 0.36
    for i, m in enumerate(MODOS):
        valores = {l["cenario"]: l for l in dados if l["modo"] == m}
        ys = [k + (i - 0.5) * (altura + 0.04) for k in range(len(cenarios))]
        ts = [float(valores[c]["tempo_total_ms"]) for c in cenarios]
        ax.barh(ys, ts, height=altura, color=COR[m], label=NOME[m])
        for y, t, c in zip(ys, ts, cenarios):
            ax.text(t + 30, y, f"{t:.0f} ms · {valores[c]['lojas_ok']} lojas · "
                               f"{valores[c]['status_loja_afetada']}", va="center", fontsize=8.5, color=TEXTO)
    ax.set_yticks(range(len(cenarios)))
    ax.set_yticklabels(cenarios)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_xlim(0, max(float(l["tempo_total_ms"]) for l in dados) * 1.55)
    ax.legend(loc="lower right")
    salvar(fig, "g6_indisponibilidade.png")


def main():
    try:
        for grafico in (g1_seq_vs_conc, g2_latencia_uniforme, g3_latencia_heterogenea,
                        g4_multiplos_clientes_latencia, g5_multiplos_clientes_vazao, g6_indisponibilidade):
            grafico()
    except FileNotFoundError as exc:
        print(f"[ERRO] {exc.filename} não encontrado. Rode antes: python experimentos.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
