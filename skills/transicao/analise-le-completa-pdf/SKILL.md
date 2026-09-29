---
name: analise-le-completa-pdf
description: "Skill para análise completa de processos de Laudo de Exigências (LE). Executa a conferência documental e técnica de projetos, focado em pranchas fornecidas em formato PDF (mesmo quando o projeto original é DWG e foi convertido pelo sistema). Aplica as regras do Decreto 42/2018, NT 1-01 e dos Aditamentos Administrativos. REGRA CRÍTICA: O Quadro Resumo é a fonte declaratória oficial — toda marcação 'X' em risco específico é VINCULANTE e DEVE ser transcrita para o Laudo. Leitura OBRIGATÓRIA campo a campo, linha a linha, célula a célula do Quadro Resumo, sem omissões."
---

# ANÁLISE DE PROCESSO PARA O LAUDO DE EXIGÊNCIAS (LE)

## Protocolo: Documentação + Análise de Pranchas (PDF)

Esta skill orienta a inteligência na análise completa de um processo para a obtenção do Laudo de Exigências (LE). Toda análise deve fundir a conferência de documentos e a conferência de plantas fornecidas (em formato PDF), baseando-se no Código de Segurança Contra Incêndio e Pânico (Decreto 42/2018), NT 1-01 e Aditamentos Administrativos atualizados.

---

## ⚠️ REGRAS GERAIS — O QUE NÃO COBRAR

Antes de qualquer análise, internalize estas três regras de **NÃO COBRANÇA** (proibido gerar pendência sobre estes itens):

### REGRA NÃO-COBRANÇA Nº 1 — FORMATO DO PROJETO (DWG → PDF)

Mesmo que o **Termo de Aceite** ou demais documentos descrevam que o projeto foi enviado em **DWG**, o arquivo será convertido pelo sistema para **PDF** apenas para facilitar a análise visual.

- **PROIBIDO** gerar pendência por "Projeto enviado em DWG e não em PDF".
- **PROIBIDO** exigir reapresentação do projeto em PDF/A por motivo de formato.
- O analista trabalha com o PDF convertido normalmente.

### REGRA NÃO-COBRANÇA Nº 2 — DISTÂNCIAS DE EXTINTORES (RAIO DE 15m / 20m)

A planta original do projetista está em escala. A verificação do **raio de cobertura de cada unidade extintora** (15m para risco pequeno, 20m para risco baixo) **é responsabilidade do analista**, que deve medir em escala usando as ferramentas de medição.

- **PROIBIDO** gerar pendência genérica do tipo "verificar raio de 15m dos extintores" ou "comprovar cobertura por mangueira".
- **OBRIGATÓRIO** (ao invés disso): calcular se o **quantitativo e a capacidade extintora total** (em unidades extintoras 2A:20BC etc.) atendem à área construída a ser protegida, conforme **tabela do Anexo A da NT 2-01** (Tabela de Capacidade Extintora vs. Área Máxima Protegida por Risco).
- Cobrar SOMENTE: (i) tipo correto para a classe de fogo do local (A, B, C, D, K); (ii) **proporção de unidades extintoras x área protegida** segundo o quadro normativo da NT 2-01; (iii) presença de extintor específico onde norma exige (PQS junto à central de GLP, CO2 em motogerador/subestação, Classe K em cozinha profissional, etc.).
- Se houver erro grosseiro de quantitativo, apontar com base no cálculo da proporção, não em raio.

### REGRA NÃO-COBRANÇA Nº 3 — VARREDURA COMPLETA DE TODOS OS ELEMENTOS DA PRANCHA

**PROIBIDO** gerar pendência do tipo "Quadro de simbologia ausente" ou "Legenda não localizada" sem antes ter feito uma **varredura sistemática de TODOS os elementos da prancha**, em TODOS os cantos, margens, rodapés, áreas livres entre desenhos e folhas anexas.

