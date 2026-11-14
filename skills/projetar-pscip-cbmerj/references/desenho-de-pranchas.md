# Como as pranchas de PSCIP são desenhadas (referência medida)

Extraído em 13/11/2026 de quatro projetos reais protocolados no CBMERJ em 2026 (restaurante com
mezanino e GLP, restaurante F-8 de 243 m² com GLP e coifa, abrigo de idosos H-2 com 5 blocos,
igreja F-2 de 355 m²). Os DWG foram lidos numa cópia; **nada dos projetos (nomes, endereços,
registros, blocos) entra no repositório**: aqui ficam só técnica, medidas e padrões. Números de
norma citados pelos projetos **não são fonte**: confirme cada um com `consultar_norma`.

## 1. Como a prancha é montada

Há duas maneiras nos projetos, e as duas passam no protocolo:

| Maneira | Como | Quando usar |
|---|---|---|
| Vários viewports | Model space em metros 1:1; uma janela por vista, cada uma na sua escala (1:50, 1:75, 1:100, 1:125, 1:250 numa A0 com 14 viewports) | É o que o motor faz (`folha` com `vistas`). Preferir. |
| Um viewport só | Tudo arrumado no model space como se fosse a folha, um viewport 1:100; vistas "1:200" são o desenho reduzido à metade no próprio model | Projetos pequenos. Evitar: a escala escrita não é a do viewport e a cota mente. |

Formatos vistos: A0, A1 (841 x 594), folhas fora de série (1030 x 477, 594 x 297). Duas
pranchas é o comum em edificação pequena: **01 = Quadro Resumo e situação**, **02 = planta,
cortes, cobertura e fachada**. Projeto com vários blocos: um quadro emoldurado por bloco
("CASA TÉRREO", "ÁREA COBERTA", "ACESSO PRINCIPAL"), cada um com planta, cortes, fachada e
cobertura do bloco, e o nome do bloco grande no canto do quadro.

### Ordem de leitura que as pranchas seguem
1. Planta baixa (a maior vista, à esquerda ou embaixo à esquerda) com o título "1 PLANTA BAIXA".
2. Cortes ao lado ou acima da planta, na mesma escala, alinhados com ela quando possível.
3. Fachada(s) e cobertura (esta às vezes em 1:200).
4. Detalhes (abrigo de GLP, escada, instalação de placas) em 1:25 a 1:50.
5. Coluna da direita: legendas (sinalização, sistema móvel, sistema fixo), notas por sistema,
   quadro de áreas, cálculo das saídas, Quadro Resumo (às vezes como OLE de planilha) e carimbo.

## 2. Títulos, textos e cotas (alturas impressas)

Medido nos DWG (altura no model / escala):

| Elemento | Altura impressa | Observação |
|---|---|---|
| Título de vista | 3,0 a 3,5 mm | "PLANTA BAIXA", "CORTE AA", "FACHADA" |
| Número da vista | igual ao título | dentro de um círculo à esquerda do título, título sublinhado |
| Escala sob o título | 2,0 mm, em cinza | "ESCALA 1:100" ou "ESC. 1/100" |
| Nome do ambiente | 1,5 mm | maiúsculas; abaixo a área "A=15,74 m²" em 1,0–1,2 mm |
| Lotação no ambiente | 1,5 mm | "(lotação 100 pessoas)", "(6 PESSOAS)" sob o nome |
| Cotas | 1,4 a 2,0 mm | tique oblíquo (ArchTick), duas casas, sem "m" |
| Etiqueta de vão | 1,0 a 1,4 mm | porta em duas linhas "0.80 / 2.10"; janela "1.50X0.80" |
| Notas numeradas | 2,1 mm | "NOTAS:" e itens "1-", "2-" |
| Rótulo de classe NT 2-20 | 1,9 mm itálico serifado | moldura "PISO / CLASSE" e "I" embaixo |
| Chamada de placa | código 1,3 mm, dimensão 0,7 mm | círculo dividido por um traço |
| Nome de rua (situação) | 2,7 mm | ao longo da rua |

