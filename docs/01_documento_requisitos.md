# Documento de Requisitos — Agregador de Preços de Eletrônicos

**UNIVERSIDADE FEDERAL DO SUL E SUDESTE DO PARÁ (UNIFESSPA)**
Faculdade de Sistemas de Informação (FACSI) · Disciplina: Sistemas Distribuídos
Professor: Gleison de Oliveira Medeiros · Trabalho 1 — Tema 6
**Grupo VI:** Youri, José Miguel, Mateus Leitão, Michelangelo e Ângelo
Versão 1.3 — novembro de 2026 (1.1: interface web, UC05, CA16–CA18; 1.2: roteiro da demonstração pelos 5 experimentos; 1.3: requisitos reduzidos aos 8 RF e 5 RNF dos exemplos do enunciado)

---

## 1. Descrição do problema

Quem compra eletrônicos (placas de vídeo, notebooks, monitores, SSDs, smartphones) costuma consultar várias lojas para achar o melhor preço. Fazer isso manualmente é lento. Além disso, o preço anunciado nem sempre é o custo final, porque frete, garantia e reputação do produto variam de loja para loja.

Plataformas de comparação resolvem isso consultando várias fontes independentes. Cada consulta passa pela rede e tem uma latência própria. Se as consultas forem feitas **uma após a outra**, o tempo de resposta cresce com o número de lojas. Se forem feitas **ao mesmo tempo**, o tempo total tende ao da loja mais lenta.

## 2. Objetivo do sistema

Desenvolver uma aplicação cliente-servidor, em Python com **sockets TCP** e **multithreading**, que:

- receba do usuário a pesquisa de um eletrônico;
- consulte pelo menos quatro lojas independentes (cada uma um processo servidor);
- consolide, ordene e destaque a melhor oferta;
- permita comparar experimentalmente a estratégia **sequencial** com a **concorrente**.

## 3. Escopo

**Dentro do escopo**
- Cliente de linha de comando (interativo e por argumentos).
- Interface web (Vite + React, em `frontend/`) que usa um gateway HTTP local (`backend/gateway_http.py`) como cliente TCP do agregador.
- Agregador TCP que atende vários clientes ao mesmo tempo.
- Quatro serviços de loja com catálogos simulados (arquivos JSON).
- Consultas sequenciais e concorrentes (threads).
- Ordenação por preço total e por custo-benefício (evolução do Tema 6).
- Tratamento de falhas: loja fora do ar, queda durante a consulta, timeout e mensagens inválidas.
- Registro do tempo de cada pesquisa e scripts para os 5 experimentos com tabelas e gráficos.

**Fora do escopo**
- Integração com lojas reais, preços reais ou APIs comerciais.
- Autenticação, carrinho de compras e pagamento.
- Persistência em banco de dados, cache e replicação.
- Comunicação entre máquinas diferentes (é suportada pela configuração, mas não é exigida nem testada).

## 4. Atores

| Ator | Tipo | Descrição |
|---|---|---|
| **Usuário comprador** | Primário (humano) | Informa o produto, o modo de consulta e o critério de ordenação, e analisa o resultado |
| **Pesquisador / avaliador** | Primário (humano) | Executa os experimentos de desempenho e de falha e analisa tabelas e gráficos |
| **Serviço de loja** | Secundário (sistema) | Processo independente que responde consultas sobre o seu catálogo |

O **agregador** é um componente interno do sistema, não um ator. Ele intermedia o usuário e as lojas.

## 5. Requisitos funcionais

Os oito requisitos funcionais seguem os exemplos da seção 5.2 do enunciado, adaptados ao tema.

| ID | Requisito | Prioridade |
|---|---|---|
| **RF01** | O sistema deverá permitir que o usuário informe os parâmetros de uma pesquisa: o produto (com a lista dos produtos disponíveis no catálogo das lojas), o modo de consulta (sequencial, concorrente ou comparação dos dois) e o critério de ordenação. | Essencial |
| **RF02** | O sistema deverá consultar diferentes serviços independentes: pelo menos quatro lojas, cada uma executando como processo servidor próprio. | Essencial |
| **RF03** | O sistema deverá permitir consultas **sequenciais**, em que uma loja é consultada após a resposta da anterior. | Essencial |
| **RF04** | O sistema deverá permitir consultas **concorrentes**, em que todas as lojas são consultadas simultaneamente por threads. | Essencial |
| **RF05** | O sistema deverá apresentar os resultados encontrados: para cada loja, o produto, as especificações técnicas, o preço, o frete, o preço total, a avaliação, a garantia e o tempo de resposta, além das lojas sem o produto e das que falharam, com o motivo (fora do ar, queda, timeout), sem deixar de apresentar as demais. | Essencial |
| **RF06** | O sistema deverá ordenar os resultados conforme um critério definido: preço total (preço + frete) ou índice de custo-benefício, à escolha do usuário. | Essencial |
| **RF07** | O sistema deverá identificar a melhor opção segundo o critério escolhido: a **loja com menor preço total** e a **oferta de melhor custo-benefício**. | Essencial |
| **RF08** | O sistema deverá registrar o tempo de execução das consultas (tempo total e tempo por loja) em `resultados/log_pesquisas.csv` (colunas `tempo_total_ms` e `tempos_lojas_ms`) e exibir o comparativo entre os modos sequencial e concorrente, com o speedup obtido. | Essencial |

