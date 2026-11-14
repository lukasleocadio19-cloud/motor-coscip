# Motor CAD/COSCIP — modo PROJETO (arquitetura)

Documento de arquitetura, não registro: estado, histórico e pendências continuam só em
[`proxima-sessao.md`](proxima-sessao.md). Iniciado em 09/11/2026.

## 1. Objetivo

O motor nasceu para **conferir** projetos (planta → evidência → achado). O modo projeto faz o
caminho inverso: a partir dos dados da edificação, **dimensiona** as medidas de segurança, gera o
**memorial de cálculo**, **desenha** as plantas com a simbologia oficial e os cortes esquemáticos, e
usa o próprio motor de conferência para verificar o que desenhou.

Meta: um rascunho completo de Projeto de Segurança Contra Incêndio e Pânico (PSCIP) que um
responsável técnico revisa e assina. O motor **não substitui** o profissional habilitado: sem
ART/RRT, sem homologação das regras e sem conferência humana, nada tem valor normativo.

## 2. Princípios (herdados do projeto)

1. **Todo número da norma tem citação conferida.** Os parâmetros ficam em
   `normative/projeto/parametros.yaml`, cada um com documento, item e termos que são procurados no
   texto ingerido ao carregar. Citação que não confere → o parâmetro não é usado e o cálculo é
   recusado (não há valor "de memória").
2. **O que a norma não fixa é premissa do projetista**, listada à parte no memorial: constante da
   fórmula de Hazen-Williams (imagem no texto ingerido), C da mangueira, comprimentos equivalentes,
   rendimento da bomba. Nenhuma premissa entra escondida.
3. **Dados da edificação vêm do usuário.** Ocupação, áreas, alturas, traçado da tubulação: a IA
   pergunta, não supõe.
4. **Ausência não vira dispensa.** Tabela não carregada responde "fora do escopo", nunca "nada
   exigido".
5. **Projetar e conferir são o mesmo motor.** O que o modo projeto desenha é relido pelo leitor de
   plantas; distâncias a percorrer (extintor, hidrante, acionador, saída) só são dadas como
   atendidas depois de `analisar_planta`.

## 3. Componentes

| Camada | Onde | Papel |
|---|---|---|
| Parâmetros | `normative/projeto/parametros.yaml` | valores das NTs com citação; Anexo A da NT 2-08 linha a linha |
| Cálculo | `packages/design/coscip_design` | `params` (carrega e confere), `memorial` (passos, premissas, pendências), `extintores`, `saidas`, `hidrantes`, `sistemas` |
| Desenho | `apps/mcp/coscip_mcp/autoria.py`, `simbologia.py` | operações de planta, catálogo NT 1-03/2-05, legenda, corte esquemático |
| Conferência | `packages/analysis`, `packages/normative` | leitura do DXF, percursos, Plano de Verificação (já existia) |
| Ferramentas | `apps/mcp/coscip_mcp/server.py` | MCP: `enquadrar_edificacao`, `dimensionar_*`, `requisitos_iluminacao_alarme`, `salvar_memorial`, `desenhar_planta` (com `corte`) |

`coscip_design` não depende do MCP: a API e o app web podem chamá-lo depois.

## 4. Fluxo de um projeto

```
enquadrar_edificacao      divisão + ATC + pavimentos → risco (NT 1-04), medidas exigidas
        │                 (Decreto 42/2018, Anexo III), limite até a saída (NT 2-08, Anexo C)
        ▼
dimensionar_extintores    NT 2-01: quantidade por pavimento, tipo, capacidade
dimensionar_saidas        NT 2-08: população, unidades de passagem, larguras, portas, escadas
dimensionar_hidrantes     NT 2-02: sistema, RTI, perdas, altura manométrica, bomba
requisitos_iluminacao_alarme  NT 2-06 / NT 2-07: o que as NTs fixam
        │                 cada cálculo devolve memorial com base normativa, premissas e pendências
        ▼
criar_planta → desenhar_planta   salas, paredes, portas, símbolos nas quantidades calculadas,
        │                        legenda e corte esquemático (esquema vertical)
        ▼
confirmar_unidade → definir_pavimentos → analisar_planta   percursos reais e Plano de Verificação
        │                 pendência → ajustar o desenho e analisar de novo
        ▼
salvar_memorial           Markdown com todos os cálculos da sessão
```