- Quadros de simbologia, legendas, quadros de áreas, quadros resumo, quadros de portas, quadros de carga de incêndio, isométricos e detalhes construtivos **frequentemente são posicionados nos cantos das pranchas, em margens laterais ou em folhas dedicadas**.
- O analista DEVE percorrer a prancha em zonas (canto superior esquerdo, superior direito, inferior esquerdo, inferior direito, faixa central, margem superior, margem inferior, áreas livres) antes de declarar qualquer elemento ausente.
- Se a baixa qualidade do PDF impedir a leitura, declarar **"NÃO LEGÍVEL — solicitar esclarecimento"**, não "ausente".

---

## 🏗 FASE 1 — CONFERÊNCIA DOCUMENTAL FECHADA

Inicie cruzando os dados do projeto com a documentação fornecida. Esta fase é **obrigatória** antes da análise técnica das pranchas.

### REGRA CRÍTICA DA FASE 1

**PROIBIDO** avançar para a análise das pranchas sem preencher o checklist documental abaixo. Quando um documento não for localizado, marcar como **"NÃO APRESENTADO"**. Quando estiver ilegível, marcar como **"NÃO LEGÍVEL — solicitar reapresentação/esclarecimento"**. Quando houver divergência entre documentos, gerar **pendência de incompatibilidade documental**.

### 1. Requerimento eletrônico e declarações

Verificar se o requerimento está apresentado, preenchido e assinado pelo requerente ou representante legal, conferindo:

- Razão social / nome do proprietário ou responsável legal;
- CPF/CNPJ;
- Endereço completo da edificação ou área de risco;
- Área Total Construída (ATC);
- Número de pavimentos;
- Ocupação/atividade declarada;
- Tipo de solicitação/processo;
- Compatibilidade com o Quadro Resumo e com as pranchas.

### 2. DAEM e comprovante de pagamento

- Verificar se o DAEM foi apresentado.
- Conferir se a receita corresponde à análise de projeto de segurança contra incêndio e pânico, em especial receitas 101/102 ou correspondentes de reentrada, conforme o caso.
- Confirmar se há comprovante de pagamento associado ao DAEM.
- Conferir se a ATC utilizada para cálculo do emolumento é compatível com a ATC declarada no requerimento, memorial, Quadro Resumo e pranchas.
- Se houver divergência relevante de ATC, gerar pendência documental.

### 3. Identificação do responsável legal, proprietário ou representante

Verificar se foi apresentada documentação de identificação do responsável legal que assina o requerimento e/ou as plantas:

- Documento de identidade ou documento equivalente;
- CPF, quando aplicável;
- Procuração, quando o processo for assinado por representante;
- No caso de condomínio, ata de eleição/nomeação do síndico ou documento equivalente;
- Compatibilidade entre o responsável legal indicado no requerimento, nas plantas, no memorial e nos demais documentos.

### 4. Título de propriedade, posse ou vínculo com o imóvel

Verificar se há documento que demonstre vínculo legítimo com o imóvel ou área de risco, tais como:

- Registro Geral de Imóveis (RGI), certidão de ônus reais ou documento similar;
- Contrato de locação;
- Termo de cessão, autorização de uso ou documento equivalente;
- Escritura, matrícula, inscrição imobiliária ou outro documento aceito no processo;
- Compatibilidade do endereço com o requerimento, DAEM, memorial e pranchas.

### 5. Ato constitutivo da pessoa jurídica, quando aplicável

No caso de pessoa jurídica, verificar:

- Contrato social, estatuto, ata de constituição, requerimento de empresário ou documento similar;
- CNPJ;
- Identificação de sócio, administrador ou representante com poderes para assinar;
- Compatibilidade entre a atividade econômica declarada e a ocupação efetivamente projetada.

**ATENÇÃO:** A ocupação para fins de SCIP deve considerar a atividade efetivamente projetada ou desenvolvida, ainda que o ato constitutivo indique atividade diferente.

### 6. Memorial descritivo do projeto

Verificar se foi apresentado memorial descritivo e se ele contém, no mínimo:

