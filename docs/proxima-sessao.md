# Motor CAD/COSCIP — registro único do projeto

**Este é o ÚNICO arquivo que registra informações do projeto** (estado, status por ID, histórico,
pendências, cuidados). Desde 20/09/2026 ele mora **dentro do repositório**, em
`docs/proxima-sessao.md`, e por isso passou a ter histórico de versões no Git.
`C:\Users\USER\Downloads\proxima-sessao.md` virou apenas um ponteiro para cá — não editar lá,
não criar cópia, não criar outro registro.

Última atualização: 29/09/2026, sessão em nuvem que executou o plano de correção
(`docs/plano/01-plano-de-correcao.md`, fases F0–F9; estado na seção 3 e detalhe na seção 13).
Antes: 25/09/2026, segundo computador e fase 3 da arquitetura v2 (CAD → `Evidence` → `Finding`)
para extintores, hidrantes, acionador manual e saídas. O usuário **não tem mais as plantas reais**: o trabalho
segue só com dados sintéticos.
Referências (não são registro): arquitetura-alvo em [`docs/arquitetura-v2.md`](arquitetura-v2.md),
plano `docs/plano/00-plano-completo.html` (v2.0; IDs e critérios de aceite no documento 03) e
runbook `docs/runbooks/dwg-para-dxf.md`.

---

## 1. Onde estamos

- **Gate A aprovado** pelo usuário em 19/09 (conferência humana considerada feita).
- App real com a **base normativa completa**: 52 NTs vigentes (grupos 1–5) + Decreto 42/2018
  (53 fontes, SHA-256) e **pacote de regras v3** importado (9 regras RASCUNHO, tabela de
  enquadramento da NT 1-04, 11 itens de conferência humana; toda citação conferida no texto).
- **Pacote v4 em código** com as Tabelas 2, 3 e 4 do Anexo III (239 células conferidas nas
  páginas 26–28 do PDF oficial). **Ainda não importado na base real** — ver seção 2.
- **Arquitetura v2, fases 1 e 2 implementadas** (20/09): `Check`, `Evidence`, `Finding`, os três
  status separados, catálogo de checks versionado, compilador do Plano de Verificação, executor
  com dependências e consolidador de achados. Aditivo: **nada do fluxo atual foi alterado**.
- **Repositório publicado no GitHub** (privado). O registro do projeto e a arquitetura-alvo
  entraram junto.
- **Fase 3 da arquitetura v2 (25/09):** a saída da análise da planta vira `Evidence` por
  pavimento (`coscip_analysis.evidence`), os checks de pavimento rodam uma vez por pavimento e o
  comando `v2-findings` produz os `Finding` de uma análise gravada, lendo o `analysis.json` e
  não o relatório. Catálogo v2 com **17 checks** (extintores, hidrantes, alarme, saídas), 19
  citações conferidas. Testado só com DXF sintético: **as plantas reais não estão mais
  disponíveis** (seção 7).
- As **5 plantas reais** têm pavimentos recortados e foram analisadas com enquadramento
  proposto pelo assistente (confirmar com os processos).
- **Revisão humana** pronta na tela e no relatório; **nenhuma decisão registrada** (cabe ao
  analista; decisões são append-only e não se apagam).
- **Nada tem valor normativo**: regras e checks em rascunho, sem homologação técnica (REG-05/06).

---

## 2. Pendências (o que ainda precisa ser feito)

### Com o analista (usuário)
- [ ] F2: decidir as 2 tabelas `divergente` (NT 2-02 T5; NT 2-11 A.6 p. 14) e as inconsistências da fonte registradas nos `.yaml` (ex.:
      NT 1-04 sobreposição em 1.200 MJ/m²; NT 4-05 T1 120 m × Anexo A T2 122 m acima de
      3.785 m³; NT 3-02 duas "Tabela 2"; NT 4-05 Anexo B nota 8 que deveria ser 9).
- [ ] F2: dizer se as Tabelas 22–32 do Anexo III (grupos J, L, M) entram no motor depois de
      conferidas (hoje o motor usa T2–21).
- [ ] Revisar as 5 análises na tela (`#/desenhos/<id>/analise`) e fazer nova emissão dos relatórios.
- [ ] Confirmar as ocupações propostas: 9715 D-2 (agência bancária); 21471 e 41336 M-2 (depósito
      de GLP); 21778/21801 A-2 (apartamentos).
- [ ] 21471 e 41336: marcar as camadas de parede no item 4 do formulário e reanalisar.
- [ ] Informar em cada processo o limite da NT 2-08 (Anexo C é imagem) e os sistemas exigidos.
- [ ] 21778/21801: pendência real no pavimento tipo (1 extintor por andar; mínimo 2) — decidir
      na revisão (exceção NT 2-01 5.2.4 só vale abaixo de 50 m²).
- [ ] 41336: confirmar os 5 extintores presumidos pelas placas E5 + E17.
- [ ] Gate A: 1 medida real independente ainda não feita (POC-02/08).

### Desenvolvimento, em ordem

> **Prioridade do usuário (25/09/2026):** primeiro fazer do motor uma ferramenta para a IA
> vencer a dificuldade de LER a planta (MCP local, seção 12, sexta parte); depois construir o
> software em servidor. O MCP existe e está testado; o próximo passo nele é usar com plantas
> reais (o usuário não tem as antigas) e ajustar pelo que a IA errar.

1. **Importar o pacote v4 na base real.** É o que ainda falta da entrega anterior: a permissão de
   gravação em `%LOCALAPPDATA%\MotorCoscip` não foi concedida, então a base real continua em v3.
   Quando houver permissão: `normative-import-package`, reiniciar o aplicativo e conferir a tela.
2. **Conferir a interface na tela.** O build compila (no segundo computador o `npm run build`
   padrão funciona; no primeiro falhava no esbuild com "Acesso negado" e usava a alternativa da
   seção 9). Falta a conferência visual no navegador, que depende do app rodando com a base real.
3. **Persistência e API do fluxo v2 (V2-13).** Fase 3 feita (seção 12). Próximo: gravar plano,
   evidências e achados de cada análise (tabelas do §45, migração 0005, com backup antes) e
   expor as rotas do §47 de leitura; hoje o fluxo v2 só existe em memória e no `v2-findings`.
   Pendências menores da fase 3: portas (largura, GEO-03) como evidência; exceção 5.2.4 da
   NT 2-01; checks de iluminação (NT 2-06) e sinalização (NT 2-05).
4. **Fase 4 — motor documental mínimo** (ART, RRT, memorial, laudo, curva de bomba): upload,
   versionamento, extração e localização. Só depois disso os checks documentais do catálogo
   (`HID-DOC-001`, `HID-DOC-004`, `HID-CROSS-002`) deixam de depender de evidência sintética.
5. ~~**Anexo III, Tabelas 5–21**~~ — feito no plano de correção (F4.3 e F2, seção 13).
   Mapa: `decreto-42-2018-coscip-compilado.md`, linhas ~997–2080, PDF p. 26–45.
   Na Tabela 2, **F1/F2/F3/F4/F7/F8/F10 formam UMA coluna**; não há linhas de hidrantes/alarme
   e M-2 não tem coluna. A consulta não converte essas ausências em dispensa.
6. Mobiliário como obstáculo opcional, portas desenhadas fechadas, largura e número de saídas
   (NT 2-08 5.3, população por ocupação).
7. Relatório em PDF (REP-02/03), painel de jobs (LOC-10), atualização lado a lado (SAFE-03),
   isolamento do parser (SAFE-05), teste real de disco cheio (SAFE-04).
8. Homologação das regras e dos checks com responsável técnico (REG-05/06) — só então valor
   normativo.

**Não fazer ainda** (o documento de arquitetura é explícito): Jev e LLM só entram depois que o
fluxo determinístico `Check → Evidence → Finding` estiver alimentado por evidência real do CAD e
dos documentos. Hoje ele está testado, mas com evidência sintética.

---

## 3. Status por ID do plano (consolidado)

Legenda: **feito** (código + teste) · **base** (estrutura pronta, falta fluxo) · **—** (não iniciado).

### Viabilidade
| ID | Estado | Observação |
|---|---|---|
| POC-01 | **feito** | 16 GB, i7-3770, RTX 3050, SSD único |
| POC-02 | **feito** | 5 projetos em `Downloads\coscip-corpus`; referências = cotas do projeto; falta 1 medida real independente |
| POC-03 | **feito** | DWG→DXF: AutoCAD 2027 `accoreconsole` + `DXFOUT` 2018 para o corpus (runbook); ODA File Converter no MCP (ADR 0006) |
| POC-04 | **feito** | `coscip_cad.dxf_reader` (entidades, layers, textos, blocos) |
| POC-05 | **feito** | espelhamento, escala, unidades, blocos |
| POC-06 | **feito** | cena binária por camada, seleção → origem no DXF; 1,28 mi de segmentos (9715) |
| POC-07 | **feito** | `coscip_api.cli benchmark`; pior caso 20,6 s / 271 MB |
| POC-08 | **aprovado (19/09)** | 1.452/1.460 cotas conferem (ver `coscip-corpus/RELATORIO.md`) |

