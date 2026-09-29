# Plano de correção integral — motor + base normativa + skills

**Versão:** 1.0 · 29/09/2026 · redigido a partir da avaliação do repositório e das skills CBMERJ.
**Natureza:** documento de referência (como `arquitetura-v2.md`). O **registro único** continua
sendo `docs/proxima-sessao.md`: o estado de cada fase deste plano é marcado lá, não aqui.

Objetivo do usuário, nas palavras dele: corrigir toda a base normativa, deixar o projeto no
GitHub acessível de qualquer computador, estruturar o código de análise, cálculo determinístico
com o mínimo de incerteza, identificação dos elementos da planta **sem contagem em dobro e sem
deixar passar nada**, avaliar bibliotecas, robustecer a base normativa das skills, converter
todas as imagens de página que faltam em tabelas legíveis e tornar a análise o mais fidedigna
possível.

---

## 0. Como executar este plano

### 0.1 Ambiente

- A máquina principal do usuário (`C:\Users\Usuario`) **não tem Python nem Node** e não
  consegue instalá-los. Tem Git 2.55 com Git Credential Manager já autenticado no GitHub
  (clone em `C:\Users\Usuario\motor-coscip`).
- Portanto: **nada é validado localmente nessa máquina.** Toda execução de teste acontece em
  (a) GitHub Actions (fase F0 cria o workflow) ou (b) uma sessão com Python — Claude Code na
  web / nuvem, ou o segundo computador (`raquel`), que tem Python 3.12 e Node.
- Recomendado: executar as fases F0–F9 numa sessão **Claude Code na nuvem** ligada a este
  repositório (tem Python/Node, clona e faz push pelo app do GitHub). A sessão local serve para
  revisar e para o que depende do Windows do usuário (ODA, Claude Desktop).

### 0.2 Regras de trabalho (valem para todas as fases)

1. Uma **branch por fase** (`fase/F0-ci`, `fase/F1-base-unica`, …) e um pull request por fase.
   Merge em `master` só com a CI verde.
2. Antes de mudar código: rodar a suíte completa e anotar o número de testes (hoje 335).
3. Toda correção normativa: citação conferida pelo `verify_package`/`verify_catalog` **e**
   decisão de interpretação registrada quando o texto não diz literalmente o que a regra aplica
   (ver F4.1). Nada de item inventado.
4. Nada de LLM/Jev no fluxo determinístico (arquitetura v2, fases 5/6 continuam bloqueadas).
5. Dados reais nunca entram no repositório.
6. Ao fim de cada fase: atualizar `docs/proxima-sessao.md` (seção 2 e seção 3, IDs `COR-*`
   deste plano) — não criar outro registro.
7. Critério de "pronto" de cada fase = a lista **Aceite** da fase, verificada na CI.

### 0.3 Ordem e dependências

```
F0 CI + distribuição ─┬─> F1 base normativa única ─> F2 imagens → tabelas ─> F3 skills
                      ├─> F4 correções normativas do motor
                      ├─> F5 identificação sem dupla contagem/omissão ─> F6 contagem por objeto
                      └─> F7 cálculo com incerteza mínima
F3 + F5 + F6 + F7 ─> F8 integração skills ↔ MCP ─> F9 validação de fidelidade
```

F4, F5 e F7 podem correr em paralelo depois de F0. F2 depende de F1 (a base única decide onde
as tabelas moram).

### 0.4 Decisão já tomada pelo usuário (29/09/2026)

**EXT-CAD-002: exigir no mínimo 2 unidades extintoras POR PAVIMENTO.** A NT 2-01 não diz
"por pavimento" literalmente (5.2.5 fala em "área de risco a ser protegida"; 5.2.4 em
"edificações do risco pequeno com área inferior a 50 m²"). A regra fica como **decisão do
analista**, registrada no check e no registro (F4.1), com o texto de apoio: 5.2.5 (mínimo de
dois), 6.7 (multifamiliar: extintores nas circulações dos pavimentos) e a vedação de extintor
sobre rodas proteger pavimentos diferentes. A redação do achado deixa de dizer "a NT 2-01 exige
por pavimento" e passa a dizer "critério adotado: …".

---

## F0 — CI, dependências travadas e distribuição portátil (COR-F0)

**Por quê:** hoje os 335 testes só rodam no PC de quem desenvolve; a máquina principal não tem
Python; o projeto precisa rodar "em qualquer computador".