- Descrição da edificação ou área de risco;
- Ocupação/atividade;
- ATC;
- Número de pavimentos e altura;
- Classificação da edificação;
- Risco de incêndio/carga de incêndio;
- Medidas de segurança propostas;
- Riscos específicos existentes ou declaração expressa de inexistência;
- Compatibilidade com o Quadro Resumo e com as pranchas.

Se o memorial declarar inexistência de risco específico, mas o Quadro Resumo ou a prancha indicar GLP, GN, inflamáveis, motogerador, subestação, cozinha profissional, caldeira, heliponto ou outro risco, gerar **pendência de incompatibilidade documental**.

### 7. Responsabilidade Técnica (ART/RRT)

Verificar se foram apresentadas ARTs/RRTs válidas, definitivas, pagas e assinadas pelo contratante e pelo profissional contratado, quando exigível:

- **Projeto de SCIP:** ART/RRT específica com atribuição de Projeto de Segurança Contra Incêndio e Pânico;
- **Levantamento/Projeto Arquitetônico:** verificar se foi apresentada responsabilidade técnica do profissional responsável pela elaboração do projeto arquitetônico, levantamento arquitetônico ou execução da obra, conforme orientação administrativa aplicável;
- **Riscos específicos:** quando houver GLP/GN, motogerador, subestação, cozinha profissional, inflamáveis, caldeira/vaso de pressão, heliponto, explosivos ou produtos perigosos, verificar se há ART/RRT específica ou compatível com o serviço técnico correspondente;
- Conferir se o profissional possui atribuição compatível e se os dados da edificação coincidem com o requerimento, memorial e pranchas.

### 8. Composição mínima do Projeto de Segurança Contra Incêndio e Pânico

Verificar se o conjunto de pranchas/projeto contém, conforme aplicabilidade:

- Planta de situação;
- Plantas baixas de todos os pavimentos;
- Cortes;
- Planta de telhado/cobertura, quando aplicável;
- Fachada, quando aplicável;
- Isométrico dos sistemas hidráulicos preventivos, quando exigidos;
- Detalhes técnicos das medidas de segurança;
- Quadro Resumo impresso na planta de situação ou na Prancha 01, conforme procedimento vigente;
- Carimbos com identificação do projeto, proprietário/responsável legal e responsável técnico.

No caso de lojas ou salas comerciais, observar as dispensas próprias quanto à planta de situação, telhado e fachada, quando aplicável.

### 9. Documentos complementares conforme caso específico

Verificar, conforme a ocupação, riscos específicos e características do processo, se há necessidade de documentos complementares, tais como:

- Documentação comprobatória de anterioridade, quando a edificação for anterior ao Decreto nº 42/2018;
- Certificado de Aprovação/Laudo anterior, quando houver histórico de regularização;
- Memorial ou ficha técnica de materiais armazenados;
- Ficha técnica/FISPQ de produtos perigosos;
- Termos de responsabilidade específicos;
- Documentos relativos a depósitos de explosivos, pirotécnicos ou munições, quando aplicável;
- Documentos próprios para pátio de armazenagem, postos, GNV, GLP, quiosques, sites de antena, eventos ou demais casos específicos previstos na NT 1-01.

### MATRIZ OBRIGATÓRIA — CHECKLIST DOCUMENTAL FECHADO

Preencher antes de avançar para a Fase 2:

| Documento / Item | Apresentado? | Conferência obrigatória | Resultado / Pendência |
|---|---:|---|---|
| Requerimento eletrônico assinado | Sim/Não | Dados cadastrais, ATC, pavimentos, ocupação e endereço | ... |
| DAEM | Sim/Não | Receita correta e compatibilidade com ATC | ... |
| Comprovante de pagamento | Sim/Não | Pagamento vinculado ao DAEM | ... |
| Identidade do responsável legal | Sim/Não | Nome compatível com requerimento e plantas | ... |
| Procuração / representação | Sim/Não/NA | Poderes para representar/assinar | ... |
| Título de propriedade / locação / vínculo | Sim/Não | Endereço e titularidade/posse compatíveis | ... |
| Contrato social / estatuto / ato constitutivo | Sim/Não/NA | Pessoa jurídica e poderes de representação | ... |
| Memorial descritivo | Sim/Não | Compatível com Quadro Resumo e pranchas | ... |
| ART/RRT de Projeto de SCIP | Sim/Não | Assinada, paga, definitiva e com atribuição compatível | ... |
| ART/RRT de levantamento/projeto arquitetônico | Sim/Não/NA | Responsável técnico e atribuição compatível | ... |
| ART/RRT de risco específico | Sim/Não/NA | GLP/GN, motogerador, subestação, inflamáveis etc. | ... |
| Projeto/pranchas | Sim/Não | Plantas, cortes, detalhes, isométrico e carimbos | ... |
| Quadro Resumo na prancha | Sim/Não | Localizado e legível | ... |
| Documentos complementares do caso específico | Sim/Não/NA | Conforme NT 1-01 e NTs específicas | ... |

