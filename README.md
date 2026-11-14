# Trabalho 1 — Sistemas Distribuídos (UNIFESSPA 2026)
## Tema 6: Agregador de Preços de Eletrônicos (sockets TCP + multithreading)

**Grupo VI:** Youri, José Miguel, Mateus Leitão, Michelangelo e Ângelo · Prof. Gleison de Oliveira Medeiros

O cliente pesquisa um eletrônico. O **agregador** (porta 8000) consulta **4 lojas independentes** (processos nas portas 9001–9004) de forma **sequencial** ou **concorrente** (uma thread por loja), consolida as ofertas e aponta o menor preço total e o melhor custo-benefício.

O projeto tem duas partes:

- **`backend/`**: o sistema distribuído em Python (só biblioteca padrão): lojas, agregador, cliente de linha de comando, experimentos e testes.
- **`frontend/`**: interface web (Vite + React + TypeScript) para demonstrar os requisitos no navegador. Ela fala HTTP com um **gateway** (`backend/gateway_http.py`), que é só mais um cliente TCP do agregador.

```
cliente.py ─────────────TCP──┐
                             ▼
navegador ─HTTP─► gateway_http.py :8080 ─TCP─► agregador.py :8000 ──TCP──► KabumSim :9001
 (frontend/)                                    (thread/cliente)    ├─────► PichauSim :9002
                                                                    ├─────► TerabyteSim :9003
                                                                    └─────► MagaluTechSim :9004
```

## Requisitos

- Python **3.10+**. O sistema usa apenas a biblioteca padrão.
- `matplotlib` só para gerar os gráficos e `python-docx` só para regerar os `.docx`. Ficam num ambiente virtual dentro de `backend/`:

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

- Node.js 20+ apenas para a interface web.

## Interface web (demonstração no navegador)

**Terminal 1**: sobe as 4 lojas, o agregador e o gateway HTTP (Ctrl+C encerra tudo):

```bash
python3 backend/gateway_http.py
```

Para latências diferentes por loja: `python3 backend/gateway_http.py --latencias 100,200,300,400`.

**Terminal 2**: a interface (na primeira vez, rode `npm install` dentro de `frontend/`):

```bash
cd frontend && npm install && npm run dev
```

Abra http://localhost:5173. As quatro abas cobrem os requisitos:

| Aba | O que demonstra |
|---|---|
| Pesquisa | produto, modo (sequencial, concorrente ou comparar), critério e latência; menor preço, melhor custo-benefício, speedup, tempo de cada loja (soma × máximo) e tabela de ofertas (RF01–RF11) |
| Lojas e falhas | status de cada loja por `ping`; botões para **derrubar e subir** uma loja e pesquisar de novo (3/4 lojas + motivo da falha) (RF02, RF09, RNF04) |
| Teste de carga | 1 a 50 clientes TCP simultâneos: média, p95, vazão e falhas (RNF03, RNF05) |
| Experimentos e log | tabelas dos CSVs, gráficos g1–g6 e as últimas linhas de `log_pesquisas.csv` (RF08, RF12) |

Se o ambiente já estiver rodando por `iniciar_servicos.py` (ou pelos 6 terminais da demo manual), use `python3 backend/gateway_http.py --externo`: o gateway só se conecta a ele, sem controlar os processos.

Para servir a interface compilada pelo próprio gateway (sem o Vite), rode `npm run build` em `frontend/` e abra http://127.0.0.1:8080.

## Demonstração pela linha de comando

Todos os comandos Python abaixo rodam dentro de `backend/`:

```bash
cd backend
```

**Terminal 1**: sobe as 4 lojas e o agregador (Ctrl+C encerra tudo):

```bash
python3 iniciar_servicos.py
```

Para latências diferentes por loja (útil para mostrar soma × máximo):

```bash
python3 iniciar_servicos.py --latencias 100,200,300,400
```

**Terminal 2**: cliente:

```bash
python3 cliente.py
```

```bash
python3 cliente.py rtx 4060
```

```bash
python3 cliente.py notebook --modo concorrente --criterio custo_beneficio
```

```bash
python3 cliente.py --listar
```

| Opção | Valores | Padrão |
|---|---|---|
| `--modo` | `comparar` (roda os dois e mostra o speedup), `sequencial`, `concorrente` | `comparar` |
| `--criterio` | `preco` (preço + frete), `custo_beneficio` | `preco` |
| `--atraso` | latência artificial em ms aplicada a todas as lojas | a de cada loja (150) |
| `--host`, `--porta` | endereço do agregador | `127.0.0.1`, `8000` |

Produtos do catálogo: `rtx 4060`, `notebook`, `monitor`, `ssd`, `iphone`.

### Demo manual (6 terminais, mostra que cada serviço é um processo)

Em `backend/`:

```bash
python3 loja_server.py KabumSim 9001 150
```

```bash
python3 loja_server.py PichauSim 9002 150
```

```bash
python3 loja_server.py TerabyteSim 9003 150
```

```bash
python3 loja_server.py MagaluTechSim 9004 150
```

```bash
python3 agregador.py
```

