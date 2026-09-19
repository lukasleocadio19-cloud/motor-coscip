# Guia para a próxima sessão — Motor CAD/COSCIP

Atualizado em 19/09/2026, noite (sessão Claude: todas as NTs na base real + telas "Base normativa" e
"Análise da planta").
**Este arquivo fica em `C:\Users\USER\Downloads\proxima-sessao.md` e deve ser atualizado aqui mesmo**,
sem criar outro; `motor-coscip/docs/proxima-sessao.md` é uma cópia sincronizada.
Plano: `motor-coscip/docs/plano/00-plano-completo.html` (v2.0). Status por ID: `motor-coscip/docs/backlog.md`.

## Onde estamos

- **Gate A aprovado** (19/09).
- O app real já tem **a base normativa completa** (52 NTs vigentes dos grupos 1–5 + Decreto 42/2018)
  e o pacote de regras importado. A análise da planta **tem tela** e já rodou no app real (9715).
- Nada tem valor normativo: as 9 regras são **RASCUNHO** (citações conferidas no texto, sem
  homologação técnica). As demais NTs estão na base para **consulta e citação**, sem regra automática.

## O que foi feito nesta sessão

| Parte | O que faz | Onde |
|---|---|---|
| Ambiente | `.venv` reinstalado em modo editável: os pacotes `coscip_normative`/`coscip_analysis` não eram importáveis pelo app real | `pip install -e . --no-deps` |
| Base real | backup verificado (`C:\BackupsMotorCoscip\motor-coscip-backup-20260919T172112Z`), migração 0003 aplicada, **53 fontes** ingeridas, pacote importado (9 regras, 11 itens de conferência humana) | `%LOCALAPPDATA%\MotorCoscip` |
| Leitor de fontes | aceita decreto (`DECRETO-42-2018` → `Decreto 42/2018`), indexa artigos (`Art. 15`) e anexos romanos (`Anexo III`) | `packages/normative/.../sources.py` |
| API de consulta | índice de itens da fonte, texto de um item, busca (todos os termos no mesmo item; prefere item numerado a seção/anexo inteiro; ~40 ms após a 1ª) e `GET /v1/rule-packages` completo | `normative_base.py`, `routers/normative.py` |
| CLI | `normative-import-sources <pasta>` e `normative-import-package [pasta]` | `coscip_api/cli.py` |
| Tela Base normativa | `#/base-normativa` (menu): contadores, documentos por grupo com a cobertura de cada NT, busca, envio de .md, importação do pacote (lista falhas de citação); detalhe `#/base-normativa/:id` com identificação, regras/itens citados, índice de itens e texto do item (tabelas renderizadas) | `apps/web/src/features/normative/` |
| Tela Análise da planta | `#/desenhos/:id/analise` (botão "Analisar planta" na planta): enquadramento, distância à saída, pavimentos, paredes (automático/manual), mapeamento de blocos; histórico; resultado por região com mapa, contagens, percursos, áreas declaradas, resultados com citação e página; blocos não reconhecidos → "mapear"; relatório e nova emissão | `apps/web/src/features/plant-analysis/` |

### Verificações
- **123 testes passaram** (121 + 2 novos: consulta/busca e decreto/artigos), `ruff` ok, `tsc` e
  `npm run build` ok.
- No app real, pelo navegador: busca "distância máxima percorrida" (35 itens em várias NTs),
  NT 2-01 Tabela 3 com tabela legível, análise do 9715 pela tela: concluída em 27,6 s, 20 em revisão +
  3 dado ausente (sem recorte, tudo em revisão), aba "PLANTA TÉRREO - PPCI" com 6 extintores,
  4 hidrantes, 22 luminárias, 27 detectores; pior percurso a extintor 20,62 ± 1,32 m (exigido 15 m,
  risco médio de teste → indicativo "não atende"). Relatório abre (HTML, 1 MB).

### Limitações conhecidas
- Mobiliário não é obstáculo; portas desenhadas fechadas isolam ambientes (→ revisão).
- Nome de região automática às vezes pega o título errado; legenda erra em casos raros.
- Busca é por termo exato sem acento ("percorrer" não acha "percorrida").
- Anexo C da NT 2-08 é imagem: o limite até a saída é informado pelo analista.
- Revisão humana dos resultados ainda não tem tela (a rota `/analises/:id/revisao` é esboço).