### Fundação local
| ID | Estado | Observação |
|---|---|---|
| LOC-01 | **feito** | Python 3.12 travado + React/Vite → `static/` |
| LOC-02 | **feito** | launcher, porta livre, sessão; testes Host/Origin/CSRF |
| LOC-03 | **feito** | SQLite, org/operador locais (migração 0001) |
| LOC-04 | **feito** | projetos e revisões imutáveis (manifesto + hash) |
| LOC-05 | **feito** | upload em partes com SHA-256, quarentena |
| LOC-06 | **feito** | `LocalFileStorage.resolve`, testes de traversal |
| LOC-07 | **feito** | job persistido, supervisor único |
| LOC-08 | **feito** | worker separado, timeout, cancelamento |
| LOC-09 | **feito** | recuperação e token de tentativa |
| LOC-10 | base | log rotativo; painel de jobs pendente |

### CAD, visualização e preparação
| ID | Estado | Observação |
|---|---|---|
| CAD-01 | **feito** | adaptador + diagnóstico; ignora entidades `invisible` de blocos dinâmicos (11.190 no 9715); grava ponto de inserção |
| CAD-02 | **feito** | confirmação de unidade por medida de referência (desvio ≤ 2 %), novo quadro + snapshot, correção auditada |
| CAD-03 | **feito** | instâncias sem colisão de identidade |
| CAD-04 | base | cena visual separada das entidades exatas; modelo CBM de elementos ainda não |
| VIEW-01 | **feito** | cena `scene/1.0` (Float32 + ids), erro de discretização registrado |
| VIEW-02 | **feito** | `GET /drawings/{id}/entities/{row}`: handle, caminho, layer, bloco, hash |
| VIEW-03 | base | marcações e medidas sobrepostas; medida com ajuste ao vértice |
| VIEW-04 | base | estados de carregamento/erro; lista de resultados existe na tela da análise |
| PREP-01 | **feito** | recorte retangular e poligonal → novo snapshot; 7 recortes reais feitos |
| PREP-02 | base | classificação assistida; reconhecimento automático de símbolos; extintor presumido por placa E-5 + piso E-17 |
| PREP-03 | base | contornos redesenháveis, área/perímetro/incerteza; falta ligar a ambiente semântico |
| PREP-04 | base | dicionário de símbolos no pacote (`simbolos.yaml`, citando NT 1-03 Anexo A) |

### Geometria e regras
| ID | Estado | Observação |
|---|---|---|
| GEO-01 | **feito** | `ToleranceProfile` experimental, `compare_minimum/maximum` |
| GEO-02 | base | área/comprimento com validação |
| GEO-03 | base | vão/folha/largura livre em porta classificada; revisar invalidação |
| GEO-04 | base | percurso real: Dijkstra em grade de 16 vizinhos, paredes como obstáculo, incerteza declarada |
| GEO-05 | base | cobertura de extintor/hidrante/acionador/saída, área além do limite e sem acesso |
| GEO-06 | **feito** | invariância por propriedades (Hypothesis) |
| REG-01 | **feito** | ingestão de NTs/decreto em Markdown (front matter, páginas, itens, tabelas, anexos, artigos, SHA-256); consulta e busca |
| REG-02 | base | base real v3; código v5: Tabelas 2–4 do Anexo III + Anexo C da NT 2-08 (importação real pendente) |
| REG-03 | base | enquadramento NT 1-04 Anexo B (60 divisões → risco); `risk_basis` no contexto; Anexo III Tabelas 2–4 em v4; Tabelas 5–21 pendentes |
| REG-04 | **feito** | DSL `rules/1.1`: sujeito FLOOR/SYMBOL/ROOM, exigido por valor/tabela/⌈divisão⌉, `fail_status`, portas de qualidade |
| REG-05, REG-06 | — | exigem homologação técnica |

### Arquitetura v2 (novo bloco, 20/09/2026)
| ID | Estado | Observação |
|---|---|---|
| V2-01 domínio | **feito** | `ComplianceStatus`, `EvidenceStatus`, `ReviewStatus`, `Severity`, `FindingKind`, `ConsensusStatus` em `coscip_cbm.enums`; os três status **nunca** são fundidos |
| V2-02 evidência | **feito** | `coscip_evidence`: `Evidence` imutável com localizador, hash e método; `ExtractionGap` (§54); consenso entre fontes (§55); `Claim` (§22) |
| V2-03 catálogo | **feito** | `coscip_normative.verification.catalog`: carga, validação, hash, dependências, `verify_catalog` confere toda citação contra o texto ingerido |
| V2-04 plano | **feito** | `compile_verification_plan`: aplicabilidade em três valores, aplicáveis/inaplicáveis/manuais/inconclusivos, ordem topológica, `plan_sha256` |
| V2-05 executor | **feito** | 6 perguntas fechadas (`presence`, `required_fields`, `minimum_count`, `minimum_value`, `maximum_value`, `consistency`); portas de qualidade; gating de dependência |
| V2-06 achados | **feito** | `coscip_findings`: `Finding`, `FindingGroup`, agrupamento por causa raiz, resumo executivo, texto por template |
| V2-07 catálogo piloto | **feito** | 10 checks RASCUNHO em `normative/checks/` (extintores, hidrantes, porta de qualidade); 10/10 citações conferidas |
| V2-08 CAD → Evidence | **feito** | `coscip_analysis.evidence`, execução por pavimento, `v2-findings`; extintores, hidrantes, acionador, saídas; só DXF sintético; portas (GEO-03) fora |
| V2-09 motor documental | — | fase 4 |
| V2-10 LLM / V2-11 Jev | — | fases 5 e 6; **não começar** antes de V2-08 e V2-09 |
| V2-12 UI v2 | — | fase 8 |
| V2-13 persistência | — | tabelas do §45 ainda não existem; hoje o fluxo v2 roda em memória |

### Plano de correção (`docs/plano/01-plano-de-correcao.md`, 29/09/2026)
Executado na branch `claude/admiring-einstein-n5rh19`, **um commit por fase** (a sessão não
pôde abrir uma branch por fase). Detalhe na seção 13.
| ID | Estado | Observação |
|---|---|---|
| COR-F0 CI e pacote | **feito** | CI Windows+Linux (ruff, pytest, npm build, lock conferido); `requirements/*.lock` com hash; `tools/package/portatil.py` + `release.yml`; ADR 0007. Falta: proteção da `master`, teste do zip na máquina principal, SHA-256 do Python embeddable fixado |
| COR-F1 base única | **feito** | `skills/` no repositório (9 vigentes + 8 em `transicao/`), zips pela CI, manifesto `normative/manifests/base.yaml`, índice de itens (4.738), workflow de vigência; MCP só lê `normative/fontes` |
| COR-F2 imagens e tabelas | **parcial** | Imagens de página renderizadas pela CI (`normas-midia.yml`). **108 tabelas `verificada`**, 2 `divergente`, 4 falsos positivos (`nao_tabela`), 38 capas, **148 `bruto`** (fora da lista de prioridade, salvo Decreto p. 1 e 46–57, NT 1-04 p. 20 e NT 2-01 p. 3). Lista de prioridade: NT 2-01 (T1–5, A1, A2), NT 2-02 (T1–4), NT 2-08 (T1, Anexos A–C), NT 1-04 (Anexos A–D), NT 2-11 (Anexos A–D), NT 2-14 (Quadros 1–2), NT 2-19 (Tabelas A–D2), NT 3-02 (T1–3, T5, Anexo A T1–4), NT 4-05 (T1–6, Anexos A, B, C, E), NT 5-05 e Decreto (Anexo II T1 p. 20–25 e Anexo III T2–21). Divergentes: NT 2-02 T5 (grade e texto fundem as linhas), NT 2-11 A.6 p. 14 (cabeçalho em outra coluna da grade). O motor confere contra as tabelas conferidas: enquadramento (NT 1-04 Anexo B), divisões (Decreto T1) e Anexo III T2–4. Inconsistências da fonte registradas em cada `.yaml` (`inconsistencias_da_fonte`) e no `RELATORIO.md` |
| COR-F3 skills | **feito** | correções de conteúdo, `anatomia-do-bilhete`, `protocolo-de-reducao`, `contar_bilhete.py`, `localizar_item.py` (índice), `achado.schema.json`, `verificar_links.py` verde |
| COR-F4 normativo | **feito** | `interpretation` (critério adotado, base conferida); EXT-CAD-002 por pavimento; 5.2.4 pela área da edificação (EXT-CAD-002-EXC); EXT-CAD-004 composição 5.2.5; EXT-CAD-005 (6.7); Anexo III T5–21 por altura (`sistemas-exigidos-5-21.yaml`); pacote v6 |
| COR-F5 reconhecimento | **feito** | camadas desligadas/congeladas/não plotáveis, MINSERT, ATTRIB, `object_key`, dedupe, balanço de reconhecimento e porta `quality.recognition.complete`; 19 testes de armadilha |
| COR-F6 executor | **feito** | conta objetos distintos (`COUNT_DIVERGENCE`), `accepted_evidence` aplicado, pior caso por valor ± incerteza |
| COR-F7 cálculo | **feito** | vetorial exato (grafo de visibilidade + branch and bound) como principal; FMM (`scikit-fmm`) e grade como conferência; porta `quality.geometry.consistent`; orçamento de incerteza; `confirmar_unidade` com duas referências não paralelas (≤ 0,5 %); hash canônico igual em Windows e Linux (job `determinismo` da CI) |
| COR-F8 integração | **feito** | `coscip_findings.achado.to_achado`: `Finding` → contrato comum (`achado.schema.json`), sem mudar status; `achados` em `analisar_planta` e em `v2-findings --out`; `consolidar_matriz.py` (orquestrador), `rascunho_bilhete.py` e `conferir_citacoes.py` (bilhete); processo sintético (DXF + memorial fictício) de ponta a ponta no teste. Falta: rodar a skill real com o MCP no Claude Desktop |
| COR-F9 validação | **base** | `tools/validacao/fidelidade.py` (exigências acertadas/faltantes/indevidas, citações corretas, precisão/revocação de símbolos, erro de distância; corpus fora do repositório, recusado se estiver dentro); relatório `docs/validacao/2026-09-29.md` só com a referência sintética (**corpus real não medido**); trava `homologation` (responsável, CREA/CAU, data, relatório): sem ela regra/check não fica `HOMOLOGATED`/`PUBLISHED` nem vai à produção. Todos os 30 seguem DRAFT |

