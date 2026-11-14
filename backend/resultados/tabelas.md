# Resultados dos experimentos

Gerado em 14/11/2026 14:05 — Python 3.15.0, Darwin arm64, 10 CPUs.

### Exp. 1 e 2 - Tempo total da pesquisa (4 lojas, 150 ms cada)

| modo | n | media_ms | desvio_ms | min_ms | max_ms | speedup |
|---|---|---|---|---|---|---|
| sequencial | 30 | 621.11 | 2.52 | 612.83 | 623.64 | 1.0 |
| concorrente | 30 | 156.5 | 0.24 | 156.01 | 156.89 | 3.97 |

### Exp. 3a - Tempo total x latência artificial (igual em todas as lojas)

| latencia_ms | modo | n | media_ms | desvio_ms | min_ms | max_ms | speedup |
|---|---|---|---|---|---|---|---|
| 0 | sequencial | 10 | 0.87 | 0.26 | 0.69 | 1.45 | 1.0 |
| 0 | concorrente | 10 | 0.72 | 0.1 | 0.6 | 0.9 | 1.21 |
| 50 | sequencial | 10 | 219.69 | 1.74 | 217.03 | 222.37 | 1.0 |
| 50 | concorrente | 10 | 56.35 | 0.19 | 55.98 | 56.64 | 3.9 |
| 100 | sequencial | 10 | 419.89 | 3.52 | 413.21 | 424.46 | 1.0 |
| 100 | concorrente | 10 | 106.35 | 0.13 | 106.2 | 106.62 | 3.95 |
| 200 | sequencial | 10 | 820.59 | 1.54 | 818.55 | 823.48 | 1.0 |
| 200 | concorrente | 10 | 206.34 | 0.18 | 206.06 | 206.58 | 3.98 |
| 350 | sequencial | 10 | 1421.23 | 2.76 | 1416.05 | 1423.41 | 1.0 |
| 350 | concorrente | 10 | 356.36 | 0.24 | 355.98 | 356.72 | 3.99 |
| 500 | sequencial | 10 | 2012.21 | 3.6 | 2007.34 | 2016.6 | 1.0 |
| 500 | concorrente | 10 | 506.13 | 0.29 | 505.56 | 506.61 | 3.98 |

### Exp. 3b - Lojas com latências diferentes (100/200/300/400 ms)

| modo | n | media_ms | desvio_ms | min_ms | max_ms | previsto_ms | regra |
|---|---|---|---|---|---|---|---|
| sequencial | 10 | 1020.55 | 3.77 | 1011.83 | 1024.04 | 1000 | soma das latências |
| concorrente | 10 | 405.93 | 1.36 | 402.14 | 406.77 | 400 | maior latência |

### Exp. 4 - Clientes simultâneos (tempo medido no cliente)

| clientes | modo | latencia_media_ms | latencia_p95_ms | latencia_max_ms | tempo_lote_ms | vazao_req_s | falhas |
|---|---|---|---|---|---|---|---|
| 1 | sequencial | 423.07 | 424.33 | 424.44 | 423.27 | 2.36 | 0 |
| 1 | concorrente | 107.39 | 107.59 | 107.61 | 107.55 | 9.3 | 0 |
| 5 | sequencial | 424.31 | 425.8 | 425.89 | 426.07 | 11.74 | 0 |
| 5 | concorrente | 110.23 | 111.25 | 111.58 | 111.11 | 45.0 | 0 |
| 10 | sequencial | 425.69 | 428.36 | 428.5 | 427.7 | 23.38 | 0 |
| 10 | concorrente | 111.7 | 112.63 | 112.69 | 113.28 | 88.28 | 0 |
| 20 | sequencial | 426.08 | 428.8 | 429.4 | 429.27 | 46.59 | 0 |
| 20 | concorrente | 114.59 | 117.77 | 118.35 | 118.39 | 168.93 | 0 |
| 50 | sequencial | 431.34 | 435.76 | 437.14 | 438.25 | 114.09 | 0 |
| 50 | concorrente | 122.57 | 132.09 | 133.73 | 134.57 | 371.56 | 0 |

### Exp. 5 - Comportamento diante da indisponibilidade de uma loja

| cenario | modo | tempo_total_ms | lojas_ok | status_loja_afetada | detalhe | menor_preco |
|---|---|---|---|---|---|---|
| 0) todas as lojas ativas | sequencial | 618.95 | 4/4 | sucesso | - | PichauSim |
| 0) todas as lojas ativas | concorrente | 156.23 | 4/4 | sucesso | - | PichauSim |
| a) loja desligada antes | sequencial | 465.06 | 3/4 | erro_comunicacao | ConnectionRefusedError | PichauSim |
| a) loja desligada antes | concorrente | 156.59 | 3/4 | erro_comunicacao | ConnectionRefusedError | PichauSim |
| b) loja derrubada durante | concorrente | 307.69 | 3/4 | erro_comunicacao | ConexaoEncerrada | PichauSim |
| b) loja derrubada durante | sequencial | 757.82 | 3/4 | erro_comunicacao | ConexaoEncerrada | PichauSim |
| c) loja lenta (timeout) | sequencial | 2964.3 | 3/4 | timeout | TimeoutError | PichauSim |
| c) loja lenta (timeout) | concorrente | 2502.33 | 3/4 | timeout | TimeoutError | PichauSim |
| d) loja recuperada | sequencial | 623.37 | 4/4 | sucesso | - | PichauSim |
| d) loja recuperada | concorrente | 156.74 | 4/4 | sucesso | - | PichauSim |
