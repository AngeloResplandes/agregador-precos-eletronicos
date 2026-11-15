# Plano de Verificação e Testes — Agregador de Preços de Eletrônicos

**UNIFESSPA · FACSI · Sistemas Distribuídos · Trabalho 1 — Tema 6**
Grupo VI: Youri, José Miguel, Mateus Leitão, Michelangelo e Ângelo
Versão 1.2 — 14 de novembro de 2026 (código enxugado em `backend/` e `frontend/` sem mudar o comportamento; plano de testes da seção 3.8 executado)

---

## 1. Objetivo

Este documento confere o projeto com o enunciado (`TRABALHO EM grupo SD2026.pdf`) em duas partes:

- **Plano de verificação** (seção 2): para cada exigência do enunciado, onde ela é atendida no projeto e como isso foi conferido.
- **Plano de testes** (seção 3): os casos de teste que mostram que o sistema funciona como o enunciado pede, em quatro níveis (unidade, integração, sistema e experimentos).

As seções 4 e 5 registram a execução de 14/11/2026, as não conformidades encontradas e as correções feitas. A seção 3.8 é o plano de testes completo da versão 1.2 (backend e interface), executado depois da simplificação do código.

Legenda de situação: **OK** atendido · **CORRIGIDO** não atendia e foi corrigido · **PENDENTE** depende de ação do grupo.

## 2. Plano de verificação (enunciado × projeto)

### 2.1 Organização e tema (seções 3 e 4 do enunciado)

| # | Exigência | Onde é atendida | Como foi verificado | Situação |
|---|---|---|---|---|
| V01 | Comunicação real por sockets TCP; não vale simular | `protocolo.py` (`socket.create_connection`, `sendall`, `recv`), `servidor_base.py` | Leitura do código; CT29–CT34 com processos reais | OK |
| V02 | Tema 6: pesquisa de produtos | `cliente.py` (argumentos e menu), operação `consultar` | CT30, CT31 | OK |
| V03 | Consulta a diferentes lojas independentes | 4 processos `loja_server.py` (9001–9004) | CT27, CT29 | OK |
| V04 | Apresentação dos preços | `cliente.exibir_relatorio` (preço, frete, total) | CT31 | OK |
| V05 | Ordenação por preço | `Agregador.executar_busca` (por `preco_total`) | CT08 | OK |
| V06 | Identificação da loja com menor preço | campo `menor_preco`, linha `[MENOR PREÇO]` | CT08, CT31 | OK |
| V07 | Comparação entre consultas sequenciais e concorrentes | `--modo comparar` (speedup); experimentos 1–3 | CT31, CT37–CT39 | OK |
| V08 | Dados simulados | `dados/lojas/*.json` | Leitura dos catálogos | OK |
| V09 | Evolução: características técnicas, avaliações e custo-benefício | `specs`, `avaliacao`, `garantia_meses`, `score_custo_beneficio`, `--criterio custo_beneficio` | CT09, CT32 | OK |

### 2.2 Engenharia de software (seção 5)

| # | Exigência | Onde é atendida | Situação |
|---|---|---|---|
| V10 | Descrição do problema, objetivo, escopo, atores, RF, RNF, restrições, critérios de aceitação | `01_documento_requisitos.md`, seções 1–9 | OK |
| V11 | Pelo menos 8 requisitos funcionais | RF01–RF08 (8), um para cada exemplo da seção 5.2, adaptados ao tema | **CORRIGIDO** (NC09) |
| V12 | Pelo menos 5 requisitos não funcionais | RNF01–RNF05 (5), um para cada exemplo da seção 5.3 | **CORRIGIDO** (NC08, NC09) |
| V13 | Diagrama de casos de uso UML | `02_modelagem.md` §1, `img/casos_de_uso.png` (notação UML: atores, fronteira do sistema, «include»/«extend»; fonte `diagramas/casos_de_uso.svg`) | **CORRIGIDO** (NC08) |
| V14 | Diagrama de arquitetura | `02_modelagem.md` §2, `img/arquitetura.png` | OK |
| V15 | Diagrama de sequência de uma operação principal | `02_modelagem.md` §3, `img/sequencia_pesquisa.png` | OK |

### 2.3 Arquitetura e requisitos técnicos (seções 6 e 7)

| # | Exigência | Onde é atendida | Como foi verificado | Situação |
|---|---|---|---|---|
| V16 | Componentes cliente, agregador e ≥ 4 serviços independentes, cada um em processo próprio e porta distinta | `cliente.py`, `agregador.py` (8000), `loja_server.py` (9001–9004), `iniciar_servicos.py` | CT27–CT29 | OK |
| V17 | Agregador consulta sequencialmente ou simultaneamente | `Agregador.consultar_todas` | CT10, CT11 | OK |
| V18 | RT1 — sockets TCP | ver V01 | — | OK |
| V19 | RT2 — ≥ 4 serviços independentes | ver V16 | — | OK |
| V20 | RT3 — consultas sequenciais | `MODO_SEQUENCIAL` | CT10 | OK |
| V21 | RT4 — consultas concorrentes com threads | uma `threading.Thread` por loja + `join()` | CT11, CT12 | OK |
| V22 | RT5 — múltiplos clientes | `ServidorTCPMultithread` (uma thread por conexão) | CT24, CT40 | OK |
| V23 | RT6 — protocolo definido e documentado | `protocolo.py`, `03_protocolo.md` | CT01–CT07 | OK |
| V24 | RT7 — tratamento de erros e desconexões | `servidor_base.py`, `Agregador.consultar_loja`, `cliente._requisitar` | CT13–CT20, CT25–CT26 | **CORRIGIDO** (NC01, NC02) |
| V25 | RT8 — registro do tempo de execução | `RegistroPesquisas` → `resultados/log_pesquisas.csv` | CT21–CT23 | **CORRIGIDO** (NC05) |
| V26 | RT9 — consolidar e apresentar resultados | `executar_busca`, `exibir_relatorio` | CT08, CT31 | OK |
| V27 | RT10 — demonstrar durante a apresentação | `iniciar_servicos.py` + `cliente.py`; roteiro no README | CT29–CT35 | **CORRIGIDO** (NC03, NC04) |

