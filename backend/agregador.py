#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo: agregador.py (Agregador concorrente via sockets TCP e threads)

Responsabilidades:
  * receber pesquisas dos clientes (uma thread por cliente, via ServidorTCPMultithread);
  * consultar as lojas de forma SEQUENCIAL ou CONCORRENTE (uma thread por loja);
  * consolidar, ordenar e identificar a melhor oferta;
  * registrar o tempo de cada pesquisa em resultados/log_pesquisas.csv.

Uso:
    python agregador.py [--porta 8000] [--timeout-loja 2.5] [--sem-log]
"""
import argparse
import csv
import logging
import os
import sys
import threading
import time
from datetime import datetime

import protocolo
from config import ARQUIVO_LOG_PESQUISAS, HOST, LOJAS, PORTA_AGREGADOR, TIMEOUT_LOJA
from servidor_base import ServidorTCPMultithread

CAMPOS_LOG = ["timestamp", "cliente", "operacao", "produto", "modo", "criterio", "atraso_ms",
              "tempo_total_ms", "tempos_lojas_ms", "lojas_consultadas", "lojas_responderam",
              "lojas_falharam", "clientes_simultaneos", "status"]

# Campos obrigatórios de uma oferta devolvida por uma loja com status "sucesso"
CAMPOS_TEXTO_OFERTA = ("produto", "specs")
CAMPOS_NUMERICOS_OFERTA = ("preco", "frete", "preco_total", "avaliacao", "garantia_meses")
RESPONDEU = (protocolo.STATUS_SUCESSO, protocolo.STATUS_NAO_ENCONTRADO)  # a loja respondeu (com ou sem o produto)


def calcular_score_custo_beneficio(oferta: dict) -> float:
    """Combina avaliação, garantia e preço total (maior = melhor)."""
    preco_total = oferta.get("preco_total") or 0
    if preco_total <= 0:
        return 0.0
    avaliacao = float(oferta.get("avaliacao", 4.0))
    garantia = int(oferta.get("garantia_meses", 12))
    return round(avaliacao ** 2 * (1.0 + 0.01 * garantia) / preco_total * 1000.0, 4)


def validar_resposta_loja(operacao: str, resposta: dict) -> None:
    """
    Confere se uma resposta de 'sucesso' da loja tem os campos que o agregador usa.
    Uma loja com defeito não pode derrubar a pesquisa: a resposta vira falha só daquela loja.
    """
    if resposta.get("status") != protocolo.STATUS_SUCESSO:
        return
    if operacao == protocolo.OP_CONSULTAR:
        for campo in CAMPOS_TEXTO_OFERTA:
            if not isinstance(resposta.get(campo), str):
                raise protocolo.MensagemInvalida(f"resposta inválida da loja: campo de texto '{campo}' ausente")
        for campo in CAMPOS_NUMERICOS_OFERTA:
            valor = resposta.get(campo)
            if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                raise protocolo.MensagemInvalida(
                    f"resposta inválida da loja: campo numérico '{campo}' ausente ou de tipo errado")
    elif operacao == protocolo.OP_LISTAR_PRODUTOS:
        produtos = resposta.get("produtos")
        if not isinstance(produtos, list) or not all(
                isinstance(p, dict) and isinstance(p.get("chave"), str) for p in produtos):
            raise protocolo.MensagemInvalida("resposta inválida da loja: lista 'produtos' malformada")


class RegistroPesquisas:
    """Registro persistente (CSV) do tempo de execução das pesquisas. Thread-safe."""

    def __init__(self, caminho):
        self.caminho = caminho
        self._lock = threading.Lock()
        if caminho:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)

    def registrar(self, linha: dict) -> None:
        if not self.caminho:
            return
        with self._lock:
            novo = not os.path.exists(self.caminho) or os.path.getsize(self.caminho) == 0
            with open(self.caminho, "a", newline="", encoding="utf-8") as arquivo:
                escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_LOG)
                if novo:
                    escritor.writeheader()
                escritor.writerow({c: linha.get(c, "") for c in CAMPOS_LOG})


class Agregador:
    def __init__(self, lojas=None, timeout_loja: float = TIMEOUT_LOJA, arquivo_log=ARQUIVO_LOG_PESQUISAS):
        self.lojas = lojas if lojas is not None else LOJAS
        self.timeout_loja = timeout_loja
        self.registro = RegistroPesquisas(arquivo_log)
        self.log = logging.getLogger("agregador")
        self._lock = threading.Lock()
        self.clientes_simultaneos = 0

    # ------------------------------------------------------------------ comunicação com as lojas
    def consultar_loja(self, loja: dict, mensagem: dict) -> dict:
        """Envia uma requisição a UMA loja e devolve a resposta (ou a falha, já classificada)."""
        inicio = time.perf_counter()
        try:
            resposta = protocolo.requisitar(loja["host"], loja["porta"], mensagem, self.timeout_loja)
            resposta.setdefault("fonte", loja["nome"])
            validar_resposta_loja(mensagem.get("operacao"), resposta)
        except Exception as exc:  # recusa, queda, timeout, resposta inválida...
            status = protocolo.STATUS_TIMEOUT if isinstance(exc, TimeoutError) else protocolo.STATUS_ERRO_COMUNICACAO
            resposta = {"fonte": loja["nome"], "produto": mensagem.get("produto"), "preco": None,
                        "preco_total": None, "status": status, "detalhe": f"{type(exc).__name__}: {exc}"}
        resposta["tempo_loja_ms"] = protocolo.ms_desde(inicio)
        return resposta

    def consultar_todas(self, mensagem: dict, modo: str) -> list:
        """Consulta todas as lojas no modo indicado; preserva a ordem do cadastro."""
        resultados = [None] * len(self.lojas)

        def tarefa(indice, loja):  # cada thread grava só no seu índice: dispensa lock
            resultados[indice] = self.consultar_loja(loja, mensagem)

        if modo == protocolo.MODO_SEQUENCIAL:
            for i, loja in enumerate(self.lojas):
                tarefa(i, loja)
        else:
            threads = [threading.Thread(target=tarefa, args=(i, loja)) for i, loja in enumerate(self.lojas)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        return resultados

    # ------------------------------------------------------------------ operações
    def executar_busca(self, produto: str, modo: str = protocolo.MODO_CONCORRENTE,
                       criterio: str = protocolo.CRITERIO_PRECO, atraso_ms=None) -> dict:
        mensagem = {"operacao": protocolo.OP_CONSULTAR, "produto": produto}
        if atraso_ms is not None:
            mensagem["atraso_ms"] = atraso_ms

        inicio = time.perf_counter()
        resultados = self.consultar_todas(mensagem, modo)
        tempo_total_ms = protocolo.ms_desde(inicio)

        ofertas = [r for r in resultados if r["status"] == protocolo.STATUS_SUCESSO]
        nao_encontrado = [r for r in resultados if r["status"] == protocolo.STATUS_NAO_ENCONTRADO]
        falhas = [r for r in resultados if r["status"] not in RESPONDEU]
        for oferta in ofertas:
            oferta["score_custo_beneficio"] = calcular_score_custo_beneficio(oferta)
        if criterio == protocolo.CRITERIO_CUSTO_BENEFICIO:
            ofertas.sort(key=lambda o: o["score_custo_beneficio"], reverse=True)
        else:
            ofertas.sort(key=lambda o: o["preco_total"])

        return {
            "status": protocolo.STATUS_SUCESSO if ofertas else protocolo.STATUS_NAO_ENCONTRADO,
            "produto_pesquisado": produto,
            "modo_execucao": modo,
            "criterio_ordenacao": criterio,
            "tempo_total_ms": tempo_total_ms,
            "tempos_lojas_ms": {r["fonte"]: r["tempo_loja_ms"] for r in resultados},
            "total_lojas_consultadas": len(self.lojas),
            "total_lojas_responderam": len(ofertas) + len(nao_encontrado),
            "total_ofertas": len(ofertas),
            "menor_preco": min(ofertas, key=lambda o: o["preco_total"]) if ofertas else None,
            "melhor_custo_beneficio": max(ofertas, key=lambda o: o["score_custo_beneficio"]) if ofertas else None,
            "ofertas_ordenadas": ofertas,
            "lojas_sem_produto": [r["fonte"] for r in nao_encontrado],
            "ocorrencias_ou_falhas": falhas,
        }

    def listar_produtos(self) -> dict:
        resultados = self.consultar_todas({"operacao": protocolo.OP_LISTAR_PRODUTOS, "atraso_ms": 0},
                                          protocolo.MODO_CONCORRENTE)
        ok = [r for r in resultados if r["status"] == protocolo.STATUS_SUCESSO]
        return {"status": protocolo.STATUS_SUCESSO,
                "produtos": sorted({p["chave"] for r in ok for p in r["produtos"]}),
                "ocorrencias_ou_falhas": [r for r in resultados if r["status"] != protocolo.STATUS_SUCESSO]}

    # ------------------------------------------------------------------ atendimento ao cliente
    def responder(self, req: dict) -> dict:
        """Executa a operação pedida pelo cliente (ou devolve o erro de requisição)."""
        operacao = req.get("operacao")
        if operacao == protocolo.OP_LISTAR_PRODUTOS:
            return self.listar_produtos()
        if operacao != protocolo.OP_CONSULTAR:
            return protocolo.resposta_erro(protocolo.STATUS_ERRO_REQUISICAO, f"operação desconhecida: {operacao!r}")
        try:
            pesquisa = protocolo.validar_pesquisa(req)
        except ValueError as exc:
            return protocolo.resposta_erro(protocolo.STATUS_ERRO_REQUISICAO, str(exc))
        return self.executar_busca(*pesquisa)

    def tratar(self, req: dict, endereco=None) -> dict:
        """Chamado pelo servidor TCP, uma thread por cliente: responde e registra a pesquisa no CSV."""
        if req.get("operacao") == protocolo.OP_PING:  # verificação de saúde: não entra no registro
            return {"status": protocolo.STATUS_SUCESSO, "operacao": "pong"}

        with self._lock:
            self.clientes_simultaneos += 1
            simultaneos = self.clientes_simultaneos
        try:
            resposta = self.responder(req)
        finally:
            with self._lock:
                self.clientes_simultaneos -= 1

        cliente = f"{endereco[0]}:{endereco[1]}" if endereco else "local"
        linha = {"timestamp": datetime.now().isoformat(timespec="milliseconds"), "cliente": cliente,
                 "operacao": req.get("operacao"), "clientes_simultaneos": simultaneos,
                 "status": resposta.get("status")}
        if "tempo_total_ms" in resposta:  # pesquisa executada
            linha.update({
                "produto": resposta["produto_pesquisado"], "modo": resposta["modo_execucao"],
                "criterio": resposta["criterio_ordenacao"], "atraso_ms": req.get("atraso_ms", ""),
                "tempo_total_ms": resposta["tempo_total_ms"],
                "tempos_lojas_ms": ";".join(f"{loja}={ms}" for loja, ms in resposta["tempos_lojas_ms"].items()),
                "lojas_consultadas": resposta["total_lojas_consultadas"],
                "lojas_responderam": resposta["total_lojas_responderam"],
                "lojas_falharam": len(resposta["ocorrencias_ou_falhas"]),
            })
            self.log.info("%s consultou '%s' (%s) em %s ms -> %s", cliente, linha["produto"], linha["modo"],
                          linha["tempo_total_ms"], linha["status"])
        self.registro.registrar(linha)
        return resposta


def criar_servidor_agregador(agregador: Agregador = None, host: str = HOST,
                             porta: int = PORTA_AGREGADOR) -> ServidorTCPMultithread:
    return ServidorTCPMultithread("agregador", host, porta, (agregador or Agregador()).tratar, backlog=256)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Agregador concorrente de preços de eletrônicos.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--porta", type=int, default=PORTA_AGREGADOR)
    parser.add_argument("--timeout-loja", type=float, default=TIMEOUT_LOJA)
    parser.add_argument("--sem-log", action="store_true", help="não grava resultados/log_pesquisas.csv")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    agregador = Agregador(timeout_loja=args.timeout_loja, arquivo_log=None if args.sem_log else ARQUIVO_LOG_PESQUISAS)
    servidor = criar_servidor_agregador(agregador, args.host, args.porta)
    try:
        servidor.iniciar()
    except OSError as exc:
        print(f"[ERRO] Não foi possível abrir a porta {args.porta}: {exc}", file=sys.stderr)
        return 1

    print(f"[*] AGREGADOR DE ELETRÔNICOS ativo em {args.host}:{servidor.porta} "
          f"({len(agregador.lojas)} lojas, timeout {args.timeout_loja}s)", flush=True)
    try:
        servidor.servir_para_sempre()
    except KeyboardInterrupt:
        print("\n[!] Encerrando agregador...", flush=True)
    finally:
        servidor.encerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