### Revisão, relatório e recuperação
| ID | Estado | Observação |
|---|---|---|
| REV-01 | **feito** | decisão append-only com veredito (`final_status`, migração 0004), validação e auditoria |
| REV-02 | **feito** | revisão na tela; nova emissão do relatório com decisões e `review_snapshot` |
| REP-01 | base | relatórios HTML imutáveis (mapa SVG, citações com página, hashes, decisões) |
| REP-02, REP-03 | — | PDF e demais formatos |
| SAFE-01 | **feito** | backup do SQLite + artefatos verificados |
| SAFE-02 | **feito** | restauração em pasta separada e vazia |
| SAFE-03 | — | atualização lado a lado |
| SAFE-04 | base | escrita atômica testada; disco cheio real pendente |
| SAFE-05 | — | isolamento do parser |

### IA opcional, piloto e futuro
| ID | Estado | Observação |
|---|---|---|
| AI-01 | — | corpus cego de 100–200 tarefas |
| AI-02 | base | credencial no cofre do Windows; provedor desligado por padrão |
| AI-03 | base | `BudgetLedger` em memória; persistir em `budget_reservations` |
| AI-04..07 | — | |
| PILOT-01..06, FUT-01..09 | — | ver documento 03 do plano |

---

## 4. Dados reais: recortes, enquadramento e resultados

Enquadramento **proposto pelo assistente** a partir dos rótulos da planta — confirmar com o processo.
Coordenadas do desenho em metros (unidade confirmada em todas).

| Planta | Desenho | Pavimento | Recorte x0–x1 / y0–y1 | Divisão → risco | Resultado atual |
|---|---|---|---|---|---|
| 9715 | `475c6532…` | Térreo | 2507–2558 / 1588,8–1612 | D-2 agência bancária → Médio 1 | 8 conformes, 7 revisão, 1 dado ausente; 6 extintores (área e mínimo ok); pior percurso 20,6 ± 1,3 m > 15 m (indicativo não atende, em revisão) |
| 21471 | `7b20ec47…` | Térreo | 5561,8–5575,6 / 1641,5–1673 | M-2 depósito de GLP → Grande | 5 conformes, 5 revisão, 1 ausente; sem camada de parede; percurso 19,7 m > 10 m (indicativo) |
| 41336 | `cd8821cc…` | Térreo (depósito de GLP) | 4579,5–4607,5 / 2071,2–2089,5 | M-2 → Grande | 5 extintores presumidos (placas E5 + E17), regras de extintor com indicativo "atende" e em revisão; sem paredes; quadro "F-8 Restaurante" na folha contradiz a planta |
| 21778 | `8a5e7f0f…` | Térreo | 441,3–460,4 / 293–310,8 | A-2 multifamiliar → Pequeno | extintores conformes (15,4 ± 1,2 m ≤ 20 m) |
| 21778 | idem | Pavimento tipo (1º ao 3º) | 461,5–481 / 293–310,8 | idem | pendência: 1 extintor por andar (mínimo 2) |
| 21801 | `426ce3e8…` | Térreo e tipo | iguais ao 21778 | A-2 → Pequeno | idêntico ao 21778 (mesmo prédio, outra submissão) |

Análises mais recentes: 9715 `f2c44ad2…`, 21471 `4722e788…`, 41336 `629e6ba9…`,
21778 `e01b8890…`, 21801 `f830890d…`. O desenho `a46640fe…` (41336, revisão antiga) está vazio.

---

## 5. Histórico das sessões

### 19/09/2026

1. **Fundação e viabilidade** (`d53f65d`, `2aa8572`, `3187435`): app local, leitor DXF, viewer,
   confirmação de unidade, recorte de pavimento, benchmark, backup/restauração.
2. **Codex** (`ab0f50a`): revisão de unidades, recortes poligonais, classificação assistida,
   contornos e áreas, larguras de porta, relatório de preparação.
3. **Base normativa e análise automática** (`0ef4842`): ingestão das NTs com verificação de
   citação; DSL `rules/1.1`; pacote com 9 regras; análise da planta inteira no worker
   (`PLANT_ANALYSIS`, migração 0003); relatório HTML com mapa por pavimento.
4. **Todas as NTs e telas** (`d1468e2`): `.venv` reinstalado; 53 fontes na base real; leitor de
   decreto/artigos/anexos romanos; API de consulta e busca; CLI normativo; telas Base normativa
   e Análise da planta.
5. **Recortes, enquadramento e revisão** (`3bda712`): 7 recortes reais; tabela NT 1-04 com
   `verify_table_row`, 24 células mescladas conferidas; `risk_basis`; revisão humana
   (migração 0004) e relatório com decisões.
6. **Extintor presumido** (`c004b6a`): placa E-5 + piso E-17 → extintor presumido; regras NT201
   v2 com porta `quality.extinguisher.not_presumed`; pacote v3; 41336 reanalisado.
7. **Busca por radical** (`7837b63`) e mapa do Anexo III (`86dc8b3`, `4cfacf8`, `97e65a4`).
8. **Codex, Anexo III Tabelas 2–4** (sem commit à época): 239 células conferidas nas páginas
   26–28 do PDF oficial (SHA-256 `358fcbbd…`); `normative/base/sistemas-exigidos.yaml` e
   `coscip_normative.requirements`; formulário com ATC, pavimentos e altura da edificação;
   rota `POST /v1/rule-packages/{id}/requirements-query`; aviso de divergência quando a tabela
   traz X incondicional e o analista informa não exigido. A sessão terminou sem conseguir gravar
   no Git (`Permission denied` em `.git/index.lock`).

### 20/09/2026 — arquitetura v2, fases 1 e 2, e publicação

- A gravação no Git **voltou a funcionar** sem mudança de ACL. O trabalho do Codex que estava
  solto foi commitado junto com esta sessão; nada foi descartado.
- Suíte completa executada **antes** de qualquer mudança: **181 testes passaram** (3m40s). Era a
  verificação que a sessão anterior deixou pendente.
- Implementadas as **fases 1 e 2** da arquitetura v2, de forma aditiva (nenhum arquivo do fluxo
  atual de análise foi alterado):
  - `coscip_cbm.enums` ganhou os três status separados mais `Severity`, `FindingKind` e
    `ConsensusStatus`;
  - novo pacote `coscip_evidence` (evidência imutável, localizador, lacuna de extração, consenso,
    claim);
  - novo pacote `coscip_findings` (achado, grupo, consolidação, texto por template);
  - novo subpacote `coscip_normative.verification` (modelos de check, catálogo, contexto do
    processo, aplicabilidade, dependências, compilador, executor);
  - `coscip_rules.engine` ganhou `evaluate_condition` público, para não duplicar a lógica de três
    valores (única mudança em código existente, coberta pelos testes que já havia).
- **Catálogo piloto** em `normative/checks/`: 10 checks RASCUNHO. As 10 citações foram conferidas
  contra o texto ingerido das NTs — inclusive NT 2-04 5.1.21, cuja lista tem **oito**
  características (o documento de arquitetura esquecia "número de série").
- **62 testes novos** (13 evidência, 16 catálogo, 13 plano, 10 achados, 10 integração).
- Três correções de modelagem saíram dos próprios testes e estão registradas na seção 11.
- Repositório publicado no GitHub como **privado**, com o registro do projeto e o documento de
  arquitetura dentro dele.

### 25/09/2026 — segundo computador e fase 3 (extintores)

- Repositório clonado do GitHub em `C:\Users\raquel\Downloads\Analise\motor-coscip`;
  Python 3.12.10 e Node 24 LTS instalados via `winget`; `.venv` recriado. **243 testes passaram
  antes de qualquer mudança**, `ruff` limpo e `npm run build` padrão funcionou.