### 2.4 Protocolo (seção 8)

| # | Exigência | Onde é atendida | Situação |
|---|---|---|---|
| V28 | Mensagens JSON por sockets TCP (formato como o exemplo `operacao`/`produto` → `fonte`/`produto`/`preco`/`status`) | `03_protocolo.md` §2 e §4.2 | OK |
| V29 | Documentar formato das mensagens | `03_protocolo.md` §2 | OK |
| V30 | Documentar identificação das operações | `03_protocolo.md` §4 | OK |
| V31 | Documentar tratamento de erros | `03_protocolo.md` §5 | OK |
| V32 | Documentar encerramento das conexões | `03_protocolo.md` §3 | OK |

### 2.5 Experimentos e resultados (seção 9)

| # | Exigência | Onde é atendida | Como foi verificado | Situação |
|---|---|---|---|---|
| V33 | Exp. 1 — sequencial, tempo total | `experimentos_1_e_2`, `exp1_2_*.csv` | CT37 | OK |
| V34 | Exp. 2 — concorrente com threads, tempo total | idem | CT37 | OK |
| V35 | Exp. 3 — atrasos artificiais | `experimento_3a` (0–500 ms) e `experimento_3b` (100/200/300/400 ms) | CT38, CT39 | OK |
| V36 | Exp. 4 — múltiplos clientes simultâneos | `experimento_4` (1–50 clientes) | CT40 | OK |
| V37 | Exp. 5 — desativar um serviço durante a pesquisa | `experimento_5` (cenários a–d, inclusive queda durante a consulta) | CT41 | OK |
| V38 | Tabelas de resultados | `resultados/tabelas.md`, relatório §6 | Leitura | OK |
| V39 | Pelo menos dois gráficos | `g1`–`g6` (6 gráficos) | CT42 | OK |
| V40 | Comparação, discussão e conclusões sobre multithreading | relatório §6–§8 | Leitura | OK |

### 2.6 Entregáveis e apresentação (seções 10 e 11)

| # | Exigência | Onde é atendida | Situação |
|---|---|---|---|
| V41 | Documento de requisitos (análise, requisitos, atores, casos de uso, critérios de aceitação) | `01_documento_requisitos.md/.docx` | OK |
| V42 | Modelagem (casos de uso, arquitetura, sequência) | `02_modelagem.md/.docx` | OK |
| V43 | Código-fonte completo e instruções de execução | `backend/` (sistema), `frontend/` (interface web) + `README.md` | OK |
| V44 | Relatório técnico (introdução, requisitos, modelagem, implementação, experimentos, resultados, conclusão) | `04_relatorio_tecnico.md/.docx` | OK |
| V45 | Slides | deck no Claude Design (20 slides, com o slide "Análise de requisitos" (escopo, atores, restrições e critérios), nas 5 partes sugeridas pelo enunciado, com agenda e tempos, interface web e gráficos com os números de `resultados/`), exportado para `docs/apresentacao.pptx` | OK |
| V46 | Demonstração prática (5 min) | roteiro da seção 3.5, um passo por experimento da seção 9 (Exp. 1–5), e slide 13 do deck (roteiro) | **CORRIGIDO** (NC07) |
| V47 | Referências | relatório, seção Referências | OK |

## 3. Plano de testes

### 3.1 Estratégia

| Nível | O que cobre | Onde | Como roda |
|---|---|---|---|
| Unidade | framing do protocolo, regras da loja, score, validação | `test_protocolo.py`, `test_servicos.py` (`TestLoja`), `test_agregador.py` | `unittest`, sem rede ou com `socketpair` |
| Integração | cliente → agregador → lojas por TCP real, em threads e portas efêmeras | `test_agregador.py`, `test_integracao.py` | `unittest`; não depende das portas fixas |
| Sistema | processos reais nas portas da apresentação, usando o `cliente.py` como o usuário | `test_servicos.py` (`TestAmbiente`), `test_sistema.py` | `unittest`; `test_sistema.py` é pulado se as portas 8000/9001–9004 estiverem ocupadas |
| Gateway HTTP (interface web) | pesquisa, comparação, validação, falhas, carga, derrubar/subir loja, arquivos servidos | `test_gateway.py` | `unittest`, gateway em thread e portas efêmeras; derrubar/subir com processos reais |
| Interface web | as 4 telas no navegador | `frontend/` | `npm run build` (tipos), `npx oxlint src`, comparação automática do HTML e dos estilos com a versão anterior e roteiro no navegador (seções 3.7 e 3.8) |
| Desempenho e falhas | os 5 experimentos do enunciado | `experimentos.py`, `graficos.py` | manual, `--rapido` para conferência |

Comando único para os níveis automatizados (o código Python fica em `backend/`):

```bash
cd backend && python3 -m unittest discover -s tests -v
```

### 3.2 Casos de teste — protocolo (unidade)

| ID | Caso | Resultado esperado | Teste automatizado | Req. |
|---|---|---|---|---|
| CT01 | Mensagem com acentos ida e volta | objeto igual | `test_ida_e_volta_com_acentos` | RNF01 |
| CT02 | Mensagem fragmentada em vários `send` | remontada até o `\n` | `test_mensagem_fragmentada` | RNF01 |
| CT03 | JSON inválido | `MensagemInvalida` | `test_json_invalido` | RNF04 |
| CT04 | JSON que não é objeto | `MensagemInvalida` | `test_json_que_nao_e_objeto` | RNF01 |
| CT05 | Mensagem > 64 KB | `MensagemInvalida` | `test_mensagem_grande_demais` | RNF01 |
| CT06 | Conexão fechada sem `\n` | `ConexaoEncerrada` | `test_conexao_encerrada_sem_terminador` | RNF04 |
| CT07 | Par não envia nada | `socket.timeout` | `test_timeout_sem_dados` | RNF04 |