---

## 📊 FASE 2 — AVALIAÇÃO DO QUADRO RESUMO E PARÂMETROS GERAIS

As pranchas e o projeto digital passarão por uma triagem geral.

### 1. Quadro Resumo Obrigatório (Aditamento Adm 01/2025)

- Localize o Quadro Resumo inserido **DIRETAMENTE NAS PRANCHAS** fornecidas em PDF. É obrigatório constar na planta e substitui a exigência de ser anexado avulso.
- O Quadro Resumo pode estar em **qualquer canto da prancha** — fazer varredura visual completa antes de declarar ausente (vide Regra Não-Cobrança nº 3).
- Confira no Quadro: a Classificação da Edificação, a Área Total Construída (ATC), a altura/número de pavimentos, a Carga de Incêndio e os Riscos Específicos declarados.

### 2. Confronte de ATC e Classificação

A ATC do Quadro Resumo (na prancha) deve ser **idêntica** à do Requerimento e do DAEM.

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

## 📏 FASE 3 — ENQUADRAMENTO E DEFINIÇÃO DE NORMAS (DECRETO 42/2018)

### 1. Classificação (Anexo II - Decreto 42)

Defina o Grupo e a Divisão da edificação de acordo com o uso apontado no projeto.

### 2. Medidas de Segurança (Anexo III - Decreto 42)

Monte a lista das medidas obrigatórias (ex: Extintores, Iluminação, Sinalização, Saídas de Emergência, Hidrantes, Alarme, SPDA etc.) cruzando a ATC, altura e risco levantado.

### 3. Riscos Específicos — VINCULAÇÃO COM A FASE 2

Para cada risco específico assinalado no Quadro Resumo da Fase 2, **adicionar AUTOMATICAMENTE** a NT correspondente (Grupo 3 ou 4) na lista de medidas obrigatórias.

#### Mapeamento obrigatório Quadro Resumo → NT:

| Risco Específico | NT Correspondente | Descrição |
|---|---|---|
| GLP | NT 3-02 | Gás Combustível |
| Gás Natural | NT 3-02 | Gás Combustível |
| Inflamáveis líquidos | NT 3-06 / NT 4-03 | Armazenagem / Posto |
| Cozinha profissional | NT 3-01 | Cozinhas Profissionais |
| Motogerador | NT 3-03 | Motogerador |
| Subestação | NT 3-04 | Subestação |
| Caldeira / Vaso de pressão | NT 3-05 | Vasos de Pressão / Caldeiras |
| Paiol / Explosivos | NT 4-06 | Paiol de Explosivos |
| Heliponto | NT 4-11 | Heliponto |

---

## 🔍 FASE 4 — ANÁLISE TÉCNICA DAS PRANCHAS (PDF) POR MEDIDA

Nesta etapa, vasculhe **todas as folhas PDF** da planta fornecida e confronte com as exigências técnicas:

### Simbologia e Cores (Aditamento 01/2025)

Verifique se no projeto constam as definições padrão ou layers/cores de identificação correspondentes (ainda que exportado em PDF, as medidas devem ser facilmente distinguíveis conforme simbologia da NT 1-03). **Antes de cobrar quadro de simbologia "ausente", aplique o PROTOCOLO DE VARREDURA EXAUSTIVA DA PRANCHA** (vide seção dedicada acima) — a legenda de sinalização frequentemente fica nos cantos das pranchas.

