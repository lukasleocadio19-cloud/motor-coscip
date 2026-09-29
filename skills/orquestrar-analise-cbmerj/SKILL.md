---
name: orquestrar-analise-cbmerj
description: "Orquestrar a análise completa de processos de segurança contra incêndio e pânico do CBMERJ — PSCIP/LE, CA, CAA, CAS, CVA, AE/EvRP, fiscalização, recurso, modificação, transição e atos correlatos — aplicando o Decreto Estadual nº 42/2018. Chamar $cbmerj-atos-administrativos e $analisar-processo-cbmerj para governança e execução documental, e ativar cumulativamente $cbmerj-grupo-1-generalidades, $cbmerj-grupo-2-medidas-seguranca, $cbmerj-grupo-3-riscos-especificos, $cbmerj-grupo-4-estruturas-especiais e $cbmerj-grupo-5-eventos."
---

# Orquestrador de Análise CBMERJ

Coordenar o rito, o analista de processo, os módulos normativos e os coletores de NT. Preservar a hierarquia das fontes e emitir uma conclusão única e rastreável.

Papéis:

- **orquestrador**: fixa a hipótese de cabimento, o regime, as dependências, os módulos e a governança;
- **`$cbmerj-atos-administrativos`**: fornece o catálogo vigente/aparente de atos, competência, fluxo digital, assinatura, prazo e modalidade;
- **`$analisar-processo-cbmerj`**: executa o SOP do tipo de processo, lê documentos e constrói a matriz requisito-evidência; recomenda, mas não pratica o ato decisório;
- **habilidade de grupo**: interpreta o conjunto de NTs de sua série;
- **subagente coletor**: extrai de uma NT delimitada regras, testes e evidências; não conclui o processo.

Aplicar [references/contrato-de-papeis.md](references/contrato-de-papeis.md). Somente o orquestrador fixa a hipótese de cabimento e o regime; somente a autoridade administrativa competente defere, indefere, emite ou autoriza.

## Carregar a base

1. Ler [references/indice-do-orquestrador.md](references/indice-do-orquestrador.md).
2. Ler [references/decreto-42-2018-coscip-compilado.md](references/decreto-42-2018-coscip-compilado.md) para incidência, matriz de medidas, documentos, competência, fiscalização, sanções e CAT.
3. Ler [references/fluxo-operacional-e-governanca.md](references/fluxo-operacional-e-governanca.md) para regime, fase, tramitação, evidência e bloqueios.
4. Ler [references/matriz-de-roteamento.md](references/matriz-de-roteamento.md) para ativar os grupos.
5. Ler [references/catalogo-geral-das-nts.md](references/catalogo-geral-das-nts.md) para selecionar as NTs por objeto e pergunta de análise.
6. Abrir `$cbmerj-atos-administrativos` para o catálogo oficial, estado de vigência, competência, digitalização e modalidade do pedido.
7. Ler [references/matriz-de-cobertura.md](references/matriz-de-cobertura.md) e atribuir um responsável a cada requisito acionado.
8. Usar as sínteses derivadas do relatório técnico-operacional para decisões de governança, fluxo, atualização e controvérsia.
9. Se a análise ocorrer após 23/07/2026, ou se o ato estiver marcado como `vigência aparente`, `transitória`, `superação parcial` ou `requer validação`, confirmar no portal oficial do CBMERJ se houve alteração do Decreto, NT, Portaria, AAST ou Nota DGST.

## Executar o ciclo

### 1. Fixar o processo

Registrar antes de analisar:

- data de protocolo e data de cada ato relevante;
- fase e documento solicitado;
- endereço, responsável legal e responsáveis técnicos;
- atos anteriores: LE, CA, CAA, CAS, CVA, AE/EvRP, notificações, pareceres e recursos;
- arquivos recebidos e versão de cada prancha, memorial, cálculo e Quadro Resumo.
- Termo de Aceite ou manifesto de upload, quando houver, reconciliado com os arquivos efetivamente recebidos;
- segmentação de PDFs compostos em atos lógicos, sem atribuir um único efeito administrativo ao arquivo inteiro.

Não reconhecer direito adquirido, prazo, sobrestamento, caducidade ou dispensa sem fonte expressa.

### 2. Definir o regime