```bash
python3 cliente.py
```

Para demonstrar a **falha de serviço**, pressione Ctrl+C no terminal de uma loja e repita a pesquisa. O cliente mostra 3/4 lojas e um `[ALERTA]` com o motivo. Ao subir a loja de novo, ela volta a responder.

## Experimentos (seção 9 do enunciado)

Em `backend/`:

```bash
python3 experimentos.py
```

```bash
.venv/bin/python graficos.py
```

- `experimentos.py` sobe os processos sozinho e roda os 5 experimentos (~3 min; `--rapido` para uma versão curta). Precisa das portas 8000 e 9001–9004 livres (pare o gateway antes).
- Saídas em `backend/resultados/`:
  - `exp*.csv` (dados);
  - `tabelas.md` (tabelas prontas);
  - `g1..g6_*.png` (gráficos);
  - `log_pesquisas.csv` (registro do tempo total e do tempo de cada loja em cada pesquisa feita no agregador).

| Exp. | O que mede |
|---|---|
| 1 e 2 | Sequencial × concorrente, 30 repetições, lojas com 150 ms |
| 3a / 3b | Latência uniforme de 0 a 500 ms; latências diferentes (100/200/300/400 ms) |
| 4 | 1, 5, 10, 20 e 50 clientes simultâneos (tempo de resposta, p95, vazão) |
| 5 | Loja desligada antes, derrubada durante a consulta, lenta além do timeout e recuperada |

## Testes

```bash
cd backend && python3 -m unittest discover -s tests -v
```

São 82 testes: protocolo, ordenação, desempenho, falhas (loja desligada, queda, timeout, resposta inválida), validação, registro em CSV, múltiplos clientes, serviço de loja, gerenciamento de processos, o roteiro da demonstração com processos reais (`tests/test_sistema.py`, pulado se as portas 8000/9001–9004 estiverem ocupadas) e o gateway HTTP da interface (`tests/test_gateway.py`). O plano de verificação e testes está em `docs/05_plano_verificacao_testes.md`.

Na interface, `npm run build` (em `frontend/`) também confere os tipos TypeScript e `npx oxlint src` aponta problemas de código.

## Estrutura

```
agregador_precos_eletronicos/
├── backend/                  # sistema distribuído (Python, biblioteca padrão)
│   ├── protocolo.py          # framing JSON+\n, operações, códigos de status
│   ├── servidor_base.py      # servidor TCP multithread (1 thread por conexão)
│   ├── config.py             # portas, latências e timeouts
│   ├── loja_server.py        # serviço independente de loja
│   ├── agregador.py          # agregador sequencial/concorrente + registro de tempo
│   ├── cliente.py            # interface do usuário (CLI)
│   ├── gateway_http.py       # ponte HTTP -> TCP para a interface web
│   ├── iniciar_servicos.py   # sobe 4 lojas + agregador
│   ├── experimentos.py       # 5 experimentos -> resultados/*.csv
│   ├── graficos.py           # resultados/*.png
│   ├── dados/lojas/*.json    # catálogos simulados
│   ├── tests/                # unittest
│   ├── resultados/           # gerado pelos experimentos
│   ├── requirements.txt      # matplotlib e python-docx (opcionais)
│   └── .venv/                # ambiente virtual (criado na instalação)
├── frontend/                 # interface web (Vite + React + TypeScript)
│   └── src/                  # App.tsx, api.ts, componentes.tsx, formato.ts, estilos.css, telas/
└── docs/                     # requisitos, modelagem, protocolo, relatório, plano de testes (.md/.docx)
```

## Documentação (`docs/`)

- `01_documento_requisitos.md` / `.docx`: problema, escopo, atores, RF/RNF, restrições, casos de uso e critérios de aceitação.
- `02_modelagem.md`: diagramas de casos de uso, arquitetura e sequência (Mermaid + PNG).
- `03_protocolo.md`: protocolo de aplicação (e, no Apêndice A, a API HTTP do gateway).
- `04_relatorio_tecnico.md` / `.docx`: relatório técnico.
- `05_plano_verificacao_testes.md` / `.docx`: conferência item a item com o enunciado, plano de testes, resultados e correções.
- `gerar_docx.py`: regenera os .docx a partir dos .md (`../backend/.venv/bin/python gerar_docx.py`).
- Slides: o deck da apresentação está no Claude Design (https://claude.ai/artifact/Lgii1Psd9TgHD3QbrMmJpz), com visual escuro "rede/terminal" e 19 slides nas 5 partes do enunciado (agenda com tempos e divisão sugerida das falas nas notas; o 13 mostra a interface web). `apresentacao.pptx` é a exportação dele para PowerPoint (basic fonts): depois de editar o deck, exporte de novo (botão de download › PowerPoint) e substitua este arquivo. O deck anterior, de fundo claro, continua em https://claude.ai/artifact/E8msabfUmYRJvqqFxBS1U8 como reserva.
- Design da interface web: canvas no Claude Design (https://claude.ai/artifact/TyEFDuFHtMT7KWniR6aKeY), com a mesma paleta dos slides.