### Apresentação e Assinaturas (Aditamento 01/2025)

A documentação de projeto/prancha (se via principal a ser assinada posteriormente) deve no mínimo conter as informações essenciais nos carimbos: RT, RL, área e identificações. Na via física/digital híbrida exige-se apenas a assinatura do RT.

---

## Detalhes das NTs Primárias (Grupo 2)

### 1. NT 2-01 (Extintores)

⚠️ **NÃO COBRAR raio de cobertura (15m / 20m)** — vide Regra Não-Cobrança nº 2. Cobrar apenas:

- **Quantitativo correto** segundo a **Tabela de Capacidade Extintora vs. Área Máxima Protegida** (Anexo A da NT 2-01). Calcular: (Área protegida total ÷ Área máxima por unidade extintora) ≤ Quantidade de extintores apresentada na prancha.
- **Tipo correto para a classe de fogo** do local protegido (A: papel/madeira/tecido; B: líquidos inflamáveis; C: elétrico; D: metais pirofóricos; K: óleo de cozinha).
- **Capacidade extintora mínima** (ex: 2A:20BC para risco pequeno; 3A:40BC para risco médio).
- **Extintores específicos onde a norma exige** (CO2 em motogerador/subestação; PQS junto à central de GLP; Classe K em cozinha profissional).

### 2. NT 2-02 (Hidrantes e Mangotinhos)

- Existência da RTI (Reserva Técnica de Incêndio) e CMI (Casa de Máquinas de Incêndio) delimitadas em planta.
- Volume de RTI compatível com a classificação (mínimo 8.000L para sistema tipo 1; até 24.000L para A-5 risco pequeno; etc.).
- Isométrico do sistema apresentado.
- **Raio de 30m das mangueiras** — verificar em escala (analista mede), cobrar apenas se evidente que há área não coberta.

### 3. NT 2-05 (Sinalização)

- Placas de orientação e socorro sinalizadas em planta detalhada e em corte conforme aplicabilidade.
- **Quadro/legenda de simbologia** — só cobrar como ausente após aplicar o PROTOCOLO DE VARREDURA EXAUSTIVA DA PRANCHA (geralmente está nos cantos).

### 4. NT 2-06 (Iluminação de Emergência)

- Posicionamento em descidas, corredores, rotas de fuga.

### 5. NT 2-08 (Saídas de Emergência)

- Cálculo das UTs e adequação de rotas de fuga.
- Dimensão e tipo de escadas (Comum, EEP, EEPF) conforme número de pavimentos.
- Distâncias de caminhamento (máximo 30m sem sprinkler) — verificar em escala.
- Verifique os quadros de portas e acessos em prancha (geralmente nos cantos).

---

## Detalhes das NTs Secundárias (Grupo 3/4 — acionadas a partir do Quadro Resumo)

### 6. NT 3-02 (Gás Combustível – GLP / GN)

Se "X" em GLP ou Gás Natural no Quadro Resumo, exigir:

- Localização, dimensões e ventilação da central de GLP (abrigo ventilado, afastamento de aberturas, proteção contra radiação solar, proibição de instalação em poço de elevador ou lixeira)
- Projeto específico de gás (tubulação, trajeto, teste de estanqueidade)
- ART/RRT específica de projeto de gás
- Extintor de PQS próximo à central
- Ventilação superior/inferior

### 7. NT 3-01 (Cozinhas Profissionais)

- Extintor Classe K
- Detecção sob coifa
- Registro corta-chama em dutos

### 8. NT 3-03 (Motogerador)

- Bacia de contenção
- Ventilação
- Escape de gases para fora das rotas de fuga
- Extintor CO2

### 9. NT 3-04 (Subestação)

- Sala enclausurada
- PCF P-90
- Extintor CO2
- Sinalização

### 10. NT 3-05 (Vasos de Pressão / Caldeiras)

- Válvulas de segurança
- Ensaios
- Distanciamento

