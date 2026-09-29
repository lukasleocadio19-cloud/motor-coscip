# Fluxo de análise de PSCIP / Laudo de Exigências

## Objetivo do rito

A análise de projeto avalia medidas de segurança e riscos específicos a partir de PSCIP elaborado por profissional técnico. A aprovação resulta no LE; o LE não regulariza, por si só, a edificação ou área de risco. Base principal: NT 1-01, Parte 1, itens 5.1.7, 5.3 e, quando aplicável, 5.4.

## Fase 0 — cabimento

Antes do mérito:

1. confirmar que o caso não se enquadra em baixo risco, CAS, CAA ou ato especial;
2. identificar se é projeto inicial, modificação, substituição, regularização de edificação anterior ou adequação;
3. fixar a norma temporal aplicável por NT 1-05 e NT 1-06;
4. localizar processos, LE, CA, CDD ou decisões anteriores;
5. testar a sobrevivência dos atos anteriores com [quadro-resumo-e-atos-anteriores.md](quadro-resumo-e-atos-anteriores.md), sem presumir que um CA/CAA ainda cubra a situação atual;
6. abrir `$cbmerj-atos-administrativos` para competência, fluxo digital, projeto em CAD e, quando houver LE anterior ao regime atual, AAST 02/2020;
7. verificar competência da unidade e hipóteses de retenção/encaminhamento à DGST;
8. registrar eventual solução não padronizada que possa exigir CAT.

## Fase 1 — admissibilidade documental

Extraia da edição vigente da NT 1-01, item 5.3.7, o checklist exato e confronte cada documento. O conjunto inclui, conforme o caso: requerimento/solicitação, emolumento, identificação e representação, vínculo com o imóvel, atos constitutivos, responsabilidade técnica e peças do PSCIP.

No projeto digital, aplique a Nota DGST vigente indicada por `$cbmerj-atos-administrativos`: formato aceito, arquivo corrente, unidades, Model Space/layouts, cores, Quadro Resumo incorporado, DAEM pago e Termo de Aceite. Reconciliar o Termo de Aceite com o lote real por nome, quantidade, extensão, tamanho e horário quando disponíveis. Se a NT e o fluxo digital divergirem formalmente quanto a upload autônomo, registrar o ato vigente e a razão da prevalência procedimental, sem alterar o conteúdo técnico exigido.

Classificar a leitura CAD em três estados independentes:

1. `estrutura_lida`: cabeçalho, versão, unidade, layers, blocos, layouts e entidades foram inventariados;
2. `preview_gerado`: foi possível renderizar vistas úteis;
3. `fidelidade_validada`: textos, OLE, referências externas, fontes, escalas, tabelas e geometrias determinantes foram conferidos.

Não converter `estrutura_lida` ou `preview_gerado` em `fidelidade_validada`. Não calcular área pelos extents globais nem contar dispositivos antes de filtrar blocos de legenda/detalhe, transformações, entidades fora dos limites e referências externas.

Bloquear o mérito quando faltar elemento que impeça identificar o objeto, o responsável, o imóvel ou a versão analisável. Demais faltas podem ser registradas como pendência e o exame continuar no que for independente.

## Fase 2 — classificação

1. Ler atividade real, compartimentos e usos de cada área; não depender só de CNAE ou título do projeto.
2. Classificar ocupação/divisão e combinações de uso.
3. Fixar ATC, área por pavimento/setor, altura, pavimentos, população e demais parâmetros.
4. Aplicar NT 1-04 para risco e carga de incêndio quando acionada.
5. Confrontar os resultados com requerimento, Quadro Resumo, memorial e pranchas.
6. Inventariar todos os usos por ambiente, inclusive acessórios, e acionar os riscos específicos correspondentes; a ocupação predominante declarada não elimina cozinha, GLP, gerador, subestação, líquidos ou reunião de público.
7. Resolver contradições antes de derivar medidas.

## Fase 3 — matriz do Decreto

