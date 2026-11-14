# -*- coding: utf-8 -*-
"""Testes do agregador: consolidação, ordenação, estratégias e tratamento de falhas."""
import csv
import os
import tempfile
import unittest

import apoio
import protocolo
from agregador import Agregador, RegistroPesquisas, calcular_score_custo_beneficio
from servidor_base import ServidorTCPMultithread


class TestConsolidacao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.amb = apoio.AmbienteTeste()

    @classmethod
    def tearDownClass(cls):
        cls.amb.encerrar()

    def test_ordena_por_preco_e_identifica_menor(self):
        r = self.amb.agregador.executar_busca("rtx 4060", protocolo.MODO_CONCORRENTE, protocolo.CRITERIO_PRECO)
        self.assertEqual(r["status"], protocolo.STATUS_SUCESSO)
        totais = [o["preco_total"] for o in r["ofertas_ordenadas"]]
        self.assertEqual(len(totais), 4)
        self.assertEqual(totais, sorted(totais))
        self.assertEqual(r["menor_preco"]["fonte"], "PichauSim")
        self.assertEqual(r["menor_preco"]["preco_total"], 1864.00)

    def test_ordena_por_custo_beneficio(self):
        r = self.amb.agregador.executar_busca("ssd", protocolo.MODO_CONCORRENTE,
                                              protocolo.CRITERIO_CUSTO_BENEFICIO)
        scores = [o["score_custo_beneficio"] for o in r["ofertas_ordenadas"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(r["melhor_custo_beneficio"]["fonte"], r["ofertas_ordenadas"][0]["fonte"])

    def test_sequencial_e_concorrente_dao_mesmo_resultado(self):
        seq = self.amb.agregador.executar_busca("monitor", protocolo.MODO_SEQUENCIAL)
        con = self.amb.agregador.executar_busca("monitor", protocolo.MODO_CONCORRENTE)
        fontes = lambda r: [o["fonte"] for o in r["ofertas_ordenadas"]]  # noqa: E731
        self.assertEqual(fontes(seq), fontes(con))

    def test_produto_inexistente(self):
        r = self.amb.agregador.executar_busca("geladeira")
        self.assertEqual(r["status"], protocolo.STATUS_NAO_ENCONTRADO)
        self.assertEqual(len(r["lojas_sem_produto"]), 4)
        self.assertIsNone(r["menor_preco"])

    def test_listar_produtos(self):
        r = self.amb.agregador.listar_produtos()
        self.assertEqual(r["produtos"], ["iphone", "monitor", "notebook", "rtx 4060", "ssd"])

    def test_score_custo_beneficio(self):
        self.assertEqual(calcular_score_custo_beneficio({"preco_total": 0}), 0.0)
        barato = calcular_score_custo_beneficio({"preco_total": 100, "avaliacao": 4.5, "garantia_meses": 12})
        caro = calcular_score_custo_beneficio({"preco_total": 200, "avaliacao": 4.5, "garantia_meses": 12})
        self.assertGreater(barato, caro)


class TestDesempenho(unittest.TestCase):
    def test_concorrente_mais_rapido_que_sequencial(self):
        amb = apoio.AmbienteTeste(latencias=(100, 100, 100, 100))
        try:
            seq = amb.agregador.executar_busca("notebook", protocolo.MODO_SEQUENCIAL)
            con = amb.agregador.executar_busca("notebook", protocolo.MODO_CONCORRENTE)
        finally:
            amb.encerrar()
        self.assertGreaterEqual(seq["tempo_total_ms"], 400)  # soma das latências
        self.assertLess(con["tempo_total_ms"], 250)  # aproximadamente a maior latência
        self.assertGreater(seq["tempo_total_ms"] / con["tempo_total_ms"], 2.5)

    def test_latencia_heterogenea(self):
        amb = apoio.AmbienteTeste(latencias=(50, 100, 150, 200))
        try:
            seq = amb.agregador.executar_busca("ssd", protocolo.MODO_SEQUENCIAL)
            con = amb.agregador.executar_busca("ssd", protocolo.MODO_CONCORRENTE)
        finally:
            amb.encerrar()
        self.assertGreaterEqual(seq["tempo_total_ms"], 500)  # 50+100+150+200
        self.assertGreaterEqual(con["tempo_total_ms"], 200)  # max
        self.assertLess(con["tempo_total_ms"], 320)


class TestFalhas(unittest.TestCase):
    def setUp(self):
        self.amb = apoio.AmbienteTeste()

    def tearDown(self):
        self.amb.encerrar()

    def _agregador_com(self, loja_extra, timeout=2.0):
        lojas = self.amb.lojas[:3] + [loja_extra]
        return Agregador(lojas, timeout_loja=timeout, arquivo_log=None)

    def test_loja_desligada(self):
        ag = self._agregador_com({"nome": "Desligada", "host": apoio.HOST, "porta": apoio.porta_livre()})
        for modo in protocolo.MODOS_VALIDOS:
            r = ag.executar_busca("notebook", modo)
            self.assertEqual(r["total_ofertas"], 3)
            self.assertEqual(r["ocorrencias_ou_falhas"][0]["status"], protocolo.STATUS_ERRO_COMUNICACAO)
            self.assertEqual(r["ocorrencias_ou_falhas"][0]["fonte"], "Desligada")

    def test_loja_cai_durante_a_consulta(self):
        derrubador = apoio.ServidorQueDerruba()
        try:
            ag = self._agregador_com({"nome": "Instavel", "host": apoio.HOST, "porta": derrubador.porta})
            r = ag.executar_busca("ssd")
        finally:
            derrubador.encerrar()
        self.assertEqual(r["total_ofertas"], 3)
        falha = r["ocorrencias_ou_falhas"][0]
        self.assertEqual(falha["status"], protocolo.STATUS_ERRO_COMUNICACAO)
        self.assertIn("ConexaoEncerrada", falha["detalhe"])

    def test_loja_lenta_gera_timeout(self):
        lenta = apoio.AmbienteTeste(latencias=(1500, 0, 0, 0))
        try:
            ag = self._agregador_com(dict(lenta.lojas[0], nome="Lenta"), timeout=0.3)
            r = ag.executar_busca("iphone", protocolo.MODO_CONCORRENTE)
        finally:
            lenta.encerrar()
        self.assertEqual(r["total_ofertas"], 3)
        self.assertEqual(r["ocorrencias_ou_falhas"][0]["status"], protocolo.STATUS_TIMEOUT)
        self.assertLess(r["tempo_total_ms"], 1000)  # o timeout limita a espera

    def _loja_falsa(self, resposta):
        srv = ServidorTCPMultithread("falsa", apoio.HOST, 0, lambda req, end: dict(resposta))
        porta = srv.iniciar_em_thread()
        self.addCleanup(srv.encerrar)
        return {"nome": "Falsa", "host": apoio.HOST, "porta": porta}

    def test_loja_com_resposta_incompleta(self):
        # 'sucesso' sem os campos da oferta não pode derrubar a pesquisa inteira
        ag = self._agregador_com(self._loja_falsa({"status": "sucesso", "fonte": "Falsa"}))
        for criterio in protocolo.CRITERIOS_VALIDOS:
            r = ag.tratar({"operacao": "consultar", "produto": "ssd", "criterio": criterio})
            self.assertEqual(r["status"], protocolo.STATUS_SUCESSO)
            self.assertEqual(r["total_ofertas"], 3)
            falha = r["ocorrencias_ou_falhas"][0]
            self.assertEqual(falha["fonte"], "Falsa")
            self.assertEqual(falha["status"], protocolo.STATUS_ERRO_COMUNICACAO)
            self.assertIn("resposta inválida", falha["detalhe"])

    def test_loja_com_preco_nao_numerico(self):
        oferta = {"status": "sucesso", "fonte": "Falsa", "produto": "SSD", "specs": "1TB", "preco": "abc",
                  "frete": 0, "preco_total": "abc", "avaliacao": 5, "garantia_meses": 12}
        r = self._agregador_com(self._loja_falsa(oferta)).tratar({"operacao": "consultar", "produto": "ssd"})
        self.assertEqual(r["total_ofertas"], 3)
        self.assertEqual(r["ocorrencias_ou_falhas"][0]["status"], protocolo.STATUS_ERRO_COMUNICACAO)

    def test_listar_com_loja_de_resposta_invalida(self):
        loja = self._loja_falsa({"status": "sucesso", "fonte": "Falsa", "produtos": ["sem chave"]})
        r = self._agregador_com(loja).tratar({"operacao": "listar_produtos"})
        self.assertEqual(r["status"], protocolo.STATUS_SUCESSO)
        self.assertIn("ssd", r["produtos"])
        self.assertEqual(r["ocorrencias_ou_falhas"][0]["status"], protocolo.STATUS_ERRO_COMUNICACAO)

    def test_todas_as_lojas_fora(self):
        lojas = [{"nome": f"L{i}", "host": apoio.HOST, "porta": apoio.porta_livre()} for i in range(4)]
        r = Agregador(lojas, arquivo_log=None).executar_busca("ssd")
        self.assertEqual(r["status"], protocolo.STATUS_NAO_ENCONTRADO)
        self.assertEqual(len(r["ocorrencias_ou_falhas"]), 4)


class TestValidacao(unittest.TestCase):
    def setUp(self):
        self.ag = Agregador([], arquivo_log=None)

    def _status(self, req):
        return self.ag.tratar(req)["status"]

    def test_requisicoes_invalidas(self):
        casos = [
            {"operacao": "apagar"},
            {"produto": "ssd"},
            {"operacao": "consultar"},
            {"operacao": "consultar", "produto": "   "},
            {"operacao": "consultar", "produto": "ssd", "modo": "paralelo"},
            {"operacao": "consultar", "produto": "ssd", "criterio": "nome"},
            {"operacao": "consultar", "produto": "ssd", "atraso_ms": "abc"},
            {"operacao": "consultar", "produto": "ssd", "atraso_ms": -5},
            {"operacao": "consultar", "produto": "ssd", "atraso_ms": 10_001},
            {"operacao": "consultar", "produto": "ssd", "atraso_ms": True},
            {"operacao": "consultar", "produto": "ssd", "atraso_ms": 1.5},
            {"operacao": "consultar", "produto": "ssd", "atraso_ms": "50"},
            {"operacao": "consultar", "produto": 123},
        ]
        for req in casos:
            with self.subTest(req=req):
                self.assertEqual(self._status(req), protocolo.STATUS_ERRO_REQUISICAO)

    def test_ping(self):
        self.assertEqual(self._status({"operacao": "ping"}), protocolo.STATUS_SUCESSO)


class TestRegistro(unittest.TestCase):
    def test_registra_tempo_em_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = os.path.join(tmp, "log.csv")
            amb = apoio.AmbienteTeste()
            try:
                ag = Agregador(amb.lojas, arquivo_log=caminho)
                ag.tratar({"operacao": "consultar", "produto": "ssd", "modo": "sequencial"}, ("127.0.0.1", 1))
                ag.tratar({"operacao": "consultar", "produto": "ssd"}, ("127.0.0.1", 2))
            finally:
                amb.encerrar()
            with open(caminho, encoding="utf-8") as f:
                linhas = f.read().strip().splitlines()
        self.assertEqual(len(linhas), 3)  # cabeçalho + 2 pesquisas
        self.assertTrue(linhas[0].startswith("timestamp,"))
        self.assertIn("sequencial", linhas[1])
        self.assertIn("concorrente", linhas[2])

    def test_registra_tempo_de_cada_loja(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = os.path.join(tmp, "log.csv")
            amb = apoio.AmbienteTeste()
            try:
                Agregador(amb.lojas, arquivo_log=caminho).tratar(
                    {"operacao": "consultar", "produto": "ssd"}, ("127.0.0.1", 1))
            finally:
                amb.encerrar()
            with open(caminho, encoding="utf-8") as f:
                linhas = list(csv.DictReader(f))
        tempos = dict(item.split("=") for item in linhas[0]["tempos_lojas_ms"].split(";"))
        self.assertEqual(set(tempos), {"KabumSim", "PichauSim", "TerabyteSim", "MagaluTechSim"})
        self.assertTrue(all(float(t) > 0 for t in tempos.values()))

    def test_registro_desativado(self):
        RegistroPesquisas(None).registrar({"produto": "x"})  # não deve falhar


if __name__ == "__main__":
    unittest.main()