### F0.1 CI no GitHub Actions
- Criar `.github/workflows/ci.yml`:
  - `windows-latest` (principal) e `ubuntu-latest` (detecta dependência de plataforma);
  - Python 3.12 (`actions/setup-python`), cache de pip; Node 24 (`actions/setup-node`);
  - `pip install -e .[dev]`; `ruff check .`; `pytest -p no:cacheprovider`;
    `npm ci && npm run build`;
  - variável `COSCIP_NORMAS_DIR` apontando para `normative/fontes` (a CI nunca procura skills);
  - publicar o relatório do pytest (JUnit XML) como artefato.
- Marcar testes que dependem do Windows (`os.kill`, `keyring`, PowerShell) com
  `@pytest.mark.windows` e pular no Linux, em vez de deixá-los falhar.
- Proteção da branch `master` (configuração do GitHub, feita pelo usuário): exigir CI verde.

### F0.2 Dependências travadas
- Gerar `requirements.lock` (pip-tools `pip-compile --generate-hashes` ou `uv pip compile`)
  a partir do `pyproject.toml`, por plataforma (win/linux). A CI instala pelo lock.
- `package-lock.json` já existe: a CI usa `npm ci`.

### F0.3 Pacote portátil (roda sem instalar Python)
- Workflow `release.yml` (disparado por tag `v*`), em `windows-latest`:
  1. baixa o **Python embeddable 3.12 (amd64)** oficial e confere o SHA-256;
  2. habilita `site-packages` no `python312._pth`, instala as dependências do lock dentro da
     pasta;
  3. copia o código, `normative/`, o build estático da interface;
  4. gera `MotorCoscip-<versão>-win64.zip` + `SHA256SUMS` e anexa à Release do GitHub.
- Scripts dentro do zip: `iniciar.cmd` (app), `mcp.cmd` (servidor MCP), `verificar.cmd`
  (`python -m coscip_mcp --verificar`). Tudo roda da pasta descompactada, sem admin.
- `scripts/mcp/instalar.ps1` ganha o modo `-Portatil <pasta>`: registra o MCP apontando para o
  `python.exe` do pacote.
- Atualizar `scripts/package/README.md` (hoje "adiado") e ADR nova `0007-pacote-portatil.md`.

### F0.4 Documentação desatualizada
- README: "71 testes" → número real, gerado pela CI (badge do workflow).
- `normative/base/pacote.yaml` (`coverage`, item Anexo C) e
  `normative/base/regras/NT208_SAIDA_DISTANCIA.yaml` (comentário): o Anexo C **não** é mais
  imagem; é dado do pacote v5 (`distancias-saida.yaml`).
- `proxima-sessao.md` §3 POC-03 "nunca ODA" × ADR 0006: reescrever como "accoreconsole para
  o corpus; ODA File Converter no MCP (ADR 0006)".

**Aceite F0:** CI verde em Windows e Linux; tag `v0.2.0` gera zip portátil; zip descompactado
numa máquina sem Python executa `verificar.cmd` com sucesso (teste manual do usuário na máquina
principal); README sem número de testes fixo.

---

## F1 — Base normativa única, versionada e com hash (COR-F1)

**Por quê:** hoje o texto das NTs existe em **três cópias** (skills em `%APPDATA%`,
`normative/fontes`, banco do app). O MCP prefere a do repositório; correção feita nas skills
não chega ao motor, e vice-versa. As skills instaladas são cópia sincronizada da conta
claude.ai: editar em `%APPDATA%` é perdido na próxima sincronização.

### F1.1 O repositório vira a fonte das skills
- Criar `skills/` no repositório com as skills CBMERJ **vigentes** (não o legado):
  `orquestrar-analise-cbmerj`, `analisar-processo-cbmerj`, `cbmerj-atos-administrativos`,
  `cbmerj-grupo-1..5-*`, `emitir-bilhete-cbmerj`.
- As referências `nt-*.md` e o Decreto **não são duplicados** dentro de `skills/`: ficam só em
  `normative/fontes/` e o empacotador copia para `skills/<grupo>/references/` na hora de gerar
  o zip.
- `scripts/skills/empacotar.ps1` (e `tools/skills/pack.py` para a CI): gera
  `dist/skills/<nome>.zip` prontos para enviar em claude.ai → Configurações → Skills.
  Workflow `skills.yml` publica os zips como artefato a cada merge.