Classificar o processo como um ou mais:

- projeto novo sob o Decreto nº 42/2018;
- edificação anterior;
- processo em transição/adequação normativa;
- modificação ou aditamento de projeto aprovado;
- procedimento simplificado ou atividade de baixo risco;
- regularização decorrente de fiscalização;
- evento permanente ou temporário;
- recurso, consulta técnica ou matéria de CAT.

Quando o regime depender de informação ausente, interromper a conclusão e registrar o bloqueio.

### 3. Normalizar os fatos

Criar uma ficha única com:

- ocupações por ambiente e eventuais usos mistos;
- risco, carga de incêndio e depósitos;
- ATC, áreas parciais, altura, pavimentos e população;
- riscos específicos, estruturas especiais e eventos;
- sistemas declarados, sistemas exigidos e sistemas projetados;
- Quadro Resumo, plantas, memoriais, cálculos, laudos e ART/RRT/TRT.
- grafo de pessoas/empresas, papéis, poderes de representação, vínculos com o imóvel e assinaturas;
- cadeia de atos anteriores e condições de sobrevivência de cada LE, CA, CAA, CAS, CVA ou decisão;
- estado de leitura de cada CAD: `estrutura_lida`, `preview_gerado` e `fidelidade_validada`.

Se duas fontes divergirem, não escolher silenciosamente uma delas. Marcar `pendente` até o saneamento.

### 4. Ativar os módulos

Ativar sempre `$cbmerj-atos-administrativos` e, em seguida, `$cbmerj-grupo-1-generalidades` para:

- identificar modalidade, competência, protocolo, prazo, assinatura e ato administrativo corrente;
- terminologia, ocupação, risco, regime, procedimento, documento e competência;
- consistência do Quadro Resumo;
- edificações anteriores, transição e baixo risco.

Com o enquadramento do Grupo 1, derivar do Decreto a matriz de medidas e ativar `$cbmerj-grupo-2-medidas-seguranca` para cada medida exigida, dispensada ou condicionada.

Ativar cumulativamente:

- `$cbmerj-grupo-3-riscos-especificos` para cozinha profissional, GLP/GN de uso na edificação, motogerador, subestação, caldeira/vaso de pressão, líquidos inflamáveis/combustíveis ou heliponto/heliporto;
- `$cbmerj-grupo-3-riscos-especificos` e `$cbmerj-atos-administrativos` para estação/infraestrutura de recarga de veículo elétrico, sem tratar minuta de NT como norma vigente;
- `$cbmerj-grupo-4-estruturas-especiais` para quiosque/exposição/venda, restrição de liberdade, edificação tombada, explosivos para fabricação/armazenagem/comércio, GLP/GN para manipulação/armazenagem/comércio, posto, garagem, pátio, túnel, canteiro ou estrutura temporária médica;
- `$cbmerj-grupo-5-eventos` para centro de reunião de público, evento temporário, pirotecnia, carro alegórico/trio/carro de som ou atendimento médico de evento.

Um processo pode acionar todos os grupos. Não tratar os grupos como alternativas excludentes.

### 5. Chamar o analista de processo

Para qualquer processo documental técnico, chamar `$analisar-processo-cbmerj` depois de fixar o ato e o regime inicial. Entregar:

- manifesto e lote documental;
- processo/fase e atos anteriores;
- data de corte normativa;
- enquadramento confirmado e conflitos ainda abertos;
- matriz inicial de medidas e lista de NTs acionadas;
- arquivos e versões que compõem a rodada.

O analista seleciona o roteiro específico, inventaria os documentos, confronta cada requisito e coordena as coletas normativas. O orquestrador não substitui essa execução por uma síntese genérica.

Para CAA, CAS, CVA, CDD, CA assistido/parcial, fiscalização, recurso, consulta, CAT ou outro rito, o analista usa o roteiro específico ou a matriz de atos administrativos; não rebaixar esses pedidos a uma análise genérica do Grupo 1.

### 6. Fornecer o contrato de entrada

Enviar a cada módulo somente os dados necessários, preservando:

