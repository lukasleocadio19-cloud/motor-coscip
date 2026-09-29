---
name: analisar-processo-cbmerj
description: Executar a análise técnico-documental de processos do CBMERJ, incluindo PSCIP/LE, CA, AE/EvRP, modificação, CA parcial, segunda via, parecer, TAC, fiscalização, recurso e desinterdição. Usar quando houver PDFs, DWG/DWF, Quadro Resumo, memoriais, cálculos, ART/RRT/TRT, atos anteriores, DAEM, comprovante, Termo de Aceite, contratos, laudos, declarações ou formulários a confrontar com o Decreto Estadual nº 42/2018, NTs dos Grupos 1 a 5 e atos administrativos vigentes; quando for preciso produzir manifesto, checklist, matriz requisito-evidência, bilhete, parecer ou recomendação técnica rastreável. Pode ser chamada por $orquestrar-analise-cbmerj.
---

# Analista de Processos CBMERJ

## Missão

Conduzir uma análise reproduzível de qualquer rito reconhecido pelo orquestrador. Ler o processo como um conjunto versionado de evidências; determinar o que é aplicável; localizar cada regra na fonte oficial incorporada; confrontar declaração, desenho, cálculo e responsabilidade técnica; e emitir achados e recomendação técnica rastreáveis.

Não substituir dado ausente por hipótese favorável. Não concluir pela aprovação quando houver conflito material, documento obrigatório ausente, cálculo não reproduzível ou norma aplicável não verificada.

## Roteamento inicial

1. Fixar o ato solicitado. Se o usuário disser “EvRP”, registrar como rótulo operacional e verificar se o ato formal é AE.
2. Ler o roteiro correspondente:
   - PSCIP/LE: [fluxo-le.md](references/fluxo-le.md)
   - CA: [fluxo-ca.md](references/fluxo-ca.md)
   - AE/evento: [fluxo-ae-eventos.md](references/fluxo-ae-eventos.md)
   - demais atos: [fluxos-outros-atos.md](references/fluxos-outros-atos.md)
3. Para qualquer rito, ler [protocolo-confronto-documental.md](references/protocolo-confronto-documental.md).
4. Ler [contrato-dados-processo.md](references/contrato-dados-processo.md) e preencher os campos aplicáveis.
5. Se o processo estiver incompleto, executar tudo o que for possível e separar “não conforme” de “não verificável”.
6. Devolver ao orquestrador atos de competência reservada ou de rito não localizado, sem inventar procedimento.

## Fontes e módulos

Aplicar esta precedência:

1. Decreto Estadual nº 42/2018 compilado e alterações;
2. NT 1-01 e demais NTs do Grupo 1;
3. NTs técnicas aplicáveis dos Grupos 2 a 5;
4. AAST, Nota DGST ou outro ato procedimental vigente, sem permitir que ato subordinado afaste Decreto ou NT.

Usar os módulos:

- `$cbmerj-grupo-1-generalidades`: rito, classificação, terminologia, símbolos, risco, edificações anteriores, transição e baixo risco;
- `$cbmerj-grupo-2-medidas-seguranca`: medidas e sistemas;
- `$cbmerj-grupo-3-riscos-especificos`: riscos tecnológicos e instalações específicas;
- `$cbmerj-grupo-4-estruturas-especiais`: atividades e estruturas especiais;
- `$cbmerj-grupo-5-eventos`: reunião de público e eventos.
- `$cbmerj-atos-administrativos`: protocolo digital, competência, assinatura, procedimento assistido, recursos, atos anteriores e demais modalidades.

Toda regra normativa deve vir da edição incorporada no módulo competente, com NT, item/subitem e página ou tabela quando disponível. Se a edição, a vigência ou o alcance estiverem em dúvida, marcar a regra como pendente de confirmação; não completar por analogia com outro Estado.

## Fluxo comum obrigatório

### 1. Abrir o dossiê

Inventariar cada arquivo, prancha e formulário: identificador, tipo, versão/data, assinatura, responsável, escopo e páginas. Preservar versões anteriores e eleger uma versão corrente somente quando isso estiver comprovado.

Executar `scripts/inventariar_dossie.py` quando os arquivos estiverem disponíveis localmente. Reconciliar o resultado com o Termo de Aceite, mantendo nome original, tamanho, horário de upload e hash. Um PDF pode conter vários atos; criar um registro por ato interno, não apenas por arquivo.

