from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

# Conjunto fechado. Novas operações entram como funções versionadas e testadas.
PREDICATE_OPERATORS = frozenset({"equals", "not_equals", "in", "gte", "lte", "gt", "lt",
                                 "is_known"})
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
    page: int | None = None
    # rules/1.1: termos que precisam constar no trecho do item ingerido (verificação REG-01).
    quote: tuple[str, ...] = ()


class Interpretation(_Strict):
    """Critério adotado quando o texto da norma não diz literalmente o alcance que a regra
    aplica (plano de correção, F4.1). ``verify_*`` confere a frase de cada ``basis``, não o
    alcance: o alcance é **decisão registrada**, mostrada separada do texto da norma."""

    scope: str  # ex.: POR_PAVIMENTO, DISTANCIA_DIRETA, PERCURSO_COMO_MANGUEIRA
    basis: tuple[Source, ...]
    decision: str
    decided_by: str
    decided_on: str  # AAAA-MM-DD

    def as_dict(self) -> dict[str, Any]:
        return {"scope": self.scope, "decision": self.decision, "decided_by": self.decided_by,
                "decided_on": self.decided_on,
                "basis": [{"document": b.document, "item": b.item} for b in self.basis]}


class Homologation(_Strict):
    """Homologação por responsável técnico (plano de correção, F9; REG-05/06). Sem ela, regra
    e check **não saem de rascunho**: ``HOMOLOGATED``/``PUBLISHED`` exigem este registro, e o
    relatório de validação que o sustenta fica em ``docs/validacao/AAAA-MM-DD.md``."""

    responsible: str = Field(min_length=3)
    registration: str = Field(min_length=3)  # CREA/CAU do responsável técnico
    decided_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    report: str = Field(pattern=r"^docs/validacao/\d{4}-\d{2}-\d{2}\.md$")


HOMOLOGATED_STATES = frozenset({"HOMOLOGATED", "PUBLISHED"})


def homologation_problem(item_id: str, state: str, eligible: bool,
                         homologation: Homologation | None) -> str | None:
    """Motivo de recusa, ou ``None``. Vale para regra e para check."""
    if state in HOMOLOGATED_STATES and homologation is None:
        return (f"{item_id}: {state} exige homologação registrada (responsável técnico, "
                "registro, data e relatório de validação)")
    if eligible and state not in HOMOLOGATED_STATES:
        return f"{item_id}: só regra/check homologado vai à produção (estado {state})"
    return None


class TableSpec(_Strict):
    key: str  # fato cujo valor escolhe a linha
    values: dict[str, float]


class RequiredSpec(_Strict):
    """Valor exigido: literal, tabela por contexto ou divisão arredondada para cima.

    Conjunto fechado; exatamente um campo preenchido.
    """

    value: float | None = None
    table: TableSpec | None = None
    ceil_div: CeilDiv | None = None

    def facts(self) -> list[str]:
        out: list[str] = []
        if self.table:
            out.append(self.table.key)
        if self.ceil_div:
            out.append(self.ceil_div.numerator)
            out.extend(self.ceil_div.denominator.facts())
        return out


class CeilDiv(_Strict):
    numerator: str
    denominator: RequiredSpec


RequiredSpec.model_rebuild()


class Calculation(_Strict):
    operator: str
    measured: str
    required: str | RequiredSpec
    unit: str


Subject = Literal["DRAWING", "FLOOR", "SYMBOL", "ROOM"]


class RuleDefinition(_Strict):
    schema_version: Literal["rules/1.0", "rules/1.1"]
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
    # rules/1.1
    title: str = ""
    subject: Subject = "FLOOR"
    measure: str | None = None  # sistema/medida (ex.: "Extintores") para agrupar o relatório
    extra_sources: tuple[Source, ...] = ()
    # Fatos obtidos por associação heurística (ex.: placa próxima) não sustentam FAIL.
    fail_status: Literal["FAIL", "REVIEW_REQUIRED"] = "FAIL"
    interpretation: Interpretation | None = None
    homologation: Homologation | None = None

    @property
    def content_hash(self) -> str:
        data = self.model_dump(mode="json")
        if data.get("homologation") is None:  # campo do F9: ausente não muda o hash antigo
            data.pop("homologation", None)
        canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
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
    req = rule.calculation.required
    refs = [rule.calculation.measured, *([req] if isinstance(req, str) else req.facts())]
    for ref in refs:
        if ref not in rule.required_inputs:
            raise RuleValidationError(f"{rule.id}: '{ref}' não declarado em required_inputs")
    if not isinstance(req, str):
        _check_required(rule.id, req)
    if rule.schema_version == "rules/1.1":
        for src in (rule.source, *rule.extra_sources):
            if not src.quote and not src.document.startswith("EXEMPLO"):
                raise RuleValidationError(
                    f"{rule.id}: citação {src.item} sem termos de conferência")
    if rule.production_eligible and rule.publication_state in {"DRAFT", "TEST_ONLY"}:
        raise RuleValidationError(
            f"{rule.id}: regra {rule.publication_state} não pode ir à produção"
        )
    if rule.production_eligible and rule.source.document.startswith("EXEMPLO"):
        raise RuleValidationError(f"{rule.id}: fonte de exemplo não pode ir à produção")
    problem = homologation_problem(rule.id, rule.publication_state, rule.production_eligible,
                                   rule.homologation)
    if problem:
        raise RuleValidationError(problem)


def _check_required(rule_id: str, spec: RequiredSpec) -> None:
    filled = [n for n in ("value", "table", "ceil_div") if getattr(spec, n) is not None]
    if len(filled) != 1:
        raise RuleValidationError(f"{rule_id}: valor exigido precisa de exatamente um tipo")
    if spec.table is not None and not spec.table.values:
        raise RuleValidationError(f"{rule_id}: tabela de valores vazia")
    if spec.ceil_div is not None:
        _check_required(rule_id, spec.ceil_div.denominator)


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
