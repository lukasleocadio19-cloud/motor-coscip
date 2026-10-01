# Anatomia do bilhete de exigências

Referência de forma. **Não é fonte normativa**: toda exigência vem da matriz consolidada e de
item conferido na NT (`banco-de-citacoes.md`, `scripts/localizar_item.py`). Os modelos de
texto abaixo são pontos de partida; a redação institucional da seção prevalece.

## 1. Estrutura

1. **Cabeçalho** (quando o sistema não o gera): processo, requerimento, interessado, endereço.
2. **Itens numerados**, na ordem da skill (enquadramento → Quadro Resumo → matriz de medidas →
   medidas na ordem do Decreto → memorial → documentação → responsabilidade técnica → arquivo).
3. **Fecho**: nota do Quadro Resumo (quando houver), itens regulares que não precisam ser
   refeitos, ressalva de nova análise.

## 2. Item — forma canônica

```
N. Título do defeito — Norma:edição, dispositivo: Fato observado, com a divergência
explicitada e as fontes nomeadas (prancha, folha, documento). Solicita-se providência
específica.
```

| Parte | Regra | Exemplo |
| --- | --- | --- |
| Título | o defeito, não o tema | "Extintores em quantidade insuficiente no pavimento tipo" |
| Norma | sigla + edição conferida em `edicoes-vigentes.md` | "NT 2-01:2020" |
| Dispositivo | item, alínea, tabela ou anexo **localizado** | "item 6.1.1, Tabela 3" |
| Fato | o que foi visto, onde, e a divergência | "a prancha 03 apresenta 1 extintor no pavimento tipo (área de 180 m²)" |
| Solicita-se | uma providência verificável | "Solicita-se prever as unidades extintoras exigidas e indicá-las em planta." |

Incisos `(i) (ii) (iii)` quando o "Solicita-se" é o mesmo para vários defeitos do mesmo tema.

Dispositivo não localizado: `NT 2-07:2019, item [A CONFERIR]` — nunca item deduzido.

## 3. Vocabulário

- Use: "observa-se", "não consta", "diverge de", "solicita-se", "apresentar", "compatibilizar".
- Não use: "indeferido", "aprovado", "reprovado", "conforme COSCIP" sem dispositivo,
  nome de ferramenta, módulo, skill, "IA", "conversão", "CAD não abriu".
- Critério adotado pelo analista (interpretação registrada, não texto literal da norma) é
  escrito como tal: "critério adotado: mínimo de 2 unidades extintoras por pavimento (NT 2-01,
  item 5.2.5)" — não "a NT 2-01 exige por pavimento".

## 4. Fecho — modelos

**Quadro Resumo** (quando houver item sobre ele):

> O Quadro Resumo deverá ser corrigido na própria prancha 01, dispensada a apresentação em
> arquivo separado.

**Itens regulares** (só o que o solicitante não precisa refazer):

> Permanecem válidos: DAEM nº …, receita …, documento … .

**Ressalva de nova análise** (modelo; ajustar à prática da seção):

> A presente análise restringe-se aos elementos apresentados. A reapresentação será
> integralmente reanalisada, podendo ser formuladas novas exigências caso as correções
> alterem o projeto ou revelem condição não declarada.

## 5. Nota de rastreabilidade (interna, não enviada)

| Item | Achado da matriz | Citação | Conferida em fonte primária? |
| --- | --- | --- | --- |
| 1 | EXT-CAD-002@pavimento-tipo | NT 2-01:2020, 5.2.5 | sim (índice + leitura do trecho) |
| 2 | … | NT 2-07:2019, [A CONFERIR] | não — pendente do analista |

Mais: contagem final de caracteres e bytes (`scripts/contar_bilhete.py`) e o que foi cortado
(`protocolo-de-reducao.md`).
