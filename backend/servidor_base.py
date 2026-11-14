#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo: servidor_base.py (Servidor TCP multithread: uma thread por conexão)

Usado pelas lojas e pelo agregador. Cada conexão aceita é atendida por uma
thread própria, o que permite atender vários clientes ao mesmo tempo.
"""
import logging
import socket
import threading
from contextlib import suppress

import protocolo
from config import TIMEOUT_OCIOSO_SERVIDOR


class ServidorTCPMultithread:
    """
    Servidor TCP genérico. Recebe uma função `tratar(requisicao: dict, endereco) -> dict`
    e cuida do resto: aceitar conexões, criar threads, ler/escrever mensagens e fechar conexões.
    """

    def __init__(self, nome: str, host: str, porta: int, tratar, backlog: int = 128,
                 timeout_ocioso: float = TIMEOUT_OCIOSO_SERVIDOR):
        self.nome, self.host, self.porta = nome, host, porta
        self.tratar = tratar
        self.backlog = backlog
        self.timeout_ocioso = timeout_ocioso
        self.log = logging.getLogger(nome)
        self._socket = None
        self._ativo = threading.Event()
        self._thread_aceite = None

    # ------------------------------------------------------------------ ciclo de vida
    def iniciar(self) -> int:
        """Cria o socket de escuta. Devolve a porta efetiva (útil quando porta=0)."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self.host, self.porta))
        self._socket.listen(self.backlog)
        self._socket.settimeout(0.5)  # accept() acorda a cada 0,5 s para ver se deve encerrar
        self.porta = self._socket.getsockname()[1]
        self._ativo.set()
        return self.porta

    def servir_para_sempre(self) -> None:
        """Laço principal: aceita conexões e despacha cada uma para uma nova thread."""
        if self._socket is None:
            self.iniciar()
        try:
            while self._ativo.is_set():
                try:
                    conn, endereco = self._socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break  # socket fechado durante o encerramento
                threading.Thread(target=self._atender, args=(conn, endereco), daemon=True).start()
        finally:
            self._fechar_socket()

    def iniciar_em_thread(self) -> int:
        """Inicia o servidor em segundo plano (usado nos testes). Devolve a porta."""
        porta = self.iniciar()
        self._thread_aceite = threading.Thread(target=self.servir_para_sempre, daemon=True)
        self._thread_aceite.start()
        return porta

    def encerrar(self) -> None:
        self._ativo.clear()
        if self._thread_aceite is not None:
            self._thread_aceite.join(timeout=2)
        self._fechar_socket()

    def _fechar_socket(self) -> None:
        if self._socket is not None:
            with suppress(OSError):
                self._socket.close()

    # ------------------------------------------------------------------ atendimento
    def _atender(self, conn: socket.socket, endereco) -> None:
        """Uma requisição e uma resposta por conexão; erros viram respostas padronizadas."""
        with conn:
            conn.settimeout(self.timeout_ocioso)
            try:
                requisicao = protocolo.receber_json(conn)
            except protocolo.ConexaoEncerrada:
                return  # o cliente desistiu antes de enviar a requisição
            except protocolo.MensagemInvalida as exc:
                return self._responder(conn, protocolo.resposta_erro(protocolo.STATUS_ERRO_REQUISICAO, str(exc)))
            except socket.timeout:
                return self._responder(conn, protocolo.resposta_erro(
                    protocolo.STATUS_ERRO_REQUISICAO, f"nenhuma requisição recebida em {self.timeout_ocioso}s"))

            try:
                resposta = self.tratar(requisicao, endereco)
            except Exception as exc:  # uma falha inesperada não pode derrubar o servidor
                self.log.exception("erro ao tratar requisição de %s", endereco)
                resposta = protocolo.resposta_erro(protocolo.STATUS_ERRO_INTERNO, f"{type(exc).__name__}: {exc}")
            self._responder(conn, resposta)

    def _responder(self, conn: socket.socket, resposta: dict) -> None:
        try:
            protocolo.enviar_json(conn, resposta)
        except OSError as exc:  # o cliente pode ter fechado a conexão enquanto processávamos
            self.log.warning("não foi possível enviar resposta: %s", exc)