- O envio dos zips para a conta é **manual, feito pelo usuário** (é configuração da conta).

### F1.2 Manifesto da base
- `normative/manifests/base.yaml`: para cada fonte — documento, edição, portaria, URL oficial,
  `sha256_pdf` (já existe no front matter), `sha256_md`, data de captura, páginas, lista de
  imagens de página e estado de conferência de cada tabela.
- Teste `tests/unit/test_base_manifest.py`: todo `.md` em `normative/fontes` está no manifesto,
  o hash confere, toda imagem referenciada existe (hoje **434 referências quebradas**).
- `coscip_mcp.norms.source_files`: remover o fallback de glob nas skills (`roots[:1]` pega uma
  pasta arbitrária); passar a exigir `COSCIP_NORMAS_DIR` ou `normative/fontes`.

### F1.3 Vigência
- `tools/normas/vigencia.py` + workflow agendado mensal (`vigencia.yml`): baixa os PDFs das URLs
  oficiais do manifesto, compara `sha256_pdf`; se mudar, abre uma issue "NT x-yy mudou no portal"
  com o hash antigo e o novo. **Nunca** substitui o texto automaticamente.
- A base foi capturada em 23/07/2026: a primeira execução desse workflow é o controle de
  vigência que todas as skills pedem.

**Aceite F1:** uma única cópia do texto de cada NT; zips de skills gerados pela CI;
`test_base_manifest` passando (depois de F2 fechar as imagens); workflow de vigência roda e
reporta.

---

## F2 — Imagens de página → tabelas legíveis (COR-F2)

**Por quê:** as tabelas complexas saíram quebradas na conversão (ex.: NT 2-01 Tabela 3 fundida
com o texto do item 6.1.1; NT 2-08 Anexo C com OCR "Edificaçoẽ s") e as imagens que deveriam
permitir a conferência **não existem**: 0 de 434 no repositório; nas skills, o Grupo 2 inteiro
(~207 páginas) está sem `media/`.

Referências quebradas por NT (repositório): Grupo 1 = 49 (1-03: 12, 1-04: 14, 1-07: 17, …);
Grupo 2 = 207 (2-14: 46, 2-03 P2: 22, 2-08: 22, 2-18: 20, 2-05: 18, 2-11: 15, 2-09: 11,
2-19: 12, …); Grupo 3 = 48; Grupo 4 = 69; Grupo 5 = 61.

### F2.1 Renderizar as páginas
- `tools/normas/render_paginas.py`: para cada fonte do manifesto, baixa o PDF oficial, confere
  `sha256_pdf` (recusa se diferente), renderiza **só as páginas referenciadas** com
  `pypdfium2` (150–200 dpi, PNG otimizado) em `normative/fontes/media/<nt>/pagina-NN.png`,
  exatamente nos caminhos que os `.md` já citam.
- Rodar na CI/nuvem (a máquina do usuário não tem Python). Tamanho estimado: 434 páginas ×
  ~150 KB ≈ 65 MB → avaliar Git LFS para `*.png` em `normative/fontes/media/`
  (`.gitattributes` já marca png como binário).

### F2.2 Extrair tabelas em dois caminhos independentes
Para cada página com tabela (lista gerada pelo manifesto + marcadores "Tabelas extraídas"):
1. **Extração geométrica** do PDF com `pdfplumber` (células pelas linhas da tabela, texto por
   coordenada) → `normative/tabelas/<nt>/<tabela>.yaml` com célula, linha, coluna,
   `merged_from`, página e bbox.
2. **Leitura visual** da imagem da página (sessão com leitura de imagem) célula a célula.
3. Comparação automática: célula igual nos dois caminhos → `verificada`; diferente →
   `divergente` com os dois valores; ilegível → `pendente_humano`. Nada é resolvido em silêncio.
- Normalização de OCR com `rapidfuzz` (score registrado; ex.: "Edificaçoẽ s" ≈ "Edificações"),
  sem alterar o texto-fonte.

### F2.3 Publicar as tabelas nos `.md`
- Para cada tabela verificada, inserir no `.md` da NT, logo após o marcador da página, um bloco
  `### Tabela N — <título> (conferida)` em Markdown limpo, com nota
  `Fonte: NT x-yy, página P, tabela N; conferida em <data> (geométrica + visual)`.
