"""Execução de uma regra: aplicabilidade (3 valores) → dados → qualidade → cálculo.

Nenhuma ausência de dado vira conformidade. Erros de software levantam exceção e
são tratados como estado operacional pelo chamador, nunca como PASS/NOT_APPLICABLE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_CEILING, Decimal
from typing import Any

from coscip_cbm import Applicability, EvaluationStatus
from coscip_geometry.tolerances import compare_maximum, compare_minimum
from coscip_rules.dsl import Condition, Predicate, RequiredSpec, RuleDefinition

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


def evaluate_condition(condition: Condition, ctx: EvaluationContext) -> Applicability:
    """Condição em lógica de três valores. Fato desconhecido não vira FALSE."""
    parts: list[bool | None] = []
    if condition.all:
        parts.append(_all([_pred(p, ctx) for p in condition.all]))
    if condition.any:
        parts.append(_any([_pred(p, ctx) for p in condition.any]))
    res = _all(parts) if parts else True
    return {True: Applicability.TRUE, False: Applicability.FALSE, None: Applicability.UNKNOWN}[res]


def applicability(rule: RuleDefinition, ctx: EvaluationContext) -> Applicability:
    return evaluate_condition(rule.applies_when, ctx)


class _MissingKey(Exception):
    def __init__(self, fact: str, value: Any) -> None:
        super().__init__(fact)
        self.fact, self.value = fact, value


def _num(ctx: EvaluationContext, name: str) -> Decimal:
    return _dec(ctx.facts[name].value)


def _dec(v: Any) -> Decimal:
    """Número da regra sem ruído de float (20.0 → 20)."""
    if isinstance(v, float) and v.is_integer():
        return Decimal(int(v))
    return Decimal(str(v))


def resolve_required(spec: str | RequiredSpec, ctx: EvaluationContext,
                     steps: list[str]) -> Decimal:
    """Valor exigido a partir do conjunto fechado de formas (rules/1.1)."""
    if isinstance(spec, str):
        val = _num(ctx, spec)
        steps.append(f"{spec} = {val}")
        return val
    if spec.value is not None:
        return _dec(spec.value)
    if spec.table is not None:
        key = ctx.get(spec.table.key)
        if key is _UNKNOWN or str(key) not in spec.table.values:
            raise _MissingKey(spec.table.key, None if key is _UNKNOWN else key)
        val = _dec(spec.table.values[str(key)])
        steps.append(f"tabela[{spec.table.key}={key}] = {val}")
        return val
    assert spec.ceil_div is not None
    num = _num(ctx, spec.ceil_div.numerator)
    den = resolve_required(spec.ceil_div.denominator, ctx, steps)
    val = (num / den).to_integral_value(rounding=ROUND_CEILING)
    steps.append(f"⌈{spec.ceil_div.numerator} ({num}) ÷ {den}⌉ = {val}")
    return val


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

    failed_gate = next((g for g in rule.quality_gates if _pred(g, ctx) is not True), None)
    if failed_gate is not None:
        # O cálculo segue para o rastro (indicativo), mas o estado é revisão humana.
        out = _calculate(rule, ctx, app)
        trace = {**out.trace, "gate": failed_gate.fact, "indicative": out.status.value
                 if out.status in (EvaluationStatus.PASS, EvaluationStatus.FAIL)
                 else out.trace.get("indicative")}
        return Outcome(app, EvaluationStatus.REVIEW_REQUIRED, "QUALITY_GATE_NOT_MET", trace)
    return _calculate(rule, ctx, app)


def _calculate(rule: RuleDefinition, ctx: EvaluationContext, app: Applicability) -> Outcome:
    calc = rule.calculation
    measured = ctx.facts[calc.measured]
    steps: list[str] = []
    try:
        required = resolve_required(calc.required, ctx, steps)
    except _MissingKey as exc:
        return Outcome(app, EvaluationStatus.MISSING_DATA, "REQUIRED_TABLE_KEY_UNKNOWN",
                       {"missing": [exc.fact], "value": exc.value})
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
    indicative = verdict
    if verdict == "FAIL" and rule.fail_status == "REVIEW_REQUIRED":
        verdict, reason = "REVIEW_REQUIRED", "HEURISTIC_EVIDENCE_VIOLATES"
    return Outcome(
        app,
        EvaluationStatus(verdict),
        reason,
        {
            "operation": f"{calc.operator}/1.0",
            "measured": measured.value,
            "uncertainty_abs": measured.uncertainty_abs,
            "required": str(required),
            "required_steps": steps,
            "indicative": indicative,
            "unit": calc.unit,
            "evidence_ids": list(measured.evidence_ids),
        },
    )
