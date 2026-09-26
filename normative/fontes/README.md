# Textos das NTs e do Decreto 42/2018 (Markdown convertido)

Base normativa que o MCP e os testes de conferência usam: 52 NTs dos grupos 1 a 5 e o
Decreto Estadual nº 42/2018 compilado — os mesmos `.md` que a base do app ingere
(`normative-import-sources`). Cada arquivo tem front matter com documento, edição e SHA-256 do
PDF oficial; as citações das regras, do catálogo e das tabelas são conferidas contra eles.

- Origem: skills CBMERJ do Claude (`cbmerj-grupo-1..5-*/references/nt-*.md` e
  `orquestrar-analise-cbmerj/references/decreto-42-2018-coscip-compilado.md`). **Nunca** o
  grupo 5 legado.
- Atualizar: `scripts\mcp\exportar-normas.ps1 -Destino normative\fontes`, rodar os testes e
  conferir o que mudou (`git diff`): NT nova ou revisada pode derrubar citações.
- Ordem de busca do MCP: `COSCIP_NORMAS_DIR` → esta pasta → skills instaladas no Claude.
- São textos convertidos de PDF: tabelas podem perder células mescladas e há erros de OCR;
  na dúvida, vale o PDF oficial.
