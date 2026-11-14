# -*- coding: utf-8 -*-
"""Testes do serviço de loja (loja_server.py) e do gerenciador de processos (iniciar_servicos.Ambiente)."""
import argparse
import subprocess
import unittest

import apoio
import protocolo

from iniciar_servicos import Ambiente, ler_latencias
from loja_server import Loja, carregar_catalogo
from servidor_base import ServidorTCPMultithread

HOST = apoio.HOST


class TestLoja(unittest.TestCase):
    def setUp(self):
        self.loja = Loja("KabumSim", carregar_catalogo("KabumSim"), latencia_ms=0)

    def test_consulta_por_chave(self):
        r = self.loja.tratar({"operacao": "consultar", "produto": "rtx 4060"})
        self.assertEqual(r["status"], protocolo.STATUS_SUCESSO)
        self.assertEqual(r["fonte"], "KabumSim")
        self.assertEqual(r["preco_total"], round(r["preco"] + r["frete"], 2))
        for campo in ("produto", "specs", "avaliacao", "garantia_meses"):
            self.assertIn(campo, r)

    def test_busca_ignora_maiusculas_e_aceita_nome(self):
        self.assertEqual(self.loja.tratar({"operacao": "consultar", "produto": "KINGSTON"})["status"],
                         protocolo.STATUS_SUCESSO)

    def test_produto_inexistente(self):
        r = self.loja.tratar({"operacao": "consultar", "produto": "geladeira"})
        self.assertEqual(r["status"], protocolo.STATUS_NAO_ENCONTRADO)
        self.assertIsNone(r["preco_total"])

    def test_devolve_o_item_mais_barato_quando_varios_casam(self):
        catalogo = [
            {"chave": "ssd", "produto": "SSD caro", "specs": "", "preco": 500, "frete": 0,
             "avaliacao": 5, "garantia_meses": 12},
            {"chave": "ssd", "produto": "SSD barato", "specs": "", "preco": 300, "frete": 20,
             "avaliacao": 4, "garantia_meses": 12},
        ]
        r = Loja("X", catalogo, 0).tratar({"operacao": "consultar", "produto": "ssd"})
        self.assertEqual(r["produto"], "SSD barato")

    def test_listar_e_ping(self):
        r = self.loja.tratar({"operacao": "listar_produtos"})
        self.assertEqual({p["chave"] for p in r["produtos"]}, {"rtx 4060", "notebook", "monitor", "ssd", "iphone"})
        self.assertEqual(self.loja.tratar({"operacao": "ping"})["operacao"], "pong")

    def test_requisicoes_invalidas(self):
        casos = [
            {"operacao": "apagar"},
            {"operacao": "consultar"},
            {"operacao": "consultar", "produto": "  "},
            {"operacao": "consultar", "produto": "ssd", "atraso_ms": -1},
            {"operacao": "consultar", "produto": "ssd", "atraso_ms": True},
            {"operacao": "consultar", "produto": "ssd", "atraso_ms": 1.5},
            {"operacao": "consultar", "produto": "ssd", "atraso_ms": "50"},
        ]
        for req in casos:
            with self.subTest(req=req):
                self.assertEqual(self.loja.tratar(req)["status"], protocolo.STATUS_ERRO_REQUISICAO)


class TestAmbiente(unittest.TestCase):
    """Os serviços sobem como processos reais (subprocess), em portas livres."""

    def _loja(self, porta, nome="KabumSim"):
        return {"nome": nome, "host": HOST, "porta": porta}

    def test_ler_latencias(self):
        self.assertEqual(ler_latencias("100,200,300,400"), [100, 200, 300, 400])
        for texto in ("100,200", "a,b,c,d", ""):
            with self.subTest(texto=texto), self.assertRaises(argparse.ArgumentTypeError):
                ler_latencias(texto)

    def test_sobe_e_derruba_loja_como_processo(self):
        porta = apoio.porta_livre()
        amb = Ambiente(saida=subprocess.DEVNULL)
        try:
            amb.subir_loja(self._loja(porta), 0)
            r = protocolo.requisitar(HOST, porta, {"operacao": "consultar", "produto": "ssd"}, 2)
            self.assertEqual(r["fonte"], "KabumSim")
            amb.derrubar_loja("KabumSim")
            with self.assertRaises(ConnectionRefusedError):
                protocolo.requisitar(HOST, porta, {"operacao": "ping"}, 2)
        finally:
            amb.encerrar()

    def test_porta_ocupada_e_detectada(self):
        # outro serviço já responde 'ping' na porta: o Ambiente não pode achar que a loja dele subiu
        impostor = ServidorTCPMultithread("impostor", HOST, 0,
                                          lambda req, end: {"status": "sucesso", "operacao": "pong"})
        porta = impostor.iniciar_em_thread()
        amb = Ambiente(saida=subprocess.DEVNULL)
        try:
            with self.assertRaisesRegex(RuntimeError, "em uso"):
                amb.subir_loja(self._loja(porta), 0)
        finally:
            amb.encerrar()
            impostor.encerrar()

    def test_falha_ao_subir_encerra_o_que_ja_tinha_subido(self):
        livre = apoio.porta_livre()
        impostor = ServidorTCPMultithread("impostor", HOST, 0,
                                          lambda req, end: {"status": "sucesso", "operacao": "pong"})
        ocupada = impostor.iniciar_em_thread()
        lojas = [self._loja(livre, "KabumSim"), self._loja(ocupada, "PichauSim")]
        amb = Ambiente(lojas=lojas, latencias=[0, 0], saida=subprocess.DEVNULL)
        try:
            with self.assertRaises(RuntimeError):
                amb.subir(com_agregador=False)
            # a KabumSim, que chegou a subir, não pode ficar órfã ocupando a porta
            with self.assertRaises(ConnectionRefusedError):
                protocolo.requisitar(HOST, livre, {"operacao": "ping"}, 2)
        finally:
            amb.encerrar()
            impostor.encerrar()


if __name__ == "__main__":
    unittest.main()
