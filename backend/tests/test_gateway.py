# -*- coding: utf-8 -*-
"""Testes do gateway HTTP (gateway_http.py): navegador -> HTTP -> gateway -> TCP -> agregador -> lojas."""
import csv
import http.client
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest

import apoio
import protocolo
from gateway_http import Gateway, criar_servidor_gateway
from iniciar_servicos import Ambiente

HOST = apoio.HOST
PNG_MINIMO = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def chamar(porta: int, metodo: str, rota: str, corpo=None, bruto: bytes = None):
    """Faz uma requisição HTTP ao gateway e devolve (código, json ou bytes, content-type)."""
    conexao = http.client.HTTPConnection(HOST, porta, timeout=30)
    try:
        dados = bruto if bruto is not None else (json.dumps(corpo).encode() if corpo is not None else None)
        cabecalhos = {"Content-Type": "application/json"} if dados is not None else {}
        conexao.request(metodo, rota, body=dados, headers=cabecalhos)
        resp = conexao.getresponse()
        conteudo = resp.read()
        tipo = resp.getheader("Content-Type", "")
        if tipo.startswith("application/json"):
            return resp.status, json.loads(conteudo), tipo
        return resp.status, conteudo, tipo
    finally:
        conexao.close()


def criar_resultados_falsos() -> str:
    """Diretório com um CSV de experimento, um gráfico e um log de pesquisas."""
    diretorio = tempfile.mkdtemp(prefix="resultados_teste_")
    with open(os.path.join(diretorio, "exp1_2_resumo.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["modo", "media_ms"])
        w.writerow(["sequencial", "621.0"])
        w.writerow(["concorrente", "156.5"])
    with open(os.path.join(diretorio, "g1_sequencial_vs_concorrente.png"), "wb") as f:
        f.write(PNG_MINIMO)
    with open(os.path.join(diretorio, "log_pesquisas.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "produto"])
        for i in range(10):
            w.writerow([f"2026-11-14T10:00:0{i}", f"produto{i}"])
    return diretorio


class ServidorGatewayTeste:
    """Sobe o gateway HTTP numa porta efêmera, numa thread."""

    def __init__(self, gateway: Gateway):
        self.servidor = criar_servidor_gateway(gateway, HOST, 0)
        self.porta = self.servidor.server_address[1]
        threading.Thread(target=self.servidor.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True).start()

    def encerrar(self):
        self.servidor.shutdown()
        self.servidor.server_close()


class TestGateway(unittest.TestCase):
    """Gateway ligado a 4 lojas reais e a um agregador real (threads, portas efêmeras)."""

    @classmethod
    def setUpClass(cls):
        cls.amb = apoio.AmbienteTeste(latencias=(40, 40, 40, 40), com_agregador=True)
        cls.resultados = criar_resultados_falsos()
        gateway = Gateway(lojas=cls.amb.lojas, porta_agregador=cls.amb.porta_agregador,
                          diretorio_resultados=cls.resultados, diretorio_estatico=None)
        cls.srv = ServidorGatewayTeste(gateway)
        cls.porta = cls.srv.porta

    @classmethod
    def tearDownClass(cls):
        cls.srv.encerrar()
        cls.amb.encerrar()
        shutil.rmtree(cls.resultados, ignore_errors=True)

    def chamar(self, metodo, rota, corpo=None, bruto=None):
        return chamar(self.porta, metodo, rota, corpo, bruto)

    # ---------------------------------------------------------------- consultas
    def test_saude(self):
        codigo, r, _ = self.chamar("GET", "/api/saude")
        self.assertEqual(codigo, 200)
        self.assertTrue(r["agregador_online"])
        self.assertFalse(r["gerencia_processos"])

    def test_lojas_online(self):
        codigo, r, _ = self.chamar("GET", "/api/lojas")
        self.assertEqual(codigo, 200)
        self.assertEqual(len(r["lojas"]), 4)
        self.assertTrue(all(loja["online"] for loja in r["lojas"]))
        self.assertEqual(r["lojas"][0]["nome"], "KabumSim")

    def test_produtos(self):
        codigo, r, _ = self.chamar("GET", "/api/produtos")
        self.assertEqual(codigo, 200)
        self.assertIn("rtx 4060", r["produtos"])

    def test_consulta_concorrente(self):
        codigo, r, _ = self.chamar("POST", "/api/consultar",
                                   {"produto": "rtx 4060", "modo": "concorrente", "criterio": "preco"})
        self.assertEqual(codigo, 200)
        self.assertEqual(r["status"], protocolo.STATUS_SUCESSO)
        self.assertEqual(r["menor_preco"]["fonte"], "PichauSim")
        self.assertEqual(r["menor_preco"]["preco_total"], 1864.0)

    def test_comparar_devolve_os_dois_modos_e_speedup(self):
        codigo, r, _ = self.chamar("POST", "/api/consultar", {"produto": "rtx 4060", "modo": "comparar"})
        self.assertEqual(codigo, 200)
        self.assertEqual(r["sequencial"]["modo_execucao"], "sequencial")
        self.assertEqual(r["concorrente"]["modo_execucao"], "concorrente")
        self.assertGreater(r["speedup"], 1.5)

    def test_produto_inexistente_nao_e_erro_http(self):
        codigo, r, _ = self.chamar("POST", "/api/consultar", {"produto": "geladeira", "atraso_ms": 0})
        self.assertEqual(codigo, 200)
        self.assertEqual(r["status"], protocolo.STATUS_NAO_ENCONTRADO)

    def test_requisicoes_invalidas(self):
        casos = [
            {"produto": ""},
            {"produto": "   "},
            {"produto": 123},
            {"produto": "ssd", "modo": "paralelo"},
            {"produto": "ssd", "criterio": "marca"},
            {"produto": "ssd", "atraso_ms": "50"},
            {"produto": "ssd", "atraso_ms": 1.5},
            {"produto": "ssd", "atraso_ms": True},
            {"produto": "ssd", "atraso_ms": 999999},
        ]
        for corpo in casos:
            with self.subTest(corpo=corpo):
                codigo, r, _ = self.chamar("POST", "/api/consultar", corpo)
                self.assertEqual(codigo, 400)
                self.assertEqual(r["status"], protocolo.STATUS_ERRO_REQUISICAO)
                self.assertIn("detalhe", r)

    def test_json_invalido(self):
        codigo, r, _ = self.chamar("POST", "/api/consultar", bruto=b"{isso nao e json")
        self.assertEqual(codigo, 400)
        self.assertEqual(r["status"], protocolo.STATUS_ERRO_REQUISICAO)

    def test_rota_desconhecida(self):
        codigo, r, _ = self.chamar("GET", "/api/nao-existe")
        self.assertEqual(codigo, 404)
        self.assertIn("detalhe", r)

    # ---------------------------------------------------------------- carga
    def test_carga_com_20_clientes(self):
        codigo, r, _ = self.chamar("POST", "/api/carga",
                                   {"clientes": 20, "produto": "ssd", "modo": "concorrente", "atraso_ms": 20})
        self.assertEqual(codigo, 200)
        self.assertEqual(r["clientes"], 20)
        self.assertEqual(r["falhas"], 0)
        self.assertEqual(len(r["tempos_ms"]), 20)
        for campo in ("media_ms", "p95_ms", "max_ms", "vazao_req_s", "tempo_total_ms"):
            self.assertIn(campo, r)

    def test_carga_fora_do_limite(self):
        for clientes in (0, 51, "10", 2.5):
            with self.subTest(clientes=clientes):
                codigo, r, _ = self.chamar("POST", "/api/carga", {"clientes": clientes, "produto": "ssd"})
                self.assertEqual(codigo, 400)

    # ---------------------------------------------------------------- controle de lojas
    def test_derrubar_sem_gerenciar_processos(self):
        codigo, r, _ = self.chamar("POST", "/api/lojas/KabumSim/derrubar")
        self.assertEqual(codigo, 409)
        self.assertIn("detalhe", r)

    # ---------------------------------------------------------------- resultados e log
    def test_experimentos(self):
        codigo, r, _ = self.chamar("GET", "/api/experimentos")
        self.assertEqual(codigo, 200)
        self.assertEqual(r["tabelas"][0]["arquivo"], "exp1_2_resumo.csv")
        self.assertEqual(r["tabelas"][0]["linhas"][1]["media_ms"], "156.5")
        self.assertEqual(r["graficos"], ["g1_sequencial_vs_concorrente.png"])

    def test_grafico_png(self):
        codigo, conteudo, tipo = self.chamar("GET", "/api/resultados/g1_sequencial_vs_concorrente.png")
        self.assertEqual(codigo, 200)
        self.assertEqual(tipo, "image/png")
        self.assertEqual(conteudo, PNG_MINIMO)

    def test_resultados_nao_permite_sair_do_diretorio(self):
        for rota in ("/api/resultados/../config.py", "/api/resultados/..%2Fconfig.py",
                     "/api/resultados/log_pesquisas.csv", "/api/resultados/inexistente.png"):
            with self.subTest(rota=rota):
                codigo, _, _ = self.chamar("GET", rota)
                self.assertEqual(codigo, 404)

    def test_log_mais_recentes_primeiro(self):
        codigo, r, _ = self.chamar("GET", "/api/log?limite=3")
        self.assertEqual(codigo, 200)
        self.assertEqual([linha["produto"] for linha in r["linhas"]], ["produto9", "produto8", "produto7"])
        self.assertEqual(r["colunas"], ["timestamp", "produto"])

    def test_log_limite_invalido(self):
        codigo, _, _ = self.chamar("GET", "/api/log?limite=abc")
        self.assertEqual(codigo, 400)


class TestGatewayFalhas(unittest.TestCase):
    """Agregador e lojas fora do ar: o gateway responde com erro amigável, sem traceback."""

    def test_agregador_fora_do_ar(self):
        lojas = [{"nome": "KabumSim", "host": HOST, "porta": apoio.porta_livre()}]
        srv = ServidorGatewayTeste(Gateway(lojas=lojas, porta_agregador=apoio.porta_livre(),
                                           diretorio_estatico=None))
        try:
            codigo, r, _ = chamar(srv.porta, "POST", "/api/consultar", {"produto": "ssd"})
            self.assertEqual(codigo, 502)
            self.assertEqual(r["status"], protocolo.STATUS_ERRO_COMUNICACAO)
            self.assertNotIn("Traceback", r["detalhe"])

            codigo, r, _ = chamar(srv.porta, "GET", "/api/saude")
            self.assertEqual(codigo, 200)
            self.assertFalse(r["agregador_online"])

            codigo, r, _ = chamar(srv.porta, "GET", "/api/lojas")
            self.assertFalse(r["lojas"][0]["online"])

            codigo, r, _ = chamar(srv.porta, "POST", "/api/carga", {"clientes": 3, "produto": "ssd"})
            self.assertEqual(codigo, 200)
            self.assertEqual(r["falhas"], 3)
        finally:
            srv.encerrar()

    def test_loja_desligada_aparece_na_consulta(self):
        amb = apoio.AmbienteTeste(latencias=(0, 0, 0, 0), com_agregador=False)
        lojas = amb.lojas[:3] + [{"nome": "MagaluTechSim", "host": HOST, "porta": apoio.porta_livre()}]
        from agregador import Agregador, criar_servidor_agregador
        srv_agregador = criar_servidor_agregador(Agregador(lojas, timeout_loja=2.0, arquivo_log=None), HOST, 0)
        porta_agregador = srv_agregador.iniciar_em_thread()
        srv = ServidorGatewayTeste(Gateway(lojas=lojas, porta_agregador=porta_agregador, diretorio_estatico=None))
        try:
            codigo, r, _ = chamar(srv.porta, "POST", "/api/consultar", {"produto": "rtx 4060"})
            self.assertEqual(codigo, 200)
            self.assertEqual(r["total_lojas_responderam"], 3)
            self.assertEqual(r["ocorrencias_ou_falhas"][0]["fonte"], "MagaluTechSim")
            _, r, _ = chamar(srv.porta, "GET", "/api/lojas")
            self.assertEqual([loja["online"] for loja in r["lojas"]], [True, True, True, False])
        finally:
            srv.encerrar()
            srv_agregador.encerrar()
            amb.encerrar()


class TestGatewayInterfaceCompilada(unittest.TestCase):
    """Com frontend/dist, o gateway também entrega a interface (rotas fora de /api)."""

    def setUp(self):
        self.dist = tempfile.mkdtemp(prefix="dist_teste_")
        os.makedirs(os.path.join(self.dist, "assets"))
        with open(os.path.join(self.dist, "index.html"), "w", encoding="utf-8") as f:
            f.write("<!doctype html><title>interface</title>")
        with open(os.path.join(self.dist, "assets", "app.js"), "w", encoding="utf-8") as f:
            f.write("console.log('ok')")
        self.srv = ServidorGatewayTeste(Gateway(lojas=[], porta_agregador=apoio.porta_livre(),
                                                diretorio_estatico=self.dist))

    def tearDown(self):
        self.srv.encerrar()
        shutil.rmtree(self.dist, ignore_errors=True)

    def test_serve_index_e_arquivos(self):
        codigo, conteudo, tipo = chamar(self.srv.porta, "GET", "/")
        self.assertEqual(codigo, 200)
        self.assertTrue(tipo.startswith("text/html"))
        self.assertIn(b"interface", conteudo)
        codigo, conteudo, _ = chamar(self.srv.porta, "GET", "/assets/app.js")
        self.assertEqual((codigo, conteudo), (200, b"console.log('ok')"))

    def test_rota_desconhecida_cai_no_index_e_nao_sai_do_diretorio(self):
        for rota in ("/lojas", "/../config.py", "/%2e%2e/config.py"):
            with self.subTest(rota=rota):
                codigo, conteudo, _ = chamar(self.srv.porta, "GET", rota)
                self.assertEqual(codigo, 200)
                self.assertIn(b"interface", conteudo)

    def test_sem_build_responde_404_amigavel(self):
        srv = ServidorGatewayTeste(Gateway(lojas=[], diretorio_estatico=None))
        try:
            codigo, r, _ = chamar(srv.porta, "GET", "/")
            self.assertEqual(codigo, 404)
            self.assertIn("npm run", r["detalhe"])
        finally:
            srv.encerrar()


class TestGatewayGerenciaProcessos(unittest.TestCase):
    """Com um Ambiente, o gateway derruba e sobe lojas que são processos reais (portas livres)."""

    def test_derrubar_e_subir_loja(self):
        loja = {"nome": "KabumSim", "host": HOST, "porta": apoio.porta_livre()}
        amb = Ambiente(latencias=[0], saida=subprocess.DEVNULL, lojas=[loja])
        srv = None
        try:
            amb.subir_loja(loja, 0)
            srv = ServidorGatewayTeste(Gateway(ambiente=amb, porta_agregador=apoio.porta_livre(),
                                               diretorio_estatico=None))
            _, r, _ = chamar(srv.porta, "GET", "/api/saude")
            self.assertTrue(r["gerencia_processos"])

            codigo, r, _ = chamar(srv.porta, "POST", "/api/lojas/KabumSim/derrubar")
            self.assertEqual(codigo, 200)
            self.assertFalse(r["online"])
            with self.assertRaises(ConnectionRefusedError):
                protocolo.requisitar(HOST, loja["porta"], {"operacao": "ping"}, 1)

            codigo, _, _ = chamar(srv.porta, "POST", "/api/lojas/KabumSim/derrubar")
            self.assertEqual(codigo, 409)  # já está fora do ar

            codigo, r, _ = chamar(srv.porta, "POST", "/api/lojas/KabumSim/subir")
            self.assertEqual(codigo, 200)
            self.assertTrue(r["online"])
            self.assertEqual(protocolo.requisitar(HOST, loja["porta"], {"operacao": "ping"}, 2)["status"],
                             protocolo.STATUS_SUCESSO)

            codigo, _, _ = chamar(srv.porta, "POST", "/api/lojas/KabumSim/subir")
            self.assertEqual(codigo, 409)  # já está no ar

            codigo, _, _ = chamar(srv.porta, "POST", "/api/lojas/LojaFantasma/derrubar")
            self.assertEqual(codigo, 404)
            codigo, _, _ = chamar(srv.porta, "POST", "/api/lojas/KabumSim/explodir")
            self.assertEqual(codigo, 404)
        finally:
            if srv:
                srv.encerrar()
            amb.encerrar()


if __name__ == "__main__":
    unittest.main()