- A seção antiga "Tabelas extraídas" permanece (é o registro bruto), marcada como "bruto, não
  usar para citação".
- Prioridade (maior impacto na análise): NT 2-08 (Anexo A população, Anexo C distâncias,
  tabelas de largura/escadas), NT 2-01 (Tabelas 1–5), Decreto Anexo III Tabelas 5–21,
  NT 1-04 (Anexos B–D), NT 2-02 (tabelas de sistemas/RTI), NT 2-11 (brigada), NT 5-05
  (atendimento médico), NT 2-14, NT 2-18, NT 2-19, NT 3-02, NT 4-05; depois o resto.

**Aceite F2:** 434/434 imagens presentes; toda tabela das NTs prioritárias com estado
`verificada` ou `divergente`/`pendente_humano` explícito; `test_base_manifest` verde; relatório
`normative/tabelas/RELATORIO.md` com contagem por estado.

---

## F3 — Correções e robustecimento das skills (COR-F3)

Aplicar nas skills dentro de `skills/` (F1) e gerar os zips.

### F3.1 Defeitos objetivos
| Skill | Defeito | Correção |
|---|---|---|
| `emitir-bilhete-cbmerj` | cita 4 referências e 2 scripts que **não existem** (`anatomia-do-bilhete.md`, `edicoes-vigentes.md`, `banco-de-citacoes.md`, `protocolo-de-reducao.md`, `localizar_item.py`, `contar_bilhete.py`) | criar os seis. `edicoes-vigentes.md` gerado do manifesto (F1.2); `banco-de-citacoes.md` gerado do índice item→página (F3.3); `contar_bilhete.py` conta caracteres e bytes UTF-8 por item |
| `analise-le-completa-pdf` | mapeamento errado: Inflamáveis → 4-03 (é tombada), Explosivos → 4-06 (é posto; correto **4-04**), Heliponto → 4-11 (é Covid; correto **3-07**) | corrigir a tabela pela `matriz-de-roteamento.md` |
| `analise-le-completa-pdf` | raio de extintor invertido ("15 m risco pequeno, 20 m risco baixo") | NT 2-01 Tabela 3: pequeno 250 m²/20 m; médio 150 m²/15 m; grande 100 m²/10 m |
| `analise-le-completa-pdf` | "2A:20BC risco pequeno; 3A:40BC risco médio", RTI "8.000 L … 24.000 L" sem fonte | substituir por remissão à Tabela 1/2 da NT 2-01 e às tabelas da NT 2-02 (F2), sem número de memória |
| `analise-le-completa-pdf` | `STATUS GERAL: APROVADO` | estados do contrato de papéis: tecnicamente favorável / desfavorável / pendente de saneamento / dependente de decisão humana |
| `analise-eventos-completa-pdf` | trio elétrico/carro de som → NT 5-02 | **NT 5-03** |
| `analise-eventos-completa-pdf` | "2 a 3 pessoas/m²" sem fonte; `STATUS: APROVADO` | coeficientes da NT 2-08 Anexo A / NT 5-04 (tabela F2); estados do contrato |
| `analise-ca-completa-pdf` | conferida (5.5.7 b, j, l, m, n; receita 116 corretas) | só trocar `APTO PARA EMISSÃO` pelos estados do contrato |
| `analisar-processo-cbmerj` | `inventariar_dossie.py` não percorre subpastas; DWG só lê a assinatura | `rglob`; DWG remete ao MCP (`abrir_planta`) para leitura real |
| `cbmerj-grupo-5-legado-nao-usar` | instalada, 6,8 MB duplicados | remover da conta |

### F3.2 Unificar as duas gerações
- As `consulta-nt-grupo1..5` e as três `analise-*-completa-pdf` são escritas de memória, sem
  item/página, e competem com as `cbmerj-*` no roteamento.
- Absorver o que elas têm de bom como **referências** do `analisar-processo-cbmerj`:
  `protocolo-leitura-pranchas.md` (varredura em 9 quadrantes, regras de não-cobrança, leitura
  do Quadro Resumo linha a linha, autoconferência dos riscos específicos) e
  `checklist-documental-le.md`.
- Aposentar as oito skills antigas (remover da conta) depois que os zips novos forem enviados.

### F3.3 Índice de citações para todas as skills
- `tools/normas/indice_itens.py` (reaproveita `coscip_normative.parse_markdown`): gera
  `normative/indices/itens.jsonl` (documento, edição, item, página, primeiras palavras) e
  `banco-de-citacoes.md`. O `localizar_item.py` do bilhete consulta esse índice.

