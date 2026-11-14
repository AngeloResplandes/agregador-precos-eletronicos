#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo: config.py (Configuração central: endereços, portas e timeouts)
"""
import os

DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
DIRETORIO_DADOS = os.path.join(DIRETORIO_BASE, "dados", "lojas")
DIRETORIO_RESULTADOS = os.path.join(DIRETORIO_BASE, "resultados")
ARQUIVO_LOG_PESQUISAS = os.path.join(DIRETORIO_RESULTADOS, "log_pesquisas.csv")
# Build de produção da interface web (frontend/dist), servido pelo gateway se existir
DIRETORIO_FRONTEND_DIST = os.path.join(os.path.dirname(DIRETORIO_BASE), "frontend", "dist")

HOST = "127.0.0.1"

# Agregador
PORTA_AGREGADOR = 8000

# Gateway HTTP da interface web (navegador -> HTTP -> gateway -> TCP -> agregador)
PORTA_GATEWAY = 8080

# Serviços independentes (lojas). "latencia_ms" é o atraso artificial padrão
# de cada loja, usado quando a requisição não informa "atraso_ms".
LOJAS = [
    {"nome": "KabumSim", "host": HOST, "porta": 9001, "latencia_ms": 150},
    {"nome": "PichauSim", "host": HOST, "porta": 9002, "latencia_ms": 150},
    {"nome": "TerabyteSim", "host": HOST, "porta": 9003, "latencia_ms": 150},
    {"nome": "MagaluTechSim", "host": HOST, "porta": 9004, "latencia_ms": 150},
]

# Timeouts (segundos)
TIMEOUT_LOJA = 2.5  # agregador -> loja (conexão + resposta)
TIMEOUT_CLIENTE = 30.0  # cliente -> agregador
TIMEOUT_OCIOSO_SERVIDOR = 5.0  # tempo máximo esperando a requisição de quem conectou

# Limites de entrada
ATRASO_MAXIMO_MS = 10_000

# Gateway HTTP
MAX_CLIENTES_CARGA = 50  # clientes simultâneos aceitos no teste de carga da interface
TAMANHO_MAXIMO_CORPO_HTTP = 64 * 1024  # mesmo limite das mensagens TCP
TIMEOUT_PING = 0.5  # verificação de status de cada loja/agregador (segundos)
LIMITE_PADRAO_LOG = 50
LIMITE_MAXIMO_LOG = 500