### 11. NT 3-06 (Inflamáveis / Tanques)

- Bacia de contenção
- Sistema LGE
- Válvulas de alívio

---

## 🧾 REGRA DE FUNDAMENTAÇÃO NORMATIVA OBRIGATÓRIA — ITEM, NORMA E MOTIVO

Toda pendência ou exigência gerada pela skill deve ser **fundamentada de forma objetiva**, com indicação da norma técnica, item/subitem, tabela, anexo ou artigo utilizado.

### REGRA CRÍTICA

**PROIBIDO** emitir exigência genérica sem base normativa identificável. A exigência somente poderá constar no laudo se vier acompanhada de:

1. **Medida analisada** — exemplo: Extintores, Saídas de Emergência, GLP, Hidrantes, Sinalização, Iluminação, SPDA etc.;
2. **Base normativa** — Decreto nº 42/2018/COSCIP, Anexo III, tabela aplicável, NT específica e item/subitem correspondente;
3. **Constatação objetiva** — o que foi visto no processo, documento ou prancha;
4. **Incompatibilidade encontrada** — por que o projeto não atende ou por que a informação está ausente/ilegível/divergente;
5. **Correção exigida** — o que o RT deve apresentar, corrigir, complementar ou esclarecer.

### FORMATO PADRÃO DE CADA PENDÊNCIA

Cada pendência deve ser redigida obrigatoriamente no seguinte formato:

```text
[MEDIDA / SISTEMA] — [NORMA + ITEM/SUBITEM/TABELA/ANEXO]
Constatação: [descrever exatamente o que foi encontrado no requerimento, memorial, Quadro Resumo ou prancha].
Não conformidade: [explicar a divergência, ausência, insuficiência ou incompatibilidade].
Exigência: [informar objetivamente o que deve ser corrigido/apresentado].
Localização no projeto: [prancha, pavimento, detalhe, quadro ou documento analisado].
```

### EXEMPLOS DE REDAÇÃO CORRETA

```text
Sistema de Gás Combustível — NT 3-02, item aplicável ao uso predial de GLP/GN.
Constatação: O Quadro Resumo da Prancha 01 indica marcação "X" para GLP.
Não conformidade: Não foi localizado detalhe da central de GLP, traçado da tubulação, ventilação, afastamentos e ART/RRT específica compatível.
Exigência: Apresentar/adequar o projeto de gás combustível, incluindo central, tubulação, ventilação, afastamentos, extintor específico e responsabilidade técnica correspondente.
Localização no projeto: Quadro Resumo da Prancha 01 e plantas baixas analisadas.
```

```text
Documentação do Projeto de SCIP — NT 1-01, Seção 5.3.
Constatação: Foi apresentado projeto em pranchas, porém não foi localizado memorial descritivo.
Não conformidade: O processo fica sem a descrição técnica consolidada da edificação, das medidas de segurança e dos riscos específicos.
Exigência: Apresentar memorial descritivo compatível com requerimento, Quadro Resumo, DAEM e pranchas.
Localização no projeto: Conferência documental da Fase 1.
```

### REGRA DE IMPOSSIBILIDADE DE CITAÇÃO PRECISA

Se o analista souber que a exigência é aplicável, mas não conseguir identificar com segurança o item/subitem exato da NT, deverá:

- indicar a NT e o tópico geral aplicável;
- registrar **"item específico a confirmar na NT correspondente antes da emissão final"**;
- **não inventar numeração normativa**;
- priorizar a revisão manual antes de fechar o laudo.

---

## 📋 FASE 5 — GERAÇÃO DA LISTA DE EXIGÊNCIAS

Todo processo que apresente não conformidades deve ser compilado e entregue na forma final do "Laudo de Pendências".

### VERIFICAÇÃO FINAL ANTES DE FECHAR O LAUDO (OBRIGATÓRIA)

**Antes de emitir o STATUS GERAL, revalide os seguintes pontos de integridade — NÃO PULE:**

