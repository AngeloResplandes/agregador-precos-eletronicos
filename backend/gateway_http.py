#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo: gateway_http.py (Ponte HTTP/JSON para a interface web)

O navegador não abre sockets TCP, então a interface web (frontend/) fala HTTP com
este gateway, que é apenas mais um CLIENTE TCP do agregador: cada pesquisa vira uma
requisição do protocolo de aplicação, enviada pelas mesmas funções do cliente.py.
A API HTTP está descrita no Apêndice A de docs/03_protocolo.md.

Uso:
    python gateway_http.py                 # sobe 4 lojas + agregador e o gateway (porta 8080)
    python gateway_http.py --externo       # usa lojas/agregador já em execução
"""
import argparse
import csv
import json
import logging
import mimetypes
import os
import re
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

import protocolo
from cliente import ErroCliente, comparar, disparar_clientes_simultaneos, listar_produtos, requisitar_agregador
from config import (ARQUIVO_LOG_PESQUISAS, DIRETORIO_FRONTEND_DIST, DIRETORIO_RESULTADOS, HOST, LIMITE_MAXIMO_LOG,
                    LIMITE_PADRAO_LOG, LOJAS, MAX_CLIENTES_CARGA, PORTA_AGREGADOR, PORTA_GATEWAY,
                    TAMANHO_MAXIMO_CORPO_HTTP, TIMEOUT_CLIENTE)
from experimentos import percentil, resumo
from iniciar_servicos import Ambiente, ler_latencias, porta_em_uso, tratar_sinais_de_encerramento

NOME_LOG = os.path.basename(ARQUIVO_LOG_PESQUISAS)
ROTA_CONTROLE_LOJA = re.compile(r"^/api/lojas/([^/]+)/(derrubar|subir)$")
ROTA_RESULTADO = "/api/resultados/"


class ErroGateway(Exception):
    """Erro já traduzido para HTTP: código, status do protocolo e detalhe amigável."""

    def __init__(self, codigo: int, status: str, detalhe: str):
        super().__init__(detalhe)
        self.codigo, self.status, self.detalhe = codigo, status, detalhe


def erro_requisicao(detalhe: str, codigo: int = HTTPStatus.BAD_REQUEST) -> ErroGateway:
    return ErroGateway(codigo, protocolo.STATUS_ERRO_REQUISICAO, detalhe)


class Gateway:
    """
    Lógica do gateway, independente do HTTP: cada método devolve o corpo JSON (HTTP 200)
    ou levanta ErroGateway. Com um `ambiente` (iniciar_servicos.Ambiente) o gateway também
    derruba e sobe lojas, para demonstrar a tolerância a falhas pela interface.
    """

    def __init__(self, lojas=None, host_agregador: str = HOST, porta_agregador: int = PORTA_AGREGADOR,
                 ambiente: Ambiente = None, diretorio_resultados: str = DIRETORIO_RESULTADOS,
                 diretorio_estatico=DIRETORIO_FRONTEND_DIST, timeout: float = TIMEOUT_CLIENTE):
        self.ambiente = ambiente
        self.lojas = list(lojas if lojas is not None else ambiente.config_lojas if ambiente else LOJAS)
        self.latencias = ambiente.latencias if ambiente else [loja.get("latencia_ms") for loja in self.lojas]
        self.conexao = {"host": host_agregador, "porta": porta_agregador, "timeout": timeout}
        self.diretorio_resultados = diretorio_resultados
        self.diretorio_estatico = diretorio_estatico
        self._lock_processos = threading.Lock()
        self.log = logging.getLogger("gateway")

    # ------------------------------------------------------------------ status e controle das lojas
    def _status_loja(self, i: int) -> dict:
        loja = self.lojas[i]
        return {"nome": loja["nome"], "host": loja["host"], "porta": loja["porta"],
                "latencia_ms": self.latencias[i], "online": protocolo.ping(loja["host"], loja["porta"])}

    def saude(self) -> dict:
        return {"status": protocolo.STATUS_SUCESSO,
                "agregador_online": protocolo.ping(self.conexao["host"], self.conexao["porta"]),
                "agregador": f"{self.conexao['host']}:{self.conexao['porta']}",
                "gerencia_processos": self.ambiente is not None}

    def status_lojas(self) -> dict:
        """Pinga todas as lojas em paralelo (uma thread por loja), na ordem do cadastro."""
        status = [None] * len(self.lojas)

        def tarefa(i):
            status[i] = self._status_loja(i)

        threads = [threading.Thread(target=tarefa, args=(i,)) for i in range(len(self.lojas))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return {"status": protocolo.STATUS_SUCESSO, "lojas": status, "gerencia_processos": self.ambiente is not None}

    def controlar_loja(self, nome: str, acao: str) -> dict:
        i = next((i for i, loja in enumerate(self.lojas) if loja["nome"] == nome), None)
        if i is None:
            raise erro_requisicao(f"loja desconhecida: {nome!r}", HTTPStatus.NOT_FOUND)
        if self.ambiente is None:
            raise erro_requisicao("o gateway foi iniciado com --externo e não controla os processos das lojas",
                                  HTTPStatus.CONFLICT)
        with self._lock_processos:
            online = self._status_loja(i)["online"]
            if (acao == "derrubar") != online:
                raise erro_requisicao(f"{nome} já está {'no ar' if online else 'fora do ar'}", HTTPStatus.CONFLICT)
            if acao == "derrubar":
                self.ambiente.derrubar_loja(nome)
            else:
                try:
                    self.ambiente.subir_loja(self.lojas[i], self.latencias[i])
                except RuntimeError as exc:
                    raise ErroGateway(HTTPStatus.INTERNAL_SERVER_ERROR, protocolo.STATUS_ERRO_INTERNO,
                                      f"não foi possível subir {nome}: {exc}") from None
            status = self._status_loja(i)
        if acao == "derrubar" and status["online"]:
            raise erro_requisicao(f"{nome} não é um processo iniciado por este gateway", HTTPStatus.CONFLICT)
        self.log.info("loja %s: %s (online=%s)", nome, acao, status["online"])
        return {"status": protocolo.STATUS_SUCESSO, **status}

    # ------------------------------------------------------------------ pesquisa (via cliente TCP)
    def _chamar(self, funcao, *args) -> dict:
        try:
            return funcao(*args, **self.conexao)
        except ErroCliente as exc:
            raise ErroGateway(HTTPStatus.BAD_GATEWAY, protocolo.STATUS_ERRO_COMUNICACAO, str(exc)) from None

    @staticmethod
    def _conferir(resposta: dict) -> dict:
        """'sucesso' e 'nao_encontrado' seguem para a interface; o resto vira erro HTTP."""
        status = resposta.get("status")
        if status == protocolo.STATUS_ERRO_REQUISICAO:
            raise erro_requisicao(resposta.get("detalhe", "requisição recusada pelo agregador"))
        if status not in (protocolo.STATUS_SUCESSO, protocolo.STATUS_NAO_ENCONTRADO):
            raise ErroGateway(HTTPStatus.BAD_GATEWAY, status or protocolo.STATUS_ERRO_COMUNICACAO,
                              resposta.get("detalhe", "resposta inesperada do agregador"))
        return resposta

    @staticmethod
    def _validar(corpo: dict, modos) -> tuple:
        try:
            return protocolo.validar_pesquisa(corpo, modos)
        except ValueError as exc:
            raise erro_requisicao(str(exc)) from None

    def produtos(self) -> dict:
        return self._conferir(self._chamar(listar_produtos))

    def consultar(self, corpo: dict) -> dict:
        produto, modo, criterio, atraso_ms = self._validar(corpo, (*protocolo.MODOS_VALIDOS, protocolo.MODO_COMPARAR))
        if modo != protocolo.MODO_COMPARAR:
            return self._conferir(self._chamar(requisitar_agregador, produto, modo, criterio, atraso_ms))
        resposta = self._chamar(comparar, produto, criterio, atraso_ms)
        self._conferir(resposta["sequencial"])
        self._conferir(resposta["concorrente"])
        return resposta

    def carga(self, corpo: dict) -> dict:
        """N clientes TCP disparam a mesma pesquisa ao mesmo tempo (cliente.disparar_clientes_simultaneos)."""
        n = corpo.get("clientes")
        if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= MAX_CLIENTES_CARGA:
            raise erro_requisicao(f"'clientes' deve ser inteiro entre 1 e {MAX_CLIENTES_CARGA}")
        produto, modo, criterio, atraso_ms = self._validar(corpo, protocolo.MODOS_VALIDOS)
        lote = disparar_clientes_simultaneos(n, produto, modo, criterio, atraso_ms, **self.conexao)
        tempos, total_ms = lote["tempos_ms"], lote["tempo_total_ms"]
        falhas = [{"cliente": i + 1, "detalhe": d} for i, d in enumerate(lote["falhas"]) if d is not None]
        estatisticas = resumo(tempos)
        del estatisticas["n"]
        return {"status": protocolo.STATUS_SUCESSO, "clientes": n, "produto": produto, "modo": modo,
                "atraso_ms": atraso_ms, **estatisticas, "p95_ms": round(percentil(tempos, 95), 2),
                "tempo_total_ms": total_ms, "vazao_req_s": round(n / (total_ms / 1000.0), 2) if total_ms > 0 else None,
                "falhas": len(falhas), "detalhes_falhas": falhas, "tempos_ms": tempos}

    # ------------------------------------------------------------------ resultados, log e interface compilada
    def _arquivos_resultados(self) -> list:
        try:
            return sorted(os.listdir(self.diretorio_resultados))
        except OSError:
            return []

    def _ler_csv(self, nome: str) -> tuple:
        with open(os.path.join(self.diretorio_resultados, nome), newline="", encoding="utf-8") as arquivo:
            leitor = csv.DictReader(arquivo)
            return list(leitor.fieldnames or []), list(leitor)

    def experimentos(self) -> dict:
        arquivos = self._arquivos_resultados()
        tabelas = []
        for nome in arquivos:
            if nome.startswith("exp") and nome.endswith(".csv"):
                colunas, linhas = self._ler_csv(nome)
                tabelas.append({"arquivo": nome, "colunas": colunas, "linhas": linhas})
        graficos = [nome for nome in arquivos if nome.startswith("g") and nome.endswith(".png")]
        return {"status": protocolo.STATUS_SUCESSO, "tabelas": tabelas, "graficos": graficos}

    def caminho_grafico(self, nome: str) -> str:
        """Só serve PNGs listados no diretório de resultados (nada de '../')."""
        if not nome.endswith(".png") or nome not in self._arquivos_resultados():
            raise erro_requisicao(f"gráfico não encontrado: {nome!r}", HTTPStatus.NOT_FOUND)
        return os.path.join(self.diretorio_resultados, nome)

    def log_pesquisas(self, limite_texto) -> dict:
        limite = LIMITE_PADRAO_LOG if limite_texto is None else limite_texto
        if not str(limite).isdigit() or not 1 <= int(limite) <= LIMITE_MAXIMO_LOG:
            raise erro_requisicao(f"'limite' deve ser inteiro entre 1 e {LIMITE_MAXIMO_LOG}")
        colunas, linhas = self._ler_csv(NOME_LOG) if NOME_LOG in self._arquivos_resultados() else ([], [])
        return {"status": protocolo.STATUS_SUCESSO, "colunas": colunas,
                "linhas": linhas[::-1][:int(limite)], "total": len(linhas)}

    def caminho_estatico(self, caminho_url: str) -> str:
        """Arquivo do build da interface (frontend/dist); rotas desconhecidas caem no index.html."""
        if self.diretorio_estatico:
            raiz = os.path.realpath(self.diretorio_estatico)
            alvo = os.path.realpath(os.path.join(raiz, unquote(caminho_url).lstrip("/")))
            if alvo.startswith(raiz + os.sep) and os.path.isfile(alvo):
                return alvo
            if os.path.isfile(os.path.join(raiz, "index.html")):
                return os.path.join(raiz, "index.html")
        raise erro_requisicao("interface não compilada: rode 'npm run build' em frontend/ ou use 'npm run dev'",
                              HTTPStatus.NOT_FOUND)


def criar_servidor_gateway(gateway: Gateway, host: str = HOST, porta: int = PORTA_GATEWAY) -> ThreadingHTTPServer:
    """Servidor HTTP com uma thread por requisição (ThreadingHTTPServer)."""

    class Manipulador(BaseHTTPRequestHandler):
        server_version = "GatewayAgregador/1.0"

        def log_message(self, formato, *args):
            gateway.log.info("%s %s", self.address_string(), formato % args)

        def _enviar(self, conteudo: bytes, tipo: str, codigo: int = HTTPStatus.OK):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(conteudo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(conteudo)

        def _json(self, corpo: dict, codigo: int = HTTPStatus.OK):
            self._enviar(json.dumps(corpo, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8",
                         codigo)

        def _arquivo(self, caminho: str):
            with open(caminho, "rb") as arquivo:
                self._enviar(arquivo.read(), mimetypes.guess_type(caminho)[0] or "application/octet-stream")

        def _corpo(self) -> dict:
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                raise erro_requisicao("Content-Length inválido") from None
            if tamanho > TAMANHO_MAXIMO_CORPO_HTTP:
                raise erro_requisicao(f"corpo maior que {TAMANHO_MAXIMO_CORPO_HTTP} bytes",
                                      HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            try:
                corpo = json.loads(self.rfile.read(tamanho).decode("utf-8") if tamanho else "{}")
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise erro_requisicao("corpo da requisição não é um JSON válido") from None
            if not isinstance(corpo, dict):
                raise erro_requisicao("o corpo da requisição deve ser um objeto JSON")
            return corpo

        def _rotear(self):
            url = urlsplit(self.path)
            caminho = url.path
            if self.command == "POST":
                controle = ROTA_CONTROLE_LOJA.match(caminho)
                acoes = {"/api/consultar": gateway.consultar, "/api/carga": gateway.carga}
                if controle:
                    return self._json(gateway.controlar_loja(unquote(controle.group(1)), controle.group(2)))
                if caminho in acoes:
                    return self._json(acoes[caminho](self._corpo()))
            else:
                consultas = {"/api/saude": gateway.saude, "/api/lojas": gateway.status_lojas,
                             "/api/produtos": gateway.produtos, "/api/experimentos": gateway.experimentos}
                if caminho in consultas:
                    return self._json(consultas[caminho]())
                if caminho == "/api/log":
                    return self._json(gateway.log_pesquisas(parse_qs(url.query).get("limite", [None])[0]))
                if caminho.startswith(ROTA_RESULTADO):
                    return self._arquivo(gateway.caminho_grafico(unquote(caminho[len(ROTA_RESULTADO):])))
                if not caminho.startswith("/api/"):
                    return self._arquivo(gateway.caminho_estatico(caminho))
            raise erro_requisicao(f"rota desconhecida: {caminho}", HTTPStatus.NOT_FOUND)

        def _executar(self):
            """Executa a rota; erros viram JSON {status, detalhe}, nunca traceback."""
            try:
                self._rotear()
            except ErroGateway as exc:
                self._json(protocolo.resposta_erro(exc.status, exc.detalhe), exc.codigo)
            except Exception:  # noqa: BLE001 - defeito inesperado: registra e responde erro_interno
                gateway.log.exception("erro inesperado em %s %s", self.command, self.path)
                self._json(protocolo.resposta_erro(protocolo.STATUS_ERRO_INTERNO, "erro inesperado no gateway"),
                           HTTPStatus.INTERNAL_SERVER_ERROR)

        do_GET = do_HEAD = do_POST = _executar  # nomes exigidos por BaseHTTPRequestHandler

    servidor = ThreadingHTTPServer((host, porta), Manipulador)
    servidor.daemon_threads = True
    return servidor


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Gateway HTTP da interface web do agregador.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--porta", type=int, default=PORTA_GATEWAY)
    parser.add_argument("--externo", action="store_true",
                        help="não sobe lojas/agregador; usa os que já estão rodando (sem derrubar/subir lojas)")
    parser.add_argument("--latencias", type=ler_latencias, help="latências das lojas em ms (ex.: 100,200,300,400)")
    parser.add_argument("--timeout-loja", type=float, default=None)
    parser.add_argument("--host-agregador", default=HOST, help="só com --externo")
    parser.add_argument("--porta-agregador", type=int, default=PORTA_AGREGADOR, help="só com --externo")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    if porta_em_uso(args.host, args.porta):
        print(f"[ERRO] a porta {args.porta} já está em uso (há outro gateway aberto?)", file=sys.stderr)
        return 1

    tratar_sinais_de_encerramento()
    ambiente = servidor = None
    try:
        if args.externo:
            gateway = Gateway(host_agregador=args.host_agregador, porta_agregador=args.porta_agregador)
        else:
            ambiente = Ambiente(args.latencias, args.timeout_loja).subir()
            gateway = Gateway(ambiente=ambiente)
        servidor = criar_servidor_gateway(gateway, args.host, args.porta)
        modo = "serviços externos" if args.externo else "lojas e agregador iniciados por este processo"
        print(f"\n[OK] Gateway HTTP em http://{args.host}:{args.porta} ({modo})")
        if os.path.isdir(DIRETORIO_FRONTEND_DIST):
            print(f"     Interface compilada: http://{args.host}:{args.porta}/")
        else:
            print("     Interface: em frontend/, rode 'npm run dev' e abra http://localhost:5173")
        print("     Ctrl+C para encerrar.\n", flush=True)
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Encerrando gateway...", flush=True)
    except (RuntimeError, OSError) as exc:
        print(f"[ERRO] {exc}", file=sys.stderr)
        if not args.externo:
            print("       Se o ambiente já estiver rodando (iniciar_servicos.py), use --externo.", file=sys.stderr)
        return 1
    finally:
        if servidor is not None:
            servidor.server_close()
        if ambiente is not None:
            ambiente.encerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
