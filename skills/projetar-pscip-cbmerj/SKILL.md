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
| CALCULA | chamar a ferramenta (`dimensionar_extintores`, `dimensionar_saidas`, `dimensionar_hidrantes`, `dimensionar_sprinklers`) com os dados do usuário; ler premissas e pendências do memorial |
| REQUISITOS | `requisitos_iluminacao_alarme`; o que ficar como pendência, resolver com o usuário |
| LER_NT | `consultar_norma` na(s) NT(s) indicada(s): primeiro sem item (sumário/busca), depois os itens de dimensionamento; registrar no `projeto.md` o que a NT exige, com documento e item |

Observações típicas das células e o que fazer com elas:
- "escada … Não Enclausurada / Enclausurada": é o tipo de escada. Detalhes na NT 2-08
  (`consultar_norma("NT 2-08", "Anexo B")` e itens 5.4 a 5.7).
- "Exigido apenas para … ATC superior a …": compare com a área informada e diga se a condição
  se aplica.
- "Pode ser substituída por …": decisão do projetista. Pergunte.

### 5. Desenhar
1. `criar_planta` (ou `retomar`), com `escala` = denominador da impressão (100 = 1:100, o
   padrão): é ela que dá a texto, cota e marcas o tamanho certo no papel.
2. `desenhar_planta`: ambientes (`sala`), paredes com o estilo certo (`corta_fogo`,
   `compartimentacao`), portas (`corta_fogo_min` quando for PCF; a etiqueta `80x210` sai sozinha),
   **janelas** (`janela`: largura, altura e peitoril, etiqueta `150x120/90`), símbolos nas
   quantidades calculadas, usando os ids de `listar_simbologia`, título do pavimento, cotas
   (`cota_cadeia` para trechos e total), `marca_corte` onde houver corte e `legenda`.
   Altura e peitoril só entram nas etiquetas: pergunte ao usuário, não invente.
   Em planta de projeto as placas de sinalização vão como `chamada` (círculo com código e
   dimensão; a dimensão vem da Tabela 7 da NT 2-05 pela distância de visualização, não se
   chuta), e louças, mesas, equipamentos de cozinha, recipientes de GLP, escada e pilar como
   `mobiliario` (ids de `listar_blocos`; o motor não os conta como equipamento de segurança).
   Pictogramas das placas marcados como `simplificado` não são o desenho oficial.
   A prancha é a operação `folha` (formato A0 a A4, carimbo, vistas com janela e escala,
   legenda, notas, revisões). O carimbo segue o modelo das pranchas aprovadas no CBMERJ (título
   do PSCIP e destinação, conteúdo, nº da prancha, proprietário, endereço, escala/data/área/
   revisão, assinaturas do proprietário, do autor do levantamento arquitetônico e do autor do
   projeto de segurança, aprovação do CBMERJ) e precisa dos dados do AAST 01/2025, item 3.2:
   responsável legal, nome completo e registro (com o conselho) do RT e do responsável pela
   arquitetura, cadastro no CBMERJ e empresa com registro quando houver. Só leva o que o usuário
   informou, nunca nomes, registros ou datas inventados: o retorno
   `carimbo.campos_aast_01_2025_em_branco` diz o que pedir a ele. Cores obrigatórias do projeto
   digital (AAST 01/2025, 3.5), já aplicadas pelas camadas do motor: vermelho para extintores,
   sistemas fixos e placas de equipamentos (E), verde para orientação e salvamento (S), azul
   para iluminação, roxo para detecção e alarme, laranja para as demais placas (P, A) e outros
   sistemas, preto para o resto. A `legenda` desenha as tabelas "LEGENDA SISTEMA DE INCÊNDIO"
   e "LEGENDA - SINALIZAÇÃO DE EMERGÊNCIA" (placa, círculo com código e tamanho, descrição);
   `folha.legenda` a põe no alto da coluna do carimbo. `exportar_pdf` gera o PDF (exige o PyMuPDF) e `exportar_dwg` grava o DWG
   (exige o ODA File Converter) e confere a ida e volta: se `conferencia.confere` vier falso, leia
   `diferencas` antes de entregar. O DWG é o formato do protocolo, mas a conferência só mostra o
   que foi preservado do DXF; abrir no AutoCAD continua sendo do responsável técnico.
   O Quadro Resumo é a operação `quadro_resumo` (uma por planta), no modelo do CBMERJ (NT 1-01,
   5.3.7 h; vai impresso na planta de situação ou prancha 01): identificação, classificação,
   estrutura, medidas, riscos especiais, RTI, bomba, hidrantes, gás, materiais e saídas vão como
   o usuário informou (em branco se faltar); as quantidades de extintores, hidrantes, placas,
   iluminação, alarme/detecção, GLP e áreas saem contadas do desenho. Passe em
   `declarado` os números que o cálculo fixou (extintores, saídas, GLP, ATC) e leia
   `quadro_resumo.conferencia` no retorno: cada divergência é uma pendência a resolver no desenho
   ou no quadro, e a contagem não prova conformidade.
   Cortes e fachadas **da planta** (não esquemáticos): peça ao usuário pé-direito, espessura da
   laje e platibanda, informe-os na operação `edificacao` (uma por planta) e acrescente `secao`
   (linha a-b na planta) e `fachada` (um dos quatro lados), desenhadas fora da planta. Altura de
   porta e janela vêm das próprias operações; volumes que passam do telhado (duto, abrigo) vão em
   `edificacao.volumes`. O resumo traz `vistas.premissas`: alturas do mobiliário são medidas usuais
   da biblioteca, não dado do projeto.
   **Composição como nas pranchas aprovadas** (medida em projetos reais, detalhes em
   `references/desenho-de-pranchas.md`): em `edificacao` informe também a cobertura (uma ou duas
   águas, caimento ou cumeeira, inclinação, beiral, telha) e o forro, que os cortes e as fachadas
   desenham com chamada; cada `secao` põe a figura humana de 1,70 m num vão livre e, com a classe
   do revestimento informada (classe_parede), o rótulo PAREDE CLASSE; faça ao menos dois cortes
   perpendiculares; a `fachada` da rua leva os traços de vidro e, se o usuário quiser, o letreiro.
   Nos ambientes, `rotulo_classe` (PISO/PAREDE/TETO CLASSE, NT 2-20) com a classe informada, em
   ponto livre. A planta de situação é a operação `situacao` (escala própria, 1:500 ou 1:250:
   lote cotado, edificação hachurada com setas de caimento, ruas com meios-fios, esquinas e
   nomes, distância à esquina e norte), com os dados do usuário, longe da planta. Na `folha`,
   cada vista ganha o título numerado; o cálculo da largura das saídas vai em `folha.quadros`
   com as linhas do memorial de `dimensionar_saidas`. Arranjo usual: prancha 01 com o Quadro
   Resumo e a situação; prancha 02 com planta, cortes, cobertura e fachada; notas por sistema e
   legendas na coluna do carimbo.
   **Detalhes de instalação** (operação `detalhe`, uma por modelo, longe da planta): extintor,
   abrigo de mangueiras, hidrante de recalque no passeio ou na fachada, bloco autônomo,
   sinalização de saída e, quando houver GLP, a central (recipiente e quantidade informados:
   abrigo, ventilação, placa PERIGO e extintores pela NT 3-02) e os reguladores de 1º e 2º
   estágio (bitolas da rede informadas, ou "conforme projeto"). Cada um sai cotado com as medidas das NTs e notas com NT e item; o
   retorno lista as medidas normativas, os dados informados e a região em metros para a vista
   da folha. Faça um detalhe para cada medida exigida que tenha equipamento instalado; peça ao
   usuário o risco e a vazão dos hidrantes, a altura do abrigo e do bloco, o fluxo luminoso e a
   dimensão das placas. Detalhe recusado por citação não conferida é pendência: diga ao usuário.
   **Sprinklers:** a classe de risco (Leve, Ordinário 1 ou 2, Extraordinário 1 ou 2) e os
   critérios (densidade, área de operação, área por bico, espaçamento) vêm da norma adotada, NBR
   10897 ou NFPA 13: pergunte; a NT 2-03 não os fixa. Rode `dimensionar_sprinklers` (ambientes
   com o tipo, para as dispensas, e zonas com o ponto de alimentação) e leia as premissas do
   memorial: o que o usuário não informar usa a referência da NFPA 13, que precisa ser conferida.
   Depois desenhe com as operações `sprinklers` (malha de bicos, ramais, subgeral, área de
   operação) e `isometrico` (a 30°, com o quadro de cálculo hidráulico), este longe da planta.
   Os bicos e as placas saem com o desenho oficial das NT 1-03 e 2-05.
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
`salvar_memorial` com `dados_da_edificacao`. Redija o **memorial descritivo** pelo
`references/modelo-memorial-descritivo.md` (estrutura, estilo e os erros encontrados nos
memoriais reais em `references/memorial-descritivo.md`): uma seção por medida exigida, na ordem
base normativa → critério → dimensionamento → especificação → instalação → manutenção →
conclusão, com os mesmos números do memorial de cálculo, do Quadro Resumo e da planta. Rode o
verificador de sobreposição nas pranchas. Entregue ao usuário, conforme
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

Conjunto de bombas (NT 2-04), zonas de pressão, quantidade de placas e de pontos de iluminação e
detecção (NBR 10898 e 17240 não estão na base), SPDA, brigada, TRRF, controle de fumaça,
posicionamento automático dos equipamentos e o texto do memorial descritivo (você o redige pelo
modelo). Telhado só sobre pegada retangular (um plano por água, beiral uniforme); cortes sem
remoção de linhas ocultas; situação desenhada com os dados informados, sem conferência com
levantamento. Nessas partes você lê a NT e registra as exigências; o dimensionamento fica como
pendência para o responsável técnico.