### 2. Determinar cabimento e regime

Registrar tipo de processo, endereço, competência administrativa, datas relevantes, atos anteriores, ocupação/divisão, uso misto, ATC, altura, pavimentos, população e riscos declarados. Aplicar Grupo 1 antes dos demais grupos. Verificar norma de transição e regularização de edificação anterior quando houver gatilho.

### 3. Fechar os fatos de entrada

Criar tabela “fato → valor → unidade → fonte documental → localização → confiabilidade”. Separar fato declarado de fato medido ou calculado. Divergências entre Quadro Resumo, plantas, memorial, formulário e responsabilidade técnica permanecem abertas até solução.

Construir também o grafo de papéis: proprietário/titular, possuidor, responsável pela edificação, representante legal, administrador, requerente, RT, empresa contratada, signatário e pagador. ART/RRT/TRT comprova responsabilidade técnica no escopo descrito; não prova automaticamente poder de representação.

### 4. Derivar aplicabilidade

Usar a matriz do Decreto para listar medidas mínimas e acrescentar NTs acionadas por risco, atividade, estrutura e evento. Para cada NT, formular perguntas objetivas de análise. Não abrir todo o acervo indiscriminadamente.

### 5. Coletar requisitos normativos

Quando houver vários pacotes independentes, chamar subagentes coletores por NT ou por conjunto estreitamente relacionado. Seguir [contrato-delegacao-e-saida.md](references/contrato-delegacao-e-saida.md). O coletor extrai regra e teste; não decide o processo.

### 6. Confrontar requisito e evidência

Para cada requisito aplicável, registrar:

| Campo | Conteúdo obrigatório |
| --- | --- |
| Requisito | Regra testável, sem generalidade |
| Fonte | Documento, edição, item/subitem, tabela/anexo e página quando disponível |
| Evidência esperada | Documento, representação, cálculo, declaração ou laudo capaz de provar |
| Evidência encontrada | Arquivo/prancha/página/camada/campo e versão |
| Método | Comparação textual, medição, recálculo, consistência ou validade |
| Resultado | Conforme, não conforme, pendente ou não aplicável |
| Justificativa | Operação reproduzível e efeito no processo |

### 7. Fazer controles cruzados

Conferir, no mínimo:

- requerimento × responsável legal × vínculo com o imóvel/local;
- ART/RRT/TRT × profissional × atribuição × objeto × endereço × etapa;
- Quadro Resumo × plantas × memorial × cálculos;
- classificação e parâmetros × matriz de exigências;
- cálculo × geometria representada × solução desenhada;
- risco declarado × inventário/capacidade/localização × proteção;
- LE/projeto aprovado × documentos de execução, no CA;
- público/data/layout/setores × saídas e atendimento médico, na AE.
- Termo de Aceite × arquivos efetivamente recebidos × nome/tamanho/upload;
- DAEM × comprovante × código de barras/receita/valor/vencimento;
- documento societário × administrador/poderes × assinatura do requerimento;
- título/vínculo × parte/todo/bloco/complexo × anexos e condições citados;
- ato anterior × cláusulas de perda/validade × situação corrente.

### 8. Consolidar achados

Eliminar duplicidade, mas preservar conflitos. Cada exigência deve informar: medida ou sistema; fonte exata; fato constatado; desconformidade; correção requerida; e localização no projeto/processo. Não usar formulações como “adequar à norma” sem indicar o teste que falhou.

### 9. Recomendar

Emitir recomendação técnica, não decisão administrativa:

- tecnicamente favorável, somente com todos os requisitos aplicáveis verificados;
- pendente de exigência/documentação;
- tecnicamente desfavorável, com fundamento e possibilidade de saneamento explicitados;
- encaminhar para CAT ou decisão superior quando houver solução não padronizada, conflito interpretativo material ou competência reservada.

Não usar “favorável com ressalva” sem fonte expressa do rito. Reservar deferimento, indeferimento, emissão e autorização à autoridade competente.

Incluir sempre “limites da análise”: arquivos não recebidos, elementos ilegíveis, cálculos não reproduzidos, vigência não confirmada e inspeções de campo não realizadas.

## Regra de encerramento

O resultado deve permitir que outro analista refaça o caminho completo: dos fatos de entrada à NT escolhida, da regra ao documento examinado e do teste à conclusão. Se essa cadeia estiver quebrada, o item permanece pendente.