- Fase 3 para extintores, detalhes na seção 12.

---

## 6. O que existe no sistema (referência rápida)

### Telas (rotas com `#`)
- `#/base-normativa` — documentos por grupo com cobertura, busca, envio de .md, importação do pacote.
- `#/base-normativa/:id` — identificação, regras/itens citados, índice e texto do item.
- `#/desenhos/:id` — planta, camadas, medida, unidade, recortes; botão "Analisar planta".
- `#/desenhos/:id/analise` — enquadramento (ocupação → risco), saídas, pavimentos, paredes,
  blocos; histórico; resultado por região com mapa; revisão; relatório e nova emissão.

> A interface **ainda não conhece** a arquitetura v2: o Plano de Verificação e os `Finding`
> existem na camada Python, nos testes e no comando `v2-findings` (só leitura). A tela v2 é a
> fase 8.

### API de normas e análise (`/v1`)
- `POST/GET /normative/sources`; `GET /normative/sources/{id}`; `GET /normative/sources/{id}/item?item=`;
  `GET /normative/search?q=&document=`
- `POST /rule-packages/import`; `GET /rule-packages`; `GET /rule-packages/{id}`;
  `POST /rule-packages/{id}/requirements-query` (consulta do Anexo III, sem gravação)
- `GET /drawings/{id}/plant-analysis-options`
- `POST/GET /drawings/{id}/plant-analyses`
- `GET /plant-analyses/{id}`; `GET /plant-analyses/{id}/reviews`; `POST /plant-analyses/{id}/reports`
- `POST /results/{id}/reviews` — `decision` (CONFIRM/CONTEST exigem `final_status`; REQUEST_DATA não)

**Ainda não existem** as rotas do §47 da arquitetura v2 (processos, documentos, plano de
verificação, findings, evidências). Nada do fluxo v2 está exposto na API.

### Regras do pacote (todas RASCUNHO)
NT 2-01: distância a percorrer (Tabela 3: 20/15/10 m), área por unidade (250/150/100 m²), mínimo
de 2 (exceção 5.2.4), extintor ≤ 5 m de instalação especial (6.4); NT 2-02 mangueira ≤ 30 m
(5.6.1); NT 2-07 acionador ≤ 30 m (5.5.2); NT 2-08 distância à saída (limite informado pelo
analista); NT 2-05 placa E-5 junto ao extintor (heurística → revisão); NT 2-06 pontos de
iluminação na planta.

### Catálogo de checks (`normative/checks/`, todos RASCUNHO)

| Check | Tipo | Pergunta | O que depende dele |
|---|---|---|---|
| `QG-CAD-WALLS` | MANUAL_CONFIRMATION | — (sempre revisão humana) | — |
| `EXT-CAD-001` v2 | CAD_PRESENCE | `presence` de extintor, por pavimento | `EXT-CAD-002`, `EXT-CAD-003-*` |
| `EXT-CAD-002` v2 | CAD_COUNT | `minimum_count` 2 por pavimento | — |
| `EXT-CAD-003-{PEQUENO,MEDIO,GRANDE}` v2 | CAD_DISTANCE | `maximum_value` 20/15/10 m, por pavimento | — |
| `HID-REQ-001` | NORMATIVE_TABLE | `presence` do registro da exigência (tabela ou analista) | todos os HID |
| `HID-CAD-001` | CAD_PRESENCE | hidrante ou mangotinho no pavimento | `HID-CAD-002` |
| `HID-CAD-002` | CAD_DISTANCE | `maximum_value` 30 m de linha de mangueira (NT 2-02 5.6.1) | — |
| `ALA-CAD-001` | CAD_PRESENCE | acionador manual no pavimento (NT 2-07 5.5.2) | `ALA-CAD-002` |
| `ALA-CAD-002` | CAD_DISTANCE | `maximum_value` 30 m até o acionador | — |
| `SAI-CAD-001` | CAD_PRESENCE | saída no pavimento, só com saídas confirmadas | `SAI-CAD-002` |
| `SAI-CAD-002` | CAD_DISTANCE | limite do Anexo C **informado pelo analista** (`required_fact`); não vale para A-2/A-5/A-6 | — |
| `SAI-MAN-001` | MANUAL_CONFIRMATION | A-2/A-5/A-6: medir da porta da unidade (NT 2-08 5.3.3.1) | — |
| `HID-DOC-001` | DOCUMENT_PRESENCE | `presence` de ART/RRT/TRT | — |
| `HID-DOC-004` | DOCUMENT_FIELD | `required_fields` (8 campos da NT 2-04 5.1.21) | — |
| `HID-CROSS-002` | CROSS_DOCUMENT | `consistency` da pressão entre ART e curva | — |

Um check por classe de risco em vez de tabela embutida: o limite fica literal, conferível e o
compilador mostra claramente qual se aplica ao processo.

Portas de qualidade dos checks de extintor v2: `quality.extinguisher.not_presumed` (001, 002),
`quality.walls_detected` (003) e, novas, `quality.region_confirmed` (todos) e
`quality.extinguisher.complete` (003: toda a área alcançada pelo percurso). **Porta não
informada conta como não atendida.**

### Limitações conhecidas
- Mobiliário não é obstáculo; portas desenhadas fechadas isolam ambientes (→ revisão).
- Nome de região automática às vezes pega o título errado; legenda erra em casos raros.
- Área do pavimento é área útil em grade (± perímetro × célula).
- Plantas de PPCI vindas de PDF ou sem layer de parede: percurso só indicativo.
- ~~Anexo C da NT 2-08 é imagem~~ (resolvido em 25/09): o texto convertido traz a tabela
  extraída da página 22; ela está em `normative/base/distancias-saida.yaml` (pacote v5), com
  cada linha conferida. O limite do analista continua valendo e prevalece, com registro.
- O fluxo v2 ainda **não persiste nada**: plano, evidências e achados vivem em memória.
- `accepted_evidence` dos checks é declarado, mas o executor ainda não filtra por ele.
- Exigência de sistema (§30): `context.normative_requirement_<s>` (só X incondicional da consulta
  ao Anexo III), `context.human_override_<s>` (formulário) e `context.effective_requirement_<s>`
  para `hydrants`, `alarm`, `lighting`. Traço ou célula condicional **não** viram dispensa.
  Quando o analista contraria um X, `v2-findings` mostra aviso; ainda não há check para isso.
- A exceção da NT 2-01 5.2.4 (um extintor abaixo de 50 m²) continua fora do `EXT-CAD-002`;
  a área do pavimento já sai como evidência (`floor_area_m2`) para quando for modelada.

---

## 7. Ambiente

- Código: `C:\Users\USER\Downloads\motor-coscip` (branch `master`, remoto `origin` no GitHub,
  repositório **privado** da conta `lukasleocadio19-cloud`).
- Dados do app: `%LOCALAPPDATA%\MotorCoscip` (base na migração **0004**; pacotes v1, v2, v3;
  5 projetos "Corpus …").
- Corpus real: `Downloads\coscip-corpus` (**nunca** entra no repositório).
- Textos das NTs: `%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\...\skills\`
  `cbmerj-grupo-1..5-*\references\nt-*.md` (**nunca** `grupo-5-legado-nao-usar`) e
  `orquestrar-analise-cbmerj\references\decreto-42-2018-coscip-compilado.md`; imagens das páginas
  em `references\media\nt-x-yy\pagina-NN.png` (o decreto não tem).
- Preview (`Downloads\.claude\launch.json`): `motor-coscip` (porta 8765; token no log "Abrir:").
- Backup: pasta local `C:\BackupsMotorCoscip` (mesmo SSD; OneDrive recusado pelo usuário por ora).

**Segundo computador (usuário `raquel`, desde 25/09/2026):** código em
`C:\Users\raquel\Downloads\Analise\motor-coscip`; Python 3.12 em
`%LOCALAPPDATA%\Programs\Python\Python312` (`py -3.12`); Node em `C:\Program Files\nodejs`
(pode faltar no PATH de terminais abertos antes da instalação). **Aqui ainda não existem** a base
real (`%LOCALAPPDATA%\MotorCoscip`) nem `Downloads\coscip-corpus`: trazer o backup de
`C:\BackupsMotorCoscip` e restaurar com `scripts\restore\restore.ps1`. Textos das NTs nas skills
em `%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\...\skills\`.

## 8. Cuidados que já custaram tempo

- Pacote novo no `pyproject.toml` exige `pip install -e . --no-deps` no `.venv` (pytest passa
  mesmo sem, porque usa `pythonpath`).
- Glob `cbmerj-grupo-[1-5]-*` pega a pasta legado: listar as pastas explicitamente.
- Tabela convertida do PDF perde células mescladas: conferir na imagem/PDF e registrar `merged_from`.
- Conferir célula pela linha inteira da tabela, não por trecho truncado.
- `$INSUNITS` estava errado em 5 de 5 projetos: unidade sempre exige confirmação humana.
- Bloco dinâmico: estados ocultos com `invisible=1` — nunca contar sem filtrar.
- Ponto de inserção de bloco pode estar longe do desenho (21471): usar o centro da geometria.
- "EXT" em nome de bloco pode ser "externo"; "P60/P80" são portas, não placas.
- Item YAML `6.12` sem aspas vira número: sempre citar itens entre aspas.
- Saída de Python no console sai em cp1252: usar `encoding="utf-8"` / `PYTHONIOENCODING=utf-8`.
- Painel do navegador não abre `file://`; servir por `http.server` no `launch.json`.
- Rotas da interface são com `#` (`/base-normativa` sem `#` dá 404, normal).
- No Windows, `os.kill(pid, 0)` **encerra** o processo; usar `_pid_alive` do launcher.
- Pytest: `-p no:cacheprovider --basetemp <pasta nova>`; nunca apontar para dados reais.
- `alembic check` sem `COSCIP_DATA_DIR` olha a base real.
- `npm run build` pode falhar com "Acesso negado" no esbuild (alternativa na seção 9).
- Grid CSS com coluna `auto` cresce até o conteúdo: usar `minmax(0,1fr)`/`min-w-0`.
- Mapa SVG da análise vai em `<img src="data:…">` (não executa script).
- Backup antes de qualquer migração; decisões de revisão só pelo analista.
- Dados reais nunca entram no repositório; nuvem só com autorização.
- Heredoc do Bash quebra com arquivos Python longos no Windows: escrever com ferramenta de
  arquivo, não com `cat <<EOF`.
