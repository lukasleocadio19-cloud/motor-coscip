# Protocolo de leitura das pranchas e do Quadro Resumo (LE)

Absorvido da skill antiga `analise-le-completa-pdf` (plano de correção, F3.2), já com as
correções objetivas do F3.1 (NT 2-01 Tabela 3; NT 3-07 heliponto; NT 4-04 explosivos). Regras
de leitura e de não-cobrança; **não** é fonte normativa: todo número e todo item vêm da NT,
localizada pelas skills de grupo. Com planta vetorial (DXF/DWG), a leitura e as medidas vêm do
MCP `coscip-plantas` ([uso-do-mcp-coscip-plantas.md](uso-do-mcp-coscip-plantas.md)).

## ⚠️ REGRAS GERAIS — O QUE NÃO COBRAR

Antes de qualquer análise, internalize estas três regras de **NÃO COBRANÇA** (proibido gerar pendência sobre estes itens):

### REGRA NÃO-COBRANÇA Nº 1 — FORMATO DO PROJETO (DWG → PDF)

Mesmo que o **Termo de Aceite** ou demais documentos descrevam que o projeto foi enviado em **DWG**, o arquivo será convertido pelo sistema para **PDF** apenas para facilitar a análise visual.

- **PROIBIDO** gerar pendência por "Projeto enviado em DWG e não em PDF".
- **PROIBIDO** exigir reapresentação do projeto em PDF/A por motivo de formato.
- O analista trabalha com o PDF convertido normalmente.

### REGRA NÃO-COBRANÇA Nº 2 — DISTÂNCIAS DE EXTINTORES (NT 2-01, TABELA 3)

A planta original do projetista está em escala. Pela **NT 2-01, item 6.1.1, Tabela 3**, a distância máxima a percorrer até um extintor é **20 m no risco pequeno, 15 m no risco médio e 10 m no risco grande** (área máxima protegida por unidade extintora: 250 m², 150 m² e 100 m²). Conferir sempre na Tabela 3 da NT (`$cbmerj-grupo-2-medidas-seguranca`), não de memória.

- **Com planta vetorial (DXF/DWG)**: a distância **é cobrada**, porque é medida pelo motor (MCP `coscip-plantas`: `abrir_planta` → `confirmar_unidade` com duas cotas → `definir_pavimentos` → `analisar_planta`; ver `uso-do-mcp-coscip-plantas.md`). Com o GATE-0 aberto (`gate_0.aberto`), o achado `EXT-CAD-003-*` do motor entra na matriz **como veio** (lista `achados`, contrato `achado.schema.json`): não conforme ⇒ pendência concreta com o pavimento, a distância medida ± incerteza, o limite e o ponto mais distante; inconclusivo (porta de qualidade fechada, métodos divergentes) ⇒ **não** vira pendência: o analista mede ou pede esclarecimento. O mesmo vale para hidrante (`HID-CAD-002`), acionador (`ALA-CAD-002`) e saídas (`SAI-CAD-002/003`).
- **Só com PDF**: a verificação da distância percorrida **é responsabilidade do analista**, que mede em escala usando as ferramentas de medição; valem as proibições abaixo.

- **PROIBIDO** gerar pendência genérica do tipo "verificar raio de 15m dos extintores" ou "comprovar cobertura por mangueira" — com ou sem planta vetorial: a pendência de distância só existe com a medida concreta.
- **OBRIGATÓRIO** (ao invés disso): calcular se o **quantitativo e a capacidade extintora total** atendem à área construída a ser protegida, conforme a **NT 2-01, Tabela 3** (área máxima protegida por unidade extintora, por risco), com a capacidade extintora mínima das **Tabelas 1 e 2** (item 5.2.1 d e 6.1.1.1).
- Cobrar SOMENTE: (i) tipo correto para a classe de fogo do local (A, B, C, D, K); (ii) **proporção de unidades extintoras x área protegida** segundo o quadro normativo da NT 2-01; (iii) presença de extintor específico onde norma exige (PQS junto à central de GLP, CO2 em motogerador/subestação, Classe K em cozinha profissional, etc.).
- Se houver erro grosseiro de quantitativo, apontar com base no cálculo da proporção, não em raio.