### 3.3 Casos de teste — consolidação, desempenho e falhas (integração)

| ID | Caso | Resultado esperado | Teste automatizado | Req. |
|---|---|---|---|---|
| CT08 | "rtx 4060", critério preço | 4 ofertas em ordem crescente de preço total; menor preço PichauSim R$ 1.864,00 | `test_ordena_por_preco_e_identifica_menor` | RF06, RF07 / CA01 |
| CT09 | Critério custo-benefício | ordem decrescente de score | `test_ordena_por_custo_beneficio`, `test_score_custo_beneficio` | RF06 / CA02 |
| CT10 | Mesma pesquisa nos dois modos | mesmo resultado e mesma ordem | `test_sequencial_e_concorrente_dao_mesmo_resultado` | RF03, RF04 / CA03 |
| CT11 | 4 lojas × 100 ms | sequencial ≥ 400 ms, concorrente < 250 ms, speedup > 2,5 | `test_concorrente_mais_rapido_que_sequencial` | RNF02 / CA04 |
| CT12 | Latências 50/100/150/200 ms | sequencial ≈ soma; concorrente ≈ máximo | `test_latencia_heterogenea` | RNF02 / CA05 |
| CT13 | Loja desligada | 3 ofertas; `erro_comunicacao` | `test_loja_desligada` | RNF04 / CA07 |
| CT14 | Loja cai durante a consulta | 3 ofertas; `ConexaoEncerrada` sem esperar o timeout | `test_loja_cai_durante_a_consulta` | RNF04 / CA08 |
| CT15 | Loja mais lenta que o timeout | `timeout`; pesquisa limitada pelo timeout | `test_loja_lenta_gera_timeout` | RNF04 / CA09 |
| CT16 | Todas as lojas fora | `nao_encontrado` com 4 falhas | `test_todas_as_lojas_fora` | RNF04 |
| CT17 | Loja responde `sucesso` sem campos da oferta | `erro_comunicacao` para ela; 3 ofertas nos dois critérios | `test_loja_com_resposta_incompleta` | RNF04 / CA13 |
| CT18 | Loja responde preço em texto | `erro_comunicacao`; 3 ofertas | `test_loja_com_preco_nao_numerico` | RNF04 / CA13 |
| CT19 | `listar_produtos` com loja de resposta malformada | catálogo das outras lojas + falha registrada | `test_listar_com_loja_de_resposta_invalida` | RF01 |
| CT20 | Requisições inválidas (operação, produto vazio ou não texto, modo, critério, `atraso_ms` negativo, acima de 10000, booleano, fracionário ou texto) | `erro_requisicao` | `test_requisicoes_invalidas` (agregador e loja) | CA10 |
| CT21 | Registro em CSV | cabeçalho + uma linha por pesquisa | `test_registra_tempo_em_csv` | RF08 / CA11 |
| CT22 | Tempo de cada loja no CSV | coluna `tempos_lojas_ms` com as 4 lojas | `test_registra_tempo_de_cada_loja` | RF08 / CA11 |
| CT23 | Validação de pesquisa compartilhada por agregador e gateway (`protocolo.validar_pesquisa`) | normaliza produto, modo e critério; recusa produto vazio, modo/critério inválido e `atraso_ms` fora do padrão; `comparar` só quando o chamador permite | `test_validar_pesquisa_normaliza`, `test_validar_pesquisa_recusa`, `test_validar_pesquisa_com_modos_extras` | CA10 |
| CT24 | 20 clientes simultâneos | 20 respostas completas | `test_multiplos_clientes_simultaneos` | RNF03 / CA06 |
| CT25 | Cliente conecta e não envia nada | `erro_requisicao` após 5 s; servidor segue | `test_cliente_ocioso_e_desconectado` | RNF04 |
| CT26 | Exceção no tratamento | `erro_interno`; próxima requisição atendida | `test_erro_interno_nao_derruba_servidor` | RNF04 / CA10 |
| CT54 | `protocolo.ping` | `True` com o serviço no ar; `False` com a porta sem serviço | `test_ping` (`TestValidacaoEPing`) | RNF04 |
| CT55 | `cliente.comparar` (usado pela CLI e pelo gateway) | os dois modos na resposta e speedup > 1,5 | `test_comparar_os_dois_modos` | RF08 |
| CT56 | `cliente.disparar_clientes_simultaneos` com 10 clientes (usado pelo gateway e pelo Exp. 4) | 10 tempos e nenhuma falha | `test_disparar_clientes_simultaneos` | RNF03 |
| CT57 | O mesmo com o agregador fora do ar | todos os clientes com o motivo da falha, sem exceção | `test_clientes_simultaneos_com_agregador_fora` | RNF04 |
| CT58 | `iniciar_servicos.ler_latencias` (opção `--latencias` do gateway e do `iniciar_servicos.py`) | `"100,200,300,400"` vira lista; quantidade errada ou texto → erro do argparse | `test_ler_latencias` | RT2 |
| CT67 | `cliente.executar` no modo comparar | imprime o relatório completo do sequencial, depois o do concorrente e por fim o comparativo com o speedup | `test_comparar_imprime_relatorio_dos_dois_modos` | RF08 |
| CT68 | `cliente.py <produto> --clientes N` (Exp. 4 pelo terminal) | um lote de N clientes simultâneos por modo (só o escolhido, ou os dois em `comparar`), com tempo do lote, média/mín/máx, vazão e `Falhas: 0/N`; N fora de 1–50 ou não inteiro → erro do argparse | `test_cli_multiplos_clientes`, `test_cli_multiplos_clientes_compara_os_dois_modos`, `test_cli_clientes_fora_do_limite` | RNF03 / CA06 |