- `Path.write_text` no Windows grava CRLF; o repositório é LF (`.gitattributes`). Usar
  `write_bytes(s.encode())` ou a ferramenta de arquivo.
- Id da região de pavimento é `floor-` + 8 primeiros caracteres do id do pavimento: em teste,
  ids como `floor-0001`/`floor-0002` colidem. Com UUID real não colide.
- Check de pavimento (`scope: FLOOR`) só roda por pavimento quando `execute_plan` recebe
  `floors`; sem isso, conta a planta inteira (2 pavimentos com 1 extintor cada = "2").
- **Empate de `created_at` no Windows**: dois registros seguidos saem com o mesmo horário. Onde
  a ordem decide algo (snapshot e quadro vigentes, decisão de revisão mais nova), desempatar por
  `rowid` (ordem de inserção), nunca pelo id UUID. Listagens de tela ainda usam só `created_at`.
- Heredoc do Bash também quebra com YAML longo: gravar checks com a ferramenta de arquivo.
- Anexo C da NT 2-08: o texto convertido tem "Edificaçoẽ s" (OCR) e "35,00m" sem espaço na
  linha β; a conferência usa as células literais.
- **Decisão do analista (25/09/2026): a regra principal é o item 5.3.3.3 da NT 2-08.** Sem
  leiaute definido, limite do Anexo C reduzido **em** 30% (×0,7) e distância **direta** (linha
  reta), não a observação C ("reduzidas a 30%"). Registrada em `distancias-saida.yaml`
  (`layout_reduction`), conferida na importação; fator diferente de 0,7 é recusado.
- As imagens das páginas da NT 2-08 (`media/nt-2-08/`) **não existem** neste computador: a
  conferência visual das células do Anexo C contra o PDF oficial está pendente.

## 9. Comandos úteis

```powershell
.venv\Scripts\python -m pytest -p no:cacheprovider --basetemp <pasta-nova>   # 335 testes (~2,5 min)
.venv\Scripts\ruff check . --no-cache
.venv\Scripts\python -m coscip_api.cli backup
.venv\Scripts\python -m coscip_api.cli normative-import-sources <pasta-com-md>
.venv\Scripts\python -m coscip_api.cli normative-import-package
.venv\Scripts\python -m coscip_api.cli v2-findings <id-da-analise> --out achados.json   # só leitura
scripts\start\start.ps1
```

Build da interface quando o `npm run build` falha com "Acesso negado" (em `apps/web`):

```powershell
node ../../node_modules/typescript/bin/tsc -b
node --experimental-strip-types --input-type=module -e "import {build} from 'vite'; import config from './vite.config.ts'; await build({...config,configFile:false});"
```

## 10. Frase para abrir a próxima sessão

> Leia `docs/proxima-sessao.md` no repositório (registro único do projeto), em especial as
> seções 2, 11 e 12. Fases 1, 2 e 3 da arquitetura v2 prontas (CAD → `Evidence` por pavimento →
> `Finding`, 17 checks, comando `v2-findings`). Não há plantas reais: trabalhe com DXF
> sintético. Próximo passo: persistir plano, evidências e achados (V2-13, migração 0005 com
> backup antes) e expor as rotas de leitura do §47; depois a fase 4 (motor documental mínimo).
> Não introduza LLM nem Jev. Toda mudança com teste e atualização deste mesmo arquivo; não crie
> outro registro nem cópia.

## 11. Sessão 20/09/2026 — fases 1 e 2 da arquitetura v2

### O que foi construído

**`coscip_cbm.enums`** — os três status do §3, que nunca podem ser fundidos:
`ComplianceStatus` (COMPLIANT / NON_COMPLIANT / NOT_APPLICABLE / UNDETERMINED),
`EvidenceStatus` (SUFFICIENT / PARTIAL / MISSING / CONFLICTING / UNVERIFIED),
`ReviewStatus` (NOT_REQUIRED / PENDING / CONFIRMED / CONTESTED / DATA_REQUESTED).
Mais `Severity`, `SEVERITY_ORDER`, `FindingKind` (+ rótulos em português), `EvidenceSourceType`
e `ConsensusStatus`.

**`packages/analysis/coscip_evidence/`**
- `models.py` — `Evidence` imutável: origem, versão, hash, localizador, método de extração, valor
  bruto e normalizado, incerteza, algoritmo, confiança, porta de qualidade. A regra §53 está no
  código: `located` é falso quando não há localizador, e aí o status nasce `UNVERIFIED`.
  Declaração humana e cálculo dispensam localizador — só eles.
- `registry.py` — `EvidenceSet` (índice por sujeito+campo), `ExtractionGap` (§54: a extração
  rodou e não achou; isso **não** é ausência documental) e `consensus()` (§55, quatro estados).
  Número e texto comparam sem ruído ("73,0" == 73).
- `claims.py` — `Claim` (§22), projetando só evidência localizada e com valor.

**`packages/analysis/coscip_findings/`**
- `models.py` — `Finding` com os três status separados, `Divergence` e `MeasuredResult` (§27:
  valor, unidade, incerteza, algoritmo, versão, porta de qualidade).
- `consolidate.py` — agrupamento por causa raiz (§32), ordem da tela, `AnalysisSummary` (§36).
- `wording.py` — texto por template determinístico (§58). Nenhuma LLM redige nada.

**`packages/normative/coscip_normative/verification/`**
- `models.py` — `CheckDefinition`. `type` usa a taxonomia inteira do §6; `question.kind` é um
  conjunto **fechado** de 6 perguntas executáveis. Sem `question`, o check é manual.
  `ResultRules` recusa, na validação, qualquer regra que concluísse COMPLIANT a partir de
  ausência, conflito ou porta de qualidade reprovada.
- `catalog.py` — carga, validação, hash, dependências, `verify_catalog` (mesmo rigor do pacote de
  regras: citação que não confere impede o check).
- `context.py` — `ProcessContext` e `effective_requirement` (§30: exigência normativa, override
  humano e exigência efetiva convivem; nada é sobrescrito em silêncio).
- `applicability.py`, `dependencies.py`, `compiler.py`, `executor.py`.

### Decisões de modelagem que os testes obrigaram a corrigir

1. **`HID-REQ-001` não pode ter `applies_when`.** Estava condicionado a "a exigência é
   conhecida"; com a exigência desconhecida o check era *dispensado* — exatamente o contrário do
   certo, porque não saber é a pendência. Agora ele vale para qualquer processo.
2. **`HID-CROSS-002` não depende de `HID-DOC-004`.** A divergência de pressão entre ART e curva é
   detectável e acionável mesmo com a identificação da bomba incompleta. Depende só de
   `HID-REQ-001`.
3. **Campo ausente e valor divergente convivem no mesmo achado.** Antes o conflito escondia a
   ausência. Agora o achado carrega os dois; o tipo continua "documento incompleto" porque a
   providência é a mesma: completar a documentação.

### Verificações

- **243 testes passaram** (181 anteriores + 62 novos), `ruff check . --no-cache` limpo,
  `tsc -b` sem erro e build da interface refeito pela alternativa da seção 9.
- Catálogo conferido contra as 29 fontes dos grupos 1 e 2 ingeridas do Markdown original:
  **10/10 citações verificadas**, incluindo as nove expressões do item 5.1.21 da NT 2-04.
- O teste de integração reproduz o processo sintético do §76 e comprova, entre outras coisas:
  plano e achados reproduzíveis por hash; extintor não encontrado → inconclusivo, **nunca**
  reprovado nem conforme; porta de qualidade reprovada → sem conclusão de conformidade; medida
  dentro da incerteza → inconclusiva; check inaplicável → sem pendência.

### O que deliberadamente **não** foi feito

