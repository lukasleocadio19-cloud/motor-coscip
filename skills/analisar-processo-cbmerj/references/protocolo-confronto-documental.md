# Protocolo de confronto documental

## 1. Manifesto e snapshots

Antes do inventário, fixe:

| Campo | Conteúdo |
| --- | --- |
| processo_id | Número oficial ou identificador controlado |
| tipo_solicitacao | LE, CA, AE ou rota ainda indeterminada |
| data_protocolo | Data documentada |
| data_corte_normativa | Data usada para selecionar edições |
| fase | Entrada, análise, bilhete, retorno ou decisão |
| unidade_competente | Unidade indicada, ainda que provisória |
| atos_anteriores | LE, CA, CDD, CAT, aditamentos, bilhetes e decisões |
| lote_documental | Remessa inicial ou resposta específica |
| termo_aceite | Identificador, data e relação declarada de uploads |

Congele um `snapshot_documental` e um `snapshot_normativo` para cada rodada. Resposta a bilhete cria novos snapshots; não altera retroativamente os anteriores.

Quando o ambiente permitir, preserve o original e registre hash, extensão, tamanho, origem, data de recebimento e vínculo `substitui_documento_id`. A ausência desse controle deve aparecer nos limites da análise.

## 2. Unidade de análise

Trate o processo como um dossiê versionado. A unidade mínima de evidência é:

`arquivo + versão/data + página/prancha + campo/camada/região + responsável`

Não cite apenas o nome do arquivo quando ele contiver várias pranchas, revisões ou anexos.

## 3. Inventário

Abra uma tabela com:

| ID | Documento | Versão/data | Assinatura | Responsável | Objeto | Localização | Estado |
| --- | --- | --- | --- | --- | --- | --- | --- |

Estados: corrente, superado, duplicado, ilegível, incompleto ou não identificado.

Antes de ler o mérito:

1. detectar duplicatas e revisões;
2. identificar qual arquivo pretende substituir qual;
3. conferir se o conjunto possui todas as páginas/pranchas citadas;
4. registrar assinaturas, certificados e datas sem presumir validade;
5. separar documento declaratório, gráfico, cálculo e comprovação de execução.
6. detectar PDF composto por mais de um ato e criar subregistros por ato;
7. reconciliar arquivo, nome original, tamanho e horário com o Termo de Aceite;
8. listar anexos e condições mencionados no conteúdo e testar se foram entregues.

Arquivos de formatos diferentes exigem extração adequada:

- PDF textual: conservar página, tabela e título;
- digitalização: registrar OCR e confiança; baixa confiança não serve como prova única;
- DWG/DWF: inventariar layouts, unidades, escalas, layers, cotas, textos, Quadro Resumo, isométricos e revisões;
- planilha: preservar aba, célula, valor, fórmula e unidade;
- foto: exigir identificação do sistema, ambiente, data/legenda e documento de origem;
- ART/RRT/TRT: extrair número, profissional, conselho, atividade, objeto, endereço, datas e sistemas abrangidos.

Classificar assinatura como: manuscrita digitalizada, imagem/carimbo, assinatura
declarada por portal, certificado de plataforma anexado, PAdES embutida,
QR/URL pendente de validação ou assinatura efetivamente validada. Aparência visual
não comprova autenticidade.

Renderização ou texto extraído de DWG/DWF não substitui medição geométrica validada.

## 4. Fatos e proveniência

Extraia somente fatos necessários à análise. Para cada fato, guarde:

- valor literal e valor normalizado;
- unidade;
- fonte e localização;
- responsável pela declaração;
- data/versão;
- nível: declarado, representado, medido, calculado ou inferido.

Uma inferência nunca substitui evidência obrigatória. Se precisar inferir para continuar, identifique-a explicitamente e não use a inferência para aprovar.

## 5. Matriz requisito-evidência

Cada linha deve ser atômica: uma condição, um teste e um resultado. Divida itens normativos que contenham várias obrigações.

Resultados:

- **conforme**: regra aplicável e evidência suficiente, coerente e reproduzível;
- **não conforme**: evidência demonstra descumprimento;
- **pendente**: evidência ausente, ilegível, contraditória ou cálculo não reproduzível;
- **não aplicável**: gatilho examinado e comprovadamente ausente.

Não use “conforme” para “não encontrei problema”.

## 6. Camadas de confronto

### 6.1 Admissibilidade

Confira solicitação, identidade e representação, vínculo com o imóvel/local, pagamento quando aplicável, responsabilidade técnica, assinaturas, formato, integridade e vinculação a atos anteriores.

Separar contratação técnica de representação. ART/RRT/TRT não substitui procuração ou
poder societário quando estes forem necessários ao ato. Pagamento por terceiro não invalida
automaticamente a quitação, mas deve ser registrado.

### 6.2 Coerência cadastral

Compare endereço, denominação, proprietário/responsável, CNPJ/CPF quando presente, número do processo, LE/CA anterior, área, altura, pavimentos, ocupação e datas em todos os documentos.

Normalizar `parte`, `toda edificação`, `bloco`, `complexo`, `loteamento` e
`agrupamento` como escopos espaciais distintos. Exigir delimitação quando atos anteriores
e pedido atual usam abrangências diferentes.

### 6.3 Classificação e aplicabilidade

Recalcule ocupação/divisão, uso misto, risco, ATC, altura, população e demais gatilhos a partir das fontes. Compare o resultado com o Quadro Resumo e com a matriz do Decreto.

### 6.4 Geometria e representação

Meça ou leia dimensões na versão corrente. Verifique escala/unidade, continuidade de rotas, larguras úteis, distâncias, áreas, afastamentos, setores, localização de equipamentos e detalhes citados. Quando a imagem não permitir medição confiável, marque pendente.

### 6.5 Cálculos

Reproduza:

1. entradas e unidades;
2. fórmula ou procedimento da NT;
3. substituição numérica;
4. arredondamento;
5. resultado mínimo;
6. solução projetada;
7. margem ou déficit.

Um resultado final sem memória e entradas verificáveis permanece pendente.

### 6.6 Sistemas e riscos

Para cada sistema, cruze cobertura, capacidade, alimentação, acionamento, reserva, componentes, localização, sinalização, interação com outros sistemas e documentação de responsabilidade. Para cada risco, cruze tipo, quantidade/capacidade, acondicionamento, localização, afastamentos e proteção.

### 6.7 Execução e operacionalidade

Aplicável sobretudo ao CA. Vincule cada exigência do LE e cada elemento do projeto aprovado a documento de execução: declaração, ART/RRT/TRT, laudo circunstanciado, ensaio, manutenção, nota fiscal, foto ou outro comprovante exigido. Documento genérico sem objeto/endereço/escopo compatível não comprova o item.

### 6.8 Atos anteriores

Decompor cada LE, CA, CAA, CAS, CVA ou decisão em titular, endereço, abrangência,
ATC, pavimentos, ocupação, finalidade, riscos, medidas, validade e observações. Aplicar
teste de sobrevivência: cláusulas de perda automática, mudança de responsável, área,
layout, finalidade, gás, inflamáveis e demais limitações. Data nominal de validade não
prevalece sobre condição resolutiva comprovadamente acionada.

### 6.9 Coerência interna

Confrontar também trechos dentro do mesmo documento. Regra textual mínima incompatível
com cálculo ou quadro do próprio memorial é divergência material, ainda que a planta repita
o resultado declarado.

## 7. Contradições

Regra de precedência documental não autoriza escolher silenciosamente a versão conveniente. Quando duas fontes correntes divergirem:

1. registre ambas;
2. determine se a divergência altera enquadramento, dimensionamento ou responsabilidade;
3. peça correção ou confirmação formal;
4. mantenha os itens dependentes como pendentes.

## 8. Forma da exigência

Redija:

`[localização] — [fato encontrado]. A [fonte, item] exige [regra]. O processo não comprova/atende [teste]. Apresentar/corrigir [evidência ou solução necessária].`

Não prescreva solução única quando a norma admite alternativas. Nesse caso, peça que o RT escolha, represente, dimensione e assuma a alternativa normativa.