## 5. O que existe (fase P1, 09/11/2026)

- **Extintores (NT 2-01):** unidades pela área máxima por risco, mínimo de dois, exceção de 50 m²,
  capacidade mínima (Tabelas 1 e 2), sobre rodas e 4-A no risco grande, instalações especiais.
- **Saídas (NT 2-08):** população pelo Anexo A (área, dormitórios, leitos, vagas), N = P/C,
  larguras mínimas, vãos de porta, escadas pelo pavimento de maior população, duas saídas e barra
  antipânico no grupo F, duas escadas a partir de 15 pavimentos.
- **Hidrantes (NT 2-02):** sistema pela Tabela 1, RTI (redação de 2020), Hazen-Williams por trecho
  com comprimento equivalente, velocidades (2, 3 e 5 m/s), perda na mangueira, altura manométrica
  total no modelo do Anexo B, pressão máxima de 100 mca, potência estimada, hidrante de recalque,
  casa de máquinas e abrigos.
- **Iluminação e alarme:** só o que as NT 2-06 e 2-07 fixam (locais, autonomia, 30 m até o
  acionador).
- **Corte esquemático:** pavimentos empilhados com níveis, cota total, prumada de hidrantes,
  reservatório com a RTI e registro de recalque. Sai das alturas informadas.

- **Enquadramento completo (09/11/2026):** Anexo III, Tabelas 2 a 32, com as observações de cada célula e o roteiro de cada medida (`medidas.yaml` → `como_tratar`).
- **Skill** `skills/projetar-pscip-cbmerj`: conduz o Claude pelo projeto inteiro, incluindo as medidas sem cálculo (ler a NT e registrar).

## 6. Limites conhecidos (o que falta para "o projeto todo")

| Falta | Por quê | Fase |
|---|---|---|
| Conferência do Anexo III por responsável técnico | as Tabelas 5 a 32 foram conferidas no PDF oficial pelo assistente em 09/11/2026 (registro com resumo da leitura em `normative/projeto/anexo-iii.yaml`); falta a conferência de um profissional | sempre |
| Ocupação mista | o enquadramento trata uma ocupação por vez | P2 |
| Detalhamento da escada (NT 2-08) | o tipo (enclausurada ou não) já vem nas observações do Anexo III; o Anexo B e o detalhamento são lidos na NT | P2 |
| Conjunto de pressurização (NT 2-04) | quantidade e tipo de bombas, partida, NPSH | P2 |
| Tabela de comprimentos equivalentes | a NT não traz; hoje o projetista informa a soma por trecho | P2 |
| Sinalização (NT 2-05) | quantidade e posição das placas, dimensão pela distância de visualização (Tabela 7) | P2 |
| Sprinklers (NT 2-03) | cálculo hidráulico por área de operação | P3 |
| Iluminação e detecção por norma ABNT | NBR 10898 e NBR 17240 não estão na base (direito autoral: não podem ser copiadas para o repositório) | P3 |
| SPDA, brigada, compartimentação, TRRF, CMAR, controle de fumaça, acesso de viaturas | NT 2-10 a 2-20: nada calculado | P3 |
| Riscos específicos e ocupações especiais | NTs dos grupos 3, 4 e 5 | P4 |
| Posicionamento automático de equipamentos | hoje a IA posiciona e o motor confere; falta um otimizador sobre a grade de percursos | P3 |
| Corte real | uma planta 2D não tem altura; corte de verdade exige modelo 3D ou dados por ambiente | P4 |
| Pranchas (folha, carimbo, Quadro Resumo, escala) e PDF | hoje sai DXF em modelspace e memorial em Markdown | P2 |
| Isométrico da rede de hidrantes | só o esquema vertical | P3 |
| Homologação | regras e parâmetros em rascunho; sem responsável técnico | sempre |

## 7. Bibliotecas

