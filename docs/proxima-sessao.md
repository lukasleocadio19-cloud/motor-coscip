# Motor CAD/COSCIP — registro único do projeto

**Este é o ÚNICO arquivo que registra informações do projeto** (estado, status por ID, histórico,
pendências, cuidados). Desde 20/09/2026 ele mora **dentro do repositório**, em
`docs/proxima-sessao.md`, e por isso passou a ter histórico de versões no Git.
`C:\Users\USER\Downloads\proxima-sessao.md` virou apenas um ponteiro para cá — não editar lá,
não criar cópia, não criar outro registro.

Última atualização: 20/09/2026, fim da sessão que implementou as fases 1 e 2 da arquitetura v2
e publicou o repositório no GitHub.
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
- As **5 plantas reais** têm pavimentos recortados e foram analisadas com enquadramento
  proposto pelo assistente (confirmar com os processos).
- **Revisão humana** pronta na tela e no relatório; **nenhuma decisão registrada** (cabe ao
  analista; decisões são append-only e não se apagam).
- **Nada tem valor normativo**: regras e checks em rascunho, sem homologação técnica (REG-05/06).

---

## 2. Pendências (o que ainda precisa ser feito)

### Com o analista (usuário)
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

1. **Importar o pacote v4 na base real.** É o que ainda falta da entrega anterior: a permissão de
   gravação em `%LOCALAPPDATA%\MotorCoscip` não foi concedida, então a base real continua em v3.
   Quando houver permissão: `normative-import-package`, reiniciar o aplicativo e conferir a tela.
2. **Conferir a interface na tela.** O build foi refeito em 20/09 pela alternativa da seção 9
   (`tsc -b` sem erro e Vite gerando `apps/api/coscip_api/static/` em 3,8 s), então o código dos
   ajustes de alerta de divergência e versão no seletor **compila**. Falta apenas a conferência
   visual no navegador, que depende do app rodando. O `npm run build` padrão continua falhando
   no esbuild com "Acesso negado".
3. **Fase 3 da arquitetura v2 — adaptar o motor CAD.** Converter os resultados que o motor já
   produz (extintores, portas, paredes, distâncias, saídas) em `Evidence`, em vez de texto de
   relatório. Critério de aceite: uma análise real produz `Finding` sem depender do texto antigo.
   É a ponte que falta para os checks já escritos receberem evidência de verdade.
4. **Fase 4 — motor documental mínimo** (ART, RRT, memorial, laudo, curva de bomba): upload,
   versionamento, extração e localização. Só depois disso os checks documentais do catálogo
   (`HID-DOC-001`, `HID-DOC-004`, `HID-CROSS-002`) deixam de depender de evidência sintética.
5. **Anexo III, Tabelas 5–21**, conferindo células e notas no PDF oficial.
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
| POC-03 | **feito** | DWG→DXF: AutoCAD 2027 `accoreconsole` + `DXFOUT` 2018 (runbook); nunca ODA |
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
| REG-02 | base | base real v3; código v4 com Tabelas 2–4 do Anexo III (importação real pendente) |
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
| V2-08 CAD → Evidence | — | **próximo passo** (fase 3) |
| V2-09 motor documental | — | fase 4 |
| V2-10 LLM / V2-11 Jev | — | fases 5 e 6; **não começar** antes de V2-08 e V2-09 |
| V2-12 UI v2 | — | fase 8 |
| V2-13 persistência | — | tabelas do §45 ainda não existem; hoje o fluxo v2 roda em memória |

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

---

## 6. O que existe no sistema (referência rápida)

### Telas (rotas com `#`)
- `#/base-normativa` — documentos por grupo com cobertura, busca, envio de .md, importação do pacote.
- `#/base-normativa/:id` — identificação, regras/itens citados, índice e texto do item.
- `#/desenhos/:id` — planta, camadas, medida, unidade, recortes; botão "Analisar planta".
- `#/desenhos/:id/analise` — enquadramento (ocupação → risco), saídas, pavimentos, paredes,
  blocos; histórico; resultado por região com mapa; revisão; relatório e nova emissão.

> A interface **ainda não conhece** a arquitetura v2: o Plano de Verificação e os `Finding`
> existem só na camada Python e nos testes. A tela v2 é a fase 8.

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
| `EXT-CAD-001` | CAD_PRESENCE | `presence` de extintor | `EXT-CAD-002`, `EXT-CAD-003-*` |
| `EXT-CAD-002` | CAD_COUNT | `minimum_count` 2 por pavimento | — |
| `EXT-CAD-003-{PEQUENO,MEDIO,GRANDE}` | CAD_DISTANCE | `maximum_value` 20/15/10 m | — |
| `HID-REQ-001` | NORMATIVE_TABLE | `presence` do registro da exigência | todos os HID |
| `HID-DOC-001` | DOCUMENT_PRESENCE | `presence` de ART/RRT/TRT | — |
| `HID-DOC-004` | DOCUMENT_FIELD | `required_fields` (8 campos da NT 2-04 5.1.21) | — |
| `HID-CROSS-002` | CROSS_DOCUMENT | `consistency` da pressão entre ART e curva | — |

Um check por classe de risco em vez de tabela embutida: o limite fica literal, conferível e o
compilador mostra claramente qual se aplica ao processo.

### Limitações conhecidas
- Mobiliário não é obstáculo; portas desenhadas fechadas isolam ambientes (→ revisão).
- Nome de região automática às vezes pega o título errado; legenda erra em casos raros.
- Área do pavimento é área útil em grade (± perímetro × célula).
- Plantas de PPCI vindas de PDF ou sem layer de parede: percurso só indicativo.
- Anexo C da NT 2-08 é imagem: limite até a saída informado pelo analista.
- O fluxo v2 ainda **não persiste nada**: plano, evidências e achados vivem em memória.

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

## 9. Comandos úteis

```powershell
.venv\Scripts\python -m pytest -p no:cacheprovider --basetemp <pasta-nova>   # 243 testes (~3 min)
.venv\Scripts\ruff check . --no-cache
.venv\Scripts\python -m coscip_api.cli backup
.venv\Scripts\python -m coscip_api.cli normative-import-sources <pasta-com-md>
.venv\Scripts\python -m coscip_api.cli normative-import-package
scripts\start\start.ps1
```

Build da interface quando o `npm run build` falha com "Acesso negado" (em `apps/web`):

```powershell
node ../../node_modules/typescript/bin/tsc -b
node --experimental-strip-types --input-type=module -e "import {build} from 'vite'; import config from './vite.config.ts'; await build({...config,configFile:false});"
```

## 10. Frase para abrir a próxima sessão

> Leia `docs/proxima-sessao.md` no repositório (registro único do projeto), em especial as
> seções 2 e 11. As fases 1 e 2 da arquitetura v2 estão implementadas e testadas, mas rodam
> com evidência sintética. Comece pela **fase 3**: converter os resultados que o motor CAD já
> produz em `Evidence`, para que os checks de extintor do catálogo recebam evidência real.
> Antes disso, resolva as duas pendências de entrega da seção 2 (importar o pacote v4 na base
> real e recompilar a interface). Não introduza LLM nem Jev. Toda mudança com teste e
> atualização deste mesmo arquivo; não crie outro registro nem cópia.

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
