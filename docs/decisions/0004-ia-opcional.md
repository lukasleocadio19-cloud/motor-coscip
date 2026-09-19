# ADR 0004 — IA opcional e com teto de gasto

**Status:** aceita · 19/09/2026

**Decisão.** Cálculo, regras implementadas e relatório por template funcionam sem IA. Ao
habilitar: `DocumentAssistant` (candidatos Gemini 2.5 Flash / 3.1 Flash-Lite) e, opcionalmente,
`DecisionClassifier` (Jev, só texto/JSON). Teto proposto: US$ 0,25 por análise e US$ 5 por mês.

**Regras.**
- Sem chave cadastrada e sem habilitação explícita, nada é enviado.
- Reservar o custo máximo antes de cada chamada; consumo desconhecido continua reservado.
- Não repetir automaticamente chamada cujo resultado se perdeu.
- Limite atingido → tarefas restantes vão à revisão humana; nunca presumir conformidade.
- Extração sem evidência verificável é descartada ou fica pendente.
- Escolha final pelo custo por resposta correta num teste cego de 100–200 tarefas (AI-01/AI-04).
