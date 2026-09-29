# Manifestos de fontes normativas

Um arquivo por fonte oficial (REG-01). Campos obrigatórios:

```yaml
document: NT 2-01            # identificação no catálogo CBMERJ
edition: <edição aplicável>  # não usar "a mais recente" por padrão
amending_act: <ato modificador, se houver>
url: <URL oficial>
file_sha256: <hash do PDF preservado>
published_at: AAAA-MM-DD
effective_from: AAAA-MM-DD
effective_until: null
collected_at: AAAA-MM-DD
transition_notes: <condições de transição>
referenced_documents: []
validated_by: <responsável técnico>
```

Fluxo de publicação: rascunho → revisão técnica → testes → homologação →
publicação imutável → substituição/depreciação. Norma revogada permanece no histórico.

**Pendente:** homologar edição, requisitos, exceções e dependências da NT 2-01
(extintores) antes de qualquer resultado real.

## `base.yaml` — manifesto da base de textos (plano de correção, F1.2)

Derivado de `normative/fontes` por `python -m tools.normas.manifesto` (não editar à mão):
documento, edição, ato, URL oficial, SHA-256 do PDF e do Markdown, captura, páginas, cada
imagem de página (presente/ausente, com hash) e o estado de cada tabela (`bruto`,
`verificada`, `divergente`, `pendente_humano`). `tests/unit/test_base_manifest.py` recalcula
e compara.