Também ficam neste nível: `test_produto_inexistente`, `test_listar_produtos`, `test_ping`, `test_pesquisa_via_cliente`, `test_atraso_informado_pelo_cliente`, `test_listar`, `test_json_malformado_recebe_erro`, `test_agregador_fora_do_ar` (CA12) e os testes de `TestLoja` (busca por chave e por nome, item mais barato, listar, ping, validação).

### 3.4 Casos de teste — sistema (processos reais)

| ID | Caso | Resultado esperado | Teste automatizado | Req. |
|---|---|---|---|---|
| CT27 | Subir e derrubar uma loja como processo | responde; depois recusa conexão | `test_sobe_e_derruba_loja_como_processo` | RT2 |
| CT28 | Subir loja em porta já ocupada | `RuntimeError` "em uso" | `test_porta_ocupada_e_detectada` | CA14 |
| CT29 | Falha no meio da subida | o que já subiu é encerrado | `test_falha_ao_subir_encerra_o_que_ja_tinha_subido` | CA14 |
| CT30 | `cliente.py --listar` | as 5 chaves do catálogo | `test_1_listar_catalogo` | RF01 / CA15 |
| CT31 | `cliente.py rtx 4060` (modo comparar) | relatórios dos dois modos (sequencial e concorrente), 4/4 lojas, menor preço PichauSim, melhor custo-benefício, speedup | `test_2_comparar_sequencial_e_concorrente` | RF05–RF07, RF08 |
| CT32 | `--criterio custo_beneficio` | ordenação por custo-benefício | `test_3_custo_beneficio` | RF06 |
| CT33 | `--atraso -5` | `erro_requisicao`, sem traceback | `test_4_parametro_invalido_nao_gera_traceback` | RNF04 |
| CT34 | Loja desligada e religada | 3/4 com `[ALERTA]`; depois 4/4 | `test_5_loja_desligada_e_recuperada` | RNF04 / CA07 |
| CT35 | Segundo `iniciar_servicos.py` com o primeiro aberto | código 1, mensagem "em uso", sem "Ambiente pronto" | `test_6_segundo_ambiente_com_portas_ocupadas_falha` | CA14 |
| CT36 | SIGTERM no `iniciar_servicos.py` | todas as portas liberadas | `test_sigterm_encerra_todos_os_processos` | CA14 |
| CT69 | Console do `iniciar_servicos.py`: `derrubar <loja>`, `subir <loja>`, `status`, `ajuda` | derruba e sobe a loja (processo real, latência original), sem diferenciar maiúsculas; ação repetida, loja inexistente ou comando desconhecido → `[!]`, sem exceção | `test_console_derruba_e_sobe_loja`, `test_console_comandos_invalidos` | RNF04 / CA15 |
| CT70 | Exp. 4 pela CLI com processos reais: `cliente.py rtx 4060 --clientes 10` | dois lotes (sequencial e concorrente) com `Falhas: 0/10` | `test_7_exp4_multiplos_clientes` | RNF03 / CA15 |
| CT71 | Exp. 5 pela CLI: loja derrubada pelo console **durante** `cliente.py ssd --modo sequencial --atraso 1500` | a pesquisa conclui com 3/4 e `[ALERTA] MagaluTechSim: erro_comunicacao`, sem traceback; depois de `subir`, 4/4 | `test_8_exp5_loja_derrubada_durante_a_pesquisa` | RNF04 / CA08 / CA15 |

### 3.5 Roteiro manual da demonstração (apresentação, ~5 min)

O roteiro segue os cinco experimentos obrigatórios da seção 9 do enunciado, na mesma ordem, cada um com um comando
real no terminal (é o mesmo do slide do roteiro no deck, o 13º). Todos os comandos rodam em `backend/`.

| Passo | Terminal | Comando | O que mostrar |
|---|---|---|---|
| 0 | 1 | `cd backend && python3 iniciar_servicos.py` | 4 lojas (150 ms cada) e o agregador como processos separados; o terminal fica aceitando comandos (`status`, `derrubar`, `subir`) |
| Exp. 1 | 2 | `python3 cliente.py rtx 4060 --modo sequencial` | uma loja após a outra: tempo total ≈ 600 ms (soma), tempo de cada loja; a pesquisa é registrada em `resultados/log_pesquisas.csv` |
| Exp. 2 | 2 | `python3 cliente.py rtx 4060 --modo concorrente` | uma thread por loja: ≈ 150 ms (a maior latência), mesmo resultado (PichauSim, R$ 1.864,00) |
| Exp. 3 | 2 | `python3 cliente.py rtx 4060 --atraso 500` | atraso artificial de 500 ms em todas as lojas, os dois modos e o comparativo: ≈ 2.000 × ≈ 500 ms, speedup ≈ 4× |
| Exp. 4 | 2 | `python3 cliente.py rtx 4060 --clientes 20` | 20 clientes TCP simultâneos em cada modo: tempo do lote, média/máx por cliente, vazão e `Falhas: 0/20` |
| Exp. 5 | 2 e 1 | `python3 cliente.py ssd --modo sequencial --atraso 2000` e, enquanto ela roda (≈ 8 s), no terminal 1: `derrubar MagaluTechSim` | a pesquisa termina com 3/4 lojas e `[ALERTA] MagaluTechSim: erro_comunicacao`, sem traceback; `subir MagaluTechSim` e repetir → 4/4 sem reiniciar o agregador |

Variações, se houver tempo: `python3 iniciar_servicos.py --latencias 100,200,300,400` (Exp. 3 com latências
diferentes: soma × máximo), `--criterio custo_beneficio` e `python3 cliente.py ssd --atraso -5` (erro tratado).

