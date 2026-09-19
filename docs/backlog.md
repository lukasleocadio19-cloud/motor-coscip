# Backlog local — estado da implementação

Legenda: **feito** (código + teste) · **base** (estrutura/contrato pronto, falta o fluxo) · **—** (não iniciado).
IDs e critérios de aceite vêm do documento 03 do plano.

## Viabilidade (semanas 1–4)

| ID | Entrega | Estado | Onde |
|---|---|---|---|
| POC-01 | Inventário de hardware e espaço | **feito** | 16 GB, i7-3770, RTX 3050, SSD único (relatório do corpus) |
| POC-02 | 5–10 DXFs reais autorizados | **feito** | 5 projetos em `Downloads/coscip-corpus`; referências = cotas do projeto; falta 1 medida real independente |
| POC-03 | Procedimento DWG → DXF | **feito** | AutoCAD 2027 `accoreconsole` + `DXFOUT` 2018; `docs/runbooks/dwg-para-dxf.md` |
| POC-04 | Extrair entidades, layers, textos, blocos | **feito** | `coscip_cad.dxf_reader`, `tests/unit/test_dxf_reader.py` |
| POC-05 | Conferir medidas e transformações | **feito** | espelhamento, escala, unidades, blocos |
| POC-06 | Viewer com seleção | **feito** | cena binária por camada, seleção → origem no DXF; testado com 1,28 mi de segmentos (9715) |
| POC-07 | Tempo, memória e expansão | **feito** | `coscip_api.cli benchmark`; pior caso 20,6 s / 271 MB |
| POC-08 | Gate de continuidade | **aprovado (usuário, 19/09)** | 1.452/1.460 cotas conferem; faltam revisão humana das 5 confirmações e 1 medida real (ver `coscip-corpus/RELATORIO.md`) |

## Fundação local

| ID | Entrega | Estado | Onde |
|---|---|---|---|
| LOC-01 | Python travado + build React/Vite | **feito** | `pyproject.toml`, `npm run build` → `static/` |
| LOC-02 | Launcher, porta livre, sessão | **feito** | `launcher.py`, `security.py`, testes de Host/Origin/CSRF |
| LOC-03 | SQLite, esquema, org/operador locais | **feito** | `models.py`, migração `0001` |
| LOC-04 | Projetos e revisões imutáveis | **feito** | selagem com manifesto e hash |
| LOC-05 | Upload local, hash, quarentena | **feito** | partes com SHA-256, streaming |
| LOC-06 | Resolução segura de arquivos | **feito** | `LocalFileStorage.resolve`, testes de traversal |
| LOC-07 | Job persistido e supervisor único | **feito** | `coscip_jobs`, `supervisor.py` |
| LOC-08 | Worker, timeout, cancelamento | **feito** | processo separado, ambiente mínimo |
| LOC-09 | Recuperação e token de tentativa | **feito** | `tests/recovery/test_job_queue.py` |
| LOC-10 | Logs locais e painel | base | log rotativo; painel de jobs pendente |

## CAD, visualização e preparação

| ID | Estado | Observação |
|---|---|---|
| CAD-01 | **feito** | adaptador + diagnóstico publicado |
| CAD-02 | **feito** | `POST /drawings/{id}/unit-confirmation` com referência medida (desvio ≤ 2 %), novo quadro + snapshot + correção auditada; tela na planta |
| CAD-03 | **feito** | instâncias sem colisão de identidade |
| CAD-04 | base | cena visual separada das entidades exatas; snapshots derivados por mudança; modelo CBM de elementos ainda não |
| VIEW-01 | **feito** | cena `scene/1.0` (Float32 + ids), camadas, erro de discretização registrado |
| VIEW-02 | **feito** | `GET /drawings/{id}/entities/{row}`: handle, caminho de instâncias, layer, bloco, hash do arquivo |
| VIEW-03 | base | marcações e medidas sobrepostas; medida com ajuste ao vértice exato |
| VIEW-04 | base | estados de carregamento/erro; lista textual de resultados ainda não |
| PREP-01 | **feito** | recorte retangular → novo snapshot; medida fora do recorte recusada |
| PREP-02..04 | — | classificação, contornos e dicionário |