As duas interfaces do usuário (o `cliente.py` de linha de comando e a interface web, que usa um gateway HTTP como cliente TCP do agregador) atendem esses mesmos requisitos.

## 6. Requisitos não funcionais

Os cinco requisitos não funcionais seguem os exemplos da seção 5.3 do enunciado.

| ID | Categoria | Requisito |
|---|---|---|
| **RNF01** | Comunicação | A comunicação entre os componentes (cliente, agregador e lojas) deverá utilizar **sockets TCP** reais, com o protocolo de aplicação documentado em `docs/03_protocolo.md` (JSON UTF-8 terminado por `\n`, uma requisição por conexão, limite de 64 KB). |
| **RNF02** | Concorrência | A estratégia concorrente deverá utilizar **threads** (`threading`), uma por loja consultada, de modo que o tempo total fique próximo da maior latência entre as lojas (sobrecarga inferior a 50 ms em ambiente local). |
| **RNF03** | Escalabilidade | O servidor deverá atender **múltiplas conexões simultaneamente**: o agregador e as lojas usam uma thread por conexão e devem atender pelo menos 50 clientes simultâneos sem falhas. |
| **RNF04** | Confiabilidade | O sistema deverá tratar falhas de comunicação (conexão recusada, queda durante a consulta, timeout de 2,5 s por loja, mensagens malformadas) sem encerrar o agregador e sem exibir *traceback* ao usuário. |
| **RNF05** | Experimentação | A aplicação deverá permitir experimentos de desempenho: latência das lojas configurável (por loja ou por requisição), execução automatizada dos cinco experimentos com tabelas e gráficos e resultados reprodutíveis. |

## 7. Restrições

- Linguagem **Python 3.10+** e apenas a biblioteca padrão (`socket`, `threading`, `json`); `matplotlib` só para os gráficos. Configuração centralizada em `config.py`.
- Comunicação obrigatoriamente por **sockets TCP**. Não é permitido simular a comunicação.
- Pelo menos **quatro** serviços independentes, cada um em processo separado e em porta TCP distinta (9001–9004). O agregador usa a porta 8000.
- Dados de produtos e preços **simulados**, armazenados em `backend/dados/lojas/*.json`.
- Organização: o sistema distribuído (Python) fica em `backend/` e a interface web em `frontend/`. HTTP existe apenas entre o navegador e o gateway; o gateway é um cliente TCP do agregador como o `cliente.py`.
- Execução local (`127.0.0.1`), com demonstração prática ao vivo na apresentação de 16/11/2026.

## 8. Casos de uso

O diagrama UML está em `02_modelagem.md`.

### UC01 — Pesquisar produto
- **Ator:** Usuário comprador · **Requisitos:** RF01–RF08, RNF01–RNF04
- **Pré-condição:** agregador e lojas em execução.
- **Fluxo principal:**
  1. O usuário informa o produto, o modo e o critério.
  2. O cliente envia a requisição `consultar` ao agregador.
  3. O agregador consulta as 4 lojas (sequencial ou concorrente).
  4. Cada loja responde com a sua oferta.
  5. O agregador ordena, identifica o menor preço e o melhor custo-benefício, e registra o tempo.
  6. O cliente exibe o relatório.
- **Fluxos alternativos:**
  - **A1:** produto inexistente → as lojas respondem `nao_encontrado` e o cliente informa que não há ofertas.
  - **A2:** uma loja falha (fora do ar, queda ou timeout) → a falha é listada e as demais ofertas são exibidas.
  - **A3:** agregador indisponível → o cliente exibe mensagem amigável.
  - **A4:** parâmetro inválido → o agregador responde `erro_requisicao` e o cliente exibe o motivo.