### 3.6 Experimentos (desempenho e falhas)

| ID | Caso | Resultado esperado | Como rodar |
|---|---|---|---|
| CT37 | Exp. 1 e 2 | concorrente ≈ 1 latência; sequencial ≈ 4; speedup próximo de 4 | `python3 experimentos.py` |
| CT38 | Exp. 3a | sequencial cresce ≈ 4 × latência, concorrente ≈ 1 × | idem |
| CT39 | Exp. 3b | sequencial ≈ 1.000 ms (soma), concorrente ≈ 400 ms (máximo) | idem |
| CT40 | Exp. 4 | 0 falhas até 50 clientes; vazão crescente | idem |
| CT41 | Exp. 5 | pesquisa sempre conclui com 3/4; status correto por cenário; recuperação | idem |
| CT42 | Gráficos | `g1`–`g6` gerados | `.venv/bin/python graficos.py` (em `backend/`) |

### 3.7 Casos de teste — gateway HTTP e interface web

| ID | Caso | Resultado esperado | Teste automatizado | Req. |
|---|---|---|---|---|
| CT43 | `POST /api/consultar` "rtx 4060" | 200; menor preço PichauSim R$ 1.864,00 | `test_consulta_concorrente` | RF01 / CA16 |
| CT44 | Modo `comparar` | 200 com `sequencial`, `concorrente` e `speedup` > 1,5 | `test_comparar_devolve_os_dois_modos_e_speedup` | RF08 / CA16 |
| CT45 | Produto vazio, modo/critério/`atraso_ms` inválidos, JSON malformado | 400 `erro_requisicao` com `detalhe` | `test_requisicoes_invalidas`, `test_json_invalido` | RNF04 / CA16 |
| CT46 | Agregador fora do ar | 502 `erro_comunicacao`, sem traceback; `/api/saude` informa offline; carga com todas as falhas contadas | `test_agregador_fora_do_ar` | RNF04 / CA17 |
| CT47 | Uma loja desligada | 200 com 3/4 lojas e a falha em `ocorrencias_ou_falhas`; `/api/lojas` mostra a loja offline | `test_loja_desligada_aparece_na_consulta` | RNF04 / CA17 |
| CT48 | Derrubar e subir loja (processo real) | derrubada recusa conexão; subida volta a responder; 409 para ação repetida; 404 para loja/ação inexistente | `test_derrubar_e_subir_loja` | RF01 / CA17 |
| CT49 | Gateway com `--externo` | derrubar loja → 409 | `test_derrubar_sem_gerenciar_processos` | RF01 |
| CT50 | Teste de carga com 20 clientes; 0, 51, "10", 2,5 clientes | 0 falhas e 20 tempos; valores fora do limite → 400 | `test_carga_com_20_clientes`, `test_carga_fora_do_limite` | RNF03 / CA18 |
| CT51 | Gráficos e log | PNG servido com `image/png`; `../config.py` e arquivos não-PNG → 404; log em ordem inversa com `limite` | `test_grafico_png`, `test_resultados_nao_permite_sair_do_diretorio`, `test_log_mais_recentes_primeiro` | RF08, RNF05 / CA18 |
| CT52 | Interface compilada | `/` e `/assets/*` servidos de `frontend/dist`; rota desconhecida cai no `index.html`; sem build → 404 amigável | `TestGatewayInterfaceCompilada` | RF01 |
| CT53 | Interface no navegador (manual) | pesquisa "rtx 4060" em comparar (speedup ≈ 4×); derrubar MagaluTechSim → 3/4 e alerta; subir → 4/4; carga com 50 clientes e 0 falhas; 6 gráficos e log; sem rolagem horizontal a 375 px; gateway parado → mensagem amigável | — | RF01 |

Roteiro da demonstração pela interface: `python3 backend/gateway_http.py` (sobe lojas, agregador e gateway) e, em outro terminal, `cd frontend && npm run dev`; abrir `http://localhost:5173`.

### 3.8 Plano de testes completo da versão 1.2 (backend e interface)

A versão 1.2 enxugou o código sem mudar o protocolo, a API HTTP nem a interface. Este plano confere que tudo continua
funcionando, do teste de unidade ao navegador. Ordem de execução: B1–B2 com as portas livres; B3–B5 e F3–F8 com o
gateway no ar (`python3 backend/gateway_http.py`); F8 parando o gateway; B6 de novo com as portas livres.

**Backend**