Nenhuma dependência nova nesta fase: `ezdxf` (DXF), `shapely` (geometria), `pydantic` (entradas),
`pyyaml` (parâmetros). Candidatas para as próximas fases, a decidir quando o caso chegar:

- **PDF das pranchas:** o backend de desenho do `ezdxf` com `PyMuPDF` ou `matplotlib`.
- **Rede hidráulica malhada (sprinklers, anéis):** resolver por Hardy-Cross próprio ou `wntr`
  (EPANET); para rede ramificada o cálculo por trechos atual basta.
- **Modelo 3D / IFC para cortes reais:** `ifcopenshell`.

## 8. Como estender

1. Ler o item na NT (`consultar_norma`) e, se for tabela com célula mesclada, conferir na imagem.
2. Acrescentar o parâmetro em `parametros.yaml` com `fonte` (`quote` ou `linha`).
3. Rodar `pytest tests/unit/test_design.py`: o primeiro teste falha se a citação não conferir.
4. Usar o parâmetro no cálculo com `params.get(...)` e registrar no memorial (`m.passo(..., base=[p])`).
5. O que não vier da norma entra em `m.premissas`; o que ficar em aberto, em `m.pendencias`.

## 9. Desenho profissional: lacunas medidas contra um projeto real (frente D, 09/11/2026)

Referência: um projeto digital real de restaurante (processo de retorno, DWG de 1,8 MB, 2 pavimentos,
central de GLP, cozinha com coifa), lido por conversão para DXF e `ezdxf`. O arquivo é local e **não
entra no repositório** (dados reais). Nada foi copiado dele; só se mediu como ele é apresentado.

**Como o desenho profissional é montado**

| Aspecto | No projeto real | No motor hoje |
|---|---|---|
| Espaços | model space com todas as vistas espalhadas; **layouts A0/A1** com 14 a 15 *viewports* em escalas fixas (1:100 plantas e cortes, 1:50 detalhe de GLP, 1:75 isométrico, 1:250 situação e cobertura) | só model space, sem layout; o PDF das pranchas foi montado à parte |
| Unidades | desenhado em **metros** (portas de 0,6 a 1,6; texto de 0,1 a 0,3), apesar de `$INSUNITS` = mm | metros, `$INSUNITS` = 6 (correto) |
| Camadas | nomes funcionais em português (Alvenaria, Porta, Janela, Escada, Sanitários, Coifa, Sinalização, Incêndio, Cotas e texto, Detalhes, Hachuras, tubulação de sprinkler) com **espessura e cor por camada**: alvenaria 0,60 mm, estrutura de aço 0,30, incêndio/porta/janela 0,25, hachura 0,13, texto e cota 0,09; incêndio em vermelho, saída em verde, iluminação em azul | 17 camadas, todas cor 7 e espessura padrão |
| Texto e cota | 22 estilos de cota e dezenas de estilos de texto **nomeados pela escala** ("1-100", "1-50"); texto de 2 mm impresso (0,2 m a 1:100); cotas em cadeia mais total, "24,00" com vírgula | uma cota simples, texto "2500", sem estilo por escala |
| Paredes e vãos | parede em polilinha grossa com hachura sólida; portas com folha, arco e etiqueta (`80x210`); **janelas** com etiqueta (`150x120/60`); porta de enrolar | parede em duas linhas finas; só porta com arco; sem janela nem etiqueta |
| Símbolos de incêndio | blocos da NT 1-03 na camada Incêndio **mais chamadas**: círculo com código e dimensão (E-5 `150x150`, S-1 `240x120`, S-12 `252x126`), bloco de iluminação, legenda em planta, setas de corte | símbolos da NT 1-03 e placas esquemáticas (sem pictograma), sem chamada nem dimensão |
| Biblioteca | cerca de 100 blocos: louças, mesas, fogão, coifa, recipientes de GLP (P-45, P-190), central de GLP, recalque, chave | nenhum bloco de arquitetura ou equipamento |
| Quadro Resumo | tabela completa no model space (identificação, classificação, NT 2-19, medidas, GLP, quadro de áreas, extintores, **sinalização por código e dimensão**, iluminação, materiais NT 2-20, saídas NT 2-08) | não existe |
| Folha | selo com responsável técnico, autor, proprietário, escala, prancha, histórico; quadro de áreas; termo de responsabilidade; notas de projeto citando as NBR | não existe |
| Corte e fachada | cortes com piso, estrutura, hachura de vidro, equipamento (fogão, coifa, damper corta-fogo) e cotas de altura | `corte` esquemático só com níveis |
| Detalhes | central de GLP 1:50, instalação de sinalização, planta de situação e cobertura | não existem |

