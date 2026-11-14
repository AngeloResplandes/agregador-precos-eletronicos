# -*- coding: utf-8 -*-
"""
Testes de sistema: o ambiente da apresentação, com processos reais nas portas fixas de config.py
(agregador 8000, lojas 9001-9004), usando o cliente de linha de comando como o usuário usaria.

São pulados se alguma dessas portas já estiver ocupada (por exemplo, com iniciar_servicos.py aberto).
"""
import os
import signal
import socket
import subprocess
import sys
import time
import unittest

import apoio  # noqa: F401  (ajusta o sys.path)
from config import DIRETORIO_BASE, HOST, LOJAS, PORTA_AGREGADOR
from iniciar_servicos import Ambiente

PORTAS = [PORTA_AGREGADOR] + [loja["porta"] for loja in LOJAS]


def porta_ocupada(porta: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex((HOST, porta)) == 0


def portas_livres() -> bool:
    return not any(porta_ocupada(p) for p in PORTAS)


def aguardar(condicao, prazo_s: float) -> bool:
    limite = time.monotonic() + prazo_s
    while time.monotonic() < limite:
        if condicao():
            return True
        time.sleep(0.1)
    return condicao()


def rodar(script: str, *args, prazo_s: float = 30):
    """Executa um script do projeto como o usuário faria e devolve (código de saída, saída)."""
    proc = subprocess.run([sys.executable, os.path.join(DIRETORIO_BASE, script), *args],
                          cwd=DIRETORIO_BASE, capture_output=True, text=True, timeout=prazo_s)
    return proc.returncode, proc.stdout + proc.stderr


@unittest.skipUnless(portas_livres(), "portas 8000/9001-9004 ocupadas")
class TestDemonstracao(unittest.TestCase):
    """Roteiro da demonstração prática, com 4 lojas e o agregador como processos independentes."""

    @classmethod
    def setUpClass(cls):
        cls.amb = Ambiente(latencias=[50, 50, 50, 50], saida=subprocess.DEVNULL, sem_log=True).subir()

    @classmethod
    def tearDownClass(cls):
        cls.amb.encerrar()

    def test_1_listar_catalogo(self):
        codigo, saida = rodar("cliente.py", "--listar")
        self.assertEqual(codigo, 0)
        self.assertIn("iphone | monitor | notebook | rtx 4060 | ssd", saida)

    def test_2_comparar_sequencial_e_concorrente(self):
        codigo, saida = rodar("cliente.py", "rtx", "4060")
        self.assertEqual(codigo, 0)
        self.assertIn("Lojas que responderam: 4/4", saida)
        self.assertIn("[MENOR PREÇO]            PichauSim", saida)
        self.assertIn("[MELHOR CUSTO-BENEFÍCIO]", saida)
        self.assertIn("Speedup", saida)

    def test_3_custo_beneficio(self):
        codigo, saida = rodar("cliente.py", "notebook", "--modo", "concorrente", "--criterio", "custo_beneficio")
        self.assertEqual(codigo, 0)
        self.assertIn("ORDENAÇÃO: CUSTO_BENEFICIO", saida)

    def test_4_parametro_invalido_nao_gera_traceback(self):
        codigo, saida = rodar("cliente.py", "ssd", "--modo", "concorrente", "--atraso", "-5")
        self.assertIn("erro_requisicao", saida)
        self.assertNotIn("Traceback", saida)

    def test_5_loja_desligada_e_recuperada(self):
        nome = LOJAS[-1]["nome"]
        self.amb.derrubar_loja(nome)
        try:
            codigo, saida = rodar("cliente.py", "ssd", "--modo", "concorrente")
            self.assertEqual(codigo, 0)
            self.assertIn("Lojas que responderam: 3/4", saida)
            self.assertIn(f"[ALERTA] {nome}: erro_comunicacao", saida)
            self.assertNotIn("Traceback", saida)
        finally:
            self.amb.subir_loja(LOJAS[-1], 50)
        codigo, saida = rodar("cliente.py", "ssd", "--modo", "concorrente")
        self.assertIn("Lojas que responderam: 4/4", saida)

    def test_6_segundo_ambiente_com_portas_ocupadas_falha(self):
        proc = subprocess.Popen([sys.executable, os.path.join(DIRETORIO_BASE, "iniciar_servicos.py")],
                                cwd=DIRETORIO_BASE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, start_new_session=True)
        try:
            saida, _ = proc.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            saida, _ = proc.communicate()
            self.fail("iniciar_servicos.py não percebeu as portas ocupadas:\n" + saida)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("em uso", saida)
        self.assertNotIn("Ambiente pronto", saida)


@unittest.skipUnless(portas_livres(), "portas 8000/9001-9004 ocupadas")
class TestEncerramento(unittest.TestCase):
    def test_sigterm_encerra_todos_os_processos(self):
        # fechar o terminal ou dar 'kill' no iniciar_servicos.py não pode deixar lojas órfãs nas portas
        proc = subprocess.Popen([sys.executable, os.path.join(DIRETORIO_BASE, "iniciar_servicos.py"),
                                 "--latencias", "0,0,0,0"], cwd=DIRETORIO_BASE,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            self.assertTrue(aguardar(lambda: all(porta_ocupada(p) for p in PORTAS), 15), "ambiente não subiu")
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=10)
            self.assertTrue(aguardar(portas_livres, 5), "processos órfãos continuam nas portas")
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)  # limpeza garantida, mesmo se o teste falhar
            except ProcessLookupError:
                pass


if __name__ == "__main__":
    unittest.main()