| ID | O que testar | Como | Resultado esperado | Resultado (14/11/2026) |
|---|---|---|---|---|
| B1 | Suíte automatizada completa (unidade, integração, sistema com processos reais, gateway) | `cd backend && python3 -m unittest discover -s tests -v > saida.txt 2>&1` | todos passam, nenhum pulado | **82 testes passando em 36,9 s**, nenhum pulado (`test_sistema.py` rodou com processos reais) |
| B2 | Funções novas compartilhadas | incluídas em B1 (CT23, CT54–CT58) | passam | passam; antes do código, falharam pelo motivo esperado (`AttributeError`/`ImportError`) |
| B3 | Cada rota da API HTTP (Apêndice A de `03_protocolo.md`) | `curl` em `/api/saude`, `/api/lojas`, `/api/produtos`, `/api/consultar` (concorrente, comparar, `"Sequencial"`, inexistente, `atraso_ms` texto, JSON malformado), `/api/carga` (50 e 51 clientes), `/api/lojas/<nome>/<ação>` (subir loja no ar, loja e ação inexistentes), `/api/experimentos`, `/api/resultados/g1…png`, `/api/resultados/..%2Fconfig.py`, `/api/log` (limite 2 e `abc`), rota inexistente, corpo de 70 KB | 200 / 200 / 200 / 200·200·200·200·400·400 / 200·400 / 409·404·404 / 200 / 200 `image/png` / 404 / 200·400 / 404 / 413 | todos os códigos como esperado; carga com 50 clientes: 0 falhas, 351 req/s |
| B4 | CLI | `cliente.py --listar`; `cliente.py rtx 4060`; `cliente.py ssd --modo concorrente --atraso -5`; `cliente.py ssd --porta 8999` | catálogo com 5 chaves; 4/4, PichauSim R$ 1.864,00, speedup ≈ 4×; erro tratado sem traceback; `[ERRO] agregador indisponível`, saída 1 | como esperado (speedup 3,97×) |
| B5 | Encerramento | parar o gateway | portas 8000, 8080 e 9001–9004 livres | livres |
| B6 | Experimentos e gráficos | `python3 experimentos.py --rapido` e `.venv/bin/python graficos.py`, com cópia de `resultados/` antes e restauração depois | 5 experimentos e 6 gráficos sem erro; speedup ≈ 4; Exp. 5 com 3/4 lojas nos cenários de falha | concluído em 40 s; speedup 3,93× (615,6 → 156,6 ms); Exp. 3b 1.018 ms (soma 1.000) × 402 ms (máximo 400); Exp. 5 com 3/4 lojas e PichauSim em todos os cenários de falha; 6 gráficos. `resultados/` restaurado (números do relatório intactos) |
| B7 | Gráficos idênticos | `graficos.py` sobre os CSVs da bateria de referência, comparado pixel a pixel com os PNGs anteriores | os 6 PNGs iguais | iguais |

**Interface web**

| ID | O que testar | Como | Resultado esperado | Resultado (14/11/2026) |
|---|---|---|---|---|
| F1 | Tipos | `cd frontend && npm run build` | sem erros | sem erros |
| F2 | Lint | `npx oxlint src` | sem erros | 0 erros; 2 avisos `set-state-in-effect` já existentes na 1.1 |
| F3 | Regressão visual automática | no navegador, executar uma pesquisa em cada aba e gravar o HTML renderizado (números trocados por `#`) e 36 propriedades de estilo computado de todos os elementos das 4 abas, em 1024 px e 375 px; repetir com a versão nova e comparar | iguais à versão 1.1 | 891 elementos iguais nas duas larguras; única diferença: qual barra do histograma de carga é a mais alta, que depende dos tempos sorteados em cada execução |
| F4 | Aba Pesquisa | "rtx 4060" em comparar; critério custo-benefício em sequencial; produto "geladeira" | speedup e barras soma × máximo; título "ordenadas por custo-benefício" e uma barra; alerta "Nenhuma loja tem…" sem tabela | como esperado |
| F5 | Aba Lojas e falhas | derrubar MagaluTechSim, pesquisar, subir, pesquisar | selo "Fora do ar", cabeçalho 3/4, alerta com `erro_comunicacao` (ConnectionRefusedError), menor preço PichauSim R$ 1.864,00; depois 4/4 | como esperado |
| F6 | Aba Teste de carga | 50 clientes, concorrente, 100 ms | 0 falhas, métricas e histograma | como esperado |
| F7 | Aba Experimentos e log | abrir a aba | 3 métricas de resumo, 6 gráficos, tabelas e log | como esperado |
| F8 | Gateway fora do ar | parar o gateway com a interface aberta (`npm run dev`) | cabeçalho "Gateway HTTP fora do ar"; pesquisa com mensagem amigável; lojas sem cartões nem botões | como esperado |
| F9 | Responsividade e console | 375 px; console do navegador | sem rolagem horizontal; nenhum erro no console | como esperado |

## 4. Execução (14/11/2026)

Ambiente: macOS (Darwin arm64), Python 3.15.0, `127.0.0.1`.

| Etapa | Resultado |
|---|---|
| Suíte automatizada antes das correções | 31 testes, todos passando, mas sem cobrir os defeitos da seção 5 |
| Sondagem exploratória e testes manuais com processos reais | 5 não conformidades encontradas (seção 5) |
| Testes novos escritos antes das correções | 21 testes; os que reproduzem as não conformidades falharam pelo motivo esperado |
| Suíte automatizada depois das correções | **52 testes, todos passando em 3 execuções seguidas** (unidade, integração e sistema), sem nenhum pulado e sem processos deixados nas portas |
| Roteiro manual da demonstração (3.5) | todos os passos com o resultado esperado; queda durante a consulta → `erro_comunicacao` em ~500 ms; loja lenta → `timeout` em 2,5 s; 30 clientes simultâneos sem falha |
| `experimentos.py --rapido` + `graficos.py` (em pasta temporária) | 5 experimentos concluídos e 6 gráficos gerados; valores coerentes com o relatório (speedup ≈ 3,9; Exp. 5 com 3/4 lojas em todos os cenários de falha) |
| Separação em `backend/` + `frontend/`, gateway HTTP e interface web | 52 testes anteriores passando sem alteração depois da mudança de pasta; 23 testes novos do gateway escritos antes do código (falharam por import) e depois passando: **75 testes no total**; `npm run build` sem erros de tipo; roteiro CT53 conferido no navegador |
| `experimentos.py --rapido` + `graficos.py` depois da separação em `backend/` (em cópia temporária, para não sobrescrever `backend/resultados/`) | concluído em 40 s; speedup 3,97× (621,0 → 156,3 ms); Exp. 5 com 3/4 lojas e PichauSim como menor preço em todos os cenários de falha; 6 gráficos gerados. Valores coerentes com a bateria de referência |
| Bateria completa `experimentos.py` + `graficos.py` na versão final (14h03) | concluída sem erros em ~2 min; speedup 3,97× (621,11 → 156,50 ms); Exp. 3b 1.020,55 ms (soma 1.000) × 405,93 ms (máximo 400); Exp. 4 sem falhas até 50 clientes (372 req/s no concorrente); Exp. 5 com 3/4 lojas e PichauSim como menor preço em todos os cenários de falha. Relatório (seções 5 a 8), `backend/resultados/` e slides atualizados com esses números |
| Versão 1.2: código enxugado (ver tabela abaixo), mesmo protocolo, mesma API HTTP e mesma interface | 8 testes novos para as funções compartilhadas escritos antes do código (falharam pelo motivo esperado) e 1 removido (arquivamento do log, que deixou de existir): **82 testes passando**; plano da seção 3.8 executado por completo, todos os itens com o resultado esperado |
| Roteiro da demonstração pelos 5 experimentos (NC07, 15/11/2026) | 7 testes novos (CT68–CT71) escritos antes do código e falhando pelo motivo esperado; depois, **90 testes passando em 42 s, nenhum pulado** (`test_sistema.py` com processos reais). Ensaio do roteiro da seção 3.5 com `iniciar_servicos.py` real e comandos pelo stdin: Exp. 1 621 ms; Exp. 2 156 ms; Exp. 3 2.016 × 506 ms (speedup 3,99×); Exp. 4 com 20 clientes: lote de 630 ms (sequencial) e 166 ms (concorrente), 0/20 falhas nos dois; Exp. 5 `derrubar MagaluTechSim` aos 3 s → 3/4 lojas e `erro_comunicacao`, `subir` → 4/4 |

