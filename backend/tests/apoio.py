# -*- coding: utf-8 -*-
"""Utilitários compartilhados pelos testes: sobem lojas e agregador em threads (portas efêmeras)."""
import logging
import os
import socket
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.disable(logging.CRITICAL)  # os testes provocam erros de propósito; não poluir a saída

from agregador import Agregador, criar_servidor_agregador  # noqa: E402
from config import LOJAS  # noqa: E402
from loja_server import criar_servidor_loja  # noqa: E402

HOST = "127.0.0.1"


class AmbienteTeste:
    """Sobe as 4 lojas reais (catálogos de dados/lojas) e, opcionalmente, o agregador."""

    def __init__(self, latencias=(20, 20, 20, 20), timeout_loja=2.0, com_agregador=False):
        self.servidores = []
        self.lojas = []
        for loja, latencia in zip(LOJAS, latencias):
            srv = criar_servidor_loja(loja["nome"], 0, latencia, HOST)
            porta = srv.iniciar_em_thread()
            self.servidores.append(srv)
            self.lojas.append({"nome": loja["nome"], "host": HOST, "porta": porta})
        self.agregador = Agregador(self.lojas, timeout_loja=timeout_loja, arquivo_log=None)
        self.porta_agregador = None
        if com_agregador:
            srv = criar_servidor_agregador(self.agregador, HOST, 0)
            self.porta_agregador = srv.iniciar_em_thread()
            self.servidores.append(srv)

    def encerrar(self):
        for srv in self.servidores:
            srv.encerrar()


def porta_livre() -> int:
    """Porta TCP sem ninguém escutando (simula serviço desligado)."""
    with socket.socket() as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


class ServidorQueDerruba:
    """Aceita a conexão, lê a requisição e fecha sem responder (queda durante a consulta)."""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.bind((HOST, 0))
        self.sock.listen(16)
        self.porta = self.sock.getsockname()[1]
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            conn.recv(4096)
            conn.close()

    def encerrar(self):
        self.sock.close()