O que **não** copiar: 100+ camadas com nomes duplicados e legados, estilos de texto repetidos,
camadas importadas de PDF, blocos de mobiliário de terceiros com 1.500 entidades, 300 correções de
auditoria, unidade declarada errada.

**Ordem sugerida (cada item é entregável e testável sozinho)**

1. **D1, padrões de apresentação (FEITO em 09/11/2026):** `coscip_mcp/apresentacao.py` com a
   tabela de camadas (cor, espessura e tipo de linha; o catálogo inteiro está coberto por teste),
   estilos de texto, estilo de cota por escala (`COSCIP-100`, tique arquitetônico, "24,00"),
   altura de texto pela escala de impressão (`criar_planta escala=`), operações `janela`
   (vão, caixilho e etiqueta `150x120/90`), `cota_cadeia` (trechos e total) e `marca_corte`
   (linha, setas e círculos), e etiqueta `80x210` nas portas. Testes: `tests/unit/test_apresentacao.py`
   e `tests/integration/test_autoria_apresentacao.py`. **Fica para depois:** poché sólido nas
   paredes comuns (a NT 1-03 só preenche corta-fogo e compartimentação), multileaders e chamadas
   (D2), e o servidor MCP precisa ser reiniciado para listar as operações novas.
2. **D2, símbolos e chamadas (FEITO em 09/11/2026):** operação `chamada` (bloco
   `PLACA_CHAMADA_<código>` com atributos `CODIGO` e `DIMENSAO`, círculo na cor do grupo, linha
   de chamada até o alvo; o leitor a conta como sinalização e, em S-12/S-14, também como saída);
   biblioteca própria `coscip_mcp/biblioteca.py` (18 blocos: louças, mesas, equipamentos de
   cozinha, coifa, recipientes de GLP, escada, pilar), operação `mobiliario` e ferramenta
   `listar_blocos`; pictogramas **simplificados** para 15 placas, **substituídos em 11/11/2026
   pelo desenho oficial** (ver "Desenho oficial das NTs" abaixo). Corrigido o preenchimento sólido
   dos símbolos, que o ezdxf forçava para a cor 7. **Fica para depois:** a dimensão da placa pela
   distância de visualização (Tabela 7; hoje é informada), legenda que inclua as chamadas e
   blocos de mais mobiliário.
3. **D3, folhas (FEITO em 09/11/2026):** `coscip_mcp/folhas.py`: operação `folha` (A0 a A4, em
   paper space) com moldura, selo (só o que o usuário informa; aviso de rascunho sempre), quadro
   de áreas a partir dos ambientes e da ATC, notas, tabela de revisões e uma *viewport* por vista
   (`altura da vista = altura no papel × escala / 1000`), com arrumação automática e erro que
   sugere a escala ou o formato quando não cabe; ferramenta `exportar_pdf` (renderiza cada vista
   na escala e recorta na janela; exige PyMuPDF, extra `pdf`). **Fica para depois:** camadas
   congeladas por viewport, mais de um pavimento por folha, selo em modelo próprio do CBMERJ e o
   Quadro Resumo (D4).
