# Contrato de papéis da análise

## Responsabilidade exclusiva

| Papel | Pode fazer | Não pode fazer |
| --- | --- | --- |
| Orquestrador | Fixar hipótese de cabimento, regime inicial, dependências, módulos e bloqueios; consolidar | Inventar regra, assinar ato administrativo ou substituir a autoridade competente |
| Atos administrativos | Localizar modalidade, competência, fluxo, prazo, assinatura e estado de vigência | Reduzir requisito técnico de Decreto/NT |
| Analista de processo | Inventariar o dossiê, ler documentos, confrontar regra/evidência e recomendar estado técnico | Deferir, indeferir, emitir, autorizar ou resolver competência controvertida |
| Grupo normativo | Interpretar NTs do grupo e devolver testes atômicos | Alterar a modalidade ou concluir o processo inteiro |
| Coletor de NT | Extrair regra delimitada com fonte exata | Usar memória como fonte ou preencher lacuna normativa |
| Autoridade competente | Praticar o ato decisório nos limites legais | Ter sua decisão simulada pela automação |

## Estados permitidos

- requisito: `conforme`, `não conforme`, `pendente`, `não aplicável`;
- análise técnica: `tecnicamente favorável`, `tecnicamente desfavorável`, `pendente de saneamento`, `dependente de decisão humana/CAT`;
- ato administrativo: somente registrar o resultado efetivamente praticado pela autoridade.

“Favorável com ressalva” só pode ser usado se a modalidade e a fonte vigente o autorizarem expressamente.

## Regra de conflito

Conflito de módulos retorna ao orquestrador. Conflito de fonte, competência, transição, solução compensatória ou enquadramento sem previsão sobe para decisão humana/CAT, conforme o caso. Nenhum coletor desempata silenciosamente.
