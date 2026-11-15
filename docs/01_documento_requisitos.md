# Documento de Requisitos — Agregador de Preços de Eletrônicos

**UNIVERSIDADE FEDERAL DO SUL E SUDESTE DO PARÁ (UNIFESSPA)**
Faculdade de Sistemas de Informação (FACSI) · Disciplina: Sistemas Distribuídos
Professor: Gleison de Oliveira Medeiros · Trabalho 1 — Tema 6
**Grupo VI:** Youri, José Miguel, Mateus Leitão, Michelangelo e Ângelo
Versão 1.1 — novembro de 2026 (inclui a interface web: RF13, UC05, CA16–CA18)

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

| ID | Requisito | Prioridade |
|---|---|---|
| **RF01** | O sistema deverá permitir que o usuário informe o produto a pesquisar, o modo de consulta (sequencial, concorrente ou comparação dos dois) e o critério de ordenação. | Essencial |
| **RF02** | O sistema deverá consultar pelo menos quatro lojas independentes, cada uma executando como processo servidor próprio. | Essencial |
| **RF03** | O sistema deverá permitir consultas **sequenciais**, em que uma loja é consultada após a resposta da anterior. | Essencial |
| **RF04** | O sistema deverá permitir consultas **concorrentes**, em que todas as lojas são consultadas simultaneamente por threads. | Essencial |
| **RF05** | O sistema deverá apresentar, para cada loja, o produto, as especificações técnicas, o preço, o frete, o preço total, a avaliação, a garantia e o tempo de resposta. | Essencial |
| **RF06** | O sistema deverá ordenar as ofertas pelo preço total (preço + frete) ou pelo índice de custo-benefício, conforme escolha do usuário. | Essencial |
| **RF07** | O sistema deverá identificar a **loja com menor preço total** e a **oferta de melhor custo-benefício**. | Essencial |
| **RF08** | O sistema deverá medir e registrar o tempo de execução de cada pesquisa (tempo total e tempo por loja), gravando-o em `resultados/log_pesquisas.csv` (colunas `tempo_total_ms` e `tempos_lojas_ms`). | Essencial |
| **RF09** | O sistema deverá informar as lojas que não possuem o produto e as lojas que falharam, indicando o motivo (fora do ar, queda, timeout), sem deixar de apresentar os resultados das demais. | Essencial |
| **RF10** | O sistema deverá permitir listar os produtos disponíveis nos catálogos das lojas. | Desejável |
| **RF11** | O sistema deverá exibir o comparativo de tempo entre os modos sequencial e concorrente, com o speedup obtido. | Essencial |
| **RF12** | O sistema deverá oferecer a execução automatizada dos cinco experimentos obrigatórios, gerando tabelas (CSV/Markdown) e gráficos. | Essencial |
| **RF13** | O sistema deverá oferecer uma interface web que permita pesquisar e comparar os modos (RF01–RF11), ver o status de cada loja e derrubá-la ou subi-la para demonstrar falhas, disparar até 50 clientes simultâneos e consultar os resultados dos experimentos e o registro de pesquisas. O navegador fala HTTP com um gateway local, que repassa cada operação ao agregador por socket TCP. | Desejável |

## 6. Requisitos não funcionais

