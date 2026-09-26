# Motor CAD/COSCIP — versão local

Aplicação para **um operador no próprio computador Windows**: entrada DXF, geometria,
regras normativas, evidências e relatórios locais. IA por API é **opcional** e fica
desligada até ser configurada. Plano de referência: [`docs/plano/00-plano-completo.html`](docs/plano/00-plano-completo.html) (v2.0, 19/09/2026).

> Estado: o fluxo projeto → upload → importação DXF → preparação → análise da planta → revisão
> humana → relatório funciona e tem testes, com a base normativa completa (53 fontes) e um pacote
> de regras em rascunho. A **arquitetura v2** (`Check` → `Evidence` → `Finding`, Plano de
> Verificação) tem as fases 1 e 2 implementadas na camada Python; ainda não está na interface nem
> na API. **Nenhum resultado tem valor normativo**: regras e checks estão em rascunho, sem
> homologação técnica.
>
> Registro único do projeto, com o que falta e como continuar:
> [`docs/proxima-sessao.md`](docs/proxima-sessao.md).

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

## MCP: a IA lendo a planta

`apps/mcp/coscip_mcp` expõe o motor como servidor MCP local (stdio, sem dependência nova),
para o Claude ler plantas DXF com precisão em vez de "olhar" a imagem:

| Ferramenta | O que faz |
|---|---|
| `abrir_planta` | abre DXF ou DWG (cópia convertida pelo ODA File Converter, ADR 0006); visão geral: camadas, símbolos por classe, blocos não reconhecidos, unidade provisória |
| `ver_planta` | PNG com grade e coordenadas em metros, paredes em preto, símbolos numerados, pavimentos e o pior percurso |
| `listar_textos` / `listar_simbolos` | dados exatos com posição, camada e handle |
| `classificar_blocos` | ensina ao motor um bloco não reconhecido (confirmar com o usuário) |
| `medir` | distância entre pontos |
| `confirmar_unidade` | escala por medida de referência (obrigatória antes de analisar) |
| `definir_pavimentos` | recortes por janela ou polígono |
| `analisar_planta` | enquadramento (NT 1-04, Anexo III, Anexo C) + Plano de Verificação por pavimento |
| `consultar_norma` | texto de item ou busca nas NTs e no Decreto |

**Instalar em outro computador:** [`docs/runbooks/instalar-mcp.md`](docs/runbooks/instalar-mcp.md)
(`scripts\mcp\instalar.ps1 -RegistrarClaudeDesktop`; autoteste `python -m coscip_mcp --verificar`).

- **Claude Code:** o `.mcp.json` da raiz já registra o servidor (`coscip-plantas`); aprovar ao
  abrir o projeto.
- **Claude Desktop (chat):** em `%APPDATA%\Claude\claude_desktop_config.json`, dentro de
  `mcpServers`, `"coscip-plantas": {"command": "<repo>\\.venv\\Scripts\\python.exe",
  "args": ["-m", "coscip_mcp"]}`.
- Textos das NTs: `COSCIP_NORMAS_DIR` (pastas com os `.md`, separadas por `;`) ou, sem ela, as
  skills CBMERJ instaladas no Claude. Check com citação que não confere fica fora do plano e é
  listado como não verificado.
- O arquivo fica no computador, mas o que as ferramentas devolvem (textos, medidas, imagens)
  vai para o modelo. Confirmar se o sigilo do processo permite.

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
