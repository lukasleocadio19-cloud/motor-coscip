# Textos das NTs e do Decreto 42/2018 (Markdown convertido) — fonte única

Base normativa que o motor, o MCP, os testes **e as skills CBMERJ** usam: 52 NTs dos grupos 1
a 5 e o Decreto Estadual nº 42/2018 compilado. Cada arquivo tem front matter com documento,
edição e SHA-256 do PDF oficial; as citações das regras, do catálogo e das tabelas são
conferidas contra eles.

- **Esta pasta é a única cópia** (plano de correção, F1). As skills em `skills/` não trazem os
  `nt-*.md`: `tools/skills/pack.py` copia daqui para `references/` ao gerar os zips. As skills
  instaladas no Claude são cópia da conta claude.ai; editar lá se perde na próxima
  sincronização.
- `media/<nt>/pagina-NN.(png|jpg)`: imagens de página citadas nos `.md` (conferência visual).
  As ausentes estão listadas no manifesto; `tools/normas/render_paginas.py` as gera do PDF
  oficial, conferindo o SHA-256 (F2).
- `normative/manifests/base.yaml`: manifesto derivado (documento, edição, ato, URL, hashes do
  PDF e do Markdown, imagens e estado das tabelas). Depois de qualquer mudança aqui:
  `python -m tools.normas.manifesto` e os testes (`test_base_manifest` acusa manifesto velho).
- Vigência: o workflow mensal `vigencia.yml` baixa os PDFs oficiais e abre issue se o hash
  mudar. **Nunca** substitui texto automaticamente: NT nova ou revisada é conferida e entra
  por pull request, e pode derrubar citações.
- Ordem de busca do MCP: `COSCIP_NORMAS_DIR` → esta pasta. Nada mais.
- São textos convertidos de PDF: tabelas podem perder células mescladas e há erros de OCR.
  Para citar tabela, use o bloco "(conferida)" quando existir; a seção "Tabelas extraídas" é
  registro bruto. Na dúvida, vale o PDF oficial.
