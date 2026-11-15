# -*- coding: utf-8 -*-
"""Testes ponta a ponta via sockets TCP: cliente -> agregador -> lojas."""
import contextlib
import io
import socket
import threading
import unittest

import apoio
import protocolo
from cliente import (ErroCliente, comparar, disparar_clientes_simultaneos, executar, listar_produtos,
                     requisitar_agregador)
from servidor_base import ServidorTCPMultithread


class TestPontaAPonta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.amb = apoio.AmbienteTeste(latencias=(50, 50, 50, 50), com_agregador=True)
        cls.conexao = {"host": apoio.HOST, "porta": cls.amb.porta_agregador, "timeout": 10}

    @classmethod
    def tearDownClass(cls):
        cls.amb.encerrar()

    def test_pesquisa_via_cliente(self):
        r = requisitar_agregador("notebook", "concorrente", "preco", **self.conexao)
        self.assertEqual(r["status"], protocolo.STATUS_SUCESSO)
        self.assertEqual(r["total_lojas_responderam"], 4)
        self.assertEqual(r["menor_preco"]["fonte"], "PichauSim")

    def test_atraso_informado_pelo_cliente(self):
        r = requisitar_agregador("ssd", "concorrente", "preco", atraso_ms=0, **self.conexao)
        self.assertLess(r["tempo_total_ms"], 50)

    def test_listar(self):
        self.assertIn("ssd", listar_produtos(**self.conexao)["produtos"])

    def test_multiplos_clientes_simultaneos(self):
        n = 20
        respostas = [None] * n

        def cliente(i):
            respostas[i] = requisitar_agregador("monitor", "concorrente", **self.conexao)

        threads = [threading.Thread(target=cliente, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertTrue(all(r and r["status"] == protocolo.STATUS_SUCESSO for r in respostas))
        self.assertTrue(all(r["total_ofertas"] == 4 for r in respostas))

    def test_comparar_os_dois_modos(self):
        r = comparar("notebook", **self.conexao)
        self.assertEqual(r["modo_execucao"], protocolo.MODO_COMPARAR)
        self.assertEqual(r["sequencial"]["modo_execucao"], "sequencial")
        self.assertEqual(r["concorrente"]["modo_execucao"], "concorrente")
        self.assertGreater(r["speedup"], 1.5)

    def test_comparar_imprime_relatorio_dos_dois_modos(self):
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            executar("rtx 4060", protocolo.MODO_COMPARAR, protocolo.CRITERIO_PRECO, **self.conexao)
        texto = saida.getvalue()
        self.assertIn("MODO: SEQUENCIAL", texto)
        self.assertIn("MODO: CONCORRENTE", texto)
        self.assertLess(texto.index("MODO: SEQUENCIAL"), texto.index("MODO: CONCORRENTE"))
        self.assertLess(texto.index("MODO: CONCORRENTE"), texto.index("Speedup"))

    def test_disparar_clientes_simultaneos(self):
        r = disparar_clientes_simultaneos(10, "ssd", "concorrente", atraso_ms=10, **self.conexao)
        self.assertEqual(len(r["tempos_ms"]), 10)
        self.assertEqual(r["falhas"], [None] * 10)
        self.assertGreater(r["tempo_total_ms"], 0)

    def test_json_malformado_recebe_erro(self):
        with socket.create_connection((apoio.HOST, self.amb.porta_agregador), timeout=5) as s:
            s.sendall(b"{nao eh json}\n")
            resp = protocolo.receber_json(s)
        self.assertEqual(resp["status"], protocolo.STATUS_ERRO_REQUISICAO)


class TestErrosDoCliente(unittest.TestCase):
    def test_agregador_fora_do_ar(self):
        with self.assertRaises(ErroCliente):
            requisitar_agregador("ssd", host=apoio.HOST, porta=apoio.porta_livre(), timeout=2)

    def test_clientes_simultaneos_com_agregador_fora(self):
        r = disparar_clientes_simultaneos(3, "ssd", "concorrente", host=apoio.HOST,
                                          porta=apoio.porta_livre(), timeout=2)
        self.assertTrue(all(r["falhas"]))

    def test_cliente_ocioso_e_desconectado(self):
        srv = ServidorTCPMultithread("ocioso", apoio.HOST, 0, lambda req, end: {"status": "sucesso"},
                                     timeout_ocioso=0.3)
        porta = srv.iniciar_em_thread()
        try:
            with socket.create_connection((apoio.HOST, porta), timeout=5) as s:
                resp = protocolo.receber_json(s)  # não enviamos nada
        finally:
            srv.encerrar()
        self.assertEqual(resp["status"], protocolo.STATUS_ERRO_REQUISICAO)

    def test_erro_interno_nao_derruba_servidor(self):
        def tratar(req, end):
            if req.get("falhar"):
                raise RuntimeError("bug simulado")
            return {"status": "sucesso"}

        srv = ServidorTCPMultithread("frágil", apoio.HOST, 0, tratar)
        porta = srv.iniciar_em_thread()
        try:
            r1 = protocolo.requisitar(apoio.HOST, porta, {"falhar": True}, 2)
            r2 = protocolo.requisitar(apoio.HOST, porta, {}, 2)
        finally:
            srv.encerrar()
        self.assertEqual(r1["status"], protocolo.STATUS_ERRO_INTERNO)
        self.assertEqual(r2["status"], protocolo.STATUS_SUCESSO)


if __name__ == "__main__":
    unittest.main()