| Campo | Conteúdo |
| --- | --- |
| Processo | Tipo, fase, datas e atos anteriores |
| Regime | Regra de transição/adequação aplicável |
| Enquadramento | Ocupação, risco, ATC, altura, pavimentos e população |
| Gatilhos | Medidas, riscos, estruturas e eventos identificados |
| Evidências | Arquivo, prancha, página, detalhe ou documento |
| Dúvidas | Conflitos e dados ainda não comprovados |
| Saída esperada | Campos definidos pela habilidade de grupo |

### 7. Delegar coletas diretamente nas NTs

Quando duas ou mais NTs independentes estiverem acionadas, pode chamar subagentes em paralelo. Cada coletor recebe uma NT ou um pacote inseparável e:

1. lê o arquivo Markdown da edição vigente dentro da habilidade do grupo;
2. responde apenas perguntas objetivas do caso;
3. devolve aplicabilidade, requisito atômico, gatilho, entradas, método de teste, evidência esperada, exceções, interfaces e fonte exata;
4. cita NT, edição, item/subitem, tabela/anexo e página;
5. registra `sem regra localizada`, `fonte visual necessária` ou `conflito`, em vez de inferir;
6. não decide deferimento, não altera o regime e não importa regra de outro Estado.

Não paralelizar etapas dependentes. Fechar Grupo 1 e fatos determinantes antes de distribuir dimensionamentos. O analista principal valida as referências e aplica os testes aos documentos.

### 8. Consolidar as respostas

Cruzar os módulos em uma matriz única. Para cada achado:

| Campo | Conteúdo |
| --- | --- |
| ID | Identificador estável do achado |
| Tema | Enquadramento, medida, risco, estrutura, evento ou fluxo |
| Fato | Dado observado |
| Regra | Exigência, proibição, dispensa ou condição |
| Fonte | Documento, artigo/item/tabela e página |
| Evidência | Prancha, QR, memorial, cálculo, laudo ou documento |
| Resultado | Conforme, não conforme, pendente ou não aplicável |
| Severidade | Bloqueante, maior, menor ou observação |
| Origem | Grupo 1, 2, 3, 4, 5 ou Decreto |
| Interface | Outros achados afetados |
| Saneamento | Correção ou documento necessário |

Resolver duplicidade sem apagar diferenças: consolidar achados equivalentes e preservar todas as fontes e evidências.

Antes da conclusão, executar a reconciliação de cobertura: todo requisito ativado deve ter `regra`, `responsável`, `teste`, `evidência`, `estado` e `fonte`. Requisito sem responsável ou sem evidência esperada é uma lacuna bloqueante da automação.

### 9. Aplicar bloqueios

Impedir conclusão automática de aprovação quando houver:

- regime ou versão normativa indeterminados;
- ocupação, risco, ATC, altura, população ou carga de incêndio conflitantes;
- Quadro Resumo incompatível com planta ou memorial;
- cálculo determinante não reproduzível;
- ausência de desenho, memorial, laudo ou responsabilidade técnica exigidos;
- interface entre grupos ainda não analisada;
- solução compensatória, interpretação excepcional ou matéria de CAT;
- atualização normativa posterior à captura da base ainda não verificada.

### 10. Emitir a conclusão

Organizar a resposta em:

1. identificação, fase e regime;
2. enquadramento;
3. módulos ativados e justificativa;
4. documentos avaliados;
5. matriz consolidada;
6. conformidades;
7. não conformidades;
8. pendências e saneamentos;
9. cálculos reproduzidos;
10. recomendação técnica consolidada: tecnicamente favorável, tecnicamente desfavorável, pendente de saneamento ou dependente de decisão humana/CAT.

Usar citações precisas, por exemplo:

`(Decreto Estadual nº 42/2018, art. 25, PDF p. 5)`
`(NT 2-08, item X, tabela Y, PDF p. Z)`

Não citar apenas “conforme COSCIP” quando artigo, item, tabela e página estiverem disponíveis.

## Limites do orquestrador

- Não importar critérios de outros Estados.
- Não tratar Nota DGST como se fosse Decreto ou NT.
- Não preencher lacuna de fonte com prática presumida.
- Não permitir que subagente coletor emita conclusão global.
- Não declarar aprovação quando um módulo devolveu `pendente` bloqueante.
- Não usar “favorável com ressalva” sem base expressa do rito.
- Não ocultar divergência entre módulos; apresentar o conflito e encaminhar para decisão humana quando necessário.
