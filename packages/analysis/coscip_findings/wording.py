"""Texto da pendência por template determinístico (arquitetura v2 §57 e §58).

O gerador recebe o Finding já estruturado e só o redige. Não acrescenta requisito, não
remove requisito e não interpreta norma. Se um dia uma LLM redigir, entra aqui atrás da
mesma assinatura, com a saída validada contra este resultado.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from coscip_findings.models import Divergence


def label(field: str, labels: Mapping[str, str]) -> str:
    return labels.get(field, field)


def missing_block(missing: Sequence[str], labels: Mapping[str, str]) -> str:
    if not missing:
        return ""
    itens = "\n".join(f"• {label(f, labels)}" for f in missing)
    return f"Não foram localizados:\n{itens}"


def divergence_block(divergences: Sequence[Divergence], labels: Mapping[str, str]) -> str:
    blocks = []
    for div in divergences:
        pares = [f"{src}: {val}" for src, val in zip(div.sources, div.values, strict=False)]
        if len(pares) < len(div.values):
            pares = [str(v) for v in div.values]
        blocks.append(f"{label(div.field, labels)}\n" + "\n".join(pares))
    return "\n\n".join(blocks)


def compose_explanation(base: str, missing: Sequence[str],
                        divergences: Sequence[Divergence],
                        labels: Mapping[str, str]) -> str:
    parts = [p for p in (base.strip(), missing_block(missing, labels),
                         divergence_block(divergences, labels)) if p]
    return "\n\n".join(parts)


def evidence_summary(sources: Sequence[str]) -> tuple[str, ...]:
    """Resumo curto das fontes, sem hash nem detalhe de algoritmo (§43)."""
    return tuple(dict.fromkeys(s for s in sources if s))