4. **D4, Quadro Resumo automático (FEITO em 10/11/2026):** `coscip_mcp/quadro_resumo.py`, operação
   `quadro_resumo` (uma por planta; tabela no model space, na escala da planta, com as seções do
   formato real: identificação, classificação, carga de incêndio, estruturais, medidas, riscos
   especiais, GLP, quadro de áreas, extintores, sinalização, iluminação, materiais NT 2-20 e
   saídas NT 2-08). Dois tipos de conteúdo que não se misturam: o que o usuário **informa** vai
   como informado (o que faltar fica em branco, sem inventar) e o que está **desenhado** é contado
   das operações, por pavimento (janela por pavimento): extintores por agente e capacidade, placas
   por código e dimensão, pontos de iluminação, recipientes de GLP e área útil dos ambientes.
   `quadro_resumo.conferencia` no retorno compara o desenho com o `declarado` (extintores
   calculados, saídas, GLP, ATC) e diz `confere`, `diverge` ou `sem dado declarado`, incluindo
   uma placa S-12/S-14 por saída desenhada. É consistência, não conformidade. As células com
   códigos de placa não são lidas como placas pelo leitor (teste). **Fica para depois:** contagem
   a partir do DXF relido (hoje sai das operações), luminária × farolete (o catálogo só tem
   "ponto de iluminação"), classe de extintor (2-A:20-B:C) e ligação automática com os memoriais
   de `dimensionar_*` (o `declarado` ainda é preenchido por quem chama).
5. **D5, modelo da edificação (FEITO em 10/11/2026, primeira versão):** `coscip_mcp/vistas.py` e
   as operações `edificacao` (pé-direito, laje, platibanda e volumes como duto e abrigo, **todos
   informados pelo usuário**), `secao` e `fachada`. O modelo sai da MESMA geometria da planta
   (paredes já com os vãos recortados, contorno externo, portas e janelas com altura e peitoril,
   mobiliário com altura da biblioteca, extintores e luminárias), então a cota total do corte
   (10,30 m) é a da planta. Corte: paredes, piso, laje e peças cortadas hachurados, verga e
   peitoril nos vãos, o que está além do plano em traço fino dentro de uma profundidade, cotas
   de altura e em cadeia, níveis, título e escala. Fachada: arestas externas de um lado, portas e
   janelas nas posições da planta com etiqueta `LxA/peitoril`, platibanda e volumes acima do
   telhado. As camadas `VISTA_*` evitam nomes que o leitor trata como obstáculo (teste: o leitor
   enxerga o mesmo com e sem vistas). **Fica para depois:** remoção de linhas ocultas, telhado
   inclinado, escadas em corte, mais de um pavimento por modelo, recuos de profundidade na
   fachada, esquadrias detalhadas; alturas do mobiliário são medidas usuais (`ALTURAS` na
   biblioteca), avisadas no retorno em `vistas.premissas`. Detalhes padrão (central de GLP,
   sinalização, extintor) e situação 1:250 continuam pendentes.
6. **D6, teste de referência (FEITO em 10/11/2026):** `tools/validacao/desenho_referencia.py`
   (`MEDIR`, `COMPARAR`, `EXEMPLO`) mede um DXF/DWG (camadas, blocos em uso, estilos de cota,
   layouts, escalas das *viewports*, 24 recursos sim/não) e compara com o motor; só saem números e
   presenças, nunca texto do desenho. O gabarito do projeto real está em
   `docs/validacao/desenho-referencia.yaml` (sem nome, endereço nem registro). Lacunas conhecidas,
   fixadas em `tests/unit/test_desenho_referencia.py` (o teste falha quando uma deixa de existir):
   detalhes construtivos, isométrico, planta de situação, indicação de norte e *multileaders*.
7. **D7, DWG de produção (FEITO em 10/11/2026):** `coscip_cad/dwg_export.py` e a ferramenta
   `exportar_dwg`: converte uma **cópia** do DXF do motor em DWG 2018 pelo ODA File Converter e
   confere a ida e volta, reabrindo o DWG e comparando com o DXF: camadas e suas propriedades
   (cor, espessura, tipo de linha, ligada, congelada, plotável), blocos, estilos de cota, de texto
   e de linha, layouts, escala de cada *viewport*, entidades por camada e tipo, textos (inclusive
   atributos), extensão do desenho (tolerância de 1 mm) e `$INSUNITS`. Não contam: blocos
   anônimos (renumerados pelo conversor), a *viewport* do layout inteiro (o conversor a muda de
   camada) e camadas que o conversor acrescenta. Medido com o exemplo do restaurante (3 pranchas
   A1, 32 camadas, 1.616 entidades, 372 textos): confere. O DWG só aparece inteiro (grava e
   troca), não sobrescreve sem pedir e é entregue mesmo quando a conferência diverge
   (`conferencia.confere` e `diferencas` dizem o quê). **A conferência prova o que o DWG
   preservou do DXF, não que o AutoCAD o abra sem aviso:** isso só o AutoCAD confirma.
   **Licença:** o conversor gratuito é de uso não comercial para quem não é membro da ODA; o SDK
   de teste que está nesta máquina expira (quando falhar, instalar o gratuito em opendesign.com,
   aceitando a licença, e remover `COSCIP_ODA_PATH`). Produto vendido exige assinatura da ODA.

