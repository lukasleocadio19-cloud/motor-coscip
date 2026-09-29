---
name: cbmerj-grupo-1-generalidades
description: "Analisar o Grupo 1 das Notas Técnicas do CBMERJ: procedimentos de regularização e fiscalização, terminologia, símbolos gráficos, classificação de risco, edificações anteriores, transição normativa e atividades de baixo risco. Usar diretamente nesses temas ou quando $orquestrar-analise-cbmerj solicitar o módulo de enquadramento e generalidades."
---

# CBMERJ - Grupo 1

Executar somente o escopo das NTs do Grupo 1. Não substituir o Decreto, não dimensionar medidas do Grupo 2 e não aplicar regras dos Grupos 3 a 5 sem acionar o módulo correspondente.

## Iniciar

1. Ler [references/indice-grupo-1.md](references/indice-grupo-1.md).
2. Fixar data de protocolo, fase e documento pretendido.
3. Se a consulta for posterior a 23/07/2026, confirmar vigência no portal oficial.
4. Receber do orquestrador, quando disponível: regime, ocupações, ATC, altura, pavimentos, população, riscos e documentos.
5. Abrir `$cbmerj-atos-administrativos` quando a pergunta envolver competência, rito digital, prazo, assinatura, recurso, CA assistido/parcial, ato anterior ou modalidade não integralmente definida pela NT 1-01.

## Selecionar referências

- [references/nt-1-01-parte-1-regularizacao.md](references/nt-1-01-parte-1-regularizacao.md): PSCIP, LE, CA, CVA, AE, documentos, análise, cadastramento e regularização.
- [references/nt-1-01-parte-2-fiscalizacao.md](references/nt-1-01-parte-2-fiscalizacao.md): fiscalização, notificações, autos, interdição, defesa e recurso.
- [references/nt-1-02-terminologia.md](references/nt-1-02-terminologia.md): conceitos e siglas.
- [references/nt-1-03-simbolos-graficos.md](references/nt-1-03-simbolos-graficos.md): representação gráfica; conferir imagens.
- [references/nt-1-04-classificacao-de-risco.md](references/nt-1-04-classificacao-de-risco.md): ocupação mista, depósito, carga de incêndio e classificação de risco.
- [references/nt-1-05-edificacoes-anteriores.md](references/nt-1-05-edificacoes-anteriores.md): adaptação de edificação anterior.
- [references/nt-1-06-adequacao-normativa.md](references/nt-1-06-adequacao-normativa.md): processo em transição; não reutilizar prazos históricos como regra atual.
- [references/nt-1-07-atividades-de-baixo-risco.md](references/nt-1-07-atividades-de-baixo-risco.md): dispensa e critérios cumulativos de baixo risco.

Pesquisar arquivos longos com `rg`:

```bash
rg -n -i "Laudo de Exigências|Certificado de Aprovação|documentos" references/nt-1-01-parte-1-regularizacao.md
rg -n -i "ocupação mista|carga de incêndio|depósito|médio 2" references/nt-1-04-classificacao-de-risco.md
rg -n -i "edificação anterior|adaptação|medida compensatória" references/nt-1-05-edificacoes-anteriores.md
```

## Executar

1. Determinar se o caso é projeto novo, edificação anterior, transição, modificação/aditamento, baixo risco, fiscalização ou evento.
2. Normalizar terminologia e classificar cada ocupação/divisão.
3. Resolver ocupação mista, armazenamento e carga de incêndio antes de definir o risco.
4. Conferir coerência entre requerimento, Quadro Resumo, plantas, memorial e ART/RRT/TRT, incluindo contradições internas de cada peça.
5. Modelar pessoas/empresas, papéis, representação, vínculo com o imóvel, assinaturas e escopos técnicos; ART/RRT/TRT não comprova mandato ou titularidade.
6. Segmentar PDFs compostos em atos lógicos e testar a sobrevivência de LE/CA/CAA anteriores contra área, leiaute, ocupação, responsável e condições atuais.
7. Identificar procedimento, documentos, competência e impedimentos.
8. Listar as medidas e os grupos adicionais que precisam ser acionados, sem dimensioná-los neste módulo.

## Retornar ao orquestrador

Produzir:

| Campo | Conteúdo |
| --- | --- |
| Regime | Novo, anterior, transição, modificação, baixo risco, fiscalização ou evento |
| Classificação | Ocupações/divisões, risco, carga de incêndio e justificativa |
| Procedimento | PSCIP/LE, CA, CVA, AE, fiscalização ou dispensa |
| Conformidades | Itens comprovados |
| Pendências | Inconsistências e documentos ausentes |
| Gatilhos | Medidas e habilidades dos Grupos 2, 3, 4 e 5 a acionar |
| Fontes | NT, item e página do PDF |
| Bloqueios | Lacuna, conflito, CAT ou decisão humana necessária |

Usar citações como `(NT 1-04, item 5.2, PDF p. 6)`. Não emitir conclusão global de aprovação; a consolidação pertence ao orquestrador.