1. ✅ A matriz do Quadro Resumo (Fase 2) foi preenchida com TODOS os campos, **linha por linha**?
2. ✅ O bloco "RISCOS ESPECIAIS / ESPECÍFICOS" foi lido **literalmente, célula por célula**, em CADA prancha?
3. ✅ **TODA** marcação "X" em risco específico foi transcrita nos Dados Cadastrais?
4. ✅ Para **CADA** risco específico marcado, foi incluída a NT correspondente (Grupo 3/4) na lista de medidas obrigatórias?
5. ✅ Para **CADA** risco específico marcado, foi gerada pendência técnica exigindo detalhamento na prancha?
6. ✅ Para **CADA** risco específico marcado, foi conferida a existência de ART/RRT específica do risco?
7. ✅ As declarações do Memorial foram cruzadas com as marcações do Quadro Resumo (pendência de omissão cruzada)?
8. ✅ **NÃO foi gerada pendência sobre formato DWG vs PDF** (Regra Não-Cobrança nº 1)?
9. ✅ **NÃO foi gerada pendência sobre raio de cobertura de extintores** (Regra Não-Cobrança nº 2 — usar apenas a proporção da Tabela do Anexo A da NT 2-01)?
10. ✅ Antes de cobrar QUALQUER elemento como "ausente" da prancha, foi aplicado o **PROTOCOLO DE VARREDURA EXAUSTIVA DA PRANCHA** (9 quadrantes, todas as folhas)?
11. ✅ O **CHECKLIST DOCUMENTAL FECHADO** da Fase 1 foi preenchido integralmente?
12. ✅ Foram conferidos requerimento, DAEM, comprovante, identificação, vínculo com o imóvel, ato constitutivo, memorial, ART/RRT e composição mínima do projeto?
13. ✅ Cada pendência contém **medida/sistema, base normativa, constatação, não conformidade, exigência e localização**?
14. ✅ Nenhuma exigência foi emitida sem norma, item/subitem, tabela/anexo ou justificativa técnica identificável?
15. ✅ Quando não foi possível confirmar o item exato da NT, foi registrada a observação "item específico a confirmar na NT correspondente antes da emissão final", sem inventar numeração?

**Se QUALQUER um dos itens acima estiver em aberto, NÃO FECHE o Laudo: volte à fase correspondente.**

---

## ESTRUTURA DO RESULTADO DA SKILL