## Geometria e regras

| ID | Estado | Observação |
|---|---|---|
| GEO-01 | **feito** | `ToleranceProfile` (experimental), `compare_minimum/maximum` |
| GEO-02 | base | `area`/`length` com validação |
| GEO-03 | — | vão/folha/largura livre |
| GEO-04 | base | `FloorGraph` exige topologia confirmada |
| GEO-05 | — | cobertura com erro limitado |
| GEO-06 | **feito** | invariância por propriedades (Hypothesis) |
| REG-01 | base | tabela `normative_sources` + modelo de manifesto |
| REG-02, REG-03 | — | matriz de cobertura da NT 2-01 e contexto |
| REG-04 | **feito** | DSL fechada + regra artificial, cinco estados testados |
| REG-05, REG-06 | — | exige homologação técnica da NT 2-01 |

## Revisão, relatório e recuperação

| ID | Estado | Observação |
|---|---|---|
| REV-01 | base | decisão append-only na API; fila na interface pendente |
| REV-02 | — | |
| REP-01..03 | — | |
| SAFE-01 | **feito** | API de backup do SQLite + artefatos verificados |
| SAFE-02 | **feito** | restauração em pasta separada e vazia |
| SAFE-03 | — | atualização lado a lado |
| SAFE-04 | base | escrita atômica testada com falha; teste de disco cheio real pendente |
| SAFE-05 | — | isolamento do parser (identidade restrita/VM) |

## IA opcional

| ID | Estado | Observação |
|---|---|---|
| AI-01 | — | corpus cego de 100–200 tarefas |
| AI-02 | base | credencial no cofre do Windows; provedor desligado por padrão |
| AI-03 | base | `BudgetLedger` em memória; persistir em `budget_reservations` |
| AI-04..07 | — | |

## Piloto e futuro

PILOT-01..06 e FUT-01..09 não iniciados — ver documento 03.

## Continuação Codex — 19/09/2026

- Revisão de unidades: implementada e testada, aceitação vinculada à confirmação vigente.
- PREP-01: ampliado para polígono; segmentos não podem cruzar o exterior do recorte.
- PREP-02: fluxo assistido por entidade, classe/nome por propriedade, origem e snapshot; registros
  em config JSON, integração relacional CAD-04 e classificação em lote ainda pendentes.
- PREP-03 / GEO-02: base funcional de contornos redesenháveis, área/perímetro/incerteza e histórico;
  falta associação explícita a ambiente semântico e revisão visual completa do fluxo.
- GEO-03: base funcional de vão/folha/largura livre independentes em porta classificada; revisar
  invalidação quando a classe da porta muda e conferir o fluxo visualmente.
- REP-01: base de relatório HTML imutável de preparação com evidências e hashes; não é relatório
  de análise normativa. PDF e execução normativa continuam pendentes.
- Testes novos: 9 passaram; lint, TypeScript e build alternativo passaram. Resultado da suíte
  completa e detalhes de ambiente em docs/proxima-sessao.md.
- Gate A permanece pré-aprovado; nenhuma confirmação humana do corpus foi realizada nesta sessão.

## Base normativa e análise automática da planta — 19/09/2026 (Claude)

