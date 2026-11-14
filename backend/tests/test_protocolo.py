# -*- coding: utf-8 -*-
"""Testes do framing JSON + '\\n' (protocolo.py)."""
import socket
import unittest

import apoio  # noqa: F401  (ajusta o sys.path)
import protocolo


class TestProtocolo(unittest.TestCase):
    def setUp(self):
        self.a, self.b = socket.socketpair()
        self.b.settimeout(2)

    def tearDown(self):
        self.a.close()
        self.b.close()

    def test_ida_e_volta_com_acentos(self):
        msg = {"operacao": "consultar", "produto": "câmera ção", "preco": 29.9}
        protocolo.enviar_json(self.a, msg)
        self.assertEqual(protocolo.receber_json(self.b), msg)

    def test_mensagem_fragmentada(self):
        dados = protocolo.codificar({"produto": "ssd"})
        self.a.sendall(dados[:3])
        self.a.sendall(dados[3:])
        self.assertEqual(protocolo.receber_json(self.b), {"produto": "ssd"})

    def test_json_invalido(self):
        self.a.sendall(b"isto nao e json\n")
        with self.assertRaises(protocolo.MensagemInvalida):
            protocolo.receber_json(self.b)

    def test_json_que_nao_e_objeto(self):
        self.a.sendall(b"[1, 2, 3]\n")
        with self.assertRaises(protocolo.MensagemInvalida):
            protocolo.receber_json(self.b)

    def test_mensagem_grande_demais(self):
        self.a.sendall(b"x" * 5000)
        with self.assertRaises(protocolo.MensagemInvalida):
            protocolo.receber_json(self.b, max_bytes=1024)

    def test_conexao_encerrada_sem_terminador(self):
        self.a.sendall(b'{"produto": "ss')
        self.a.close()
        with self.assertRaises(protocolo.ConexaoEncerrada):
            protocolo.receber_json(self.b)

    def test_timeout_sem_dados(self):
        self.b.settimeout(0.2)
        with self.assertRaises(socket.timeout):
            protocolo.receber_json(self.b)


class TestValidacaoEPing(unittest.TestCase):
    def test_validar_pesquisa_normaliza(self):
        self.assertEqual(protocolo.validar_pesquisa({"produto": "  SSD "}),
                         ("SSD", "concorrente", "preco", None))
        self.assertEqual(protocolo.validar_pesquisa({"produto": "ssd", "modo": "Sequencial",
                                                     "criterio": "custo_beneficio", "atraso_ms": 0}),
                         ("ssd", "sequencial", "custo_beneficio", 0))

    def test_validar_pesquisa_recusa(self):
        for req in ({}, {"produto": " "}, {"produto": 1}, {"produto": "ssd", "modo": "comparar"},
                    {"produto": "ssd", "criterio": "nome"}, {"produto": "ssd", "atraso_ms": True},
                    {"produto": "ssd", "atraso_ms": 1.5}, {"produto": "ssd", "atraso_ms": 10_001}):
            with self.subTest(req=req), self.assertRaises(ValueError):
                protocolo.validar_pesquisa(req)

    def test_validar_pesquisa_com_modos_extras(self):
        modos = (*protocolo.MODOS_VALIDOS, protocolo.MODO_COMPARAR)
        self.assertEqual(protocolo.validar_pesquisa({"produto": "ssd", "modo": "comparar"}, modos)[1], "comparar")

    def test_ping(self):
        from servidor_base import ServidorTCPMultithread
        srv = ServidorTCPMultithread("pong", apoio.HOST, 0, lambda req, end: {"status": "sucesso"})
        porta = srv.iniciar_em_thread()
        try:
            self.assertTrue(protocolo.ping(apoio.HOST, porta))
        finally:
            srv.encerrar()
        self.assertFalse(protocolo.ping(apoio.HOST, apoio.porta_livre()))


if __name__ == "__main__":
    unittest.main()