O motor já gera as alturas certas pela `escala` de `criar_planta`; a `folha` desenha o título de
cada vista no padrão acima (círculo numerado, título sublinhado, escala em cinza).

## 3. Planta baixa

- **Cotas externas em duas ou três linhas**: a de dentro com cada trecho e cada espessura de
  parede (".15", ".08" entre ambientes), a do meio por blocos, a de fora com o total. Nos quatro
  lados quando a planta é irregular. Use `cota_cadeia` (trechos + total).
- **Vãos**: portas com folha e arco e a etiqueta largura/altura; janelas com etiqueta
  largura x altura (peitoril quando importa). Porta de enrolar com a nota "Esta porta
  permanecerá aberta durante o funcionamento" e, na prancha, um termo de responsabilidade.
- **Ambiente**: nome, área e, quando é local de reunião, a lotação; rótulo PISO CLASSE I.
- **Eixos de corte**: linha traço-ponto com a letra dentro de um círculo e seta triangular cheia
  nas duas pontas (`marca_corte` ou `secao`).
- **Mobiliário** que justifica a lotação: mesas e cadeiras no salão, bancos da igreja, camas no
  abrigo. Ele mostra ao analista de onde saiu a população e que as rotas ficam livres.
- **Projeções em tracejado**: coifa, telhado, beiral ("projeção telhado").
- **GLP**: abrigo com os cilindros, rede em linha colorida até os pontos de consumo com chamada
  "TUBO AÇO CARBONO ASTM A 106 DN 1/2" (LINHA DE GLP)", placas P-1/P-2 (200) e E-5 do abrigo.
- **Equipamentos**: extintor (triângulo vermelho com a marca do agente) com a placa E-5 ao lado,
  bloco autônomo (retângulo azul com círculo), placas S-1/S-2/S-12 em verde, A e P em laranja.
- **Escada**: degraus numerados, seta de subida, guarda-corpo com chamada.
- Muro e elementos externos com texto ("MURO 0,60 ALTURA"), área descoberta identificada.
- Abaixo do título da planta, a ATC: "ATC 243,25 M2".

## 4. Planta de situação (operação `situacao`)

Sempre presente (prancha 01 ou junto da planta), em 1:250 ou 1:500:
- Ruas desenhadas pelos dois meios-fios, **esquinas arredondadas**, **linha de interrupção**
  (zigue-zague) nas pontas, nome escrito ao longo da rua.
- Lote em traço grosso com as medidas dos lados; a frente às vezes cotada por dentro.
- Edificação hachurada (linhas a 45°) ou a cobertura com o padrão da telha e **setas de caimento**.
- **Distância até a esquina** mais próxima (ex. "80,00"), "Alinhamento", "Recuo 50 cm".
- Seta do norte ou rosa dos ventos.
Pergunte ao usuário: medidas do lote, nomes e larguras das ruas, distância à esquina, recuos e
norte. Nada disso se supõe.

## 5. Cortes (operação `secao`)

Padrão comum aos quatro projetos:
- Piso em faixa de ~10 cm com hachura de concreto; paredes cortadas cheias ou hachuradas.
- **Telhado** cortado (telha + estrutura) e a **chamada da telha** com linha de chamada:
  "telhas onduladas fibrocimento", "telha trapezoidal alumínio"; **forro** com o nome sobre a
  linha ("FORRO GESSO", "FORRO DRYWALL"). Peça ao usuário tipo de cobertura, inclinação, beiral
  e forro (`edificacao` com cobertura e forro).
- **Figura humana** de 1,70 m num vão livre, para dar escala (o motor põe sozinho).
- **Rótulo PAREDE CLASSE I** nos vãos (classe do revestimento pela NT 2-20, informada).
- Cotas verticais dos dois lados: pé-direito, altura de porta (2,10), altura total, platibanda;
  níveis.