| ID | Estado | Onde |
|---|---|---|
| POC-08 | **aprovado** | usuário considerou o Gate A conferido por humano |
| CAD-01 (fix) | **feito** | leitor ignora entidades `invisible` (estados ocultos de blocos dinâmicos; 11.190 no 9715) e grava ponto de inserção (`anchor`) |
| REG-01 | **feito** | `coscip_normative`: ingestão de NTs em Markdown (front matter, páginas, itens, tabelas, anexos, SHA-256); `POST /v1/normative/sources` |
| REG-02 | base | pacote `normative/base` (package/1.0): 9 regras RASCUNHO, dicionário de símbolos, matriz do que não é automatizado; toda citação conferida no texto (documento + item + termos) antes de importar |
| REG-04 | **feito** | DSL `rules/1.1`: sujeito (FLOOR/SYMBOL/ROOM), exigido por valor/tabela de contexto/⌈divisão⌉, `fail_status`, porta de qualidade com veredito indicativo |
| PREP-02 | base | reconhecimento automático de símbolos (bloco > layer > texto), legenda, estados NOVO/EXISTENTE/DEMOLIR, agente/carga, placas embutidas |
| GEO-04 | base | percurso real: grade de 16 vizinhos, paredes como obstáculo, interior por fechamento morfológico; incerteza declarada |
| GEO-05 | base | cobertura de extintor/hidrante/acionador/saída com área além do limite e área sem acesso |
| REP-01 | base | relatório HTML imutável da análise (mapa SVG por pavimento, resultados com citação e página, cobertura normativa, hashes) |
| UI da análise | **feito** | ver seção seguinte |

## Telas da análise e base normativa completa — 19/09/2026 (Claude, noite)

| ID | Estado | Onde |
|---|---|---|
| REG-01 | **feito** | base real com **53 fontes**: as 52 NTs vigentes dos grupos 1–5 + Decreto 42/2018 (COSCIP compilado); leitor aceita decreto, indexa artigos (`Art. 15`) e anexos romanos (`Anexo III`) |
| REG-01 (consulta) | **feito** | `GET /v1/normative/sources/{id}` (índice de itens), `/sources/{id}/item?item=`, `GET /v1/normative/search?q=` (todos os termos no mesmo item; índice normalizado em memória, ~40 ms) |
| REG-02 | base | pacote importado na base real (9 regras RASCUNHO, 11 itens de conferência humana), citações conferidas contra as 53 fontes |
| Tela Base normativa | **feito** | `#/base-normativa`: documentos por grupo com cobertura (regra automática / conferência humana / símbolos / consulta), busca, envio de .md, importação do pacote com falhas listadas; `#/base-normativa/:id`: identificação, regras e itens citados, índice de itens, texto do item com tabelas renderizadas |
| Tela Análise da planta | **feito** | `#/desenhos/:id/analise` (botão "Analisar planta" na planta): enquadramento, saídas, pavimentos, paredes (automático/manual), mapeamento de blocos; histórico; resultado por região com mapa, contagens, percursos, áreas declaradas, resultados com citação, blocos não reconhecidos → "mapear"; relatório e nova emissão |
| CLI normativo | **feito** | `coscip_api.cli normative-import-sources <pasta>` e `normative-import-package [pasta]` |
| REV-01/02 | — | revisão humana dos resultados na tela ainda não existe |

## Recortes reais, enquadramento pela NT 1-04 e revisão humana — 19/09/2026 (Claude, noite 2)

| ID | Estado | Onde |
|---|---|---|
| PREP-01 (real) | **feito** | 7 pavimentos recortados nas 5 plantas reais (assistente, conferido em vista SVG dos segmentos); ver guia |
| REG-03 | base | `normative/base/enquadramento.yaml`: 60 divisões da NT 1-04 Anexo B → risco (24 por célula mesclada, conferidas nas imagens p. 11–12); verificação linha a linha (`verify_table_row`); mapa Médio 1/2 → coluna Médio da NT 2-01 Tabela 3; exceções 5.6–5.14 ficam com o analista |
| Tela: enquadramento | **feito** | ocupação escolhida da tabela sugere a classe de risco; `context.risk_basis` gravado e mostrado no relatório |
| REV-01 | **feito** | decisão append-only com veredito (`final_status`, migração 0004), validação CONFIRM/CONTEST × REQUEST_DATA, auditoria; `GET /v1/plant-analyses/{id}/reviews` |
| REV-02 | **feito** | revisão na tela (por resultado, histórico, filtro "sem conclusão", aviso de relatório desatualizado); nova emissão traz coluna "Decisão humana", contagem após revisão e `review_snapshot` |
| Decreto 42, Anexo III | — | sistemas exigidos por divisão/área/altura ainda informados à mão |