### UC02 — Comparar estratégias sequencial × concorrente
- **Ator:** Usuário comprador · **Requisitos:** RF03, RF04, RF08
- **Fluxo:** o usuário escolhe o modo "comparar". O cliente executa o UC01 nos dois modos e exibe o relatório de cada um, os dois tempos e o speedup.

### UC03 — Listar catálogo
- **Ator:** Usuário comprador · **Requisito:** RF01
- **Fluxo:** o cliente envia `listar_produtos`. O agregador consulta as lojas concorrentemente e devolve a união das palavras-chave.

### UC04 — Executar experimentos
- **Ator:** Pesquisador · **Requisitos:** RF08, RNF03, RNF05
- **Fluxo:** `experimentos.py` sobe as lojas e o agregador como processos, executa os experimentos 1 a 5 com repetições e grava os CSVs e `tabelas.md`. Em seguida, `graficos.py` gera os gráficos.
- **Fluxo alternativo (ao vivo, na apresentação):** com `iniciar_servicos.py` no ar, o pesquisador executa cada experimento pelo `cliente.py`: `--modo sequencial` (Exp. 1), `--modo concorrente` (Exp. 2), `--atraso MS` (Exp. 3), `--clientes N` (Exp. 4) e, para o Exp. 5, digita `derrubar <loja>` no terminal do `iniciar_servicos.py` durante uma pesquisa e depois `subir <loja>`.

### UC05 — Usar a interface web
- **Ator:** Usuário comprador ou avaliador · **Requisitos:** RF01–RF08, RNF03–RNF05 (a interface é mais um cliente do agregador)
- **Pré-condição:** `backend/gateway_http.py` em execução (ele sobe as lojas e o agregador) e a interface aberta no navegador.
- **Fluxo principal:** o usuário pesquisa na aba *Pesquisa*; o gateway envia `consultar` ao agregador por TCP (duas vezes no modo "comparar") e a interface mostra destaques, tempos por loja, speedup e a tabela de ofertas.
- **Fluxos alternativos:**
  - **A1:** na aba *Lojas e falhas*, o usuário derruba uma loja; a pesquisa seguinte mostra 3/4 lojas e o motivo da falha; ao subir a loja de novo, ela volta a responder.
  - **A2:** na aba *Teste de carga*, o usuário dispara N clientes TCP simultâneos (1–50) e vê média, p95, vazão e falhas.
  - **A3:** gateway ou agregador fora do ar → a interface exibe mensagem amigável, sem *traceback*.

## 9. Critérios de aceitação

Cada critério pode ser verificado por um teste automatizado (`backend/tests/`) ou por um experimento.

