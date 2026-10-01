# Skills CBMERJ — fonte no repositório

Plano de correção, F1 e F3. **O repositório é a fonte das skills**; as instaladas na conta
claude.ai são cópia. Editar em `%APPDATA%\Claude\…` se perde na próxima sincronização.

| Pasta | O que é |
| --- | --- |
| `<nome>/` | as 9 skills vigentes: SKILL.md, referências próprias, scripts, agents |
| `_comum/` | arquivos copiados para `references/` de várias skills (`uso-do-mcp-coscip-plantas.md`, `achado.schema.json`) |
| `transicao/` | as 8 skills da geração antiga, corrigidas (F3.1) só para o período de transição |
| `pacotes.yaml` | quais textos de `normative/fontes` e quais comuns entram em cada zip |

Os textos das NTs e do Decreto **não** ficam aqui: a cópia única é `normative/fontes`.
`tools/skills/pack.py` os copia (com as imagens de página) e gera `edicoes-vigentes.md`,
`banco-de-citacoes.md` e `itens.jsonl` para a skill de bilhete.

## Gerar e enviar

1. Zips: artefato **skills-cbmerj** do workflow *Skills* (GitHub → Actions), ou
   `python -m tools.skills.pack` (`scripts\skills\empacotar.ps1` no Windows com Python).
2. Em claude.ai → Configurações → Skills: enviar cada `dist/skills/<nome>.zip` (substitui a
   versão da conta). **Manual, feito pelo usuário.**
3. Depois de enviados os vigentes, **remover da conta**: `analise-le-completa-pdf`,
   `analise-eventos-completa-pdf`, `analise-ca-completa-pdf`, `consulta-nt-grupo1` … `5` e
   `cbmerj-grupo-5-legado-nao-usar` (6,8 MB duplicados). O conteúdo útil das antigas já está
   em `analisar-processo-cbmerj/references/` (`protocolo-leitura-pranchas.md`,
   `checklist-documental-le.md`).

## Conferir

`python -m tools.skills.verificar_links` (também na CI): todo caminho e script citado existe,
toda `$skill` chamada existe e é vigente, toda NT citada está na base.