Dependências: `ezdxf` já basta para layouts, *viewports*, blocos com atributos, hachuras e cotas;
`PyMuPDF` para o PDF. O mesmo vale para `shapely` na geometria das paredes. O modelo 3D/IFC
(`ifcopenshell`) só entra se D5 precisar de mais que alturas por ambiente.

## 10. Desenhos oficiais das NTs, sprinklers e isométrico (frente E, 11/11/2026)

**E1. Símbolos e placas iguais aos da NT.** Os desenhos que o motor aproximava à mão agora são os
da própria tabela. O PDF oficial (NT 1-03 2ª ed. e NT 2-05 3ª ed., hash conferido contra o
manifesto) guarda cada placa como imagem raster sem perda; `tools/normas/extrair_simbolos.py`
associa cada imagem ao código (NT 2-05) ou à linha da tabela (NT 1-03, onde renderiza a célula em
600 dpi sem a marca-d'água, porque há símbolos que misturam imagem e traço vetorial, como o
hidrante urbano, e símbolos só vetoriais, como o subterrâneo) e as vetoriza com
`tools/normas/vetorizar.py` (marching squares em numpy, sem dependência nova). Saem 59 placas
(P, A, S, E, com as variantes S-17 a S-24) em **cor verdadeira** (fundo e pictograma, como na
tabela) e 103 dos 104 símbolos de projeto em regiões de tinta que herdam a cor da camada. Ficam
à mão só E-17 (sinalização de solo, que a norma dá em medidas) e a parede corta-fogo (o motor a
desenha pela operação `parede`). O resultado está em `apps/mcp/coscip_mcp/simbolos_nt.json`
(~1 MB, com página e `xref` de cada item) e o catálogo o usa no lugar do desenho antigo, que
fica como reserva; `listar_simbologia` diz em `desenho` de onde vem cada um. A vetorização é
fiel à imagem da NT (subpixel), mas a espessura de traço dos símbolos de projeto sai um pouco
mais forte que no PDF e hachuras escuras viram preenchimento sólido.

**E2. Sprinklers (NT 2-03 parte 1).** `coscip_design/sprinklers.py` e a ferramenta
`dimensionar_sprinklers`: por ambiente, a decisão **proteger, dispensar ou detectores** pelos
itens 5.2.1 a 5.2.6 (banheiros, vestiários, subestações até 20 m², câmaras frias abaixo de 5 °C
até 12 m², varandas abertas, entreforro, CPD, casas de máquinas), número mínimo de bicos, vazão e
pressão do bico remoto, **RTI = Q × t** com o tempo da Tabela 1 do Anexo B (30/30/60 min), soma
com a RTI dos hidrantes (5.4.3), regra dos 70 % do reservatório (5.4.4), material (CPVC só em
Risco Leve com bicos FR), VGA ou comando secundário (5.5), shaft (5.6) e hidrante de recalque
com duas saídas Storz de 2½" sinalizado "SPRINKLER" (5.7, Anexo C). Os 14 parâmetros novos de
`parametros.yaml` são conferidos **por página** (`verify_page_citation`), porque o PDF da NT 2-03
junta os itens no mesmo parágrafo e o índice por item não os alcança. **A NT 2-03 não fixa a
densidade, a área de operação, a área por bico nem o espaçamento: manda seguir a ABNT NBR 10897
(ou a NFPA 13).** Esses valores não estão na base; quando o projetista não os informa, o motor usa a
referência da NFPA 13:2019 por classe (Leve, Ordinário 1 e 2, Extraordinário 1 e 2) e a lista
como **premissa a conferir** no memorial. A classe de risco é do projetista.