### REGRA NÃO-COBRANÇA Nº 3 — VARREDURA COMPLETA DE TODOS OS ELEMENTOS DA PRANCHA

**PROIBIDO** gerar pendência do tipo "Quadro de simbologia ausente" ou "Legenda não localizada" sem antes ter feito uma **varredura sistemática de TODOS os elementos da prancha**, em TODOS os cantos, margens, rodapés, áreas livres entre desenhos e folhas anexas.

- Quadros de simbologia, legendas, quadros de áreas, quadros resumo, quadros de portas, quadros de carga de incêndio, isométricos e detalhes construtivos **frequentemente são posicionados nos cantos das pranchas, em margens laterais ou em folhas dedicadas**.
- O analista DEVE percorrer a prancha em zonas (canto superior esquerdo, superior direito, inferior esquerdo, inferior direito, faixa central, margem superior, margem inferior, áreas livres) antes de declarar qualquer elemento ausente.
- Se a baixa qualidade do PDF impedir a leitura, declarar **"NÃO LEGÍVEL — solicitar esclarecimento"**, não "ausente".

---


## 🚨 CHECKLIST OBRIGATÓRIO DO QUADRO RESUMO — LEITURA CAMPO A CAMPO, CÉLULA A CÉLULA

### REGRA CRÍTICA DE ANÁLISE (HARD STOP)

**O Quadro Resumo é a fonte declaratória oficial do RT.** Toda marcação "X" presente em qualquer campo do Quadro é **DECLARAÇÃO TÉCNICA VINCULANTE** e **DEVE ser transcrita para o Laudo**, mesmo quando o memorial ou as plantas-baixas forem omissos. A ausência de detalhamento técnico em prancha **NÃO desobriga** a análise do risco declarado — ao contrário, gera **pendência específica**.

### PROTOCOLO DE LEITURA OBRIGATÓRIA — VARREDURA EXAUSTIVA DO QUADRO

**PROIBIDO ao analista** afirmar que um campo está "em branco" sem ter percorrido **literalmente cada linha e cada célula** do Quadro Resumo. O Quadro contém múltiplos blocos (Identificação, Classificação, Carga de Incêndio, Elementos Estruturais, Medidas de Segurança, **RISCOS ESPECIAIS**) e cada bloco pode conter dezenas de linhas.

**Procedimento obrigatório de leitura do Quadro Resumo:**

1. **Ampliar (zoom) o Quadro Resumo no PDF** até ler nitidamente cada célula.
2. **Percorrer linha por linha**, da primeira à última, sem pular.
3. Em cada linha do bloco "RISCOS ESPECIAIS / RISCOS ESPECÍFICOS": registrar se a célula da esquerda contém marcação ("X", "✔", "SIM", hachura) ou está vazia.
4. Atenção especial às **linhas iniciais do bloco RISCOS ESPECIAIS** — frequentemente o "X" do GLP está na **primeira linha**, podendo passar despercebido se a leitura começar pelo meio do bloco.
5. Se o Quadro está replicado em várias pranchas, **conferir TODAS** — pode haver marcação em uma e omissão em outra.

### MATRIZ OBRIGATÓRIA — PREENCHIMENTO LITERAL

**PROIBIDO AO ANALISTA:** concluir a Fase 2 sem antes preencher, literalmente, a matriz abaixo para **CADA prancha** do processo. Se algum campo não puder ser lido por baixa qualidade do PDF, declarar expressamente **"NÃO LEGÍVEL — exigir esclarecimento"**.

