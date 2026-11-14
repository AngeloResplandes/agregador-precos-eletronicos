# Protocolo de Aplicação — Agregador de Preços de Eletrônicos

**UNIFESSPA · FACSI · Sistemas Distribuídos · Trabalho 1 — Tema 6**
Grupo VI: Youri, José Miguel, Mateus Leitão, Michelangelo e Ângelo

Implementação de referência: `backend/protocolo.py`. A API HTTP do gateway da interface web está no Apêndice A.

---

## 1. Visão geral

O sistema tem três tipos de componente, todos se comunicando por **sockets TCP** (IPv4):

| Componente | Papel | Endereço padrão |
|---|---|---|
| Cliente (`cliente.py`) | Envia pesquisas ao agregador | — |
| Agregador (`agregador.py`) | Servidor para o cliente e cliente das lojas | `127.0.0.1:8000` |
| Lojas (`loja_server.py`) | 4 serviços independentes, um processo cada | `127.0.0.1:9001` a `9004` |

Existem dois "trechos" de comunicação que usam o **mesmo formato de mensagem**:

1. **Cliente ↔ Agregador**
2. **Agregador ↔ Loja**

## 2. Formato das mensagens (framing)

- Cada mensagem é **um objeto JSON** codificado em **UTF-8**.
- O fim da mensagem é marcado por um **caractere de nova linha** (`\n`, byte `0x0A`). Como o JSON é serializado em uma única linha, o `\n` nunca aparece dentro da mensagem.
- O receptor lê do socket (`recv`) em blocos de 4096 bytes até encontrar o `\n`. Uma mensagem pode chegar fragmentada em vários segmentos TCP.
- **Tamanho máximo: 64 KB.** Acima disso a mensagem é rejeitada (`MensagemInvalida`).
- Toda **resposta** contém o campo `status` (seção 5).

```
{"operacao": "consultar", "produto": "notebook"}\n
```

## 3. Ciclo de vida da conexão

O protocolo usa **uma requisição por conexão** (sem estado entre conexões):

```
cliente                          servidor
   |------ connect() -------------->|   (servidor cria uma thread para a conexão)
   |------ requisição JSON\n ------>|
   |                                |   processa
   |<----- resposta JSON\n ---------|
   |<----- close() -----------------|   o servidor fecha a conexão após responder
```

- **Quem fecha:** o servidor (agregador ou loja) fecha o socket logo após enviar a resposta. O cliente fecha o seu lado ao terminar a leitura (`with socket...`).
- **Cliente que não envia nada:** se nenhuma requisição completa chegar em `TIMEOUT_OCIOSO_SERVIDOR` (5 s), o servidor responde `erro_requisicao` e fecha a conexão. Assim nenhuma thread fica presa.
- **Cliente que desiste:** se a conexão for fechada antes do `\n`, o servidor apenas encerra a thread.

## 4. Operações

| `operacao` | Aceita por | Descrição |
|---|---|---|
| `consultar` | agregador e lojas | Pesquisa um produto |
| `listar_produtos` | agregador e lojas | Lista o catálogo (o agregador une o de todas as lojas) |
| `ping` | agregador e lojas | Verificação de disponibilidade (usada para saber se o serviço subiu) |

Qualquer outro valor (ou a ausência do campo) gera `erro_requisicao`.

### 4.1 Cliente → Agregador: `consultar`

| Campo | Tipo | Obrigatório | Valores / padrão |
|---|---|---|---|
| `operacao` | string | sim | `"consultar"` |
| `produto` | string | sim | termo de busca, não vazio (ex.: `"rtx 4060"`) |
| `modo` | string | não | `"sequencial"` ou `"concorrente"` (padrão: `concorrente`) |
| `criterio` | string | não | `"preco"` ou `"custo_beneficio"` (padrão: `preco`) |
| `atraso_ms` | inteiro | não | 0–10000. Latência artificial repassada às lojas. Se ausente, cada loja usa a sua latência base. Precisa ser um inteiro JSON: `true`, `1.5` ou `"50"` são recusados |

```json
{"operacao": "consultar", "produto": "rtx 4060", "modo": "concorrente", "criterio": "preco"}
```

**Resposta (sucesso):**

