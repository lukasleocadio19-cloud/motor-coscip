"""``Finding`` do motor → achado do contrato comum das skills (plano de correção, F8).

O esquema é ``skills/_comum/achado.schema.json`` (F3.4): os achados do motor entram na matriz
consolidada da skill **sem tradução**. A conversão só muda nomes e formato: os três status
passam iguais, a citação continua a do check (conferida no texto ingerido) e o critério
adotado fica separado do texto da norma. Nenhum achado muda de status aqui.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from coscip_evidence import Evidence

from coscip_cbm import ComplianceStatus, Severity
from coscip_findings.models import Finding

ACHADO_SCHEMA_ID = ("https://github.com/lukasleocadio19-cloud/motor-coscip/skills/_comum/"
                    "achado.schema.json")
A_CONFERIR = "[A CONFERIR]"
SYSTEM_THEMES = {"EXTINTORES": "Extintores", "HIDRANTES": "Hidrantes e mangotinhos",
                 "ALARME": "Alarme de incêndio", "SAIDAS": "Saídas de emergência",
                 "QUALIDADE": "Qualidade da leitura", "SPRINKLERS": "Chuveiros automáticos",
                 "ILUMINACAO": "Iluminação de emergência", "SINALIZACAO": "Sinalização"}


def _rule(citation: dict[str, Any] | None) -> dict[str, Any]:
    if not citation:
        return {"documento": A_CONFERIR, "item": A_CONFERIR}
    out: dict[str, Any] = {"documento": citation["document"], "item": citation["item"]}
    if citation.get("edition"):
        out["edicao"] = citation["edition"]
    if citation.get("page") is not None:
        out["pagina"] = citation["page"]
    if citation.get("quote"):
        out["citacao"] = " … ".join(citation["quote"])
    return out


def _evidence(e: Evidence) -> dict[str, Any]:
    out: dict[str, Any] = {"fonte_tipo": str(e.source_type)}
    doc = e.source_category or e.source_id
    if doc:
        out["documento"] = doc
    where = e.locator.describe() if not e.locator.is_empty else ""
    if where:
        out["localizador"] = where
    value = e.normalized_value if e.normalized_value is not None else e.raw_value
    if value is not None:
        out["valor"] = value
    if e.uncertainty_abs is not None:
        out["incerteza"] = e.uncertainty_abs
    return out


def _num(v: float) -> str:
    """Número no texto do achado (pt-BR, até 2 casas): 11.748 → "11,75"."""
    return f"{v:.2f}".rstrip("0").rstrip(".").replace(".", ",")


_SOURCE_TEXT = {"CAD": "planta vetorial", "DOCUMENT": "documento do processo",
                "CALCULATION": "cálculo sobre a planta", "NORMATIVE_TABLE": "tabela normativa",
                "HUMAN": "informação do analista"}


def _fact(f: Finding, items: list[Evidence]) -> str:
    """O que foi observado, em texto que pode ir ao bilhete: sem hash nem nome de algoritmo
    (esses ficam em ``evidencias`` e ``medida``)."""
    parts = [f.title.rstrip(".")]
    m = f.measured
    where = f"pavimento {f.scope_label}" if f.scope_label else ""
    if m is not None:
        unit = f" {m.unit}" if m.unit else ""
        text = f"medido {_num(m.value)}{unit}"
        if m.uncertainty_abs:
            text += f" (± {_num(m.uncertainty_abs)}{unit})"
        if m.required is not None:
            text += f"; limite {_num(m.required)}{unit}"
        parts.append(f"{where}: {text}" if where else text)
    elif where:
        parts.append(where)
    kinds = sorted({str(e.source_type) for e in items})
    if kinds:
        parts.append("fonte: " + ", ".join(_SOURCE_TEXT.get(k, k) for k in kinds))
    if f.missing:
        parts.append("não localizado: " + ", ".join(f.missing))
    return ". ".join(p[0].upper() + p[1:] for p in parts) + "."


def to_achado(finding: Finding, evidence: Iterable[Evidence] = ()) -> dict[str, Any]:
    """Um achado do contrato comum. ``evidence``: as evidências da análise (as citadas pelo
    finding viram a lista ``evidencias``)."""
    f = finding
    cites = list(f.normative_citations)
    rule = _rule(cites[0] if cites else None)
    by_id = {e.id: e for e in evidence}
    items = [by_id[i] for i in f.evidence_ids if i in by_id]
    if f.compliance_status is ComplianceStatus.COMPLIANT and rule["item"] == A_CONFERIR:
        raise ValueError(f"{f.ref}: conforme sem citação localizada viola o contrato")
    out: dict[str, Any] = {
        "id": f.ref, "origem": "motor", "check_id": f.check_id,
        "escopo": f.scope_label or f.scope_id,
        "tema": SYSTEM_THEMES.get(f.system, f.system.title()),
        "fato": _fact(f, items), "regra": rule,
        "compliance_status": str(f.compliance_status),
        "evidence_status": str(f.evidence_status),
        "review_status": str(f.review_status),
        "severidade": str(f.severity), "tipo": str(f.kind),
        "bloqueante": f.severity is Severity.CRITICAL and f.is_pending,
    }
    if len(cites) > 1:
        out["outras_regras"] = [_rule(c) for c in cites[1:]]
    if f.adopted_criterion:
        c = f.adopted_criterion
        crit = {"decisao": c["decision"], "decidido_por": c["decided_by"],
                "decidido_em": c["decided_on"]}
        if c.get("scope"):
            crit["escopo"] = c["scope"]
        out["criterio_adotado"] = crit
    if items:
        out["evidencias"] = [_evidence(e) for e in items]
    if f.measured is not None:
        m = f.measured
        medida: dict[str, Any] = {"valor": m.value, "unidade": m.unit, "limite": m.required}
        if m.uncertainty_abs is not None:
            medida["incerteza"] = m.uncertainty_abs
        if m.algorithm:
            medida["algoritmo"] = m.algorithm
        out["medida"] = medida
    if f.required_action and f.is_pending:
        out["saneamento"] = f.required_action
    return out


def to_achados(findings: Iterable[Finding],
               evidence: Iterable[Evidence] = ()) -> list[dict[str, Any]]:
    ev = tuple(evidence)
    return [to_achado(f, ev) for f in findings]


__all__ = ["ACHADO_SCHEMA_ID", "A_CONFERIR", "to_achado", "to_achados"]
