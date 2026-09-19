# ADR 0005 — DSL normativa fechada e cinco estados

**Status:** aceita · 19/09/2026

**Decisão.** Regras em YAML validadas por esquema estrito (`extra="forbid"`) e um conjunto
fechado de operadores. Sem `eval`, Python livre ou prompt como DSL. Fórmulas especiais viram
funções versionadas e testadas.

Estados de avaliação: `PASS`, `FAIL`, `REVIEW_REQUIRED`, `NOT_APPLICABLE`, `MISSING_DATA`.
Item não implementado é `UNSUPPORTED` no inventário de cobertura, fora desses cinco.
Erro de software e timeout são estados operacionais, nunca resultado normativo.

Comparação com incerteza (`minimum_with_uncertainty`): intervalo inteiro abaixo → `FAIL`;
intervalo atravessa o limite → `REVIEW_REQUIRED`; intervalo inteiro atende → `PASS`.

Publicação: rascunho → revisão técnica → testes → homologação → publicação imutável →
depreciação. `TEST_ONLY` ou fonte de exemplo não pode ser marcada para produção.