- Nada da interface foi tocado (fase 8).
- Nenhuma tabela do §45 foi criada: **não houve migração de banco** nesta sessão.
- Nenhuma rota do §47 foi exposta.
- Nenhuma evidência real: o CAD ainda não produz `Evidence` (fase 3) e não há motor documental
  (fase 4). Todo o teste roda com evidência sintética.
- Jev e LLM não foram tocados, como o documento de arquitetura exige.
- Nenhuma decisão humana, ocupação de processo real ou análise anterior foi alterada.

## 12. Sessão 25/09/2026 — fase 3 da arquitetura v2 (extintores)

### O que foi construído

**`coscip_analysis.evidence`** — adaptador `plant-analysis/1.0` → `Evidence`. Lê só a saída
estruturada (símbolos, cobertura, geometria e fatos `quality.*`/`floor.*` de cada região);
**não lê** `results` (vereditos das regras antigas) nem o mapa/relatório. Por pavimento (região
`PLAN`):
- cada símbolo de segurança vira uma evidência `CAD_SYMBOL` localizada (handle, camada,
  pavimento), com `source_hash` = SHA-256 do DXF; legenda e demolir ficam de fora;
- extintor presumido pela placa continua evidência, marcado com a porta
  `quality.extinguisher.not_presumed`;
- classe procurada e não achada vira `ExtractionGap` (§54);
- percurso máximo por sistema (extintor, hidrante, acionador, saída) vira `CAD_GEOMETRY` com
  valor, incerteza, `grid_dijkstra_16` versão `1.0` (agora gravado na saída da análise) e ponto
  mais distante; área útil do pavimento idem;
- região não `PLAN` (corte, fachada) é listada em `skipped_regions`, sem evidência.
`process_context` monta o `ProcessContext` com os campos do formulário como `context.*`.

**Executor (`coscip_normative.verification.executor`)**
- `FloorScope` + `execute_plan(..., floors=...)`: check `scope: FLOOR` roda uma vez por
  pavimento, só com as evidências e os fatos daquele pavimento; dependência é resolvida dentro
  do pavimento (pavimento vazio não trava o outro). Sem `floors`, o comportamento anterior.
- Porta de qualidade **não informada** agora conta como não atendida (antes só `False`
  reprovava) — mesma regra do motor de regras antigo.
- `Question.quality_gates` (várias portas além de `quality_gate`).
- Medida vinda do CAD leva `geometry_snapshot_hash` no `MeasuredResult` (§27).

**`coscip_findings`** — `Finding.scope_id`/`scope_label` e `Finding.ref`
(`EXT-CAD-002@floor-…`); `FindingGroup.scopes` diz em quais pavimentos a causa aparece.

**Catálogo** — `EXT-CAD-001/002/003-*` passam à versão 2 com `quality.region_confirmed` e, nos
003, `quality.extinguisher.complete`. As 11 citações dos 10 checks foram conferidas de novo
contra as 29 NTs dos grupos 1 e 2 nas skills deste computador: todas conferem.

**API/CLI** — `plant_service.load_output` (lê o `analysis.json` conferindo o hash, também usado
pelo relatório); `coscip_api.plant_findings.findings_for_analysis` e o comando
`v2-findings <id> [--out arquivo.json]`, **só leitura**: recusa o catálogo inteiro se alguma
citação não conferir contra a base ingerida e não grava nada.

### Verificações

- 15 testes novos em `tests/integration/test_cad_evidence.py` (DXF sintético → análise →
  evidência → plano → achado) e um passo v2 no teste de ponta a ponta da API com worker real.
  Destaques: contagem é por pavimento (dois pavimentos com 1 extintor cada reprovam os dois,
  embora a planta tenha 2); pavimento sem extintor fica inconclusivo sem contaminar o outro;
  região automática não confirmada não conclui; extintor presumido e área não alcançada não
  concluem; remover `results` e mapas da saída não muda nenhum achado (critério de aceite).
- O teste de fluxo v2 antigo ganhou as duas portas novas no contexto (sem elas, nada conclui —
  exatamente o comportamento novo).
- **Defeito antigo corrigido:** o histórico de decisões de revisão era ordenado só por
  `created_at`; no Windows duas decisões seguidas empatam e o SQLite devolvia em ordem
  arbitrária (a "mais nova" podia sair trocada). Agora desempata por `rowid` (tabela só de
  acréscimo). Achado porque o teste de ponta a ponta da API falhou uma vez na suíte completa.
- Final: **258 testes passaram**, `ruff check .` limpo, `npm run build` ok.

### O que deliberadamente **não** foi feito

- Nada gravado no banco, nenhuma rota nova na API, nada na interface.
- Nenhuma análise real foi executada ou alterada (a base real não está neste computador).
- Nenhum check novo além da versão 2 dos checks de extintor; nada de LLM ou Jev.

### Segunda parte (25/09/2026) — hidrantes, alarme e saídas

- **Sete checks novos** (seção 6): `HID-CAD-001/002`, `ALA-CAD-001/002`, `SAI-CAD-001/002`,
  `SAI-MAN-001`. Catálogo na versão 2: 17 checks, **19 citações conferidas** contra as 29 NTs
  dos grupos 1 e 2.
- **Limite informado pelo analista:** `Question.required_fact` (exclusivo com `required_value`,
  validado no catálogo). Sem o fato, o achado é `REQUIRED_LIMIT_MISSING`, a medida já apurada
  continua anexada e nada conclui. Usado na distância até a saída (Anexo C em imagem).
- **Exigência de sistema como evidência (§30):** `requirement_evidence` gera
  `hydrant_requirement`/`alarm_requirement`/`lighting_requirement` a partir da consulta ao
  Anexo III (`NORMATIVE_TABLE`, localizada pela coluna) e da declaração do formulário (`HUMAN`).
  `HID-REQ-001` passa a receber evidência real. `PlantEvidence.overrides` lista sistema com X na
  tabela declarado não exigido.
- Mangotinho conta como `hydrant` (ponto do sistema da NT 2-02), igual à cobertura do motor.
- **Defeito antigo corrigido:** snapshot e quadro de coordenadas "vigentes" desempatavam
  horário igual pelo id UUID — ao acaso. Agora por `rowid`. Achado por falha intermitente de
  `test_preparation` na suíte completa.
- 13 testes novos em `tests/integration/test_cad_checks_systems.py`. Final: **271 testes
  passaram**, `ruff` limpo, `npm run build` ok.

### Terceira parte (25/09/2026) — Anexo C da NT 2-08 como dado

O usuário pediu para tornar legível a tabela que o registro dava como "imagem". Ela já estava
no texto convertido (seção "Tabelas extraídas" da página 22), então virou dado conferível:

- `normative/base/distancias-saida.yaml` (`exit-distances/1.0`): 6 linhas (α, β, γ×2 grupos×
  piso de descarga/demais) × 4 colunas (sem/com chuveiros ou detectores × saída única/mais de
  uma) e as observações A–G com seus efeitos. **Pacote v5.**
- `coscip_normative.exit_distances`: `verify_exit_distances` confere cada linha com
  `verify_table_row` na página 22, exige que cada limite esteja escrito numa célula daquela linha
  e confere cada observação; `consult_exit_distance` só devolve limite com todos os dados
  (ocupação, tipo α/β/γ, chuveiros/detectores, número de saídas, leiaute definido). Estados:
  `FOUND`, `MISSING_DATA`, `DEPENDS_ON_FLOOR` (γ com mais de um pavimento e valores diferentes),
  `REVIEW_REQUIRED` (sem leiaute), `OUT_OF_SCOPE` (F-3 → NT 5-01, M-9 → NT 4-02, grupo fora da
  linha), `UNAVAILABLE`. Observações que **aumentam** o limite (A, +100%) não são aplicadas.
- Pacote: `exit_distances` no manifesto, conferido em `verify_package`; análise grava
  `context.exit_distance_reference`; rota `POST /v1/rule-packages/{id}/exit-distance-query`.