```json
{
  "status": "sucesso",
  "produto_pesquisado": "rtx 4060",
  "modo_execucao": "concorrente",
  "criterio_ordenacao": "preco",
  "tempo_total_ms": 156.17,
  "tempos_lojas_ms": {"KabumSim": 154.02, "PichauSim": 153.63, "TerabyteSim": 153.74, "MagaluTechSim": 0.8},
  "total_lojas_consultadas": 4,
  "total_lojas_responderam": 3,
  "total_ofertas": 3,
  "menor_preco": { "...": "oferta com menor preco_total" },
  "melhor_custo_beneficio": { "...": "oferta com maior score_custo_beneficio" },
  "ofertas_ordenadas": [
    {
      "fonte": "PichauSim",
      "produto": "GPU Galax GeForce RTX 4060 1-Click OC",
      "specs": "8GB GDDR6, DLSS3, Dual Fan",
      "preco": 1829.0, "frete": 35.0, "preco_total": 1864.0,
      "avaliacao": 4.7, "garantia_meses": 24,
      "status": "sucesso",
      "tempo_loja_ms": 153.63,
      "score_custo_beneficio": 14.6951
    }
  ],
  "lojas_sem_produto": [],
  "ocorrencias_ou_falhas": [
    {
      "fonte": "MagaluTechSim", "produto": "rtx 4060", "preco": null, "preco_total": null,
      "status": "erro_comunicacao",
      "detalhe": "ConnectionRefusedError: [Errno 61] Connection refused",
      "tempo_loja_ms": 0.8
    }
  ]
}
```

- `status` vale `sucesso` se houver pelo menos uma oferta e `nao_encontrado` se nenhuma loja tiver o produto (ou todas falharem).
- `tempo_total_ms` é o tempo que o agregador levou para consultar todas as lojas, e `tempos_lojas_ms` o tempo de cada loja, inclusive as que falharam (RF08). Os dois são gravados em `resultados/log_pesquisas.csv`.
- **Falhas parciais não invalidam a pesquisa.** As lojas com problema aparecem em `ocorrencias_ou_falhas` e o resultado é montado com as demais.

### 4.2 Agregador → Loja: `consultar`

```json
{"operacao": "consultar", "produto": "rtx 4060", "atraso_ms": 150}
```

O campo `atraso_ms` só é enviado se o cliente o informou.

**Resposta da loja (produto encontrado):**

```json
{"fonte": "KabumSim", "produto": "GPU ASUS Dual RTX 4060 OC 8GB", "specs": "8GB GDDR6, DLSS3, 2535MHz",
 "preco": 1899.9, "frete": 0.0, "preco_total": 1899.9, "avaliacao": 4.9, "garantia_meses": 36,
 "status": "sucesso"}
```

**Produto não encontrado:**

```json
{"fonte": "KabumSim", "produto": "geladeira", "preco": null, "preco_total": null, "status": "nao_encontrado"}
```

A busca não diferencia maiúsculas de minúsculas e compara o termo com a palavra-chave e com o nome do produto. Se houver mais de um item compatível, a loja devolve o de menor preço total.

### 4.3 `listar_produtos`

```json
{"operacao": "listar_produtos"}
→ {"status": "sucesso", "produtos": ["iphone", "monitor", "notebook", "rtx 4060", "ssd"], "ocorrencias_ou_falhas": []}
```

Uma loja responde `{"fonte": ..., "status": "sucesso", "produtos": [{"chave": ..., "produto": ...}, ...]}`.

### 4.4 `ping`

```json
{"operacao": "ping"}  →  {"status": "sucesso", "operacao": "pong"}
```

## 5. Códigos de status e tratamento de erros

| `status` | Quem gera | Significado |
|---|---|---|
| `sucesso` | todos | Operação concluída |
| `nao_encontrado` | loja / agregador | Produto inexistente no catálogo (ou em todas as lojas) |
| `erro_requisicao` | agregador / loja | JSON inválido, mensagem maior que 64 KB, operação desconhecida, `produto` vazio, `modo`/`criterio`/`atraso_ms` inválido ou tempo ocioso esgotado |
| `erro_interno` | agregador / loja | Exceção inesperada ao processar. O servidor continua no ar |
| `erro_comunicacao` | agregador (por loja) | Loja recusou a conexão (fora do ar), fechou a conexão sem responder (caiu durante a consulta) ou enviou resposta inválida: JSON malformado, ou `sucesso` sem algum campo da oferta (`produto`, `specs`, `preco`, `frete`, `preco_total`, `avaliacao`, `garantia_meses`) ou com tipo errado. A pesquisa continua com as demais lojas |
| `timeout` | agregador (por loja) | A loja não respondeu em `TIMEOUT_LOJA` (2,5 s) |

Mensagens de erro têm o formato `{"status": "<código>", "detalhe": "<descrição legível>"}`.

**Exemplo:**

```json
{"operacao": "consultar", "produto": "ssd", "modo": "paralelo"}
→ {"status": "erro_requisicao", "detalhe": "modo inválido: 'paralelo'; use ['sequencial', 'concorrente']"}
```

**Erros no lado do cliente** (`cliente.py`) são convertidos em mensagens amigáveis, sem *traceback*:
- agregador fora do ar (conexão recusada);
- agregador sem resposta em 30 s;
- conexão encerrada sem resposta;
- resposta inválida.

## 6. Timeouts

| Constante (`config.py`) | Valor | Onde se aplica |
|---|---|---|
| `TIMEOUT_LOJA` | 2,5 s | Agregador: conexão + resposta de cada loja |
| `TIMEOUT_CLIENTE` | 30 s | Cliente: conexão + resposta do agregador |
| `TIMEOUT_OCIOSO_SERVIDOR` | 5 s | Agregador/lojas: espera pela requisição após o `accept()` |

