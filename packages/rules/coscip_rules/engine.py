"""Execução de uma regra: aplicabilidade (3 valores) → dados → qualidade → cálculo.

Nenhuma ausência de dado vira conformidade. Erros de software levantam exceção e
são tratados como estado operacional pelo chamador, nunca como PASS/NOT_APPLICABLE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from coscip_cbm import Applicability, EvaluationStatus
from coscip_geometry.tolerances import compare_maximum, compare_minimum
from coscip_rules.dsl import Predicate, RuleDefinition

_UNKNOWN = object()


@dataclass(frozen=True)
class Fact:
    value: Any
    uncertainty_abs: float | None = None
    conflict: bool = False
    evidence_ids: tuple[str, ...] = ()


@dataclass
class EvaluationContext:
    """Fatos disponíveis para um sujeito. Chave ausente = desconhecido (≠ None ≠ 0)."""

    subject_id: str
    facts: dict[str, Fact] = field(default_factory=dict)

    def get(self, name: str) -> Any:
        f = self.facts.get(name)
        if f is None or f.value is None:
            return _UNKNOWN
        return f.value


@dataclass(frozen=True)
class Outcome:
    applicability: Applicability
    status: EvaluationStatus
    reason_code: str
    trace: dict[str, Any] = field(default_factory=dict)


def _pred(p: Predicate, ctx: EvaluationContext) -> bool | None:
    v = ctx.get(p.fact)
    if p.operator == "is_known":
        return v is not _UNKNOWN
    if v is _UNKNOWN:
        return None
    match p.operator:
        case "equals":
            return v == p.value
        case "not_equals":
            return v != p.value
        case "in":
            return v in p.value
        case "gte":
            return Decimal(str(v)) >= Decimal(str(p.value))
        case "lte":
            return Decimal(str(v)) <= Decimal(str(p.value))
    raise AssertionError(f"operador não compilado: {p.operator}")


def _all(values: list[bool | None]) -> bool | None:
    if any(v is False for v in values):
        return False
    if any(v is None for v in values):
        return None
    return True


def _any(values: list[bool | None]) -> bool | None:
    if any(v is True for v in values):
        return True
    if any(v is None for v in values):
        return None
    return False


def applicability(rule: RuleDefinition, ctx: EvaluationContext) -> Applicability:
    parts: list[bool | None] = []
    if rule.applies_when.all:
        parts.append(_all([_pred(p, ctx) for p in rule.applies_when.all]))
    if rule.applies_when.any:
        parts.append(_any([_pred(p, ctx) for p in rule.applies_when.any]))
    res = _all(parts) if parts else True
    return {True: Applicability.TRUE, False: Applicability.FALSE, None: Applicability.UNKNOWN}[res]


def evaluate(rule: RuleDefinition, ctx: EvaluationContext) -> Outcome:
    app = applicability(rule, ctx)
    if app is Applicability.FALSE:
        return Outcome(app, EvaluationStatus.NOT_APPLICABLE, "APPLICABILITY_FALSE")
    if app is Applicability.UNKNOWN:
        return Outcome(
            app, EvaluationStatus(rule.on_unknown_applicability), "APPLICABILITY_UNKNOWN"
        )

    missing = [name for name in rule.required_inputs if ctx.get(name) is _UNKNOWN]
    if missing:
        return Outcome(app, EvaluationStatus.MISSING_DATA, "REQUIRED_INPUT_MISSING",
                       {"missing": missing})

    conflicts = [n for n in rule.required_inputs if ctx.facts[n].conflict]
    if conflicts:
        return Outcome(app, EvaluationStatus.REVIEW_REQUIRED, "INPUT_CONFLICT",
                       {"conflicts": conflicts})

    for gate in rule.quality_gates:
        if _pred(gate, ctx) is not True:
            return Outcome(app, EvaluationStatus.REVIEW_REQUIRED, "QUALITY_GATE_NOT_MET",
                           {"gate": gate.fact})

    calc = rule.calculation
    measured = ctx.facts[calc.measured]
    required = Decimal(str(ctx.facts[calc.required].value))
    if measured.uncertainty_abs is None:
        return Outcome(app, EvaluationStatus.REVIEW_REQUIRED, "UNCERTAINTY_UNKNOWN")

    compare = (
        compare_minimum if calc.operator == "minimum_with_uncertainty" else compare_maximum
    )
    verdict = compare(float(measured.value), measured.uncertainty_abs, required)
    reason = {
        "PASS": "MEASURED_INTERVAL_SATISFIES",
        "FAIL": "MEASURED_INTERVAL_VIOLATES",
        "REVIEW_REQUIRED": "UNCERTAINTY_CROSSES_LIMIT",
    }[verdict]
    return Outcome(
        app,
        EvaluationStatus(verdict),
        reason,
        {
            "operation": f"{calc.operator}/1.0",
            "measured": measured.value,
            "uncertainty_abs": measured.uncertainty_abs,
            "required": str(required),
            "unit": calc.unit,
        },
    )
