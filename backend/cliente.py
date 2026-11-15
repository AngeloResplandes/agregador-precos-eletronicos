#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo: cliente.py (Interface do usuário comprador via socket TCP)

Uso:
    python cliente.py                                  # menu interativo
    python cliente.py notebook                         # compara sequencial x concorrente
    python cliente.py rtx 4060 --modo concorrente --criterio custo_beneficio
    python cliente.py --listar                         # catálogo disponível
    python cliente.py rtx 4060 --clientes 20           # 20 clientes simultâneos (Exp. 4)
"""
import argparse
import statistics
import sys
import threading
import time

import protocolo
from config import HOST, MAX_CLIENTES_CARGA, PORTA_AGREGADOR, TIMEOUT_CLIENTE

LARGURA = 100


class ErroCliente(Exception):
    """Falha de comunicação com o agregador, com mensagem amigável."""


# ---------------------------------------------------------------------- comunicação com o agregador
def _requisitar(mensagem: dict, host: str, porta: int, timeout: float) -> dict:
    try:
        return protocolo.requisitar(host, porta, mensagem, timeout)
    except ConnectionRefusedError:
        raise ErroCliente(f"agregador indisponível em {host}:{porta} (conexão recusada). Ele foi iniciado?") from None
    except TimeoutError:
        raise ErroCliente(f"o agregador não respondeu em {timeout}s") from None
    except protocolo.ConexaoEncerrada:
        raise ErroCliente("o agregador encerrou a conexão sem responder") from None
    except protocolo.MensagemInvalida as exc:
        raise ErroCliente(f"resposta inválida do agregador: {exc}") from None
    except OSError as exc:
        raise ErroCliente(f"falha de comunicação com o agregador: {exc}") from None


def requisitar_agregador(produto: str, modo: str = protocolo.MODO_CONCORRENTE,
                         criterio: str = protocolo.CRITERIO_PRECO, atraso_ms=None,
                         host: str = HOST, porta: int = PORTA_AGREGADOR, timeout: float = TIMEOUT_CLIENTE) -> dict:
    """Envia uma pesquisa ao agregador e devolve a resposta consolidada."""
    mensagem = {"operacao": protocolo.OP_CONSULTAR, "produto": produto, "modo": modo, "criterio": criterio}
    if atraso_ms is not None:
        mensagem["atraso_ms"] = atraso_ms
    return _requisitar(mensagem, host, porta, timeout)


def listar_produtos(host: str = HOST, porta: int = PORTA_AGREGADOR, timeout: float = TIMEOUT_CLIENTE) -> dict:
    return _requisitar({"operacao": protocolo.OP_LISTAR_PRODUTOS}, host, porta, timeout)


def comparar(produto: str, criterio: str = protocolo.CRITERIO_PRECO, atraso_ms=None, **conexao) -> dict:
    """Faz a mesma pesquisa nos dois modos e calcula o speedup (tempo sequencial / concorrente)."""
    seq = requisitar_agregador(produto, protocolo.MODO_SEQUENCIAL, criterio, atraso_ms, **conexao)
    conc = requisitar_agregador(produto, protocolo.MODO_CONCORRENTE, criterio, atraso_ms, **conexao)
    t_seq, t_conc = seq.get("tempo_total_ms"), conc.get("tempo_total_ms")
    return {"status": conc["status"], "modo_execucao": protocolo.MODO_COMPARAR,
            "sequencial": seq, "concorrente": conc,
            "speedup": round(t_seq / t_conc, 2) if t_seq and t_conc else None}


def disparar_clientes_simultaneos(n: int, produto: str, modo: str, criterio: str = protocolo.CRITERIO_PRECO,
                                  atraso_ms=None, **conexao) -> dict:
    """
    N clientes TCP (uma thread cada) disparam a mesma pesquisa no mesmo instante (threading.Barrier).
    Devolve o tempo de cada cliente, o motivo da falha de cada um (None = ok) e o tempo do lote.
    """
    barreira = threading.Barrier(n)
    tempos, falhas = [0.0] * n, [None] * n

    def cliente(i):
        try:
            barreira.wait(timeout=10)
        except threading.BrokenBarrierError:
            pass
        inicio = time.perf_counter()
        try:
            resposta = requisitar_agregador(produto, modo, criterio, atraso_ms, **conexao)
            if resposta.get("status") not in (protocolo.STATUS_SUCESSO, protocolo.STATUS_NAO_ENCONTRADO):
                falhas[i] = resposta.get("detalhe", resposta.get("status"))
        except ErroCliente as exc:
            falhas[i] = str(exc)
        tempos[i] = protocolo.ms_desde(inicio)

    threads = [threading.Thread(target=cliente, args=(i,)) for i in range(n)]
    inicio = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return {"tempos_ms": tempos, "falhas": falhas, "tempo_total_ms": protocolo.ms_desde(inicio)}


# ---------------------------------------------------------------------- apresentação no terminal
def _moeda(valor) -> str:
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def exibir_relatorio(resp: dict) -> None:
    status = resp.get("status")
    if status in (protocolo.STATUS_ERRO_REQUISICAO, protocolo.STATUS_ERRO_INTERNO):
        print(f"\n [ERRO] O agregador recusou a pesquisa ({status}): {resp.get('detalhe')}")
        return

    print("\n" + "=" * LARGURA)
    print(f" PESQUISA: '{resp['produto_pesquisado'].upper()}' | MODO: {resp['modo_execucao'].upper()} | "
          f"ORDENAÇÃO: {resp['criterio_ordenacao'].upper()}")
    print(f" Tempo total: {resp['tempo_total_ms']} ms | Lojas que responderam: "
          f"{resp['total_lojas_responderam']}/{resp['total_lojas_consultadas']}")
    print("=" * LARGURA)

    ofertas = resp["ofertas_ordenadas"]
    if ofertas:
        print(f"{'POS':<4}{'LOJA':<15}{'PRODUTO':<38}{'PREÇO':>13}{'FRETE':>11}{'TOTAL':>14}{'NOTA':>6}{'TEMPO':>10}")
        print("-" * LARGURA)
        for pos, of in enumerate(ofertas, 1):
            print(f"{pos:<4}{of['fonte']:<15}{of['produto'][:36]:<38}{_moeda(of['preco']):>13}"
                  f"{_moeda(of['frete']):>11}{_moeda(of['preco_total']):>14}{of['avaliacao']:>6}"
                  f"{of['tempo_loja_ms']:>8}ms")
            print(f"{'':<19}{of['specs']} | garantia {of['garantia_meses']} meses | "
                  f"score C/B {of['score_custo_beneficio']}")
        menor, melhor = resp["menor_preco"], resp["melhor_custo_beneficio"]
        print("-" * LARGURA)
        print(f" [MENOR PREÇO]            {menor['fonte']} -> {menor['produto']} por {_moeda(menor['preco_total'])}")
        print(f" [MELHOR CUSTO-BENEFÍCIO] {melhor['fonte']} -> nota {melhor['avaliacao']}/5, "
              f"{melhor['garantia_meses']} meses de garantia, {_moeda(melhor['preco_total'])} "
              f"(score {melhor['score_custo_beneficio']})")
    else:
        print(" [!] Nenhuma oferta encontrada para o produto informado.")

    for loja in resp["lojas_sem_produto"]:
        print(f" [INFO] {loja}: produto não encontrado no catálogo")
    for falha in resp["ocorrencias_ou_falhas"]:
        print(f" [ALERTA] {falha.get('fonte')}: {falha.get('status')} ({falha.get('detalhe', '-')})")
    print("=" * LARGURA)


def executar(produto: str, modo: str, criterio: str, atraso_ms=None, **conexao) -> None:
    if modo != protocolo.MODO_COMPARAR:
        exibir_relatorio(requisitar_agregador(produto, modo, criterio, atraso_ms, **conexao))
        return
    r = comparar(produto, criterio, atraso_ms, **conexao)
    for modo in protocolo.MODOS_VALIDOS:  # sequencial e depois concorrente
        exibir_relatorio(r[modo])
    if r["speedup"] is not None:
        print(" COMPARATIVO DE DESEMPENHO:")
        print(f"    * Consulta sequencial : {r['sequencial']['tempo_total_ms']} ms")
        print(f"    * Consulta concorrente: {r['concorrente']['tempo_total_ms']} ms")
        print(f"    * Speedup             : {r['speedup']}x")
        print("=" * LARGURA)


def exibir_carga(n: int, produto: str, modo: str, criterio: str, atraso_ms=None, **conexao) -> None:
    """N clientes simultâneos fazem a mesma pesquisa; em 'comparar', um lote em cada modo."""
    modos = protocolo.MODOS_VALIDOS if modo == protocolo.MODO_COMPARAR else (modo,)
    print("\n" + "=" * LARGURA)
    print(f" {n} CLIENTES SIMULTÂNEOS | PESQUISA: '{produto.upper()}' | ORDENAÇÃO: {criterio.upper()}")
    for m in modos:
        r = disparar_clientes_simultaneos(n, produto, m, criterio, atraso_ms, **conexao)
        tempos, lote = r["tempos_ms"], r["tempo_total_ms"]
        falhas = [f for f in r["falhas"] if f is not None]
        print("-" * LARGURA)
        print(f" MODO: {m.upper()} | Tempo do lote: {lote:.2f} ms | Vazão: {n / (lote / 1000.0):.2f} req/s")
        print(f"    * Tempo por cliente: média {statistics.mean(tempos):.2f} ms | "
              f"mín {min(tempos):.2f} ms | máx {max(tempos):.2f} ms")
        print(f"    * Falhas: {len(falhas)}/{n}")
        for motivo in sorted(set(falhas)):
            print(f" [ALERTA] {falhas.count(motivo)} cliente(s): {motivo}")
    print("=" * LARGURA)


def _numero_de_clientes(texto: str) -> int:
    """type= do argparse para --clientes: inteiro de 1 a MAX_CLIENTES_CARGA."""
    try:
        n = int(texto)
    except ValueError:
        raise argparse.ArgumentTypeError("informe um número inteiro") from None
    if not 1 <= n <= MAX_CLIENTES_CARGA:
        raise argparse.ArgumentTypeError(f"use de 1 a {MAX_CLIENTES_CARGA} clientes")
    return n


def exibir_catalogo(**conexao) -> None:
    resp = listar_produtos(**conexao)
    print("Catálogo disponível: " + " | ".join(resp.get("produtos", [])))
    for falha in resp.get("ocorrencias_ou_falhas", []):
        print(f" [ALERTA] {falha.get('fonte')}: {falha.get('status')}")


def _escolher(pergunta: str, opcoes: list, padrao: str) -> str:
    texto = input(f"{pergunta} [{'/'.join(opcoes)}] (Enter = {padrao}): ").strip().lower()
    return texto if texto in opcoes else padrao


def menu_interativo(**conexao) -> None:
    print("\n=== AGREGADOR DE PREÇOS DE ELETRÔNICOS (UNIFESSPA - TEMA 6) ===")
    try:
        exibir_catalogo(**conexao)
    except ErroCliente as exc:
        print(f"[ERRO] {exc}")
        return
    modos = [protocolo.MODO_COMPARAR, *protocolo.MODOS_VALIDOS]
    while True:
        try:
            termo = input("\nProduto (ou 'listar' / 'sair'): ").strip()
            if not termo or termo.lower() == "sair":
                break
            if termo.lower() == "listar":
                exibir_catalogo(**conexao)
                continue
            modo = _escolher("Modo", modos, protocolo.MODO_COMPARAR)
            criterio = _escolher("Ordenar por", list(protocolo.CRITERIOS_VALIDOS), protocolo.CRITERIO_PRECO)
            executar(termo, modo, criterio, **conexao)
        except ErroCliente as exc:
            print(f"[ERRO] {exc}")
        except (EOFError, KeyboardInterrupt):
            print()
            break


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Cliente do agregador de preços de eletrônicos.")
    parser.add_argument("produto", nargs="*", help="termo de pesquisa (vazio = menu interativo)")
    parser.add_argument("--modo", default=protocolo.MODO_COMPARAR,
                        choices=[protocolo.MODO_COMPARAR, *protocolo.MODOS_VALIDOS])
    parser.add_argument("--criterio", default=protocolo.CRITERIO_PRECO, choices=protocolo.CRITERIOS_VALIDOS)
    parser.add_argument("--atraso", type=int, default=None, help="latência artificial por loja em ms")
    parser.add_argument("--clientes", type=_numero_de_clientes, default=None,
                        help=f"dispara N clientes simultâneos (1 a {MAX_CLIENTES_CARGA})")
    parser.add_argument("--listar", action="store_true", help="lista o catálogo e sai")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--porta", type=int, default=PORTA_AGREGADOR)
    args = parser.parse_args(argv)
    if args.clientes and not args.produto:
        parser.error("--clientes exige o produto (ex.: cliente.py rtx 4060 --clientes 20)")
    conexao = {"host": args.host, "porta": args.porta}

    try:
        if args.listar:
            exibir_catalogo(**conexao)
        elif args.produto and args.clientes:
            exibir_carga(args.clientes, " ".join(args.produto), args.modo, args.criterio, args.atraso, **conexao)
        elif args.produto:
            executar(" ".join(args.produto), args.modo, args.criterio, args.atraso, **conexao)
        else:
            menu_interativo(**conexao)
    except ErroCliente as exc:
        print(f"[ERRO] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
