# Memorial descritivo do PSCIP: como os projetos o escrevem e como fazer o nosso

Extraído em 13/11/2026 dos memoriais de quatro projetos protocolados no CBMERJ em 2026 (9, 17,
17 e 4 páginas). Os dados dos projetos não entram aqui. Os valores que esses memoriais citam
**não são fonte**: vários estão desatualizados ou se contradizem (seção 4). Todo número do nosso
memorial sai de ferramenta do motor ou de `consultar_norma`, com documento e item.

Memorial descritivo ≠ memorial de cálculo. O de cálculo (`salvar_memorial`) traz fórmulas,
valores e citações por sistema; o descritivo é o texto que acompanha a prancha, descreve cada
medida de segurança, a especificação dos equipamentos, a instalação e a manutenção, e **inclui**
os cálculos (população, saídas, extintores) como "memória de cálculo". Os dois saem dos mesmos
números.

## 1. Os três formatos encontrados

**A. Memorial completo enxuto (9 páginas)** — o mais objetivo.
Capa (título "MEMORIAL DESCRITIVO DO PROJETO DE SEGURANÇA CONTRA INCÊNDIO E PÂNICO", endereço,
objeto do projeto, responsável e registro, campo de assinatura, "1ª via"). Depois:
1. Dispositivos preventivos fixos (cada um com "Isento" quando não exigido).
2. Dispositivos móveis: extintores (requisitos, classes de fogo, critério de quantidade pelo
   risco: área por unidade e distância máxima, localização).
3. Sinalização (objetivo, sinalização aplicável básica e complementar em tabela, função de cada
   tipo, implantação com alturas e espaçamentos em tabela, material, layout das placas com o
   símbolo e a descrição).
4. Iluminação (requisitos da luminária, nível em lux, tipo, ficha técnica: fluxo, autonomia,
   área atendida, dimensões).
5. Saídas (definição, fórmula N = P/C, tabela por ambiente: divisão, população, capacidade de
   acesso/escada/porta; memória de cálculo por ambiente; conclusão com as unidades de passagem
   existentes x exigidas).
6. Controle de materiais de acabamento (tabela de classes por elemento, conclusão, tabela do
   material de cada elemento).

**B. Memorial completo de escritório (17 páginas, modelo reaproveitado em dois projetos).**
Capa com proprietário, endereço, classificação e a frase de praxe ("Este Memorial Descritivo é
parte integrante do projeto ... deverá ser autenticado pelo CBMERJ e apresentado ao Oficial
Vistoriante ..."). Depois:
1. Da edificação e áreas de risco: tabela grupo/ocupação/divisão/descrição/risco, projetista,
   situação da edificação (três opções com X: em projeto; construída com projeto; construída sem
   projeto), área total construída, número de pavimentos, altura máxima de estocagem.
2. Instalações preventivas: **lista de todas as medidas com X nas exigidas**; 2.1 riscos
   especiais com X (GLP, gás natural, inflamáveis, subestação, gerador, caldeira...).
3. Sinalização: objetivo; para cada grupo (proibição, alerta, orientação e salvamento,
   equipamentos, portas corta-fogo, complementar) a forma, as cores e uma tabela
   código | símbolo | significado | aplicação; formas e dimensões.
4. Iluminação: tipo de sistema com X, requisitos, autonomia, instalação, projeto (simbologia NT 1-03).
5. Extintores: requisitos, classes de fogo, critérios, localização, **ficha de cada tipo**
   (agente, tempo de descarga, alcance, classe, corpo, válvula, pressões) e **rotina de
   manutenção** (semanal, mensal, semestral, anual, 3 e 5 anos).
6. Saídas: critérios de dimensionamento, escadas (comum, EP, PF, antecâmaras, dutos),
   guarda-corpos e corrimãos, rampas, áreas de refúgio, elevadores.
7. Detecção e alarme: central, detectores, acionadores, avisadores (com itens da NBR 17240).
Assinatura do autor no fim.

**C. Memorial de sistema (4 páginas, só sinalização e iluminação).**
Capa com a frase de autenticação, proprietário, endereço, classificação e risco; 1 Objetivo;
2 Considerações gerais; 3 Iluminação (blocos autônomos, altura de instalação, **cálculo de
iluminância** E = F·cos θ / h², manutenção mensal e semestral); 4 Sinalização (tipos e
implantação de cada um com alturas e distâncias, complementar, conservação e inspeção).

## 2. Estrutura que vamos usar (síntese dos três, com a base atual)

Use `references/modelo-memorial-descritivo.md`. Regras de montagem:

1. **Capa**: título, edificação (endereço), proprietário/responsável legal, classificação
   (grupo, divisão, descrição), risco, área, pavimentos, responsável técnico e registro (em branco
   se o usuário não informar), data, revisão; a frase de que o memorial é parte integrante do
   projeto.
2. **Seção 1 — identificação e classificação**: tabela de classificação pela NT 1-04 e pelo
   Anexo do Decreto 42/2018; situação da edificação (nova, existente com ou sem projeto); ATC,
   pavimentos, altura, lotação; tabela do Anexo III usada (`enquadrar_edificacao`).
3. **Seção 2 — medidas exigidas**: a lista completa de medidas com X nas exigidas e "não
   exigida" justificada nas outras (com a célula ou nota da tabela); riscos especiais com X.
   Igual ao Quadro Resumo: os dois têm de bater.
4. **Uma seção por medida exigida**, sempre na mesma ordem interna:
   - base normativa (NT vigente e item; NBR só quando a NT remete a ela);
   - critério de projeto (risco, classe, parâmetros);
   - dimensionamento com a memória de cálculo (fórmula, valores, resultado x exigido) — os
     números do memorial de cálculo do motor;
   - especificação dos equipamentos (tipo, capacidade, autonomia, dimensões das placas);
   - localização e instalação (alturas e distâncias, com item);
   - inspeção e manutenção;
   - conclusão de uma frase ("Portanto, as 5 unidades de passagem existentes atendem às 5
     exigidas pela NT 2-08, item ...").
5. **Medidas dispensadas** ("Isento"/"Não exigido") com a razão.
6. **Encerramento**: frase de responsabilidade e assinaturas (responsável técnico,
   proprietário).

## 3. Como escrever

- Impessoal, no futuro ou no presente normativo: "Serão instalados...", "Os extintores deverão
  ser fixados...", "A edificação foi classificada como...".
- Cada número leva a origem: "a 1,60 m do piso (NT 2-01, item x.y)". Sem origem, não entra.
- Itens com letras: a), b), c); tabelas para classes, placas, populações e materiais.
- Unidades e decimais no padrão brasileiro: "358,34 m²", "0,55 m", "15 m".
- Nomes de placas pelo código da NT 2-05 (S-1, E-5, P-1) e símbolos da NT 1-03.
- O texto descreve **este** projeto: quantidades, ambientes e equipamentos reais. Generalidades
  de norma (escada à prova de fumaça, elevador de emergência, antecâmara) só entram se o projeto
  tiver o elemento.
