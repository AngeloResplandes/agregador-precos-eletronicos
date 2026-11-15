#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo: iniciar_servicos.py (Sobe as 4 lojas e o agregador como processos independentes)

Uso (demonstração):
    python iniciar_servicos.py [--latencias 100,200,300,400]
Depois, em outro terminal: python cliente.py   (Ctrl+C encerra todos os processos)

Com o ambiente no ar, este terminal aceita comandos (Exp. 5 - indisponibilidade de serviço):
    derrubar <loja>   encerra o processo da loja (ex.: derrubar MagaluTechSim)
    subir <loja>      sobe a loja de novo, com a latência original
    status            mostra quais lojas estão no ar
"""
import argparse
import os
import signal
import socket
import subprocess
import sys
import time

import protocolo
from config import DIRETORIO_BASE, HOST, LOJAS, PORTA_AGREGADOR


def porta_em_uso(host: str, porta: int) -> bool:
    """True se já existe algum processo aceitando conexões nessa porta."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, porta)) == 0


def ler_latencias(texto: str) -> list:
    """Converte '100,200,300,400' em uma latência por loja (usado como type= do argparse)."""
    try:
        latencias = [int(x) for x in texto.split(",")]
    except ValueError:
        raise argparse.ArgumentTypeError("latências devem ser inteiros separados por vírgula") from None
    if len(latencias) != len(LOJAS):
        raise argparse.ArgumentTypeError(f"informe {len(LOJAS)} latências")
    return latencias


def tratar_sinais_de_encerramento() -> None:
    """SIGTERM (kill) e SIGHUP (terminal fechado) viram Ctrl+C, para o 'finally' encerrar os processos filhos."""
    def interromper(signum, frame):
        raise KeyboardInterrupt

    for nome in ("SIGTERM", "SIGHUP"):
        if hasattr(signal, nome):
            signal.signal(getattr(signal, nome), interromper)


def aguardar_servico(host: str, porta: int, prazo_s: float = 10.0, processo=None) -> bool:
    """Envia 'ping' até o serviço responder, o prazo acabar ou o processo morrer."""
    limite = time.monotonic() + prazo_s
    while time.monotonic() < limite and (processo is None or processo.poll() is None):
        if protocolo.ping(host, porta):
            return True
        time.sleep(0.1)
    return False


class Ambiente:
    """Conjunto de processos (lojas + agregador) usado na demo, no gateway e nos experimentos."""

    def __init__(self, latencias=None, timeout_loja=None, saida=None, sem_log=False, lojas=None):
        self.config_lojas = lojas if lojas is not None else LOJAS
        self.latencias = latencias or [loja["latencia_ms"] for loja in self.config_lojas]
        self.timeout_loja = timeout_loja
        self.saida = saida  # None = herda o terminal; subprocess.DEVNULL = silencioso
        self.sem_log = sem_log
        self.lojas = {}  # nome -> Popen
        self._processos = []  # todo processo criado, para um Ctrl+C durante a subida também encerrá-lo

    def _iniciar(self, nome: str, host: str, porta: int, script: str, *args):
        """Sobe um serviço e só o considera pronto se ESTE processo responder na porta."""
        if porta_em_uso(host, porta):
            raise RuntimeError(f"a porta {porta} já está em uso; não é possível subir {nome} "
                               "(há um iniciar_servicos.py ou outro serviço ainda aberto?)")
        processo = subprocess.Popen([sys.executable, os.path.join(DIRETORIO_BASE, script), *map(str, args)],
                                    stdout=self.saida, stderr=self.saida, cwd=DIRETORIO_BASE)
        self._processos.append(processo)
        if not aguardar_servico(host, porta, processo=processo):
            if processo.poll() is not None:
                raise RuntimeError(f"{nome} encerrou ao iniciar (código {processo.returncode})")
            raise RuntimeError(f"{nome} não respondeu na porta {porta}")
        return processo

    def subir_loja(self, loja: dict, latencia_ms: int) -> None:
        self.lojas[loja["nome"]] = self._iniciar(f"a loja {loja['nome']}", loja["host"], loja["porta"],
                                                 "loja_server.py", loja["nome"], loja["porta"], latencia_ms)

    def subir(self, com_agregador: bool = True) -> "Ambiente":
        try:
            for loja, latencia in zip(self.config_lojas, self.latencias):
                self.subir_loja(loja, latencia)
            if com_agregador:
                args = [] if self.timeout_loja is None else ["--timeout-loja", self.timeout_loja]
                if self.sem_log:
                    args.append("--sem-log")
                self._iniciar("o agregador", HOST, PORTA_AGREGADOR, "agregador.py", *args)
        except BaseException:
            self.encerrar()  # não deixa processos já iniciados ocupando as portas
            raise
        return self

    def loja_ativa(self, nome: str) -> bool:
        processo = self.lojas.get(nome)
        return processo is not None and processo.poll() is None

    def derrubar_loja(self, nome: str) -> None:
        processo = self.lojas.get(nome)
        if processo and processo.poll() is None:
            processo.terminate()
            processo.wait(timeout=5)

    def encerrar(self) -> None:
        for p in self._processos:
            if p.poll() is None:
                p.terminate()
        for p in self._processos:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()

    def __enter__(self):
        return self.subir()

    def __exit__(self, *exc):
        self.encerrar()


