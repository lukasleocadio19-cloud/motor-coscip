# Guia para a próxima sessão — Motor CAD/COSCIP

Atualizado em 19/09/2026, noite (sessão Claude, 3ª parte: extintor presumido pela sinalização;
antes: recortes reais, enquadramento pela NT 1-04, revisão humana e relatório com decisões).
**Este arquivo fica em `C:\Users\USER\Downloads\proxima-sessao.md` e deve ser atualizado aqui mesmo**,
sem criar outro; `motor-coscip/docs/proxima-sessao.md` é uma cópia sincronizada.
Plano: `motor-coscip/docs/plano/00-plano-completo.html` (v2.0). Status por ID: `motor-coscip/docs/backlog.md`.

## Onde estamos

- Gate A aprovado. Base real com **53 fontes** (52 NTs + Decreto 42/2018) e **pacote v2**
  (9 regras + tabela de enquadramento da NT 1-04), tudo com citação conferida.
  Agora **pacote v3**: extintor indicado só por placa E-5 + piso E-17 vira "presumido" e as
  regras NT201 (v2) vão para revisão quando o usam. 41336 reanalisado (`629e6ba9…`): 5 extintores
  presumidos, sem a falsa pendência.
- As 5 plantas reais têm **pavimentos recortados** e foram **analisadas com enquadramento**.
- A **revisão humana** existe na tela e entra no relatório. **Nenhuma decisão foi registrada**:
  cabe ao analista (as decisões são append-only e não se apagam).
- Nada tem valor normativo (regras em RASCUNHO, sem homologação).

## Feito nesta sessão (commits `d1468e2` e o seguinte)

| Parte | O que faz | Onde |
|---|---|---|
| Recortes | 7 pavimentos nas 5 plantas, conferidos em vistas SVG dos segmentos | base real |
| Enquadramento | `normative/base/enquadramento.yaml`: 60 divisões da NT 1-04 Anexo B → risco; 24 vêm de célula mesclada (conferidas nas imagens das p. 11–12); cada linha verificada na importação na **mesma linha da tabela** (`verify_table_row`); Médio 1/2 → coluna Médio da NT 2-01 Tabela 3 | `packages/normative`, `normative/base` |
| Tela | ocupação escolhida na lista sugere o risco e grava a origem (`risk_basis`), mostrada no relatório | `plant-analysis/PlantAnalysisPage.tsx` |
| Revisão (REV-01/02) | veredito por resultado (conforme / não conforme / não se aplica / pedir dado) com justificativa, histórico, filtro "sem conclusão"; migração **0004** (`final_status`); `GET /v1/plant-analyses/{id}/reviews`; nova emissão do relatório com coluna "Decisão humana", contagem após revisão e `review_snapshot` | `ReviewBox.tsx`, `routers/analyses.py`, `plant_service.py`, template |

### Recortes (coordenadas do desenho, m) e enquadramento proposto

Enquadramento **proposto pelo assistente** a partir dos rótulos da planta — confirmar com o processo.

| Planta | Pavimento | Recorte x0–x1 / y0–y1 | Divisão → risco | Resultado |
|---|---|---|---|---|
| 9715 | Térreo | 2507–2558 / 1588,8–1612 | D-2 agência bancária → Médio 1 | 8 conformes, 7 revisão, 1 dado ausente. Extintor: 6 un., área e mínimo ok; pior percurso 20,6 ± 1,3 m > 15 m (indicativo não atende, em revisão por área sem acesso) |
| 21471 | Térreo | 5561,8–5575,6 / 1641,5–1673 | M-2 depósito de GLP → Grande | 5 conformes, 5 revisão, 1 ausente. **Sem camada de parede** reconhecível; percurso até extintor 19,7 m > 10 m (indicativo) |
| 41336 | Térreo (depósito de GLP) | 4579,5–4607,5 / 2071,2–2089,5 | M-2 → Grande | com o pacote v3: 5 extintores **presumidos** pelas placas E5 + E17 (sem bloco), regras de extintor com indicativo "atende" e em revisão; sem paredes. O quadro "F-8 Restaurante" na folha contradiz a planta |
| 21778 e 21801 | Térreo | 441,3–460,4 / 293–310,8 | A-2 multifamiliar → Pequeno | extintores conformes (15,4 ± 1,2 m ≤ 20 m) |
| 21778 e 21801 | Pavimento tipo (1º ao 3º) | 461,5–481 / 293–310,8 | idem | **pendência**: 1 extintor por andar (mínimo 2); conferir exceção 5.2.4 (só < 50 m²) |

21778 e 21801 são o mesmo prédio (geometria idêntica nas plantas), em duas submissões.

### Verificações
- **125 testes passaram**, `ruff` ok, `alembic check` (0004) ok, `npm run build` ok.
- Backups: `C:\BackupsMotorCoscip\motor-coscip-backup-20260919T172112Z` (antes da 0003) e
  `...-20260919T180419Z` (antes da 0004).
- Na tela: origem do risco aparece; formulário de revisão abre (não enviado); 0 decisões na base.