```text
==============================================================
RELATÓRIO DE ANÁLISE DO LAUDO DE EXIGÊNCIAS (LE)
==============================================================
Dados Consolidados Extraídos:
- ATC Identificada: [m²]
- Ocupação: [Grupo - Divisão]
- Riscos Específicos (do Quadro Resumo): [TRANSCRITOS LITERALMENTE — ex: GLP (X); Cozinha Profissional (X); etc.]
- RT do Projeto: [Nome]

LEITURA DO QUADRO RESUMO — BLOCO RISCOS ESPECIAIS (autoconferência):
- Linha "GLP / Gás liquefeito de petróleo": [MARCADO X / vazio]
- Linha "Gás Natural": [MARCADO X / vazio]
- Linha "Inflamáveis líquidos": [MARCADO X / vazio]
- Linha "Cozinha profissional": [MARCADO X / vazio]
- Linha "Motogerador": [MARCADO X / vazio]
- Linha "Subestação": [MARCADO X / vazio]
- Linha "Caldeira/Vaso de pressão": [MARCADO X / vazio]
- Linha "Paiol/Explosivos": [MARCADO X / vazio]
- Linha "Produtos perigosos": [MARCADO X / vazio]
- Linha "Heliponto": [MARCADO X / vazio]

--------------------------------------------------------------
[1] PENDÊNCIAS DOCUMENTAIS
Cada pendência documental deve indicar documento, base normativa/procedimental, constatação, não conformidade, exigência e localização no processo.
- [Gravidade] [Documento] — [Norma/Seção/Item]. Constatação: [...]. Não conformidade: [...]. Exigência: [...].
- [Gravidade] Falta da ART/RRT de Levantamento Arquitetônico, quando aplicável.
- [Gravidade] Divergência na ATC entre DAEM, Requerimento, Memorial, Quadro Resumo e Pranchas.
- [Gravidade] Incompatibilidade entre Quadro Resumo (risco "GLP" marcado) e Memorial Descritivo (declarou "não há riscos").

--------------------------------------------------------------
[2] CLASSIFICAÇÃO DE MEDIDAS (DECRETO 42/2018 E NORMAS)
- Lista das medidas de segurança obrigatórias para este risco e tamanho.
- Lista das NTs do Grupo 3/4 acionadas pelos riscos específicos marcados no Quadro.

--------------------------------------------------------------
[3] EXIGÊNCIAS TÉCNICAS E DE PROJETO (PRANCHAS)
Apresentar uma lista numerada detalhada do que falta no PDF fornecido, sempre com base normativa, item/subitem/tabela/anexo, constatação, não conformidade, exigência e localização no projeto.

Exemplo:
1. Sinalização de Emergência – NT 2-05, Item X.X
   [Após varredura dos 9 quadrantes nas Pranchas 01-04, o quadro de simbologia foi localizado/não localizado em XX.] Ajustar/incluir as placas X, Y, Z em planta detalhada do pavimento tipo.

2. Sistema de Gás Combustível – NT 3-02 (acionada por marcação "X" em GLP no Quadro Resumo)
   Risco específico GLP foi declarado no Quadro Resumo (Prancha 01). Faltam detalhes de projeto: localização da central, dimensões, ventilação, tubulação, e ART específica de projeto de gás.

3. Extintores – NT 2-01 (cálculo de proporção)
   Para área protegida de [XXX m²], a NT 2-01 exige no mínimo [N] unidades extintoras 2A:20BC (cálculo: área ÷ área máxima por unidade da Tabela do Anexo A). A prancha apresenta apenas [M] extintores. Adequar quantitativo.

==============================================================
STATUS GERAL: [COM EXIGÊNCIAS / APROVADO]
==============================================================
```

---

## REGRAS DO AGENTE NA FORMULAÇÃO DAS EXIGÊNCIAS

- **Não inventar exigências** ou deduzir medidas que não existam nas NTs.
- **Tratar o projeto em PDF** como fonte unitária visual; referencie as folhas caso enumeradas (ex: Prancha 01, Folha 2/3).
- **Sinalize claramente** caso alguma medida não pôde ser avaliada devido à má visualização no PDF, exigindo esclarecimento do projetista — **mas só após aplicar o PROTOCOLO DE VARREDURA EXAUSTIVA**.
- **NUNCA omitir** um risco específico declarado no Quadro Resumo, ainda que ausente em outras partes do processo.
- **SEMPRE transcrever a marcação** do Quadro Resumo literalmente — o Quadro é a fonte primária e vinculante declarada pelo RT.
- **Ler o Quadro Resumo célula por célula, linha por linha** — proibido pular linhas do bloco RISCOS ESPECIAIS.
- **Para riscos específicos marcados**, vincular OBRIGATORIAMENTE à NT correspondente e gerar pendência de detalhamento técnico E verificação de ART específica.
- **NÃO COBRAR** divergência de formato DWG vs PDF (será convertido pelo sistema).
- **NÃO COBRAR** raio de cobertura de extintores (15m / 20m) — analista mede em escala. Cobrar apenas a **proporção quantitativa** da Tabela do Anexo A da NT 2-01.
- **NÃO COBRAR** quadros/legendas/simbologia como "ausentes" sem aplicar o PROTOCOLO DE VARREDURA EXAUSTIVA DA PRANCHA (9 quadrantes em todas as folhas).
- **SEMPRE preencher** o CHECKLIST DOCUMENTAL FECHADO da Fase 1 antes da análise técnica.
- **SEMPRE fundamentar** cada pendência com norma, item/subitem/tabela/anexo, constatação objetiva, não conformidade, exigência e localização no processo/projeto.
- **NUNCA inventar** numeração de item normativo. Se o item exato não puder ser confirmado, registrar a necessidade de confirmação antes da emissão final.