| Bloco do Quadro Resumo | Campo | Valor declarado na prancha |
|---|---|---|
| **Identificação** | Endereço / Proprietário / RT / Conselho / Nº matrícula | ... |
| **Identificação** | Nº de pavimentos / Ocupação subsolo / Edificação anterior ao Decreto | ... |
| **Classificação (Anexo II)** | Grupo / Ocupação / Divisão / Agrupamento | ... |
| **Carga de Incêndio** | Risco / Carga (MJ/m²) | ... |
| **Elementos Estruturais (NT 2-19)** | Estrutura portante / Cobertura / TRRF / Revestimento | ... |
| **Medidas de Segurança (Anexo III)** | Lista de "X" marcados (extintores, hidrantes, alarme, compartimentação, sinalização, iluminação, saídas, hidrante urbano, acesso de viatura, SPDA etc.) | ... |
| **🔴 RISCOS ESPECIAIS / ESPECÍFICOS (CRÍTICO)** | Linha 1: GLP / Gás liquefeito de petróleo → MARCADO? Linha 2: Gás Natural → MARCADO? Linha 3: Inflamáveis líquidos → MARCADO? Linha 4: Cozinha Profissional → MARCADO? Linha 5: Motogerador → MARCADO? Linha 6: Subestação → MARCADO? Linha 7: Caldeira/Vaso de Pressão → MARCADO? Linha 8: Paiol/Explosivos → MARCADO? Linha 9: Produtos Perigosos → MARCADO? Linha 10: Heliponto → MARCADO? | **OBRIGATÓRIO transcrever LITERALMENTE cada linha lida** |

---

## 🔴 REGRAS DE CONFERÊNCIA DO CAMPO "RISCOS ESPECÍFICOS"

### (a) Varredura cega de TODAS as pranchas

Abrir **cada folha PDF** do processo (não apenas a Prancha 01). O Quadro Resumo pode estar replicado nas demais folhas e a marcação de risco específico pode aparecer **somente em uma delas**. A análise SOMENTE da primeira prancha é **causa de erro grave**.

### (b) Palavras-chave OBRIGATÓRIAS a buscar

Use ferramenta de busca de texto do PDF, OCR ou análise visual da tabela de riscos:

- "Riscos Específicos" / "Riscos Especiais"
- "Gás liquefeito de petróleo" / "GLP" / "P13" / "P45"
- "Gás Natural" / "GN" / "gás canalizado"
- "Inflamáveis" / "Líquidos combustíveis" / "Tanque"
- "Cozinha profissional" / "Cozinha industrial" / "Coifa"
- "Motogerador" / "Grupo gerador"
- "Subestação" / "Transformador"
- "Caldeira" / "Vaso de pressão" / "Autoclave"
- "Paiol" / "Explosivos"
- "Produtos perigosos"
- "Heliponto" / "Heliporto"

### (c) Regra do "X" (marcação visual vinculante)

Qualquer marcação visual (X, ✔, ✓, "SIM", hachura, preenchimento de célula) em linha de risco específico do Quadro é **declaração VINCULANTE**. Deve ser:

1. **Transcrita literalmente** no item "Dados Cadastrais" do Laudo;
2. **Adicionada à lista** de medidas de segurança obrigatórias com a NT do Grupo 3 ou 4 correspondente;
3. **Usada para gerar pendência específica** se não houver detalhamento técnico na prancha nem ART específica.

### (d) Regra da OMISSÃO CRUZADA

Se o Quadro Resumo declara um risco específico (ex: "X" em GLP) **MAS:**

- o Memorial afirma "Não há riscos específicos", **OU**
- as plantas não indicam central/abrigo de botijões/tubulação de gás, **OU**
- inexiste ART específica do risco declarado,

→ **GERAR PENDÊNCIA DE INCOMPATIBILIDADE DOCUMENTAL** (item administrativo), além da pendência técnica de ausência de detalhamento (item técnico). **Não é admissível** simplesmente ignorar a marcação por achar que ela "deve ser um erro do projetista".

### (e) Regra da OMISSÃO DIRETA

Se o Quadro Resumo **NÃO marcou riscos específicos**, **MAS há indícios em planta** (abrigo de GLP, cozinha profissional, gerador, subestação, etc.) → **GERAR PENDÊNCIA** exigindo retificação do Quadro Resumo com a marcação correta.

