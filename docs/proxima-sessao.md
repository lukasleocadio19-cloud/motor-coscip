# Guia para a próxima sessão — Motor CAD/COSCIP

Atualizado em 19/09/2026 (sessão Claude: base normativa + análise automática da planta).
**Este arquivo fica em `C:\Users\USER\Downloads\proxima-sessao.md` e deve ser atualizado aqui mesmo**,
sem criar outro; `motor-coscip/docs/proxima-sessao.md` é uma cópia sincronizada.
Plano: `motor-coscip/docs/plano/00-plano-completo.html` (v2.0). Status por ID: `motor-coscip/docs/backlog.md`.

## Onde estamos

- **Gate A aprovado**: o usuário considerou a conferência humana feita (19/09).
- O motor agora **recebe a base normativa, analisa a planta inteira e gera relatório** — pela API,
  com worker isolado e testes. **Falta a tela** (hoje é só API) e rodar no app real (ver passo 1).
- Nada tem valor normativo: as 9 regras são **RASCUNHO** redigidas pelo assistente a partir do
  texto das NTs; cada citação é conferida no texto, mas não houve homologação técnica.

## O que foi feito nesta sessão

| Parte | O que faz | Onde |
|---|---|---|
| Commit do Codex | trabalho de preparação que estava sem commit | `ab0f50a` |
| Leitor DXF | ignora entidades `invisible` (estados ocultos de blocos dinâmicos: o 9715 tinha 11.190 — cada luminária aparecia 4×) e grava ponto de inserção de blocos/textos | `coscip_cad/dxf_reader.py` |
| Base normativa | ingere as NTs em Markdown (front matter, páginas, itens 5.2.4, "Tabela 3", "Anexo C"; SHA-256); verifica citação = documento + item + termos no trecho | `packages/normative` |
| Pacote de regras | `normative/base/pacote.yaml`: 9 regras + dicionário de símbolos + 11 itens "não automatizados" com motivo. Import recusa o pacote se qualquer citação não conferir | `normative/base` |
| DSL `rules/1.1` | sujeito (pavimento/símbolo/ambiente), limite por tabela de risco, ⌈área ÷ área máx⌉, portas de qualidade com veredito *indicativo* | `packages/rules` |
| Análise da planta | símbolos (bloco > layer > texto; legenda; NOVO/EXISTENTE/DEMOLIR; agente/carga; placas embutidas); regiões (pavimentos recortados ou agrupamento automático); paredes → interior; percurso real (Dijkstra, grade de 16 vizinhos, sem cortar quina, incerteza declarada); instalações especiais; áreas declaradas × contorno | `packages/analysis` |
| Worker/API | estágio `PLANT_ANALYSIS` no worker isolado; migração 0003; rotas abaixo; relatório HTML imutável com mapa SVG por pavimento, citações com página, hashes | `plant_service.py`, `routers/normative.py`, `routers/plant_analyses.py` |

Regras (todas RASCUNHO): NT 2-01 distância a percorrer (Tabela 3: 20/15/10 m por risco),
quantidade por área (250/150/100 m²), mínimo de 2 (exceção 5.2.4), extintor ≤ 5 m de instalação
especial (6.4); NT 2-02 mangueira ≤ 30 m (5.6.1); NT 2-07 acionador ≤ 30 m (5.5.2); NT 2-08 distância
à saída (limite do Anexo C é **imagem** → informado pelo analista); NT 2-05 placa E-5 junto ao extintor
(heurística → só vira revisão); NT 2-06 pontos de iluminação na planta.

### Rotas novas
- `POST /v1/normative/sources` (arquivos .md) · `GET /v1/normative/sources`
- `POST /v1/rule-packages/import` (pacote de `normative/base`) · `GET /v1/rule-packages/{id}`
- `GET /v1/drawings/{id}/plant-analysis-options` (pacotes, pavimentos, camadas sugeridas como parede)
- `POST /v1/drawings/{id}/plant-analyses` — corpo: `rule_package_id`, `context` (`risk_class`
  PEQUENO/MEDIO/GRANDE, `occupancy`, `requires_hydrants/alarm/lighting`, `exit_max_distance_m`,
  `exits_confirmed`), `use_floors`, `obstacle_layers`, `symbol_overrides` {bloco: classe}
- `GET /v1/plant-analyses/{id}` (estado, resumo, links do analysis.json e do relatório) ·
  `POST /v1/plant-analyses/{id}/reports` (nova emissão) · `GET /v1/analyses/{id}/results`

### Verificações
- **121 testes passaram** (106 anteriores + 13 unitários + 2 de integração ponta a ponta), lint ok,
  migração 0003 sem divergência (`alembic check` numa base nova). Interface web não foi alterada.