**E3. Malha, rede e hidráulica.** `coscip_design/rede_sprinklers.py` e as operações `sprinklers`
(zona por `sala`, `retangulo` ou `poligono`, mais o ponto de alimentação) e `isometrico`: malha de
bicos que respeita espaçamento máximo, área máxima por bico e cobertura (verificada por
amostragem), ramais, subgeral, geral e prumada, área de operação remota (1,2·√A ao longo do ramal)
e cálculo por bicos em cascata (q = K·√P) com Hazen-Williams, conexões por percentual e DN pela
velocidade e perda unitária máximas. A vazão do sistema e a pressão na base da prumada alimentam a
RTI e o memorial. Na planta saem os bicos (símbolo oficial), os tubos, os DN, a VGA e o contorno da
área de operação; o **isométrico a 30°** traz tubos, bicos, cota de altura e o **quadro de cálculo
hidráulico** (trecho, nós, DN, comprimento, vazão, velocidade, perda), tudo do mesmo cálculo.
**Limites:** uma zona por operação, uma subgeral e uma prumada por zona; sem obstruções, vigas,
laços, desníveis internos, bombas (NT 2-04) nem armazenamento (NT 2-03 parte 2).

## 11. Composição das pranchas a partir de projetos protocolados (frente F, 13/11/2026)

Quatro projetos reais protocolados em 2026 (DWG + memorial descritivo, dados de terceiros fora do
repo) foram medidos: arranjo das pranchas (01 = Quadro Resumo + situação; 02 = planta, cortes,
cobertura, fachada), títulos de vista (círculo numerado, título sublinhado, escala), alturas de
texto por elemento, camadas, hachuras e o conteúdo de cortes, fachadas e situações. O que virou
motor:

- **F1. Cobertura nos cortes e fachadas** (`vistas.py`): `edificacao.cobertura` (uma ou duas
  águas sobre a pegada retangular, beiral uniforme) e `forro`; telhado cortado com chamada da
  telha, paredes externas até o telhado, nível da cumeeira; na fachada, silhueta, beiral e
  nervuras. Limite: pegadas em L ou telhados de várias águas exigem modelar cada volume à parte.
- **F2. Elementos de composição**: figura humana de 1,70 m nos cortes (vão livre, sem tocar em
  peças nem vãos), traços de vidro nas janelas, letreiro da testeira abaixo do beiral.
- **F3. Controle de materiais (NT 2-20) no desenho**: rótulos PISO/PAREDE/TETO CLASSE na planta
  (`rotulo_classe`) e PAREDE CLASSE nos cortes, com a classe informada pelo usuário.
- **F4. Planta de situação** (`situacao.py`): lote, edificações hachuradas com caimento, ruas por
  meios-fios (união das faixas, esquinas por buffer +r/−r, pontas cortadas e linha de
  interrupção), distâncias, textos e bloco NORTE, na escala própria.
- **F5. Prancha**: título de vista padronizado e quadros de texto na coluna (`folha.quadros`).

A redação do memorial descritivo (três formatos encontrados, estrutura e erros) ficou na skill
(`references/memorial-descritivo.md` e o modelo); o motor continua gerando o memorial de cálculo.

## 12. Detalhes de instalação (frente G, 13/11/2026)

`detalhes.py` desenha, em tamanho real e na escala do detalhe, os detalhes de extintor, abrigo
de mangueiras, hidrante de recalque (passeio e fachada), bloco autônomo e sinalização de saída.
Toda medida normativa vem de um parâmetro `det.*` do `parametros.yaml` cuja citação é conferida
no texto da NT ao carregar (o mesmo mecanismo do dimensionamento): sem conferência, o detalhe é
recusado. O que a base não fixa (NBR 10898 e 17240, altura do abrigo, dimensão da placa) entra
como dado informado e sai assim no retorno. Próximos: acionador e avisador (quando a NBR 17240
entrar na base), mangotinho, central de GLP, escada e recalque tipo coluna.
