# Backlog local — estado da implementação

Legenda: **feito** (código + teste) · **base** (estrutura/contrato pronto, falta o fluxo) · **—** (não iniciado).
IDs e critérios de aceite vêm do documento 03 do plano.

## Viabilidade (semanas 1–4)

| ID | Entrega | Estado | Onde |
|---|---|---|---|
| POC-01 | Inventário de hardware e espaço | **feito** | 16 GB, i7-3770, RTX 3050, SSD único (relatório do corpus) |
| POC-02 | 5–10 DXFs reais autorizados | base | 5 projetos em `Downloads/coscip-corpus` (fora do repo); faltam medidas de referência |
| POC-03 | Procedimento DWG → DXF | **feito** | AutoCAD 2027 `accoreconsole` + `DXFOUT` 2018; `docs/runbooks/dwg-para-dxf.md` |
| POC-04 | Extrair entidades, layers, textos, blocos | **feito** | `coscip_cad.dxf_reader`, `tests/unit/test_dxf_reader.py` |
| POC-05 | Conferir medidas e transformações | **feito** | espelhamento, escala, unidades, blocos |
| POC-06 | Viewer com seleção | base | `packages/viewer` (render/pan/zoom; seleção pendente) |
| POC-07 | Tempo, memória e expansão | **feito** | `coscip_api.cli benchmark`; pior caso 20,6 s / 271 MB |
| POC-08 | Gate de continuidade | — | |

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
| CAD-02 | base | sugestão pelas cotas (`unit_evidence`) no diagnóstico; tela de confirmação pendente |
| CAD-03 | **feito** | instâncias sem colisão de identidade |
| CAD-04 | — | separar original/modelo/cena em snapshots |
| VIEW-01..04 | base | viewer por buffers; cena progressiva, seleção, overlays pendentes |
| PREP-01..04 | — | telas-esqueleto em `features/model-preparation` |

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
