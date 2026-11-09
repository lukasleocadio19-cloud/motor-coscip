---
name: projetar-pscip-cbmerj
description: "Elaborar (projetar) um Projeto de Segurança Contra Incêndio e Pânico (PSCIP) para o CBMERJ com o motor COSCIP (servidor MCP coscip-plantas): enquadrar a edificação pelo Decreto Estadual nº 42/2018, dimensionar extintores, saídas e hidrantes, tratar as demais medidas pelas Notas Técnicas, desenhar as plantas com a simbologia da NT 1-03, gerar corte esquemático e memorial de cálculo. Usar SEMPRE que o usuário pedir para projetar, dimensionar, calcular, desenhar ou montar um projeto de incêndio, PSCIP, PPCI, laudo de exigências a atender, memorial de cálculo ou planta de segurança — e não para analisar um processo já pronto (isso é $orquestrar-analise-cbmerj)."
---

# Projetar PSCIP para o CBMERJ com o motor COSCIP

Conduzir o projeto do começo ao fim usando as ferramentas `mcp__coscip-plantas__*`. O motor
calcula, desenha e confere; você conduz, pergunta o que falta e lê as Notas Técnicas das medidas
que o motor não calcula. O resultado é um **rascunho para o responsável técnico revisar e
assinar**: diga isso ao usuário no início e no fim.

## Regras que não se quebram

1. **Não invente dados da edificação.** Ocupação, áreas, pavimentos, alturas, traçado de
   tubulação, materiais: pergunte. Ver `references/perguntas.md`.
2. **Todo número de norma sai de ferramenta ou de `consultar_norma`**, com documento e item
   citados. Nunca de memória. Se a ferramenta recusar ("citação não conferida"), pare e relate.
3. **Premissa é premissa.** O que o memorial lista em "premissas do projetista" precisa ser
   dito ao usuário e confirmado por ele.
4. **Traço na tabela não é dispensa.** Medida "sem marcação" não é "não exigida": leia as
   observações e as notas gerais antes de afirmar qualquer coisa.
5. **A unidade do desenho precisa de duas medidas confirmadas pelo usuário** (em direções
   diferentes) antes de `analisar_planta`.
6. **Distância só vale depois de conferida na planta.** Quantidade pelo cálculo não garante
   percurso: rode `analisar_planta` e ajuste até não haver pendência de percurso.
7. **Leia o campo `conferencia` do enquadramento.** As Tabelas 5 a 32 foram conferidas no PDF
   oficial pelo assistente em 09/11/2026, não por um responsável técnico: diga isso. Se o campo
   trouxer "SEM conferência visual" (texto ou leitor mudaram), avise e recomende conferir a
   tabela no Decreto antes de usar.
8. Nada tem valor normativo. Não escreva "aprovado", "atende à norma" ou "pronto para protocolo".

## Passo a passo

### 1. Abrir o controle do projeto
Copie `references/modelo-projeto.md` para a pasta do projeto do usuário (ex.
`<pasta>/projeto.md`) e mantenha-o atualizado a cada etapa. Ele é a memória do projeto entre
sessões: dados informados, medidas, situação de cada uma, premissas e pendências.

### 2. Levantar os dados
Faça as perguntas de `references/perguntas.md` (só as que se aplicam). Se o usuário tiver planta
em DXF/DWG, abra com `abrir_planta` e leia nomes de ambientes e cotas com `listar_textos`.

### 3. Enquadrar
`enquadrar_edificacao` com `occupancy`, `building_area_m2`, `building_floors`,
`single_occupancy` e, acima de 6 pavimentos, `building_height_m`.

- `status` INDICATIVE: siga para o passo 4 com a lista `medidas`.
- MISSING_DATA: pergunte o dado que falta.
- REVIEW_REQUIRED: ocupação mista, unifamiliar ou agrupamento. Explique ao usuário; ocupações
  mistas pedem enquadramento de cada ocupação e o critério do Decreto (leia com
  `consultar_norma`, documento "Decreto 42/2018").