| ID | Critério | Verificação |
|---|---|---|
| CA01 | Uma pesquisa por "rtx 4060" com as 4 lojas ativas retorna 4 ofertas ordenadas por preço total crescente, e o menor preço é da PichauSim (R$ 1.864,00). | `test_ordena_por_preco_e_identifica_menor`, `test_pesquisa_via_cliente` |
| CA02 | Com o critério `custo_beneficio`, as ofertas aparecem em ordem decrescente de score. | `test_ordena_por_custo_beneficio` |
| CA03 | Os modos sequencial e concorrente produzem o mesmo resultado (mesma ordem de lojas). | `test_sequencial_e_concorrente_dao_mesmo_resultado` |
| CA04 | Com 4 lojas de 100 ms, o modo sequencial leva ≥ 400 ms e o concorrente < 250 ms (speedup > 2,5). | `test_concorrente_mais_rapido_que_sequencial`, Exp. 1–3 |
| CA05 | Com lojas heterogêneas (50/100/150/200 ms), o modo sequencial ≈ soma e o concorrente ≈ máximo das latências. | `test_latencia_heterogenea`, Exp. 3b |
| CA06 | 20 clientes simultâneos recebem respostas completas, sem falhas. Nos experimentos, 50 clientes. | `test_multiplos_clientes_simultaneos`, Exp. 4 |
| CA07 | Com uma loja desligada, a pesquisa retorna 3 ofertas e aponta `erro_comunicacao` para a loja ausente. | `test_loja_desligada`, Exp. 5a |
| CA08 | Se a loja cair durante a consulta, a falha é detectada imediatamente (sem esperar o timeout) e a pesquisa conclui com 3 ofertas. | `test_loja_cai_durante_a_consulta`, Exp. 5b |
| CA09 | Uma loja que não responde em 2,5 s recebe status `timeout`, e a pesquisa concorrente não passa de ≈ 2,5 s. | `test_loja_lenta_gera_timeout`, Exp. 5c |
| CA10 | Requisições inválidas (operação desconhecida, produto vazio, modo/critério/atraso inválidos, JSON malformado) recebem `erro_requisicao`, e o servidor continua atendendo. | `test_requisicoes_invalidas`, `test_json_malformado_recebe_erro`, `test_erro_interno_nao_derruba_servidor` |
| CA11 | Cada pesquisa gera uma linha em `log_pesquisas.csv` com o tempo total e o tempo de cada loja. | `test_registra_tempo_em_csv`, `test_registra_tempo_de_cada_loja` |
| CA12 | Com o agregador desligado, o cliente exibe uma mensagem de erro amigável e termina com código 1. | `test_agregador_fora_do_ar` |
| CA13 | Uma loja que responde `sucesso` com dados incompletos ou de tipo errado é registrada como `erro_comunicacao`, e a pesquisa conclui com as demais lojas. | `test_loja_com_resposta_incompleta`, `test_loja_com_preco_nao_numerico` |
| CA14 | Com as portas já ocupadas, `iniciar_servicos.py` recusa a subida (código 1) em vez de anunciar um ambiente que não é o seu; ao receber Ctrl+C, SIGTERM ou SIGHUP, encerra todas as lojas e o agregador. | `test_porta_ocupada_e_detectada`, `test_6_segundo_ambiente_com_portas_ocupadas_falha`, `test_sigterm_encerra_todos_os_processos` |
| CA15 | O roteiro da demonstração segue os 5 experimentos do enunciado e funciona com processos reais nas portas 8000 e 9001–9004: sequencial, concorrente, atraso artificial, N clientes simultâneos (`cliente.py --clientes N`) e uma loja derrubada durante a pesquisa pelo console do `iniciar_servicos.py` (`derrubar`/`subir`), além de listar, custo-benefício e parâmetro inválido. | `tests/test_sistema.py` (`TestDemonstracao`), `test_console_derruba_e_sobe_loja`, `test_cli_multiplos_clientes` |
| CA16 | Pelo gateway HTTP, a pesquisa "rtx 4060" retorna o menor preço da PichauSim (R$ 1.864,00), o modo "comparar" devolve os dois modos e o speedup, e requisições inválidas recebem HTTP 400 `erro_requisicao`. | `test_gateway.py` (`test_consulta_concorrente`, `test_comparar_devolve_os_dois_modos_e_speedup`, `test_requisicoes_invalidas`) |
| CA17 | Pelo gateway, uma loja pode ser derrubada e subida de novo (processo real); com uma loja fora do ar a pesquisa retorna 3/4 lojas; com o agregador fora do ar a resposta é HTTP 502 com mensagem amigável. | `test_derrubar_e_subir_loja`, `test_loja_desligada_aparece_na_consulta`, `test_agregador_fora_do_ar` |
| CA18 | O teste de carga do gateway atende 20 clientes simultâneos sem falhas e recusa mais de 50; o gateway só serve gráficos de `resultados/` (sem acesso a outros arquivos). | `test_carga_com_20_clientes`, `test_carga_fora_do_limite`, `test_resultados_nao_permite_sair_do_diretorio` |

## 10. Rastreabilidade

Os módulos Python ficam em `backend/`; a interface web, em `frontend/`.

| Requisito | Casos de uso | Módulos |
|---|---|---|
| RF01 | UC01, UC02, UC03, UC05 | `cliente.py`, `agregador.py` (`listar_produtos`), `gateway_http.py` + `frontend/src/` |
| RF02 | UC01 | `loja_server.py`, `config.py`, `iniciar_servicos.py` |
| RF03, RF04 | UC01, UC02 | `agregador.py` (`consultar_todas`) |
| RF05 | UC01, UC05 | `agregador.py` (`executar_busca`), `cliente.py`, `frontend/src/` |
| RF06, RF07 | UC01 | `agregador.py` (`executar_busca`, `calcular_score_custo_beneficio`) |
| RF08 | UC01, UC02, UC04 | `agregador.py` (`RegistroPesquisas`), `cliente.py` (`comparar`) |
| RNF01 | todos | `protocolo.py`, `servidor_base.py` |
| RNF02 | UC01, UC02 | `agregador.py` (uma thread por loja + `join()`) |
| RNF03 | UC01, UC04 | `servidor_base.py`, `cliente.py` (`disparar_clientes_simultaneos`, `--clientes`) |
| RNF04 | UC01 | `protocolo.py`, `agregador.py` (`validar_resposta_loja`), `cliente.py`, `iniciar_servicos.py` (`derrubar`/`subir`) |
| RNF05 | UC04 | `loja_server.py` (latência), `protocolo.py` (`atraso_ms`), `iniciar_servicos.py` (`--latencias`), `experimentos.py`, `graficos.py` |