- O que importa para incêndio aparece em vista: coifa, duto de exaustão, exaustor, fogão
  (cozinha), escada, mezanino, cilindros no corte do abrigo de GLP.
- Pelo menos dois cortes perpendiculares (AA e BB); um terceiro (XX) no abrigo de GLP.

## 6. Fachadas e cobertura (operação `fachada`)

- Fachada principal (a da rua) sempre; as outras quando o projeto tem blocos.
- Esquadrias com os **traços de vidro** a 45°; portas de enrolar com as linhas horizontais.
- Revestimentos indicados por textura: brise ou chapa metálica em linhas horizontais, reboco em
  pontilhado, telha ondulada como uma ondulação na borda.
- **Letreiro** do estabelecimento na testeira: compõe o cenário e mostra qual é a fachada
  principal (`letreiro`).
- Linha de terra prolongada para os dois lados.
- Cobertura em planta (1:200): contorno, cumeeira, **setas de caimento**, inclinação
  ("LAJE IMPERM. INCLIN. 1%"), calhas.

## 7. Detalhes que se repetem

O motor desenha os de instalação com a operação `detalhe` (cotados com as medidas das NTs, cada
nota com NT e item; medida cuja citação não confere recusa o detalhe): extintor (vistas frontal
e lateral, alça, parte inferior, suporte, placa E-5 e, em indústria/depósito, o piso pintado),
abrigo de mangueiras (dimensões, porta e registro pelo risco, mangueira e esguicho da Tabela 1,
placa E-7, piso de 1 x 1 m na rede), hidrante de recalque no passeio (caixa, profundidade,
rebordo, saída a 45°, duplo a partir de 400 L/min) e na fachada (1,0 a 1,2 m, abrigo,
inscrição), bloco autônomo (altura informada, autonomia pela divisão) e instalação da
sinalização (sobre a porta, na parede, nível inferior). Pergunte o que a NT não fixa: altura do
abrigo e do bloco, fluxo luminoso, dimensão das placas (a das chamadas), risco e vazão dos
hidrantes. Ponha cada detalhe longe da planta e dê a ele uma vista da folha na escala do
detalhe (o retorno traz a região em metros).

GLP (NT 3-02): central em corte e planta (recipientes, pigtails, coletor, válvula de retenção,
tampão, paredes e cobertura de concreto, portas com veneziana abrindo para fora), placa PERIGO /
GÁS INFLAMÁVEL / PROIBIDO FUMAR ampliada com as medidas mínimas e o pictograma de proibido
fumar, e as prumadas dos reguladores com cada conexão chamada (registro geral de corte, niple,
tê com manômetro, válvulas de espera, união, luva de redução, regulador). Pergunte tipo e
quantidade de recipientes, medidas do abrigo se já existir e as bitolas da rede.

Nível de desenho (de uma prancha protocolada usada como referência pelo usuário em 13/11/2026):
equipamento desenhado como é, não como símbolo — extintor com cúpula, válvula, manômetro,
alavanca, mangueira e frisos do cilindro; suporte de parede com parafuso e bucha; suporte de
piso; parede de alvenaria com as fiadas em corte; porta com batente, dobradiças e maçaneta; laje e
forro hachurados; placa com o pictograma oficial e, ao lado, a placa ampliada com a chave de
especificação (símbolo, código, fundo, pictograma, dimensão, NT e tabela); itens marcados com
balões numerados e uma tabela Nº | DESCRIÇÃO; chamadas com o texto apoiado sobre a linha. Escalas
padrão do motor: extintor 1:15, recalque no passeio 1:10, abrigo, recalque na fachada e bloco
1:20, sinalização 1:25 — numa A0 cabem os seis. Extintor: a vista NA PAREDE e a NO PISO (suporte)
saem juntas por padrão (montagem); o tamanho do extintor é aproximado de catálogo pelo agente
(extintor_m informa o do fabricante).

- **Abrigo de GLP** 1:25 a 1:50: planta e corte com dimensões internas, porta ventilada, cilindros
  (P-13, P-45, P-190) e alturas.