### F3.4 Contrato de saída comum
- Todas as skills passam a emitir achados no esquema do grafo (`achado.schema.json`: fato,
  regra, fonte com página, evidência esperada/localizada, resultado, severidade, confiança) —
  o mesmo vocabulário do `Finding` do motor (`ComplianceStatus` / `EvidenceStatus` /
  `ReviewStatus`), para o F8 cruzar os dois sem tradução.

**Aceite F3:** script `tools/skills/verificar_links.py` (links e scripts citados existem) verde
para todas as skills; nenhuma NT citada fora do catálogo; zips gerados; skills antigas listadas
para remoção.

---

## F4 — Correções normativas do motor (COR-F4)

### F4.1 Interpretação explícita (o `verify_catalog` confere a frase, não o alcance)
- Novo campo opcional nos checks e regras:
  ```yaml
  interpretation:
    scope: POR_PAVIMENTO
    basis: [{document: NT 2-01, item: "5.2.5", quote: [...]}, {document: NT 2-01, item: "6.7", quote: [...]}]
    decision: "Critério adotado pelo analista em 29/09/2026: mínimo de 2 por pavimento."
    decided_by: analista
    decided_on: 2026-09-29
  ```
- O verificador confere as citações de `basis` como as demais. Relatório e achado mostram
  "critério adotado" separado de "texto da norma".
- Auditar os 18 checks e as 9 regras: cada um que aplica escopo/limite além da literalidade
  recebe `interpretation` (candidatos: `EXT-CAD-002`, `NT201_EXT_MINIMO`, `SAI-CAD-003`
  (já tem a decisão 5.3.3.3 no pacote — migrar para o mesmo formato), `HID-CAD-002`).

### F4.2 Extintores (NT 2-01)
- `EXT-CAD-002` v3: 2 por pavimento (decisão 0.4), redação "critério adotado".
- Exceção 5.2.4 no nível da **edificação**: aplica-se quando risco = PEQUENO e
  `context.atc_m2 < 50` (ATC do formulário), não pela área do pavimento; dispensa o
  EXT-CAD-002 com achado informativo citando 5.2.4.
- **Novo `EXT-CAD-004` (composição, 5.2.5):** no pavimento, pelo menos um extintor classe A e
  um classe B/C, ou dois ABC. Usa `attrs.agent` do símbolo; agente desconhecido →
  `UNDETERMINED` (nunca conforme).
- **Novo `EXT-CAD-005` (6.7, multifamiliar A-2/A-5):** extintores nas áreas de uso comum e
  circulações de cada pavimento — `MANUAL_CONFIRMATION` até existir a região semântica
  "circulação".
- `NT201_EXT_AREA` (motor antigo): tirar a porta `quality.walls_detected` (contagem por área
  não depende de parede) e registrar que cada símbolo conta como **uma unidade extintora sem
  conferir capacidade** (Tabela 1 continua como item não automatizado).

### F4.3 Demais
- Revisar `sistemas-exigidos.yaml` (Anexo III, Tabelas 2–4) contra as tabelas conferidas no F2
  e implantar as **Tabelas 5–21** (pendência 5 do registro), com o mesmo rigor de célula.
- `pacote.yaml` → v6, `catalogo.yaml` → v4. Importar na base real somente quando houver
  permissão de escrita em `%LOCALAPPDATA%\MotorCoscip` (pendência 1 do registro).

**Aceite F4:** todos os checks com `interpretation` quando necessário; testes de EXT-CAD-002
(por pavimento), 5.2.4 (edificação < 50 m²), EXT-CAD-004 (A+BC, 2×ABC, agente desconhecido);
pacote e catálogo verificam nas 53 fontes.

---

## F5 — Identificação da planta sem contagem em dobro e sem omissão (COR-F5)

**Princípio:** toda inserção (INSERT) e todo texto curto do desenho termina em **exatamente um**
destino — `reconhecido(classe)`, `ignorado(motivo)` ou `não_reconhecido` — e o relatório
mostra o balanço. Nada some sem motivo; nada entra duas vezes.