### (f) Nunca concluir "Sem riscos específicos" sem declarar

Nunca concluir "Não há riscos específicos" sem antes declarar, **por escrito na análise**, que foi conferido o campo "RISCOS ESPECÍFICOS" do Quadro Resumo em **CADA prancha**, **linha por linha**, e que todos os itens do referido campo estão em branco. Citar nominalmente cada linha verificada.

### (g) Ocupações Residenciais (A-2/A-5) — Especial atenção

Em divisões residenciais (A-2/A-5): o risco GLP é **quase sempre presente** (cocção domiciliar por P13) mesmo quando o condomínio não possui central centralizada. Confirmar no Quadro Resumo e no projeto se há:

- (i) central de GLP coletiva (NT 3-02);
- (ii) P13 individual por UH (análise simplificada);
- (iii) uso de outra fonte (indução elétrica, GN concessionária).

**NUNCA presumir.** Em A-5, releia o bloco RISCOS ESPECIAIS DUAS vezes antes de declarar GLP "não marcado".

### (h) Regra da AUTOCONFERÊNCIA OBRIGATÓRIA — Anti-omissão de leitura

Antes de fechar a Fase 2, o analista DEVE responder, por escrito, à seguinte pergunta de autoconferência:

> "Eu li, **literalmente**, cada uma das 10+ linhas do bloco RISCOS ESPECIAIS do Quadro Resumo? Posso citar nominalmente o estado (marcado/vazio) de CADA linha?"

Se a resposta for "não" ou "não tenho certeza", VOLTAR à prancha e refazer a leitura ampliada.

---

## 🔎 PROTOCOLO DE VARREDURA EXAUSTIVA DA PRANCHA (LOCALIZAÇÃO DE ELEMENTOS)

Esta seção rege a busca de QUALQUER elemento dentro da prancha (quadros, legendas, simbologia, isométricos, detalhes, carimbos).

### Procedimento obrigatório antes de declarar "ausente":

1. **Dividir a prancha em 9 quadrantes** (3x3): superior-esquerdo, superior-centro, superior-direito, meio-esquerdo, meio-centro, meio-direito, inferior-esquerdo, inferior-centro, inferior-direito.
2. **Examinar cada quadrante separadamente**, com zoom, antes de passar ao próximo.
3. **Verificar margens laterais** (esquerda, direita, superior, inferior) — quadros costumam ficar fora da área principal de desenho.
4. **Verificar áreas livres entre desenhos** — quando há vários desenhos na mesma prancha, quadros e legendas costumam preencher os espaços.
5. **Verificar TODAS as folhas** (Prancha 01, 02, 03, 04...) — não apenas a primeira.
6. **Examinar próximo aos carimbos / selo do projeto** — frequentemente quadros de simbologia, legendas e quadros resumo ficam adjacentes.

### Lista de elementos que DEVEM ser procurados em todos os quadrantes:

- Quadro Resumo (Aditamento 01/2025)
- Quadro de Áreas
- Quadro de Carga de Incêndio
- Quadro de Portas / Janelas
- **Legenda / Quadro de Simbologia de Sinalização (NT 2-05)** — placas P-1, P-2, S-1, S-2, S-3, S-12, S-17, E-2, E-3, E-5, E-8 etc.
- Legenda de Iluminação de Emergência
- Quadro de cálculo de população / UTs (saídas)
- Detalhes construtivos
- Isométrico do sistema de hidrantes
- Detalhe da CMI / RTI
- Detalhe da central de GLP (quando aplicável)
- Carimbos de RT, RL e Proprietário

### Regra de diagnóstico:

- Só declarar "ausente" após percorrer os 9 quadrantes de TODAS as pranchas.
- Se o elemento estiver em qualquer canto, anotar a localização (ex: "Quadro de Simbologia localizado no canto inferior direito da Prancha 03").
- Se o elemento estiver presente mas incompleto, descrever o que falta (não dizer "ausente").

---

