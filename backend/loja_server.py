#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo: loja_server.py (Serviço independente de loja via socket TCP)

Cada loja é um processo independente que escuta em sua própria porta TCP e
responde consultas sobre o seu catálogo (dados/lojas/<NomeDaLoja>.json).

Uso:
    python loja_server.py <NomeDaLoja> <Porta> [LatenciaMS]     (ex.: KabumSim 9001 150)
"""
import argparse
import json
import logging
import os
import sys
import time

import protocolo
from config import DIRETORIO_DADOS, HOST
from servidor_base import ServidorTCPMultithread


def carregar_catalogo(nome_loja: str, diretorio: str = DIRETORIO_DADOS) -> list:
    with open(os.path.join(diretorio, f"{nome_loja}.json"), encoding="utf-8") as arquivo:
        return json.load(arquivo)["produtos"]


class Loja:
    def __init__(self, nome: str, catalogo: list, latencia_ms: int = 150):
        self.nome = nome
        self.catalogo = catalogo
        self.latencia_ms = latencia_ms

    def _erro(self, detalhe: str) -> dict:
        return protocolo.resposta_erro(protocolo.STATUS_ERRO_REQUISICAO, detalhe, fonte=self.nome)

    def tratar(self, requisicao: dict, endereco=None) -> dict:
        operacao = requisicao.get("operacao")
        erro = self._erro

        if operacao == protocolo.OP_PING:
            return {"fonte": self.nome, "status": protocolo.STATUS_SUCESSO, "operacao": "pong"}
        if operacao not in (protocolo.OP_CONSULTAR, protocolo.OP_LISTAR_PRODUTOS):
            return erro(f"operação desconhecida: {operacao!r}")

        # Latência artificial (Experimento 3): 'atraso_ms' da requisição ou, se ausente, a da loja
        atraso_ms = requisicao.get("atraso_ms")
        try:
            atraso_ms = self.latencia_ms if atraso_ms is None else protocolo.validar_atraso_ms(atraso_ms)
        except ValueError as exc:
            return erro(str(exc))
        time.sleep(atraso_ms / 1000.0)

        if operacao == protocolo.OP_LISTAR_PRODUTOS:
            return {"fonte": self.nome, "status": protocolo.STATUS_SUCESSO,
                    "produtos": [{"chave": i["chave"], "produto": i["produto"]} for i in self.catalogo]}

        termo = requisicao.get("produto")
        if not isinstance(termo, str) or not termo.strip():
            return erro("campo 'produto' obrigatório e não vazio")
        termo = termo.strip()

        # Busca sem diferenciar maiúsculas, pela chave ou pelo nome do produto
        encontrados = [i for i in self.catalogo
                       if termo.lower() in i["chave"].lower() or termo.lower() in i["produto"].lower()]
        if not encontrados:
            return {"fonte": self.nome, "produto": termo, "preco": None, "preco_total": None,
                    "status": protocolo.STATUS_NAO_ENCONTRADO}

        # Se houver mais de um item compatível, a loja devolve a sua oferta mais barata
        item = min(encontrados, key=lambda i: i["preco"] + i["frete"])
        return {"fonte": self.nome, "produto": item["produto"], "specs": item["specs"],
                "preco": item["preco"], "frete": item["frete"],
                "preco_total": round(item["preco"] + item["frete"], 2),
                "avaliacao": item["avaliacao"], "garantia_meses": item["garantia_meses"],
                "status": protocolo.STATUS_SUCESSO}


def criar_servidor_loja(nome: str, porta: int, latencia_ms: int = 150, host: str = HOST,
                        catalogo: list = None) -> ServidorTCPMultithread:
    loja = Loja(nome, catalogo if catalogo is not None else carregar_catalogo(nome), latencia_ms)
    return ServidorTCPMultithread(f"loja-{nome}", host, porta, loja.tratar)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Serviço independente de loja (TCP).")
    parser.add_argument("nome", help="nome da loja (deve existir dados/lojas/<nome>.json)")
    parser.add_argument("porta", type=int)
    parser.add_argument("latencia", type=int, nargs="?", default=150, help="latência artificial em ms (padrão 150)")
    parser.add_argument("--host", default=HOST)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    try:
        servidor = criar_servidor_loja(args.nome, args.porta, args.latencia, args.host)
        servidor.iniciar()
    except FileNotFoundError:
        print(f"[ERRO] Catálogo não encontrado para a loja '{args.nome}'.", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"[ERRO] Não foi possível abrir a porta {args.porta}: {exc}", file=sys.stderr)
        return 1

    print(f"[*] Loja '{args.nome}' ativa em {args.host}:{servidor.porta} (latência base: {args.latencia} ms)",
          flush=True)
    try:
        servidor.servir_para_sempre()
    except KeyboardInterrupt:
        print(f"\n[!] Encerrando loja {args.nome}...", flush=True)
    finally:
        servidor.encerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