### F5.1 Armadilhas encontradas no código atual e correção
| Armadilha | Onde | Efeito | Correção |
|---|---|---|---|
| MINSERT (inserção em matriz, `row_count`/`column_count` > 1) | `DxfReader._walk` usa só `e.matrix44()` | matriz de luminárias/sprinklers conta **1** | expandir com `Insert.multi_insert()`; identidade `handle#r,c` |
| Camada desligada, congelada ou `plot=False` | não verificado | símbolo invisível conta | ler estado da camada (`on`, `frozen`, `freeze in viewport`); ignorar com motivo `LAYER_OFF` |
| Bloco duplicado no mesmo ponto (erro comum de CAD) | não há deduplicação espacial | conta em dobro | agrupar por classe com `shapely.STRtree` (tolerância 0,05 m + mesmo bloco/rotação) → 1 objeto, `duplicates=[handles]` |
| Placa S-12/S-14 gera `SAIDA` além do bloco/texto de saída na mesma porta | `recognize()` | saída em dobro | fundir SAIDA a ≤ 1,0 m em um objeto com várias evidências |
| Texto "EXTINTOR"/"SAÍDA" fora do bloco, junto do símbolo | `_text_symbols` | pode duplicar | texto a ≤ raio de atributo de um símbolo da mesma classe vira atributo, não símbolo |
| Bloco não reconhecido **dentro** de outro não reconhecido | `unrecognized` conta só `len(path)==1` | omissão silenciosa | inventariar em todos os níveis, com caminho |
| Símbolo explodido (linhas soltas, sem bloco) | não detectado | omissão | detector de assinatura geométrica opcional (círculo + texto de agente, triângulo de extintor da NT 1-03) → `candidato_revisão`, nunca conforme |
| XREF | só aviso | conteúdo ausente | bloquear conclusão (`quality.xref_resolved=false`) e pedir o pacote |
| Paper space com geometria | aviso | parte da planta fora | listar e permitir analisar o layout |
| ATTRIB com agente/capacidade (ex.: `AGENTE=PQS`) | lido como texto solto | atributo perdido | ler `ins.attribs` como atributos do símbolo |
| Legenda (quadro de simbologia) | heurística `mark_legends` | falso positivo/negativo | manter e acrescentar: região marcada pelo analista como legenda tem prioridade; teste com as 3 disposições comuns |

### F5.2 Identidade do objeto
- `object_key` estável por objeto físico: classe + posição arredondada à tolerância + caminho de
  instância raiz. Evidência e achado passam a apontar para `object_key` (usado no F6).

### F5.3 Balanço de reconhecimento (novo artefato da análise)
- `recognition_ledger`: total de inserções e textos curtos por destino e motivo; lista de
  blocos não reconhecidos com contagem e camada; taxa de cobertura
  `reconhecidos+ignorados / total`.
- Porta de qualidade nova `quality.recognition.complete`: nenhum bloco não reconhecido
  **em camada de segurança** (padrões `_SAFETY_LAYER`) e nenhum XREF pendente. Checks de
  contagem e distância exigem essa porta → um extintor não reconhecido **impede** "conforme".

### F5.4 Testes-armadilha
- `coscip_cad.synthetic` ganha um DXF por armadilha (MINSERT 3×4, camada congelada, bloco
  duplicado, S-12 + SAÍDA, bloco aninhado desconhecido, extintor explodido, XREF, ATTRIB com
  agente, legenda). Cada teste afirma a contagem exata e o motivo de cada ignorado.
- Propriedade (Hypothesis): espelhar/rotacionar/escalar/transladar a planta não muda a
  contagem nem os `object_key` relativos.

**Aceite F5:** balanço fecha 100% em todos os DXFs sintéticos; cada armadilha com teste;
nenhum objeto contado duas vezes nos testes; relatório mostra o balanço.

---

## F6 — Executor conta objetos, não evidências (COR-F6)

**Por quê:** `executor._counting` conta evidências localizadas; `accepted_evidence` é declarado
mas não filtrado; `EXT-CAD-001` aceita CAD, MEMORIAL e HUMANO. Quando o motor documental (fase
4 da arquitetura) trouxer o mesmo extintor pelo memorial, um pavimento com **1** extintor pode
sair "conforme" no mínimo de 2.

- `_counting` e `_comparison` filtram por `question.accepted_evidence` (tipo de fonte).
- Contagem = número de `object_key` distintos. Evidências do mesmo objeto por fontes diferentes
  viram **consenso** (`coscip_evidence.consensus`), não soma.