- Termine cada sistema com a conclusão de atendimento, dizendo o que foi medido.
- Não escreva "aprovado". A conclusão diz que o projeto foi dimensionado conforme a NT; a
  aprovação é do CBMERJ.

## 4. Erros encontrados nos memoriais reais (não repetir)

1. **Base anterior ao Decreto 42/2018**: Decreto nº 897/1976 (COSCIP antigo) e Decreto nº
   35.671/2004 como fundamento; NBR 9077 e NBR 12693 no lugar das NTs 2-08 e 2-01. A base é o
   Decreto Estadual nº 42/2018 e as NTs vigentes; NBR só quando a NT remete a ela.
2. **Valores que se contradizem** dentro do mesmo memorial ou entre memorial e prancha:
   autonomia de iluminação (60 min, 90 min, 2 h, 4 h), altura de placas (1,50 m num, 1,80 m
   noutro), espaçamento entre placas (13 m num, 15 m noutro), área por extintor (150 m² num,
   250 m² noutro, para o mesmo risco). Cada valor vem de uma consulta à NT e aparece igual em
   todos os documentos.
3. **Modelo de outro projeto**: seções de escada à prova de fumaça, antecâmara, elevador de
   emergência e central de alarme em edificação térrea sem esses sistemas; "Localização da
   central:" em branco; ocupação de outro projeto no cálculo de saídas.
4. **Ficha comercial** (marca, modelo, "sugestão de fabricante") no lugar da especificação: o
   memorial especifica o desempenho exigido; marca só se o usuário pedir.
5. **Medidas exigidas sem seção** (ou seção sem medida exigida): a lista da seção 2, o Quadro
   Resumo e as seções seguintes precisam ser o mesmo conjunto.

## 5. Conferência antes de entregar

- [ ] Classificação, área, pavimentos e lotação iguais no memorial, no Quadro Resumo e no carimbo.
- [ ] Cada medida com X tem seção; cada seção tem medida com X.
- [ ] Quantidades (extintores, placas, blocos, saídas) iguais às contadas na planta.
- [ ] Toda altura, distância, autonomia e capacidade com NT e item.
- [ ] Nenhuma referência revogada; nenhuma generalidade de sistema que o projeto não tem.
- [ ] Campos do responsável técnico em branco quando o usuário não informou (nunca inventar).