- **Instalação da sinalização**: porta com a placa acima da verga, placa na parede com "altura
  mínima" cotada, placa no teto; e o extintor em vista frontal e lateral com a placa e a
  sinalização de piso. A altura vem da NT 2-05 (4.7: nível superior a partir de 1,80 m; 4.5:
  nível inferior até 0,50 m) — os memoriais reais divergem entre si (1,50 m, 1,80 m).
- **Escada**: planta e corte do lance, guarda-corpo e corrimão quando há mezanino ou pavimento.

## 8. Quadros e notas da coluna da direita

- **Legenda de sinalização** em tabela: código | símbolo (placa) | em planta | significado |
  identificação (círculo com código e dimensão) e a **quantidade** por placa.
- **Sistema móvel / sistema fixo**: símbolo | descrição completa ("EXTINTOR DE PÓ ABC DE 6 KG -
  (3-A:20-B:C)") | quantidade.
- **Materiais de acabamento (NT 2-20)**: símbolos círculo = piso, quadrado = parede, triângulo =
  teto, com o número do material dentro; tabela de materiais e classes. Alternativa mais simples
  (mais usada): rótulo PISO/PAREDE CLASSE em cada ambiente (`rotulo_classe`).
- **Quadro de áreas** por pavimento/bloco e total.
- **Cálculo de população** em tabela: pavimento | ocupação | população (1 pessoa por x m²) |
  área útil | cálculo | total.
- **Cálculo da largura das saídas** em caixa de texto ao lado da planta: fórmula N = P/C, área,
  P, C, N, largura mínima, largura projetada (soma das portas válidas), capacidade (use
  `folha.quadros` com as linhas do memorial de `dimensionar_saidas`).
- **Notas por sistema**, cada uma com o título da NT: iluminação (NT 2-06), sinalização
  (NT 2-05), extintores (NT 2-01), saídas (NT 2-08), TRRF (NT 2-19), cozinha (NT 3-01), GLP
  (NT 3-02). E as notas gerais: "1- Esta edificação utiliza GLP", "o desenho prevalece sobre
  memoriais e quantitativos", "cotas devem ser conferidas no local".

## 9. Camadas e hachuras vistas

- Uma camada por sistema (equipamentos, sinalização, cotas, alvenaria, hachura, vistas, prancha);
  dois projetos usam uma camada por tipo de placa (".00-Placa-E5", ".00-Placa-S1"). O motor
  segue o padrão de cores do AAST 01/2025 (`padrão CBMERJ`), mais rígido que o dos projetos.
- Hachuras: concreto (AR-CONC) em piso e laje cortados; linhas a 45° (ANSI31) para alvenaria e
  para a edificação na situação; areia (AR-SAND) para reboco e muro; telhado em planta com padrão
  de telha (AR-RROOF ou linhas); sólido para símbolos.

## 10. Erros encontrados nas pranchas reais (não repetir)

1. **Quadro copiado de outro projeto**: a igreja (F-2) trazia o cálculo de saídas do abrigo de
   idosos ("Grupo H, abrigo para idosos", "17 pessoas"); o abrigo trazia "N = 140/100" e
   "Grupo F2". Todo texto reaproveitado precisa ser refeito com os números do projeto.
2. **População incoerente** entre o ambiente ("lotação 100 pessoas") e o cálculo da caixa
   ("137,25 m²/3 = 45 pessoas", "n = 81/100").
3. **Autonomia diferente** na legenda ("2 horas") e no memorial ("60 min").
4. Cota de recuo e etiquetas escritas à mão no desenho sem ligação com a geometria.
5. Leaders com seta gigante (estilo de cota em escala errada): conferir o estilo antes de plotar.

Antes de entregar: rodar o verificador de sobreposição e conferir que quantidades da legenda,
do Quadro Resumo, do memorial e do desenho são as mesmas (`quadro_resumo.conferencia`).
