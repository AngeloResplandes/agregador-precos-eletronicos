#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo: protocolo.py (Protocolo de aplicação comum a cliente, agregador e lojas)

Regras do protocolo (detalhadas em docs/03_protocolo.md):
  * Cada mensagem é um objeto JSON codificado em UTF-8 e terminado por '\\n'.
  * Uma conexão TCP transporta exatamente UMA requisição e UMA resposta;
    depois disso, quem atende fecha a conexão.
  * Toda resposta possui o campo "status".
"""
import json
import socket
import time

from config import ATRASO_MAXIMO_MS, TIMEOUT_PING

TERMINADOR = b"\n"
TAMANHO_MAXIMO_MENSAGEM = 64 * 1024  # 64 KB
TAMANHO_BUFFER = 4096

# Operações
OP_CONSULTAR = "consultar"
OP_LISTAR_PRODUTOS = "listar_produtos"
OP_PING = "ping"

# Modos e critérios aceitos pelo agregador ("comparar" só existe no cliente e na interface)
MODO_SEQUENCIAL = "sequencial"
MODO_CONCORRENTE = "concorrente"
MODOS_VALIDOS = (MODO_SEQUENCIAL, MODO_CONCORRENTE)
MODO_COMPARAR = "comparar"

CRITERIO_PRECO = "preco"
CRITERIO_CUSTO_BENEFICIO = "custo_beneficio"
CRITERIOS_VALIDOS = (CRITERIO_PRECO, CRITERIO_CUSTO_BENEFICIO)

# Códigos de status
STATUS_SUCESSO = "sucesso"
STATUS_NAO_ENCONTRADO = "nao_encontrado"
STATUS_ERRO_REQUISICAO = "erro_requisicao"  # requisição malformada ou inválida
STATUS_ERRO_INTERNO = "erro_interno"  # falha inesperada no servidor
STATUS_ERRO_COMUNICACAO = "erro_comunicacao"  # loja recusou/derrubou a conexão ou respondeu errado
STATUS_TIMEOUT = "timeout"  # loja não respondeu dentro do prazo


class ErroProtocolo(Exception):
    """Classe base dos erros de protocolo."""


class ConexaoEncerrada(ErroProtocolo):
    """O outro lado fechou a conexão antes de enviar uma mensagem completa."""


class MensagemInvalida(ErroProtocolo):
    """A mensagem recebida não é JSON válido, não é objeto ou excede o tamanho máximo."""


# ---------------------------------------------------------------------- framing
def codificar(obj: dict) -> bytes:
    """Serializa um dicionário para o formato de transmissão (JSON UTF-8 + '\\n')."""
    return (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")


def enviar_json(sock: socket.socket, obj: dict) -> None:
    sock.sendall(codificar(obj))


def receber_json(sock: socket.socket, max_bytes: int = TAMANHO_MAXIMO_MENSAGEM) -> dict:
    """
    Lê do socket até o terminador '\\n' e devolve o objeto JSON.
    Lança ConexaoEncerrada, MensagemInvalida ou socket.timeout.
    """
    dados = bytearray()
    while TERMINADOR not in dados:
        bloco = sock.recv(TAMANHO_BUFFER)
        if not bloco:
            raise ConexaoEncerrada("conexão encerrada pelo par antes do fim da mensagem")
        dados.extend(bloco)
        if len(dados) > max_bytes:
            raise MensagemInvalida(f"mensagem excede o limite de {max_bytes} bytes")
    try:
        obj = json.loads(dados.split(TERMINADOR, 1)[0].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MensagemInvalida(f"JSON inválido: {exc}") from exc
    if not isinstance(obj, dict):
        raise MensagemInvalida("a mensagem deve ser um objeto JSON")
    return obj


def requisitar(host: str, porta: int, mensagem: dict, timeout: float) -> dict:
    """Abre uma conexão, envia uma requisição, recebe a resposta e fecha a conexão."""
    with socket.create_connection((host, porta), timeout=timeout) as sock:
        enviar_json(sock, mensagem)
        return receber_json(sock)


def ping(host: str, porta: int, timeout: float = TIMEOUT_PING) -> bool:
    """True se o serviço responder 'ping' com sucesso."""
    try:
        return requisitar(host, porta, {"operacao": OP_PING}, timeout).get("status") == STATUS_SUCESSO
    except (OSError, ErroProtocolo):
        return False


# ---------------------------------------------------------------------- validação e utilitários
def validar_atraso_ms(valor, maximo: int = ATRASO_MAXIMO_MS) -> int:
    """'atraso_ms' deve ser um inteiro JSON entre 0 e `maximo` (bool, fração e texto são recusados)."""
    if isinstance(valor, bool) or not isinstance(valor, int) or not 0 <= valor <= maximo:
        raise ValueError(f"atraso_ms deve ser inteiro entre 0 e {maximo}")
    return valor


def validar_pesquisa(req: dict, modos=MODOS_VALIDOS) -> tuple:
    """
    Valida uma pesquisa (usado pelo agregador e pelo gateway HTTP).
    Devolve (produto, modo, criterio, atraso_ms) ou lança ValueError com o motivo.
    """
    produto = req.get("produto")
    if not isinstance(produto, str) or not produto.strip():
        raise ValueError("campo 'produto' obrigatório e não vazio")
    modo = str(req.get("modo", MODO_CONCORRENTE)).lower()
    if modo not in modos:
        raise ValueError(f"modo inválido: {modo!r}; use {list(modos)}")
    criterio = str(req.get("criterio", CRITERIO_PRECO)).lower()
    if criterio not in CRITERIOS_VALIDOS:
        raise ValueError(f"critério inválido: {criterio!r}; use {list(CRITERIOS_VALIDOS)}")
    atraso_ms = req.get("atraso_ms")
    if atraso_ms is not None:
        validar_atraso_ms(atraso_ms)
    return produto.strip(), modo, criterio, atraso_ms


def resposta_erro(status: str, detalhe: str, **extras) -> dict:
    """Monta uma resposta de erro padronizada."""
    return {"status": status, "detalhe": detalhe, **extras}


def ms_desde(inicio: float) -> float:
    """Milissegundos (2 casas) desde um instante medido com time.perf_counter()."""
    return round((time.perf_counter() - inicio) * 1000.0, 2)