- Contagem por fonte divergente (CAD diz 1, memorial diz 3) → achado `DIVERGENCE`, nunca
  conforme.
- `_comparison`: escolher a medida pior **considerando a incerteza** (maior `valor + incerteza`
  para máximo), não só o maior valor.
- Testes: mesmo extintor em CAD+memorial conta 1; fonte não aceita é ignorada com registro;
  divergência de contagem entre fontes; pior medida por incerteza.

**Aceite F6:** testes acima verdes; nenhum teste antigo alterado para passar.

---

## F7 — Cálculo determinístico com incerteza mínima (COR-F7)

**Situação atual:** percurso por Dijkstra em grade de 16 vizinhos; incerteza declarada =
3 % da distância + 2 células + 0,30 m de posição do símbolo (`spatial.travel_uncertainty`).
Com célula de 0,2–1,0 m, isso dá **±1,3 a ±2,9 m** em 20 m (no 9715: 20,6 ± 1,3 m). Muitos
achados caem em "inconclusivo" só pela incerteza do método.

### F7.1 Método vetorial exato (principal)
- Obstáculos como polígonos vetoriais (paredes do DXF + espessura; portas abertas como vãos),
  montados com Shapely.
- **Grafo de visibilidade** (Shapely + NetworkX, já dependências): nós = vértices convexos dos
  obstáculos + origens (símbolos) ; arestas = segmentos livres (teste com `STRtree`). Menor
  caminho euclidiano **exato** entre dois pontos (sem erro de discretização).
- Pior ponto do pavimento: distância geodésica é 1-Lipschitz → avaliar em vértices do interior
  + amostragem da borda com espaçamento `s`; erro de amostragem ≤ `s/2` (declarado).
  Com `s = 0,10 m` → ±0,05 m.
- Posição do símbolo: centro geométrico do bloco (já calculado quando ≤ 5 m) com incerteza =
  metade do tamanho do símbolo, não 0,30 m fixo.

### F7.2 Método independente de conferência
- Manter a grade atual **e** acrescentar Fast Marching (`scikit-fmm`, eikonal de 2ª ordem) como
  segundo método. Os três resultados vão para a evidência; se vetorial e FMM divergirem mais
  que a soma das incertezas → porta `quality.geometry.consistent=false` (não conclui).

### F7.3 Orçamento de incerteza explícito
- `MeasuredResult.uncertainty_budget`: {método, amostragem, posição do símbolo, unidade/escala,
  modelagem de parede} — cada parcela com origem. Incerteza total = soma (conservador).
- Escala: `confirmar_unidade` passa a exigir **duas** medidas de referência independentes
  (não paralelas); desvio entre elas > 0,5 % bloqueia. Hoje aceita um par qualquer com
  tolerância de 2 %.

### F7.4 Determinismo
- Mesma entrada ⇒ mesmo `analysis.json` byte a byte em Windows e Linux: ordenação por
  `object_key`/handle, arredondamento fixo (`decimal` para valores normativos), sem dependência
  de ordem de dicionário/conjunto; teste na CI compara hash entre os dois sistemas.

**Aceite F7:** em DXFs sintéticos com resposta analítica conhecida (corredor em L, sala com
pilar, duas portas), o método vetorial acerta com erro ≤ 0,05 m e incerteza declarada ≤ 0,15 m;
FMM concorda; hash de saída igual em Windows e Linux.

---

## F8 — Integração skills ↔ motor (COR-F8)

- O orquestrador (`skills/orquestrar-analise-cbmerj`) ganha a referência
  `uso-do-mcp-coscip-plantas.md`: quando o processo tem DXF/DWG, a leitura da planta e as
  medições do Grupo 2 vêm do MCP (`abrir_planta` → `confirmar_unidade` → `definir_pavimentos` →
  `analisar_planta`), e o GATE-0 do grafo só abre com unidade confirmada e balanço de
  reconhecimento completo (F5.3).
- A skill de LE deixa de "não cobrar raio" por impossibilidade: com planta vetorial, a medida
  vem do motor; sem planta vetorial (só PDF), mantém a regra atual.
- `emitir-bilhete-cbmerj`: `localizar_item.py` usa o índice F3.3; o MCP `consultar_norma` é a
  alternativa quando a skill roda com o MCP disponível.
- Achados do motor (`v2-findings --out`) entram na matriz consolidada da skill sem tradução
  (esquema comum F3.4).