- Base real das skills: **52 NTs** ingeridas, as 13 citações das regras + dicionário + cobertura
  **conferidas** (pacote verificado).
- Corpus real (motor rodado direto nos DXF, escala 1 m, sem recortes, risco MÉDIO de teste):
  6–29 s por projeto. 9715: planta "PLANTA TÉRREO - PPCI" com paredes, 394 m², 6 extintores,
  4 hidrantes, 22 luminárias, 27 detectores. 21778/21801: a planta de PPCI veio de PDF (layers
  `PDF_*`) → região achada, mas sem layer de parede (percurso provisório por linhas soltas).
  21471 e 41336: sem layer de parede reconhecível. Sem recorte, **todo resultado fica em revisão**
  (com o indicativo). JSON e mapas em `%TEMP%\claude\...\scratchpad` (temporários).
- Relatório de exemplo (sintético) conferido no navegador: mapa com interior, área além de 10 m e
  pior percurso até a casa de bombas.

### Limitações conhecidas (estão no relatório)
- Mobiliário não é obstáculo (a NT 2-01, 4.5, pede); portas desenhadas fechadas isolam ambientes
  (vira "área sem acesso" → revisão).
- Nome de região automática às vezes pega o título errado; legenda ainda erra em casos raros
  (9715: 2 detectores marcados como legenda).
- Blocos não reconhecidos (ex.: `HR HID`, `A$C4D0E081D`) aparecem no relatório para mapear.
- Área do pavimento é área útil em grade (± perímetro × célula).

## Próximos passos, em ordem

1. **Rodar no app real** (a base real está na migração 0002, intocada): `coscip_api.cli backup`,
   subir o app (migra para 0003), enviar as NTs de
   `%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\...\skills\cbmerj-grupo-*\references\nt-*.md`
   (exceto `legado`), importar o pacote, recortar os pavimentos das 5 plantas e analisar.
2. **Tela da análise** (`/desenhos/:id/analise`): formulário de enquadramento, escolha de camadas de
   parede, mapeamento de blocos, acompanhamento e link do relatório; tela "Base normativa".
3. CLI `normative import-sources <pasta>` / `import-package` (hoje só API).
4. Revisão humana dos resultados (REV-01/02) e nova emissão do relatório com as decisões.
5. Melhorias da análise: mobiliário como obstáculo opcional, portas fechadas, largura/número de
   saídas (NT 2-08 5.3), classificação de risco a partir da NT 1-04 / Decreto 42 Anexo III.
6. Homologação das regras com responsável técnico (REG-05/06) — só então valor normativo.

## Estado do ambiente

- Código: `C:\Users\USER\Downloads\motor-coscip`. Commits: `d53f65d`, `2aa8572`, `3187435`,
  `ab0f50a` (Codex) e o desta sessão. `scipy` adicionado às dependências (instalado no `.venv`).
- Dados do app: `%LOCALAPPDATA%\MotorCoscip` (base na 0002; 5 projetos "Corpus …").
- Preview: `motor-coscip` (porta 8765) e `relatorio-exemplo` (servidor estático do scratchpad,
  porta 8799) em `Downloads\.claude\launch.json`.

## Cuidados que já custaram tempo

- No Windows, `os.kill(pid, 0)` **encerra** o processo; usar `_pid_alive` do launcher.
- Bloco dinâmico: estados ocultos vêm com `invisible=1` no bloco anônimo — nunca contar sem filtrar.
- Ponto de inserção de bloco pode estar longe do desenho (21471): usar o centro da geometria.
- "EXT" em nome de bloco pode ser "externo"; "P60/P80" são portas, não placas.
- Item YAML `6.12` sem aspas vira número: sempre citar itens entre aspas.
- Pytest: `-p no:cacheprovider --basetemp <pasta nova>`; nunca apontar para dados reais.
- `alembic check` sem `COSCIP_DATA_DIR` olha a base real (que está na 0002).
- `npm run build` pode falhar com "Acesso negado" no esbuild; alternativa com Node no guia anterior
  (config Vite carregada via `node --experimental-strip-types`).
- Dados reais nunca entram no repositório; nuvem só com autorização.

## Comandos úteis

```powershell
.venv\Scripts\python -m pytest -p no:cacheprovider --basetemp <pasta-nova>   # 121 testes (~2,5 min)
.venv\Scripts\ruff check . --no-cache
.venv\Scripts\python -m coscip_api.cli backup
scripts\start\start.ps1
```

## Frase para abrir a próxima sessão

> Leia `C:\Users\USER\Downloads\proxima-sessao.md` e retome pelos próximos passos (começando por rodar a análise no app real após backup e pela tela da análise). Ao terminar, atualize este mesmo arquivo e a cópia em docs; não crie outro guia.