- CHOOSE_COLUMN (grupo M): mostre as colunas e pergunte qual é o caso.
- UNVERIFIED ou sem tabela: leia a tabela com `consultar_norma` e diga que foi leitura sua.

Leia também `excecoes_que_o_motor_nao_aplica` (NT 1-04) e pergunte ao usuário se alguma vale.

### 4. Tratar cada medida
Para cada item de `medidas`, siga `como_tratar` e as `observacoes` da célula. O quadro completo
está em `references/medidas.md`. Resumo:

| `como_tratar.situacao` | O que fazer |
|---|---|
| CALCULA | chamar a ferramenta (`dimensionar_extintores`, `dimensionar_saidas`, `dimensionar_hidrantes`) com os dados do usuário; ler premissas e pendências do memorial |
| REQUISITOS | `requisitos_iluminacao_alarme`; o que ficar como pendência, resolver com o usuário |
| LER_NT | `consultar_norma` na(s) NT(s) indicada(s): primeiro sem item (sumário/busca), depois os itens de dimensionamento; registrar no `projeto.md` o que a NT exige, com documento e item |

Observações típicas das células e o que fazer com elas:
- "escada … Não Enclausurada / Enclausurada": é o tipo de escada. Detalhes na NT 2-08
  (`consultar_norma("NT 2-08", "Anexo B")` e itens 5.4 a 5.7).
- "Exigido apenas para … ATC superior a …": compare com a área informada e diga se a condição
  se aplica.
- "Pode ser substituída por …": decisão do projetista. Pergunte.

### 5. Desenhar
1. `criar_planta` (ou `retomar`).
2. `desenhar_planta`: ambientes (`sala`), paredes com o estilo certo (`corta_fogo`,
   `compartimentacao`), portas (`corta_fogo_min` quando for PCF), símbolos nas quantidades
   calculadas, usando os ids de `listar_simbologia`, título do pavimento, cotas e `legenda`.
3. Um pavimento por região do desenho, afastados entre si; `corte` para o esquema vertical
   (pavimentos, pé-direito, reservatório e prumada de hidrantes), fora das plantas.
4. `ver_planta` a cada etapa para conferir o que saiu.

### 6. Conferir
`confirmar_unidade` (com duas medidas confirmadas pelo usuário, em direções diferentes) →
`definir_pavimentos` →
`analisar_planta` com o mesmo contexto do enquadramento. Para cada pendência: ajuste o desenho
(`remover_elementos` / `desenhar_planta`) e analise de novo. `ver_planta` com `percurso` mostra
o pior caminho.

### 7. Entregar
`salvar_memorial` com `dados_da_edificacao`. Entregue ao usuário, conforme
`references/entregaveis.md`: o que foi feito, o que é premissa, o que ficou pendente e o que o
motor não cobre. Atualize o `projeto.md`.

## Quando parar e perguntar

- Dado da edificação faltando ou contraditório.
- Ferramenta recusou por citação não conferida, ou tabela UNVERIFIED.
- Ocupação mista, risco específico (GLP, inflamáveis, cozinha profissional, gerador, subestação,
  heliponto) ou ocupação especial (grupos 3, 4 e 5 das NTs): leia a NT específica e confirme o
  enquadramento com o usuário antes de dimensionar.
- A análise da planta aponta pendência que só muda com alteração de arquitetura (largura de
  corredor, nova saída).

## O que o motor ainda não faz (diga ao usuário)

Cálculo de sprinklers, conjunto de bombas (NT 2-04), zonas de pressão, quantidade de placas e de
pontos de iluminação e detecção (NBR 10898 e 17240 não estão na base), SPDA, brigada, TRRF,
controle de fumaça, pranchas com carimbo e Quadro Resumo, PDF e posicionamento automático. Nessas
partes você lê a NT e registra as exigências; o dimensionamento fica como pendência para o
responsável técnico.