Aplicar as tabelas/matrizes do Decreto nº 42/2018 à classificação comprovada. Produzir lista de medidas:

| Medida | Gatilho | Obrigatória? | Fonte no Decreto | NT de dimensionamento |
| --- | --- | --- | --- | --- |

Não usar a lista declarada pelo RT como substituto da derivação. Registrar medidas omitidas e medidas declaradas sem gatilho aparente.

## Fase 4 — completude gráfica e memorial

Conferir o conjunto previsto na NT 1-01, item 5.3.7(h), e o conteúdo do memorial do item 5.3.13:

- situação/prancha 01 e Quadro Resumo;
- plantas baixas, cortes, telhado, isométrico e fachada, observadas dispensas expressas;
- quadro de dispositivos, memórias de cálculo dos sistemas fixos e resumo de funcionamento;
- simbologia e representação pela NT 1-03;
- riscos e situações especiais indicados nos itens 5.3.8 e 5.4.

Verificar se cada referência entre prancha, detalhe, memorial e cálculo existe e aponta para a mesma versão.

Executar também testes internos do próprio documento: conclusão × cálculo, texto × tabela, largura mínima declarada × larguras aceitas, volume declarado × detalhe e quantitativo × símbolo. Uma contradição interna não pode ser saneada escolhendo silenciosamente o trecho mais conveniente.

## Fase 5 — pacotes técnicos

Abra, em ordem:

1. Grupo 2 para cada medida derivada;
2. Grupo 3 para cada risco específico materializado;
3. Grupo 4 para cada estrutura/atividade especial;
4. Grupo 5 quando houver reunião de público ou configuração de evento.

Para NTs independentes, distribua coletores em paralelo. Para dependências, respeite a ordem: classificação → população/risco → medida → cálculo → representação.

## Fase 6 — cruzamentos críticos

Conferir especialmente:

- população × saídas × larguras/distâncias × acessibilidade;
- área/risco × extintores, hidrantes, sprinklers e reserva;
- altura/pavimentos × compartimentação, segurança estrutural, escadas e acesso;
- armazenamento/processo × risco específico × medidas do Grupo 2;
- uso misto × compartimentação/separação × medidas mais gravosas;
- Quadro Resumo × todos os gatilhos e cálculos.
- ato anterior × área/leiaute/ocupação/responsável/riscos atuais;
- contrato ou título × anexos citados × condições suspensivas/resolutivas × poderes de representação;
- ART/RRT/TRT × objeto × escopo efetivo × documento técnico correspondente.

## Fase 7 — saneamento e conclusão

Produzir exigências atômicas com fonte e localização. Após resposta do RT, criar nova rodada sem apagar o histórico:

`achado anterior → documento-resposta → teste refeito → estado atual`

Conclusão favorável somente quando o projeto provar todas as medidas aplicáveis e não restar divergência material. O resultado é LE/projeto aprovado, não CA.

## Aditamento, novo projeto e CAT

Ao examinar modificação, aplicar o art. 26 do Decreto compilado:

- controlar o limite geral de até três aditamentos e suas exceções expressas;
- classificar se a alteração de leiaute, ocupação ou acréscimo de ATC ultrapassa o limite que cancela o LE aditado e exige novo projeto completo;
- após modificação aprovada, registrar a necessidade do novo CA prevista no Decreto.

Não usar CAT para suprir documento obrigatório. Encaminhar questão técnica à CAT quando a fonte aplicável assim determinar, inclusive ocupação sem enquadramento/exigência específica, divisões expressamente submetidas à CAT, solução complexa não padronizada ou medida compensatória que extrapole as alternativas normativas.

Para edificação anterior, não aplicar automaticamente o regime atual nem o revogado. Fixar o marco da construção/licenciamento, ler NT 1-05 e NT 1-06 e consultar o PDF visual quando a extração Markdown de tabela estiver incompleta. Processo atual novo não retorna ao Decreto nº 897/1976 sem fundamento temporal específico.
