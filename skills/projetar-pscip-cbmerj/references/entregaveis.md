# O que entregar e como relatar

## Arquivos

1. **Plantas em DXF** (`criar_planta` / `desenhar_planta`): um pavimento por região, com título
   ("PLANTA BAIXA - TÉRREO"), ambientes com nome e área, paredes e portas (corta-fogo quando for o
   caso), símbolos da NT 1-03, legenda com os nomes oficiais e cotas principais.
2. **Corte esquemático / esquema vertical** (operação `corte`): pavimentos, níveis, cota total,
   reservatório com a RTI e prumada de hidrantes. Diga que é esquemático: sai das alturas
   informadas, não substitui o corte arquitetônico.
3. **Memorial de cálculo** (`salvar_memorial`): um bloco por sistema, com fórmula, valores, base
   normativa conferida, premissas e pendências.
4. **Controle do projeto** (`projeto.md`, do modelo): dados, enquadramento, quadro de medidas,
   premissas, pendências.

O motor não gera prancha com carimbo, Quadro Resumo, nem PDF. Diga isso.

## Relato final ao usuário

Na ordem, em linguagem direta:

1. **O que foi feito:** enquadramento (tabela e coluna), medidas calculadas com os números
   principais, medidas lidas na NT, arquivos gerados com o caminho.
2. **O que foi conferido na planta:** percursos de extintor, hidrante, acionador e saída, com os
   valores medidos e os limites; o que ficou com pendência.
3. **Premissas a confirmar:** cada uma, com o valor adotado.
4. **Pendências e o que o motor não cobre:** lista completa, sem agrupar em "outros".
5. **Avisos obrigatórios:** rascunho sem valor normativo; precisa de responsável técnico com
   ART/RRT; a tabela do Anexo III usada e o que o campo `conferencia` diz sobre ela.

Não use "aprovado", "conforme", "atende" sem dizer o que foi medido e contra qual item. Não
apresente quantidade calculada como posição resolvida: quantidade vem do cálculo, posição só vale
depois de `analisar_planta`.