- Adaptador (§30): `context.normative_exit_max_distance_m` (tabela),
  `context.human_override_exit_max_distance_m` (formulário) e
  `context.effective_exit_max_distance_m` com `..._source` (linha, coluna, página ou "informado
  pelo analista"); `PlantEvidence.overrides` inclui `exit_max_distance_m` quando divergem.
- `SAI-CAD-002` v2 usa o limite efetivo; `MeasuredResult.required_source` mostra a origem.
- Interface: cartão "Saídas" com tipo de edificação, chuveiros/detectores, mais de uma saída,
  leiaute definido e o painel `ExitDistancePanel` com o limite da tabela ao vivo; o campo do
  analista virou "limite informado pelo analista (opcional)". **Não conferido visualmente no
  navegador** (sem base real neste computador); `tsc` estrito e build ok.
- Conferido contra as fontes reais: **pacote v5 inteiro verifica nas 53 fontes**; Anexo C com 6
  linhas e 6 observações conferidas.
- 22 testes novos (19 em `tests/unit/test_exit_distances.py`, 3 no adaptador) e a consulta na
  API dentro do teste de ponta a ponta. Final: **293 testes passaram**, `ruff` limpo, build ok.

### Quarta parte (25/09/2026) — piso de descarga não identificado (opção B)

- **Decisão pendente do usuário:** observação C ("reduzidas **a** 30%") × item 5.3.3.3
  ("reduzidas **em** 30%" e distâncias **diretas**). O usuário confirmou os dois textos, mas
  não escolheu a leitura: sem leiaute definido o motor continua sem consultar a tabela.
- **Faixa de limites:** quando γ tem mais de um pavimento e o limite do piso de descarga difere
  dos demais, a consulta devolve `DEPENDS_ON_FLOOR` com os dois valores, as duas linhas e a
  página; o adaptador grava o limite efetivo como lista (`[35, 40]`) com a origem.
- **Executor:** `required_fact` aceita lista de limites possíveis. Conclui só o que vale para
  todos — atende o mais exigente ⇒ `COMPLIANT`; não atende nem o mais brando ⇒
  `NON_COMPLIANT`; entre os dois (incerteza incluída) ⇒ `UNDETERMINED`,
  `LIMIT_NOT_DETERMINED`, revisão pendente. `MeasuredResult.required_candidates` mostra a
  faixa; `required` é o limite que decidiu.
- Limite do analista fora da faixa entra em `overrides`; dentro dela, não.
- **Opção A (marcar o piso de descarga no recorte do pavimento) não foi feita**: resolveria a
  faixa intermediária; exige campo novo no pavimento (migração), caixa na tela e fato por
  pavimento.
- 10 testes novos. Final: **303 testes passaram**, `ruff` limpo, build ok.

### Quinta parte (25/09/2026) — regra do item 5.3.3.3 e commit

- `layout_reduction` na tabela do Anexo C: fator 0,7, medida `DIRECT`, citação do 5.3.3.3
  conferida e a decisão escrita. `consult_exit_distance` sem leiaute devolve o limite reduzido
  (`base_limit_m`/`limit_m`, também por piso) e `measure: DIRECT`; com leiaute, `TRAVEL`.
- Motor CAD: `spatial.direct_farthest` (maior distância em linha reta de célula livre até a
  saída mais próxima, `grid_euclidean_nearest` 1.0, incerteza = meia diagonal da célula + posição
  do símbolo), só para saídas; evidência `exit_direct_distance_m`.
- `SAI-CAD-002` v3 só com leiaute definido; **novo `SAI-CAD-003`**: sem leiaute, distância
  direta contra o limite efetivo (sem porta de paredes). Leiaute desconhecido ⇒ os dois ficam
  com aplicabilidade desconhecida. Catálogo v3: 18 checks, 21 citações conferidas.
- Painel da interface mostra "tabela 40 m, reduzido em 30% (NT 2-08 5.3.3.3); linha reta".
- 11 testes novos. Final: **314 testes passaram**, `ruff` limpo, build ok; pacote v5 verifica
  nas 53 fontes.
- Todo o trabalho de 25/09 foi commitado nesta etapa.

### Sexta parte (25/09/2026) — MCP para a IA ler a planta

O usuário definiu que a maior dificuldade da IA é ler a planta e que o motor deve primeiro
ser uma ferramenta para isso. Criado `apps/mcp/coscip_mcp` (servidor MCP stdio, JSON-RPC 2.0,
só biblioteca padrão + numpy; **nenhuma dependência nova**):

- `png.py`: tela RGB e PNG via zlib, fonte 3×5 para coordenadas e números.
- `render.py`: planta com grade e rótulos em metros, paredes (camadas prováveis) em preto,
  símbolos coloridos e numerados (mesmo `n` de `listar_simbolos`), pavimentos `P1…` e o pior
  percurso da última análise.
- `workspace.py`: plantas abertas; **escala provisória** (cotas fortes → `$INSUNITS` → metros)
  até `confirmar_unidade` (medida de referência, snap para m/dm/cm/mm/pol/pé com desvio ≤ 2 %;
  recarrega e reconhece de novo); pavimentos guardados em unidades do desenho; análise com o
  motor, `plant_evidence`, Plano de Verificação e relatório compacto em português.
- `norms.py`: textos das NTs de `COSCIP_NORMAS_DIR` ou das skills (grupos 1–5 + Decreto, nunca
  o legado); pacote e catálogo conferidos; **check com citação que não confere sai do plano**
  (e quem depende dele) e é listado — não se recusa o catálogo inteiro.
- `server.py`: 10 ferramentas (`abrir_planta`, `ver_planta`, `listar_textos`,
  `listar_simbolos`, `classificar_blocos`, `medir`, `confirmar_unidade`, `definir_pavimentos`,
  `analisar_planta`, `consultar_norma`) com instruções de fluxo para a IA.
- `.mcp.json` na raiz registra o servidor para o Claude Code; README tem a configuração do
  Claude Desktop (não aplicada: é configuração do usuário).
- Smoke com as 53 fontes reais: planta sintética em mm com `$INSUNITS` = metros → provisória
  errada (legenda não reconhecida), confirmação pela parede de 14 m corrige para mm; D-2 → Médio
  1 pela NT 1-04; imagem conferida visualmente (legível, pior percurso pela porta da casa de
  bombas).
- 10 testes novos em `tests/integration/test_mcp_server.py` (inclui processo real por stdio).
  Final: **324 testes passaram**, `ruff` limpo.

Limites conhecidos do MCP: PDF não é lido; plantas grandes não
testadas no MCP (o motor levou até 20,6 s no 9715); a confirmação da unidade depende de a IA
usar a medida certa — a ferramenta aceita qualquer par de pontos que dê unidade padrão.

### Sétima parte (25/09/2026) — DWG pelo ODA File Converter

- Usuário escolheu a ODA para ler DWG. **ADR 0006**: `coscip_cad.dwg.dwg_to_dxf` converte uma
  cópia com o ODA File Converter (DXF 2018, auditoria), cache pelo SHA-256 do DWG, origem
  registrada; `abrir_planta` aceita `.dwg` e devolve `convertido_de_dwg`. O app continua só DXF.
- **Licença:** ODA File Converter gratuito = uso não comercial para não membros; produto vendido
  exige assinatura ODA ou Autodesk Design Automation.
- **Não testado com conversor real:** o ODA não está instalado neste computador (instalação e
  aceite da licença são do usuário) e não há DWG real. Testes simulam o conversor (7 testes em
  `tests/unit/test_dwg.py`). Com o ODA instalado, dá para testar ida e volta: DXF sintético →
  DWG → DXF.

### Oitava parte (25/09/2026) — MCP instalável em outros computadores

- `scripts/mcp/instalar.ps1` (UTF-8 com BOM, CRLF — PowerShell 5.1): acha o Python 3.12, cria
  `.venv`, `pip install -e .`, roda o autoteste; `-RegistrarClaudeDesktop` mescla
  `coscip-plantas` no `claude_desktop_config.json` preservando o resto, com cópia `.bak` e JSON
  sem BOM; `-RegistrarClaudeCode` usa `claude mcp add --scope user`; `-Normas` e `-Oda` viram
  `env` da entrada. Testado aqui com um arquivo de configuração de teste (não o real).
- `scripts/mcp/exportar-normas.ps1`: copia os 53 `.md` (grupos 1–5 + Decreto; nunca o
  legado) das skills para uma pasta, para levar a outro computador. Testado: autoteste com a
  pasta exportada = 53 documentos, 18 checks, 0 fora.
- `python -m coscip_mcp --verificar` (`coscip_mcp.diagnostico`): Python, dependências, planta
  sintética lida e desenhada, NTs e ODA.
- Guia: `docs/runbooks/instalar-mcp.md`.

### Nona parte (25/09/2026) — NTs no repositório e Claude Desktop configurado

- A pedido do usuário ("coloque tudo no repositório"): os 53 `.md` (52 NTs + Decreto) estão
  em **`normative/fontes`** (2,2 MB, README com origem e atualização). Ordem de busca do MCP:
  `COSCIP_NORMAS_DIR` → `normative/fontes` → skills. O MCP instala completo em qualquer
  computador. O app continua ingerindo pela CLI (`normative-import-sources normative/fontes`).
- `coscip_mcp.registro`: mescla `mcpServers["coscip-plantas"]` no
  `claude_desktop_config.json` em Python (preserva as preferências do aplicativo, cópia `.bak`,
  sem BOM, confere o JSON antes de trocar; JSON inválido não é sobrescrito). O instalador usa
  esse módulo em vez do `ConvertTo-Json` do PowerShell 5.1.
- **Claude Desktop deste computador configurado** (25/09, 21:49): entrada `coscip-plantas` →
  `.venv\Scripts\python.exe -m coscip_mcp`; cópia em
  `%APPDATA%\Claude\claude_desktop_config.json.20260925-214930.bak`; preferências conferidas
  iguais. Handshake com o comando registrado, fora da pasta do projeto: ok.
- Final: **335 testes passaram**, `ruff` limpo; tudo commitado e enviado ao GitHub.

## 13. Sessão 29/09/2026 — plano de correção (F0–F9)

Sessão em nuvem (Linux, Python 3.12 no `.venv`, sem acesso ao site do CBMERJ: o proxy bloqueia
`cbmerj.rj.gov.br`, por isso os PDFs oficiais são baixados e renderizados pela CI no workflow
`normas-midia.yml`, que grava de volta na branch). Um commit por fase na branch
`claude/admiring-einstein-n5rh19`. Nenhum dado real entrou no repositório; tudo sintético.

### O que foi feito, por fase
- **F0** — `.github/workflows/ci.yml` (Windows + Linux: lock conferido, ruff, pytest com
  JUnit, `npm ci` + build); `requirements/dev.lock` e `runtime.lock` (uv, `--universal`, com
  hash; `tools/ci/check_lock.py`); pacote portátil (`tools/package/portatil.py`,
  `release.yml`, `scripts/package/python-embed.json`, ADR 0007); marcador `windows` no pytest.
- **F1** — `skills/` (vigentes) e `skills/transicao/` (antigas a aposentar),
  `skills/pacotes.yaml`, `tools/skills/pack.py` (zips determinísticos, CI `skills.yml`);
  manifesto da base (`tools/normas/manifesto.py` → `normative/manifests/base.yaml`); índice de
  itens (`normative/indices/itens.jsonl`); vigência (`tools/normas/vigencia.py` +
  `vigencia.yml`); `coscip_mcp.norms` só lê `COSCIP_NORMAS_DIR` ou `normative/fontes`.
- **F2** — `tools/normas/render_paginas.py` (pypdfium2) e `tools/normas/tabelas.py`
  (caminho visual digitado da imagem × caminho geométrico `pdfplumber` × camada de texto;
  número tem de ser idêntico, texto por rapidfuzz ≥ 90; estado calculado; publicação idempotente
  no `.md` com a seção antiga marcada "bruto, não usar para citação"); relatório
  `normative/tabelas/RELATORIO.md`. Estado: ver seção 3.
  Leitura visual: `^` = mesclada com a de cima, `<` = com a da esquerda, `""` = em branco
  (grade completa na publicação). Normalizações iguais nos dois lados: caracteres da fonte
  Symbol (U+F0xx) → `<`, `>`, `≤`, `≥` e letras gregas; `m2` = `m²`; espaço entre letra e
  algarismo (nota sobrescrita) não conta. Forma por caminho: `forma` (comum) e
  `forma_geometrica` (só a grade do `pdfplumber`, que a extração regrava; ex. `faixa` das
  Tabelas 5–21 do Anexo III, que têm uma linha vazia entre medidas); `mesclar_linhas`
  aceita `[i, j, [colunas]]`; `celulas_verticais` (texto girado lido de trás para frente);
  `subscrito_deslocado` (γn1 lido como "γ = 0,60 n1"); `comparar_por_coluna` (grade que parte
  o registro em linhas de texto ou centraliza a célula mesclada: o texto de cada coluna, na
  ordem, tem de ser igual — sem tolerância —, e o resultado registra que a extensão da
  mescla vem só da leitura visual). Estados do manifesto: `capa` (p. 1), `nao_tabela`
  (`normative/tabelas/nao-tabelas.yaml`, conferido na imagem). `python -m tools.normas.tabelas
  diagnostico` imprime no log da CI o motivo de cada não verificada e a grade inteira
  comprimida (`GEO …`), porque o artefato não baixa daqui. `anexo3.py` só lê tabela com bloco
  `anexo3` (as T2–4 conferidas ficam fora do `sistemas-exigidos-5-21.yaml`, e a checagem das
  T2–4 no pacote ignora o bloco conferido publicado na página).
- **F3** — skills corrigidas (itens, remissões, estados do contrato), referências novas do
  bilhete, `skills/_comum/achado.schema.json` e `uso-do-mcp-coscip-plantas.md`,
  `tools/skills/verificar_links.py`.
- **F4** — `Interpretation` na DSL de regras e de checks (base conferida como citação,
  papel `interpretation`); pergunta `composition`; checks EXT-CAD-002 v3, EXT-CAD-002-EXC,
  EXT-CAD-004, EXT-CAD-005; pacote v6 com `requirements_height` (Anexo III T5–21 gerado por
  `tools/normas/anexo3.py` e conferido de novo no texto).
- **F5** — leitor DXF respeita estado de camada, expande MINSERT, lê ATTRIB; `object_key`
  (5 cm), dedupe, união de saídas, balanço de reconhecimento no MCP e no relatório;
  armadilhas sintéticas (`coscip_cad.synthetic.TRAPS`).
- **F6** — executor: contagem por objeto distinto, divergência de contagem, fonte fora de
  `accepted_evidence` recusada com nota, pior caso por valor + incerteza.
- **F7** — `coscip_analysis.vector_paths`: domínio vetorial das paredes (Shapely), grafo de
  visibilidade com Dijkstra (SciPy) e pior ponto por branch and bound (1-Lipschitz; erro de
  amostragem declarado ≤ 0,05 m); Fast Marching (`scikit-fmm`, nova dependência BSD-3) e a
  grade antiga como conferência; `uncertainty_budget` (método, amostragem, posição do símbolo =
  metade do bloco, unidade/escala, modelagem de parede; total = soma arredondada para cima)
  carregado em `Evidence` e `MeasuredResult`; porta `quality.geometry.consistent` nos 7 checks
  de distância (catálogo v6); `confirmar_unidade` do MCP exige duas referências não paralelas
  (≥ 30°) que concordem em 0,5 %; `tools/ci/determinismo.py` + job `determinismo` na CI.
  Nas plantas analíticas (corredor em L, pilar, duas portas) o erro ficou entre 0,009 e
  0,013 m com incerteza declarada 0,125 m; a grade dava ±1,1 a ±1,6 m.

- **F8** — `coscip_findings.achado` (`to_achado`/`to_achados`): o `Finding` vira achado do
  contrato comum com os três status copiados, citação com os termos conferidos (`quote` passou
  a sair em `normative_citations`), critério adotado separado, evidências e medida; o texto do
  `fato` não leva hash nem nome de algoritmo. `analisar_planta` devolve `achados`;
  `findings_for_analysis` (`v2-findings --out`) também. Esquema ganhou `outras_regras`
  (`$defs/regra`). Scripts de skill: `orquestrar-analise-cbmerj/scripts/consolidar_matriz.py`
  (valida — `jsonschema` se houver, senão conferência mínima —, não traduz, agrupa
  equivalentes e marca `divergente`), `emitir-bilhete-cbmerj/scripts/rascunho_bilhete.py`
  (entra não conforme e pendência do projeto sem revisão aberta; falta de dado vai para a nota
  interna) e `conferir_citacoes.py` (documento, dispositivo e ano da edição no índice).
  Protocolo de leitura de pranchas: com planta vetorial e GATE-0 aberto a distância é cobrada
  pela medida do motor. Aceite no teste `tests/integration/test_processo_sintetico_f8.py`
  (fixture `tests/fixtures/processo-sintetico/`, fictícia): matriz com motor + skill e bilhete
  com 2/2 citações localizadas. `jsonschema` entrou no extra `dev`.

- **F7.4 (correção)** — a CI mostrou hashes diferentes já no DXF: o ezdxf ordena a seção
  OBJECTS pela ordem de um conjunto de strings (depende de `PYTHONHASHSEED`). As plantas do
  teste de determinismo são geradas num subprocesso com `PYTHONHASHSEED=0`; a análise roda
  com semente aleatória e o teste confere sementes 1 e 2 com o mesmo hash. O JSON da CI leva o
  DXF e a saída comprimidos: em divergência o job imprime o diff.
- **F9** — `tools/validacao/fidelidade.py` e o formato do corpus-gabarito (pasta por
  processo com `gabarito.yaml` + saídas do sistema em `sistema/`); relatório
  `docs/validacao/2026-09-29.md` (corpus não medido; distâncias analíticas: erro de −0,013 a
  +0,009 m com ± 0,125 m, contra ± 1,1 a ± 1,6 m da grade); `Homologation` em
  `coscip_rules.dsl` usado por regras e checks (hash de conteúdo inalterado quando ausente).

### Decisões e cuidados desta sessão
- Testes antigos alterados **só** quando o plano muda o comportamento: portas novas nos
  fixtures (F4/F5/F7), algoritmo principal agora vetorial (F7), contrato de
  `confirmar_unidade` com duas medidas (F7.3). No F6 nenhum teste antigo foi alterado.
- Linha de parede em traço único vira obstáculo de 1 cm de meia-largura; o ponto de pior caso
  fica a ~2 cm do canto (entra na parcela de modelagem de parede).
- Interior fechado (pilar, shaft) não tem caminho: a grade já o marca como não alcançado e a
  porta `quality.<sistema>.complete` decide; o vetorial registra `unreachable_points`.
- A API (`CAD-02`) continua com uma medida (desvio ≤ 2 %); só o MCP passou a exigir duas.
- Depois de cada push, o bot do `normas-midia.yml` pode commitar na branch: `git pull --rebase`
  antes do próximo push; conflito em arquivo gerado se resolve **regenerando**, nunca à mão.