No modo concorrente, o tempo máximo de uma pesquisa fica limitado a aproximadamente `TIMEOUT_LOJA`, independentemente do número de lojas com problema. No modo sequencial, os timeouts se somam.

## 7. Concorrência

- **Servidores** (agregador e lojas): uma thread por conexão aceita (`servidor_base.ServidorTCPMultithread`), o que permite atender vários clientes simultaneamente.
- **Agregador, modo concorrente:** cria uma thread por loja e espera todas com `join()`. Cada thread grava apenas na sua posição de uma lista pré-alocada, então não há disputa.
- O registro em `backend/resultados/log_pesquisas.csv` é protegido por um `threading.Lock`.

## Apêndice A — API HTTP do gateway da interface web

O navegador não abre sockets TCP. Por isso a interface web (`frontend/`) fala **HTTP/JSON** com o gateway
`backend/gateway_http.py` (porta 8080), e o gateway age como mais um **cliente TCP** do agregador: cada
pesquisa vira uma requisição `consultar` deste protocolo, enviada por `cliente.requisitar_agregador`. O agregador
e as lojas não mudam e não sabem se o pedido veio da CLI ou do navegador.

```
navegador ──HTTP/JSON──► gateway_http.py :8080 ──TCP (JSON + \n)──► agregador.py :8000 ──TCP──► lojas :9001–9004
```

Em desenvolvimento, o Vite (`npm run dev`, porta 5173) repassa `/api/*` ao gateway. Se existir `frontend/dist`
(`npm run build`), o próprio gateway também entrega a interface em `http://127.0.0.1:8080/`.

| Método e rota | Corpo / parâmetros | Resposta 200 |
|---|---|---|
| `GET /api/saude` | — | `{agregador_online, agregador, gerencia_processos}` (ping TCP no agregador) |
| `GET /api/lojas` | — | `{lojas: [{nome, host, porta, latencia_ms, online}], gerencia_processos}` (ping TCP em cada loja, em paralelo) |
| `POST /api/lojas/<nome>/derrubar` | — | status da loja após encerrar o processo dela |
| `POST /api/lojas/<nome>/subir` | — | status da loja após subir o processo de novo |
| `GET /api/produtos` | — | resposta de `listar_produtos` do agregador |
| `POST /api/consultar` | `{produto, modo, criterio, atraso_ms?}`; `modo` aceita também `comparar` | resposta consolidada do agregador (§4.1); com `comparar`: `{sequencial, concorrente, speedup}` |
| `POST /api/carga` | `{clientes: 1–50, produto, modo, criterio?, atraso_ms?}` | `{clientes, media_ms, desvio_ms, min_ms, max_ms, p95_ms, tempo_total_ms, vazao_req_s, falhas, detalhes_falhas, tempos_ms}` |
| `GET /api/experimentos` | — | `{tabelas: [{arquivo, colunas, linhas}], graficos: [nomes .png]}` lidos de `backend/resultados/` |
| `GET /api/resultados/<g*.png>` | — | a imagem (só arquivos `.png` que existem em `resultados/`) |
| `GET /api/log?limite=N` | `limite` 1–500 (padrão 50) | `{colunas, linhas, total}` de `log_pesquisas.csv`, mais recentes primeiro |

No teste de carga, o gateway cria N threads, cada uma com sua conexão TCP, e as libera juntas com um
`threading.Barrier` (`cliente.disparar_clientes_simultaneos`, a mesma função usada no Experimento 4). A vazão é `N / tempo do lote`.
O gateway valida `produto`, `modo`, `criterio` e `atraso_ms` com a mesma função do agregador (`protocolo.validar_pesquisa`).

**Erros.** O corpo é sempre `{"status": "<código>", "detalhe": "<texto>"}` (via `protocolo.resposta_erro`), nunca um *traceback*:

| HTTP | `status` | Quando |
|---|---|---|
| 400 | `erro_requisicao` | JSON inválido, `produto` vazio, `modo`/`criterio`/`atraso_ms`/`clientes`/`limite` inválidos |
| 404 | `erro_requisicao` | rota, loja ou gráfico inexistente |
| 409 | `erro_requisicao` | derrubar loja já fora do ar, subir loja já no ar, ou gateway iniciado com `--externo` (não controla processos) |
| 413 | `erro_requisicao` | corpo maior que 64 KB |
| 502 | `erro_comunicacao` | agregador fora do ar, sem resposta ou com resposta inválida (mensagem de `cliente.ErroCliente`); se o agregador devolver outro status de erro, ele é repassado |
| 500 | `erro_interno` | exceção inesperada no gateway (registrada no log; o gateway continua no ar) |

`nao_encontrado` não é erro HTTP: volta com 200, como resultado válido da pesquisa.