## Próximos passos, em ordem

1. **Analista revisa** os resultados das 5 análises na tela (`#/desenhos/<id>/analise`) e faz a
   nova emissão do relatório. Sugestões: 41336 confirmar os 5 extintores presumidos, 21471/41336 marcar
   camadas de parede manualmente (item 4 do formulário) e reanalisar; confirmar as divisões.
2. Informar o limite da NT 2-08 (Anexo C, imagem) e os sistemas exigidos em cada processo.
3. Sistemas exigidos a partir do **Decreto 42/2018, Anexo III** (tabelas por divisão, área e
   altura) — mesma técnica da NT 1-04 (tabela no pacote + verificação por linha + imagem).
   Mapa já levantado (texto em `decreto-42-2018-coscip-compilado.md`, linhas ~997–2080; páginas
   26–45 do PDF): **Tabela 2** = área ≤ 900 m² e até 2 pavimentos, colunas A/D/E/G, B, C, F1–F2,
   F3/F4/F7/F8/F10, F5/F11, F6, F9, H1/H4, H2/H3, I/J/M3, L1; linhas Extintores, Sinalização,
   Iluminação, Saídas, Plano de emergência, Materiais de acabamento, Controle de fumaça — **não
   lista hidrantes nem alarme**; M-2 (GLP) não tem coluna (vai para NT 4-05). Tabelas 3–21: por
   grupo acima de 900 m² ou de 2 pavimentos, com colunas por altura. A conversão tem cabeçalhos
   de coluna quebrados em várias linhas: conferir nas imagens das páginas antes de codificar.
   Aplicação imediata: 9715 (D-2, 396 m², térreo) → Tabela 2, coluna A/D/E/G.
4. Mobiliário como obstáculo, portas fechadas, largura/número de saídas (NT 2-08 5.3).
5. Homologação com responsável técnico (REG-05/06).

## Estado do ambiente

- Código: `C:\Users\USER\Downloads\motor-coscip` (branch `master`, só local).
- Dados: `%LOCALAPPDATA%\MotorCoscip` (base na **0004**; pacotes v1, v2 e v3; análises recentes com
  enquadramento: 9715 `f2c44ad2…`, 21471 `4722e788…`, 41336 `629e6ba9…`, 21778 `e01b8890…`,
  21801 `f830890d…`).
- Textos das NTs: skills em `%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\...\skills\`
  (`cbmerj-grupo-1..5-*`, **nunca** `grupo-5-legado-nao-usar`); imagens das páginas em
  `references\media\nt-x-yy\pagina-NN.png` (úteis para conferir tabelas mescladas).
- Preview: `motor-coscip` (8765; token no log "Abrir:"; rotas com `#`). `vistas-coscip` (8798)
  serve SVGs gerados no scratchpad desta sessão (temporário).

## Cuidados que já custaram tempo

- Pacote novo no `pyproject.toml` exige `pip install -e . --no-deps` no `.venv`.
- Glob `cbmerj-grupo-[1-5]-*` pega a pasta legado: listar as pastas explicitamente.
- Tabela convertida do PDF perde **células mescladas** (risco vazio em F-2…F-11 etc.): conferir
  na imagem da página e registrar `merged_from`.
- Conferir célula por **linha inteira**, não por trecho de 300 caracteres (descrições longas).
- Saída de Python no console sai em cp1252: arquivos intermediários → `encoding="utf-8"` ou
  `PYTHONIOENCODING=utf-8`.
- Painel do navegador não abre `file://`; usar um `http.server` pelo `launch.json`.
- No Windows, `os.kill(pid, 0)` **encerra** o processo; usar `_pid_alive` do launcher.
- Bloco dinâmico: estados ocultos com `invisible=1` — nunca contar sem filtrar.
- Item YAML `6.12` sem aspas vira número: sempre citar itens entre aspas.
- Pytest: `-p no:cacheprovider --basetemp <pasta nova>`; nunca apontar para dados reais.
- `alembic check` sem `COSCIP_DATA_DIR` olha a base real.
- Grid CSS com coluna `auto` cresce até o conteúdo: usar `minmax(0,1fr)`/`min-w-0`.
- Dados reais nunca entram no repositório; nuvem só com autorização.

## Comandos úteis

```powershell
.venv\Scripts\python -m pytest -p no:cacheprovider --basetemp <pasta-nova>   # 125 testes (~2,7 min)
.venv\Scripts\ruff check . --no-cache
npm run build
.venv\Scripts\python -m coscip_api.cli backup
.venv\Scripts\python -m coscip_api.cli normative-import-sources <pasta-com-md>
.venv\Scripts\python -m coscip_api.cli normative-import-package
scripts\start\start.ps1
```

## Frase para abrir a próxima sessão

> Leia `C:\Users\USER\Downloads\proxima-sessao.md` e retome pelos próximos passos (sistemas
> exigidos pelo Decreto 42/2018, Anexo III). Ao terminar, atualize
> este mesmo arquivo e a cópia em docs; não crie outro guia.