**Aceite F8:** processo sintético completo (DXF + memorial fictício) analisado pela skill com
o MCP, produzindo matriz única e bilhete com citações todas localizadas no índice.

---

## F9 — Validação de fidelidade (COR-F9)

- **Corpus-gabarito:** 5–10 processos reais anonimizados (fora do repositório), cada um com o
  bilhete efetivamente emitido pelo analista como gabarito. Medir por processo: exigências
  acertadas, exigências faltantes, exigências indevidas, citações corretas.
- **Contagem de símbolos:** rotular à mão os símbolos de 3 plantas reais; medir precisão e
  revocação do reconhecimento (meta: revocação 100 % em camadas de segurança, com o restante em
  "não reconhecido", nunca omitido).
- **Distâncias:** 10 medidas reais conferidas à mão no CAD (pendência Gate A/POC-02).
- **Homologação** (REG-05/06): responsável técnico revisa checks e regras; só então
  `publication_state` sai de DRAFT.

**Aceite F9:** relatório `docs/validacao/AAAA-MM-DD.md` com as métricas; nenhum check sai de
rascunho sem homologação.

---

## Bibliotecas avaliadas

| Biblioteca | Licença | Uso proposto | Fase | Observação |
|---|---|---|---|---|
| **pypdfium2** | Apache-2.0 / BSD-3 | renderizar páginas dos PDFs oficiais em PNG | F2 | preferida ao PyMuPDF, que é **AGPL** (problema se o produto for vendido) |
| **pdfplumber** | MIT | extrair tabelas com geometria de célula | F2 | caminho 1 da dupla extração |
| Docling | MIT | conferência opcional de estrutura de tabela | F2 | pesado (modelos); só se pdfplumber falhar em tabelas mescladas |
| **rapidfuzz** | MIT | casar texto com erro de OCR; padrões de bloco | F2, F5 | score sempre registrado |
| **scikit-fmm** | BSD-3 | segundo método de distância (eikonal) | F7 | conferência independente |
| Shapely `STRtree` | BSD | deduplicação espacial, visibilidade | F5, F7 | **já é dependência** |
| NetworkX | BSD | grafo de visibilidade | F7 | **já é dependência** |
| `ezdxf.addons.odafc` | MIT | wrapper oficial do ODA File Converter | — | pode substituir parte de `coscip_cad.dwg`; manter o registro de origem |
| `Insert.multi_insert()` (ezdxf) | MIT | expandir MINSERT | F5 | já incluso no ezdxf |
| `ezdxf.recover` | MIT | abrir DXF danificado com relatório de reparo | F5 | registrar que houve reparo |
| `ezdxf.addons.drawing` + matplotlib | MIT / PSF | imagem fiel da planta para conferência humana | F8 | opcional; o `png.py` próprio continua sem dependência |
| pip-tools ou uv | BSD / MIT-Apache | lock de dependências com hash | F0 | |
| Python embeddable 3.12 | PSF | pacote portátil sem instalação | F0 | |

Não recomendadas: PyMuPDF (AGPL), camelot (exige Ghostscript/OpenCV no Windows), `triangle`
(licença não comercial), `pyvisgraph` (sem manutenção — implementar com Shapely/NetworkX).

---

## Pendências que dependem do usuário

1. Proteção da branch `master` no GitHub (F0.1).
2. Testar o zip portátil na máquina principal (F0.3).
3. Enviar os zips das skills em claude.ai e remover as oito antigas + o legado (F1.1, F3.2).
4. Decidir cada tabela `divergente`/`pendente_humano` do F2 (lista gerada).
5. Permissão de escrita em `%LOCALAPPDATA%\MotorCoscip` para importar os pacotes v4–v6.
6. Corpus-gabarito e medidas reais (F9); responsável técnico para homologação.

---

## Frase para abrir a sessão de execução

> Leia `docs/proxima-sessao.md` (registro único) e `docs/plano/01-plano-de-correcao.md`.
> Execute o plano de correção a partir da primeira fase ainda não concluída (F0 se nenhuma),
> uma branch e um PR por fase, CI verde antes do merge, atualizando o registro ao fim de cada
> fase. Decisão já tomada: EXT-CAD-002 exige 2 extintores por pavimento, como critério
> registrado (F4.1). Não introduza LLM nem Jev. A máquina principal do usuário não tem Python:
> valide pela CI ou numa sessão com Python.