Tamanho do código antes × depois da versão 1.2:

| Parte | Versão 1.1 | Versão 1.2 |
|---|---|---|
| `backend/*.py` (sistema) | 2.106 linhas | 1.868 linhas (−11%) |
| `backend/tests/` | 1.062 linhas, 75 testes | 1.106 linhas, 82 testes |
| `frontend/src/` | 22 arquivos (1.391 linhas TS + 1.004 CSS) | 10 arquivos (1.189 TS + 975 CSS) |
| `frontend/tsconfig*.json` | 3 arquivos | 1 arquivo |

O que saiu foi duplicação: a validação da pesquisa (agregador e gateway), o `ping` (gateway e `iniciar_servicos`), a
comparação dos modos (CLI e gateway), o disparo de N clientes simultâneos (gateway e Exp. 4) e a leitura de `--latencias`
(gateway e `iniciar_servicos`) passaram a ter uma implementação cada; contadores sem uso do `servidor_base` e o
arquivamento do log antigo foram removidos.

## 5. Não conformidades e correções

| ID | Problema encontrado | Impacto | Correção | Teste |
|---|---|---|---|---|
| NC01 | Uma loja que respondesse `sucesso` sem os campos da oferta, ou com preço em texto, gerava `KeyError`/`TypeError` no agregador: a pesquisa inteira virava `erro_interno` e as outras 3 lojas eram descartadas | Contrariava RNF04, o RF05 (lojas com falha informadas sem descartar as demais) e o protocolo (resposta inválida = `erro_comunicacao`) | `agregador.validar_resposta_loja` confere tipos e campos obrigatórios; a resposta inválida vira `erro_comunicacao` só para aquela loja | CT17–CT19 |
| NC02 | `atraso_ms` aceitava `true`, `1.5` e `"50"` (convertidos com `int()`), embora o protocolo diga "inteiro" | Divergência entre protocolo e implementação | `protocolo.validar_atraso_ms`, usado pelo agregador e pelas lojas | CT20 |
| NC03 | Com as portas já ocupadas (por exemplo, um `iniciar_servicos.py` esquecido aberto), um novo `iniciar_servicos.py` ou `experimentos.py` anunciava "Ambiente pronto": o `ping` era respondido pelos processos antigos | Demonstração e experimentos rodando sobre processos errados; no Exp. 5, derrubar a loja não teria efeito | `Ambiente` verifica se a porta está livre e se o próprio processo continua vivo; se a subida falha, encerra o que já tinha subido | CT28, CT29, CT35 |
| NC04 | SIGTERM (`kill`) ou SIGHUP (fechar o terminal) no `iniciar_servicos.py` deixava as 4 lojas e o agregador órfãos, ocupando as portas; Ctrl+C no `experimentos.py` mostrava traceback | Próxima execução falhava (ver NC03) | `tratar_sinais_de_encerramento()` converte SIGTERM/SIGHUP em Ctrl+C nos dois scripts; `experimentos.py` trata a interrupção. Na verificação final, o CT36 revelou uma condição de corrida: um sinal recebido enquanto um serviço ainda subia deixava esse processo órfão (o agregador, em 5 de 6 tentativas). O `Ambiente` passou a registrar cada processo no instante em que o cria (0 de 6 depois da correção) | CT36 |
| NC05 | RF08 diz que o tempo total **e o tempo por loja** são gravados em `log_pesquisas.csv`, mas o CSV só tinha o tempo total | Divergência entre requisito e implementação | Nova coluna `tempos_lojas_ms` no CSV e campo `tempos_lojas_ms` na resposta. (Na versão 1.1, um log com colunas antigas era renomeado; com o formato estável, isso saiu na 1.2.) | CT22 |
| NC09 | Em 15/11/2026: o documento tinha 13 RF e 8 RNF; os extras (RF09–RF13, RNF06–RNF08) não correspondiam aos exemplos das seções 5.2 e 5.3 do enunciado | A lista de requisitos não seguia fielmente o enunciado | Requisitos reduzidos a RF01–RF08 e RNF01–RNF05, um por exemplo do enunciado; o conteúdo dos removidos foi incorporado aos que ficaram (falhas e lojas sem o produto em RF05, catálogo em RF01, speedup em RF08, experimentos automatizados em RNF05, protocolo em RNF01, meta de desempenho em RNF02, Python e biblioteca padrão nas restrições) e a interface web passou a ser descrita como mais um cliente que atende os mesmos RF. Referências dos casos de teste, casos de uso, rastreabilidade, relatório, README e slide (agora com RF e RNF em tabela) atualizadas | V11, V12 |
| NC08 | Em 15/11/2026, na conferência com a seção 5 do enunciado: (1) o RNF05 do enunciado ("permitir experimentos de desempenho") era o nosso RNF07, e o nosso RNF05 era a meta de desempenho; (2) o diagrama de casos de uso era um fluxograma, sem a notação UML (atores como caixas, «include» com seta cheia); (3) o slide de requisitos dizia "12 requisitos funcionais", sem o RF13; (4) os slides não mostravam escopo, atores, restrições e critérios de aceitação; (5) o relatório citava RF01–RF12, CA01–CA15 e casos de uso sem o UC05; (6) a fonte Mermaid embutida no `02` não tinha o UC05; (7) a rastreabilidade não cobria RNF05, RNF07 e RNF08 | Documento, relatório e slides não seguiam fielmente a seção 5 | RNF05 ↔ RNF07 trocados (e CT11, CT12 e UC04 ajustados); diagrama redesenhado em UML (`diagramas/casos_de_uso.svg` → `img/casos_de_uso.png`); slide de requisitos com 13 RF e novo slide "Análise de requisitos"; relatório §2–§3, `02` §1 e §3 e `01` §10 atualizados | V12, V13 |
| NC07 | Em 15/11/2026: o roteiro da demonstração (slide do roteiro no deck e seção 3.5) não seguia os experimentos da seção 9 do enunciado. O Exp. 4 não tinha comando de terminal, e o passo "derrubar uma loja (Ctrl+C)" encerrava **todo** o `iniciar_servicos.py`, não uma loja; desativar uma loja durante a pesquisa exigia 6 terminais | A demonstração não mostrava os 5 experimentos pedidos | `cliente.py --clientes N` (Exp. 4) e console no `iniciar_servicos.py` (`derrubar`/`subir`/`status`) para o Exp. 5; roteiro da seção 3.5, slide do roteiro e README reescritos um passo por experimento. Os testes novos falharam antes do código (`ImportError: executar_comando`; `--clientes` desconhecido) | CT68–CT71 |
| NC06 | Em 15/11/2026: no modo comparar (padrão da CLI), `cliente.py` fazia as duas pesquisas mas só imprimia o relatório do concorrente; o sequencial aparecia apenas como um tempo no comparativo | Na demonstração não dava para ver a tabela do modo sequencial | `cliente.executar` imprime o relatório de cada modo (sequencial e depois concorrente) antes do comparativo. O teste novo falhou antes da correção (`'MODO: SEQUENCIAL' not found`) | CT31, CT67 |