AJUDA_CONSOLE = ("Comandos: derrubar <loja> | subir <loja> | status | ajuda   (Ctrl+C encerra tudo)")


def executar_comando(ambiente: Ambiente, linha: str) -> str:
    """Interpreta um comando do console do iniciar_servicos.py e devolve a mensagem para o terminal."""
    partes = linha.split()
    if not partes:
        return ""
    comando, argumentos = partes[0].lower(), partes[1:]
    if comando == "ajuda":
        return AJUDA_CONSOLE
    if comando == "status":
        return "\n".join(f"  {loja['nome']}: {'no ar' if ambiente.loja_ativa(loja['nome']) else 'fora do ar'} "
                         f"(porta {loja['porta']})" for loja in ambiente.config_lojas)
    if comando not in ("derrubar", "subir"):
        return f"[!] comando desconhecido: '{comando}'. {AJUDA_CONSOLE}"
    if len(argumentos) != 1:
        return f"[!] uso: {comando} <loja>"
    nomes = {loja["nome"].lower(): i for i, loja in enumerate(ambiente.config_lojas)}
    indice = nomes.get(argumentos[0].lower())
    if indice is None:
        return f"[!] loja desconhecida: '{argumentos[0]}'. Lojas: {', '.join(l['nome'] for l in ambiente.config_lojas)}"
    loja = ambiente.config_lojas[indice]
    ativa = ambiente.loja_ativa(loja["nome"])
    if comando == "derrubar":
        if not ativa:
            return f"[!] {loja['nome']} já está fora do ar"
        ambiente.derrubar_loja(loja["nome"])
        return f"[OK] {loja['nome']} derrubada (porta {loja['porta']} fechada)"
    if ativa:
        return f"[!] {loja['nome']} já está no ar"
    try:
        ambiente.subir_loja(loja, ambiente.latencias[indice])
    except RuntimeError as exc:
        return f"[!] não foi possível subir {loja['nome']}: {exc}"
    return f"[OK] {loja['nome']} no ar de novo (porta {loja['porta']}, {ambiente.latencias[indice]} ms)"


def console(ambiente: Ambiente) -> None:
    """Lê comandos do terminal; sem entrada (stdin fechado, segundo plano) só mantém o ambiente no ar."""
    try:
        while True:
            resposta = executar_comando(ambiente, input("> "))
            if resposta:
                print(resposta, flush=True)
    except EOFError:
        while True:
            time.sleep(1)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Sobe as 4 lojas e o agregador.")
    parser.add_argument("--latencias", type=ler_latencias, help="latências em ms (ex.: 100,200,300,400)")
    parser.add_argument("--timeout-loja", type=float, default=None)
    args = parser.parse_args(argv)

    tratar_sinais_de_encerramento()
    ambiente = Ambiente(args.latencias, args.timeout_loja)
    try:
        ambiente.subir()
        print("\n[OK] Ambiente pronto. Em outro terminal execute: python cliente.py")
        print(f"     {AJUDA_CONSOLE}\n", flush=True)
        console(ambiente)
    except KeyboardInterrupt:
        print("\n[!] Encerrando ambiente...")
    except RuntimeError as exc:
        print(f"[ERRO] {exc}", file=sys.stderr)
        return 1
    finally:
        ambiente.encerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