## Próximos passos, em ordem

1. **Recortar os pavimentos** das 5 plantas reais na tela da planta (nenhuma tem recorte) e rodar
   a análise pela tela nova, com o enquadramento real de cada processo (risco, ocupação, sistemas
   exigidos, limite da NT 2-08). Mapear os blocos não reconhecidos (ex.: `HR HID`).
2. Revisão humana dos resultados (REV-01/02) na tela da análise e nova emissão do relatório com as
   decisões.
3. Enquadramento a partir da base: sugerir classe de risco e sistemas exigidos pela NT 1-04 e pelo
   Decreto 42/2018, Anexo III (os textos já estão na base e citáveis por artigo/anexo).
4. Melhorias da análise: mobiliário como obstáculo opcional, portas fechadas, largura/número de
   saídas (NT 2-08 5.3).
5. Novas regras de outras NTs só com citação conferida (o import recusa se não conferir).
6. Homologação das regras com responsável técnico (REG-05/06) — só então valor normativo.

## Estado do ambiente

- Código: `C:\Users\USER\Downloads\motor-coscip`. Commits: `d53f65d`, `2aa8572`, `3187435`,
  `ab0f50a`, `0ef4842`. **O trabalho desta sessão ainda não foi commitado.**
- Dados do app: `%LOCALAPPDATA%\MotorCoscip` (base na 0003; 5 projetos "Corpus …"; 53 fontes;
  1 pacote; 1 análise do 9715).
- Textos das NTs: skills em `%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\...\skills\`
  (`cbmerj-grupo-1..5-*\references\nt-*.md`, **nunca** a pasta `grupo-5-legado-nao-usar`) e
  `orquestrar-analise-cbmerj\references\decreto-42-2018-coscip-compilado.md`.
- Preview: `motor-coscip` (porta 8765) em `Downloads\.claude\launch.json`; o token de sessão está no
  log "Abrir:". O app usa rotas com `#` (ex.: `http://127.0.0.1:8765/#/base-normativa`).

## Cuidados que já custaram tempo

- Pacote novo em `pyproject.toml` exige `pip install -e . --no-deps` no `.venv`, senão o app real
  não importa (os testes passam porque o pytest usa `pythonpath`).
- Glob `cbmerj-grupo-[1-5]-*` pega também `grupo-5-legado-nao-usar`: listar as pastas explicitamente.
- Rotas da interface são com `#`; `/base-normativa` sem `#` dá 404 (normal).
- No Windows, `os.kill(pid, 0)` **encerra** o processo; usar `_pid_alive` do launcher.
- Bloco dinâmico: estados ocultos vêm com `invisible=1` no bloco anônimo — nunca contar sem filtrar.
- Ponto de inserção de bloco pode estar longe do desenho (21471): usar o centro da geometria.
- "EXT" em nome de bloco pode ser "externo"; "P60/P80" são portas, não placas.
- Item YAML `6.12` sem aspas vira número: sempre citar itens entre aspas.
- Pytest: `-p no:cacheprovider --basetemp <pasta nova>`; nunca apontar para dados reais.
- `alembic check` sem `COSCIP_DATA_DIR` olha a base real (agora na 0003).
- Grid CSS com coluna `auto` cresce até o conteúdo (tabelas/pre): usar `minmax(0,1fr)` e `min-w-0`.
- Mapa SVG da análise vai em `<img src="data:…">` (não executa script); navegadores bloqueiam abrir
  `data:` em nova aba.
- Dados reais nunca entram no repositório; nuvem só com autorização.

## Comandos úteis

```powershell
.venv\Scripts\python -m pytest -p no:cacheprovider --basetemp <pasta-nova>   # 123 testes (~2,7 min)
.venv\Scripts\ruff check . --no-cache
npm run build
.venv\Scripts\python -m coscip_api.cli backup
.venv\Scripts\python -m coscip_api.cli normative-import-sources <pasta-com-md>
.venv\Scripts\python -m coscip_api.cli normative-import-package
scripts\start\start.ps1
```

## Frase para abrir a próxima sessão

> Leia `C:\Users\USER\Downloads\proxima-sessao.md` e retome pelos próximos passos (começando por
> recortar os pavimentos das plantas reais e analisar pela tela nova). Ao terminar, atualize este
> mesmo arquivo e a cópia em docs; não crie outro guia.