| ID | Categoria | Requisito |
|---|---|---|
| **RNF01** | Comunicação | Toda comunicação entre cliente, agregador e lojas deverá usar **sockets TCP** reais. |
| **RNF02** | Concorrência | A estratégia concorrente deverá usar **threads** (`threading`), uma por loja consultada. |
| **RNF03** | Escalabilidade | O agregador e as lojas deverão atender **múltiplas conexões simultâneas** (uma thread por conexão). Pelo menos 50 clientes simultâneos devem ser atendidos sem falhas. |
| **RNF04** | Confiabilidade | O sistema deverá tratar falhas de comunicação (conexão recusada, queda durante a consulta, timeout de 2,5 s por loja, mensagens malformadas) sem encerrar o agregador e sem exibir *traceback* ao usuário. |
| **RNF05** | Desempenho | No modo concorrente, o tempo total de uma pesquisa deverá ficar próximo da maior latência entre as lojas, com sobrecarga inferior a 50 ms em ambiente local. |
| **RNF06** | Interoperabilidade | As mensagens deverão seguir o protocolo documentado (`docs/03_protocolo.md`): JSON UTF-8 terminado por `\n`, uma requisição por conexão, limite de 64 KB. |
| **RNF07** | Experimentação | A latência das lojas deverá ser configurável (por loja ou por requisição) para permitir experimentos de desempenho reprodutíveis. |
| **RNF08** | Portabilidade / manutenção | O sistema deverá executar em Python 3.10+ usando apenas a biblioteca padrão (matplotlib somente para os gráficos), com configuração centralizada em `config.py`. |

## 7. Restrições

- Linguagem **Python 3** e biblioteca padrão (`socket`, `threading`, `json`).
- Comunicação obrigatoriamente por **sockets TCP**. Não é permitido simular a comunicação.
- Pelo menos **quatro** serviços independentes, cada um em processo separado e em porta TCP distinta (9001–9004). O agregador usa a porta 8000.
- Dados de produtos e preços **simulados**, armazenados em `backend/dados/lojas/*.json`.
- Organização: o sistema distribuído (Python) fica em `backend/` e a interface web em `frontend/`. HTTP existe apenas entre o navegador e o gateway; o gateway é um cliente TCP do agregador como o `cliente.py`.
- Execução local (`127.0.0.1`), com demonstração prática ao vivo na apresentação de 16/11/2026.

## 8. Casos de uso

O diagrama UML está em `02_modelagem.md`.

### UC01 — Pesquisar produto
- **Ator:** Usuário comprador · **Requisitos:** RF01, RF02, RF05–RF09
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
- **Ator:** Usuário comprador · **Requisitos:** RF03, RF04, RF11
- **Fluxo:** o usuário escolhe o modo "comparar". O cliente executa o UC01 nos dois modos e exibe o relatório de cada um, os dois tempos e o speedup.

### UC03 — Listar catálogo
- **Ator:** Usuário comprador · **Requisito:** RF10
- **Fluxo:** o cliente envia `listar_produtos`. O agregador consulta as lojas concorrentemente e devolve a união das palavras-chave.

### UC04 — Executar experimentos
- **Ator:** Pesquisador · **Requisitos:** RF08, RF12, RNF07
- **Fluxo:** `experimentos.py` sobe as lojas e o agregador como processos, executa os experimentos 1 a 5 com repetições e grava os CSVs e `tabelas.md`. Em seguida, `graficos.py` gera os gráficos.

### UC05 — Usar a interface web
- **Ator:** Usuário comprador ou avaliador · **Requisitos:** RF13 (e, através dela, RF01–RF12, RNF03, RNF04)
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
| RF01 | UC01, UC02 | `cliente.py` |
| RF02 | UC01 | `loja_server.py`, `config.py` |
| RF03, RF04 | UC01, UC02 | `agregador.py` (`consultar_todas`) |
| RF05–RF07 | UC01 | `agregador.py` (`executar_busca`), `cliente.py` |
| RF08 | UC01, UC04 | `agregador.py` (`RegistroPesquisas`) |
| RF09 | UC01 | `agregador.py`, `cliente.py` |
| RF10 | UC03 | `agregador.py` (`listar_produtos`) |
| RF11 | UC02 | `cliente.py` (`comparar`) |
| RF12 | UC04 | `experimentos.py`, `graficos.py` |
| RNF01, RNF06 | todos | `protocolo.py` |
| RNF02, RNF03 | UC01, UC04 | `servidor_base.py`, `agregador.py` |
| RNF04 | UC01 | `protocolo.py`, `agregador.py`, `cliente.py` |
| RF13 | UC05 | `backend/gateway_http.py`, `frontend/src/` |
