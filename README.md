# Motor CAD/COSCIP — versão local

Aplicação para **um operador no próprio computador Windows**: entrada DXF, geometria,
regras normativas, evidências e relatórios locais. IA por API é **opcional** e fica
desligada até ser configurada. Plano de referência: [`docs/plano/00-plano-completo.html`](docs/plano/00-plano-completo.html) (v2.0, 19/09/2026).

> Estado: **fundação da fase de viabilidade.** O fluxo projeto → revisão → upload → selagem →
> importação DXF em processo separado → diagnóstico já funciona e tem testes. Preparação da
> planta, regras reais, relatório e viewer com cena ainda não existem; as rotas respondem
> `501` com o ID do backlog. Nenhum resultado aqui tem valor normativo: a única regra é a
> artificial `DEMO_DOOR_WIDTH_MIN` (`TEST_ONLY`).

## Começar

```powershell
scripts\setup\setup.ps1      # .venv com Python 3.12, dependências e build da interface
scripts\start\start.ps1      # abre http://127.0.0.1:<porta livre> no navegador
scripts\stop\stop.ps1        # encerramento controlado
```

Backup para outro dispositivo:

```powershell
scripts\backup\backup.ps1 -SetDestination E:\BackupsCoscip -Label "HD externo"
scripts\backup\backup.ps1
```

DXFs sintéticos para testar: `.venv\Scripts\python -m coscip_api.cli make-fixtures .\amostras`.

Desenvolvimento (Vite com recarga + API na porta 8765): `scripts\start\dev.ps1`.

## Stack

| Camada | Componente |
|---|---|
| Interface | React + TypeScript + Vite (build estático servido pelo FastAPI), Tailwind, TanStack Query |
| Visualização | Three.js, câmera ortográfica, buffers por layer (`packages/viewer`) |
| Backend | Python 3.12, FastAPI, Pydantic |
| Banco | SQLite (WAL, `synchronous=FULL`, FKs), SQLAlchemy, Alembic |
| CAD | ezdxf (`packages/cad`) |
| Geometria / grafos | Shapely/GEOS, NumPy, NetworkX |
| Jobs | Fila persistente no SQLite + worker em processo separado |
| IA (opcional) | `DocumentAssistant` (Gemini econômico) e `DecisionClassifier` (Jev), atrás de interfaces |
| Segredos | Cofre do Windows via `keyring` |

## Estrutura

```
apps/
  web/                 React/Vite; build vai para apps/api/coscip_api/static
  api/coscip_api/      FastAPI, sessão local, supervisor de jobs, backup, launcher, CLI
workers/local/         worker de estágios pesados (sem banco, sem chaves)
packages/
  cbm_schema/          contratos do domínio (independentes de ezdxf)
  cad/                 leitor DXF, identidade de origem, DXFs sintéticos
  geometry/            unidades, transformações 4x4, tolerâncias, medidas
  topology/            grafo do pavimento e percursos sobre topologia confirmada
  semantics/           classificação assistida (candidatos + conflitos)
  rules/               DSL fechada e motor em três valores
  storage/             filesystem local, SHA-256, publicação atômica
  jobs/                fila persistente com lease e token de tentativa
  ai_gateway/          provedores substituíveis e reserva de orçamento
  viewer/ api_client/ ui/   pacotes TypeScript
normative/             manifestos de fontes, regras (YAML) e fixtures
tests/                 unit, integration, e2e, geometry, recovery
scripts/               setup, start, stop, backup, restore, package
docs/                  arquitetura, decisões, runbooks, compatibilidade, backlog
```

## Verificação

```powershell
.venv\Scripts\python -m pytest     # 71 testes: regras, geometria, DXF, fila, API, pipeline, backup
.venv\Scripts\ruff check .
npm run build                      # tsc estrito + build estático
```

## Invariantes que o código já protege

- Falta de dado, aplicabilidade desconhecida ou incerteza que atravessa o limite **nunca** vira `PASS`.
- Unidade não declarada → execução `WAITING_INPUT` com `DRAWING_UNIT_UNCONFIRMED`.
- Originais imutáveis, gravados de forma atômica com SHA-256; caminhos resolvidos só por chave interna.
- Serviço só em loopback; Host/Origin validados; sessão por token de uso único; CSRF em mutações.
- Worker não recebe variáveis de credencial nem a pasta do perfil; só a tentativa vigente publica.
- Regra `TEST_ONLY` ou com fonte de exemplo não pode ser marcada para produção.

Dados reais e segredos ficam **fora do repositório** (pasta padrão: `%LOCALAPPDATA%\MotorCoscip`).