### Pendências do grupo

| ID | Pendência | Ação |
|---|---|---|
| PEND01 | Os slides existiam só no Claude Design, não como arquivo do projeto | **Resolvida em 14/11/2026:** deck conferido renderizado e exportado para `docs/apresentacao.pptx` (PowerPoint com fontes básicas) |
| PEND02 | Os números do relatório vinham da bateria anterior às correções | **Resolvida em 14/11/2026:** bateria completa rodada na versão final; relatório, `resultados/`, `.docx` e slides atualizados |
| PEND03 | `img/arquitetura.png` e `img/casos_de_uso.png` mostravam a versão sem gateway/interface | **Resolvida em 14/11/2026:** renderizados de novo com `mermaid-cli` a partir de `diagramas/*.mmd`, `.docx` regerados e as imagens dos slides 5 (casos de uso, agora cinco) e 6 (arquitetura) trocadas no deck |
| PEND04 | O deck ganhou o slide 12 (interface web), os diagramas novos nos slides 5 e 6 e o roteiro da demo em `backend/`, mas `docs/apresentacao.pptx` ainda era a exportação anterior (17 slides) | **Resolvida em 14/11/2026:** deck exportado de novo (PowerPoint, basic fonts) e `docs/apresentacao.pptx` substituído; conferidos 18 slides com os textos novos |
| PEND05 | Deck redesenhado em 14/11/2026 (https://claude.ai/artifact/Lgii1Psd9TgHD3QbrMmJpz): visual escuro, 19 slides (agenda com tempos 2/4/4/5/3 min e divisão sugerida das falas entre os 5 integrantes nas notas), gráficos e arquitetura desenhados no próprio slide; todos os slides conferidos renderizados | **Resolvida em 14/11/2026:** deck novo exportado (PowerPoint, basic fonts) e `docs/apresentacao.pptx` substituído; conferidos 19 slides, 19 notas do apresentador, textos e números iguais aos do deck, e a capa renderizada com Arial/Courier New sem texto cortado |
| PEND06 | Em 15/11/2026, o slide do roteiro da demonstração passou a seguir os 5 experimentos (NC07), mas `docs/apresentacao.pptx` ainda é a exportação anterior | **Resolvida em 15/11/2026:** deck exportado de novo (PowerPoint, basic fonts) e `docs/apresentacao.pptx` substituído; conferidos 19 slides, o 12 com os 5 experimentos e as notas novas |
| PEND07 | Em 15/11/2026 (NC08), o deck ganhou o slide "Análise de requisitos" (20 slides), o slide de requisitos passou a mostrar os 8 RF e os 5 RNF em duas tabelas (NC09) e o de casos de uso usa o diagrama UML novo, mas `docs/apresentacao.pptx` ainda era a exportação anterior (19 slides) | **Resolvida em 15/11/2026:** deck exportado de novo (PowerPoint, basic fonts) e `docs/apresentacao.pptx` substituído; conferidos 20 slides: o 5 com a análise de requisitos, o 6 com as tabelas de RF01–RF08 e RNF01–RNF05, o 7 com o diagrama UML novo e o 13 com o roteiro pelos 5 experimentos; notas com 90 testes |
