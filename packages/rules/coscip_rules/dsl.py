from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

# Conjunto fechado. Novas operações entram como funções versionadas e testadas.
PREDICATE_OPERATORS = frozenset({"equals", "not_equals", "in", "gte", "lte", "is_known"})
CALCULATION_OPERATORS = frozenset({"minimum_with_uncertainty", "maximum_with_uncertainty"})
OUTCOMES = frozenset({"MISSING_DATA", "REVIEW_REQUIRED"})


class RuleValidationError(ValueError):
    pass


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Predicate(_Strict):
    fact: str
    operator: str
    value: Any = None


class Condition(_Strict):
    all: tuple[Predicate, ...] = ()
    any: tuple[Predicate, ...] = ()


class Source(_Strict):
    document: str
    edition: str
    item: str


class Calculation(_Strict):
    operator: str
    measured: str
    required: str
    unit: str


class RuleDefinition(_Strict):
    schema_version: Literal["rules/1.0"]
    id: str
    version: int = Field(ge=1)
    publication_state: Literal["DRAFT", "TEST_ONLY", "HOMOLOGATED", "PUBLISHED", "DEPRECATED"]
    production_eligible: bool
    jurisdiction: str
    source: Source
    applies_when: Condition
    required_inputs: tuple[str, ...]
    quality_gates: tuple[Predicate, ...] = ()
    calculation: Calculation
    on_missing: Literal["MISSING_DATA"]
    on_conflict: Literal["REVIEW_REQUIRED"]
    on_unknown_applicability: Literal["REVIEW_REQUIRED", "MISSING_DATA"]
    evidence_required: tuple[str, ...]
    depends_on: tuple[str, ...] = ()

    @property
    def content_hash(self) -> str:
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _check(rule: RuleDefinition) -> None:
    preds = [*rule.applies_when.all, *rule.applies_when.any, *rule.quality_gates]
    for p in preds:
        if p.operator not in PREDICATE_OPERATORS:
            raise RuleValidationError(f"{rule.id}: operador não permitido '{p.operator}'")
    if rule.calculation.operator not in CALCULATION_OPERATORS:
        raise RuleValidationError(
            f"{rule.id}: cálculo não permitido '{rule.calculation.operator}'"
        )
    for ref in (rule.calculation.measured, rule.calculation.required):
        if ref not in rule.required_inputs:
            raise RuleValidationError(f"{rule.id}: '{ref}' não declarado em required_inputs")
    if rule.production_eligible and rule.publication_state in {"DRAFT", "TEST_ONLY"}:
        raise RuleValidationError(
            f"{rule.id}: regra {rule.publication_state} não pode ir à produção"
        )
    if rule.production_eligible and rule.source.document.startswith("EXEMPLO"):
        raise RuleValidationError(f"{rule.id}: fonte de exemplo não pode ir à produção")


def parse_rule(data: dict[str, Any]) -> RuleDefinition:
    try:
        rule = RuleDefinition.model_validate(data)
    except ValidationError as exc:
        raise RuleValidationError(str(exc)) from exc
    _check(rule)
    return rule


def load_rule(path: str | Path) -> RuleDefinition:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return parse_rule(data)


def check_dependency_cycles(rules: list[RuleDefinition]) -> None:
    graph = {r.id: set(r.depends_on) for r in rules}
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(node: str) -> None:
        if node in done:
            return
        if node in visiting:
            raise RuleValidationError(f"ciclo de dependência envolvendo {node}")
        visiting.add(node)
        for dep in graph.get(node, ()):
            visit(dep)
        visiting.discard(node)
        done.add(node)

    for rid in graph:
        visit(rid)
