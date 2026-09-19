"""Regra artificial: cinco estados, fronteiras e proteções da DSL (REG-04)."""

from __future__ import annotations

import copy

import pytest
import yaml

from coscip_cbm import Applicability, EvaluationStatus
from coscip_rules import EvaluationContext, RuleValidationError, evaluate, load_rule
from coscip_rules.dsl import check_dependency_cycles, parse_rule
from coscip_rules.engine import Fact
from tests.conftest import ROOT

RULE_PATH = ROOT / "normative" / "rules" / "DEMO_DOOR_WIDTH_MIN.v1.yaml"


@pytest.fixture
def rule():
    return load_rule(RULE_PATH)


def ctx(width=0.87, unc=0.002, cls="DOOR", demo=True, validated=True, **extra) -> EvaluationContext:
    facts = {
        "context.demo_enabled": Fact(demo),
        "element.class": Fact(cls),
        "element.clear_width": Fact(width, uncertainty_abs=unc),
        "context.demo_required_width": Fact("0.90"),
        "quality.width_validated": Fact(validated),
    }
    facts.update(extra)
    return EvaluationContext(subject_id="door-017", facts=facts)


@pytest.mark.parametrize(
    ("width", "expected"),
    [
        (0.87, EvaluationStatus.FAIL),  # intervalo inteiro abaixo
        (0.900, EvaluationStatus.REVIEW_REQUIRED),  # atravessa o limite
        (0.905, EvaluationStatus.PASS),  # intervalo inteiro atende
        (0.898, EvaluationStatus.REVIEW_REQUIRED),  # limite superior = 0,900
        (0.897, EvaluationStatus.FAIL),
        (0.902, EvaluationStatus.PASS),  # limite inferior = 0,900
    ],
)
def test_minimum_with_uncertainty(rule, width, expected):
    assert evaluate(rule, ctx(width=width)).status is expected


def test_not_a_door_is_not_applicable(rule):
    out = evaluate(rule, ctx(cls="WINDOW"))
    assert out.applicability is Applicability.FALSE
    assert out.status is EvaluationStatus.NOT_APPLICABLE


def test_unknown_applicability_goes_to_review(rule):
    c = ctx()
    del c.facts["element.class"]
    out = evaluate(rule, c)
    assert out.applicability is Applicability.UNKNOWN
    assert out.status is EvaluationStatus.REVIEW_REQUIRED


def test_missing_width_is_missing_data_never_pass(rule):
    out = evaluate(rule, ctx(width=None))
    assert out.status is EvaluationStatus.MISSING_DATA
    assert "element.clear_width" in out.trace["missing"]


def test_zero_is_not_missing(rule):
    assert evaluate(rule, ctx(width=0.0)).status is EvaluationStatus.FAIL


def test_quality_gate_blocks(rule):
    assert evaluate(rule, ctx(validated=False)).status is EvaluationStatus.REVIEW_REQUIRED


def test_conflict_goes_to_review(rule):
    c = ctx()
    c.facts["element.clear_width"] = Fact(0.95, uncertainty_abs=0.002, conflict=True)
    assert evaluate(rule, c).status is EvaluationStatus.REVIEW_REQUIRED


def test_unknown_uncertainty_goes_to_review(rule):
    assert evaluate(rule, ctx(unc=None)).status is EvaluationStatus.REVIEW_REQUIRED


def _raw():
    return yaml.safe_load(RULE_PATH.read_text(encoding="utf-8"))


def test_disallowed_operator_rejected():
    data = _raw()
    data["applies_when"]["all"][0]["operator"] = "eval"
    with pytest.raises(RuleValidationError):
        parse_rule(data)


def test_test_only_cannot_be_production():
    data = _raw()
    data["production_eligible"] = True
    with pytest.raises(RuleValidationError):
        parse_rule(data)


def test_unknown_field_rejected():
    data = _raw()
    data["python"] = "import os"
    with pytest.raises(RuleValidationError):
        parse_rule(data)


def test_content_hash_changes_with_parameters(rule):
    data = _raw()
    data["calculation"]["unit"] = "cm"
    assert parse_rule(data).content_hash != rule.content_hash


def test_dependency_cycle_detected(rule):
    a = rule.model_copy(update={"id": "A", "depends_on": ("B",)})
    b = copy.copy(rule).model_copy(update={"id": "B", "depends_on": ("A",)})
    with pytest.raises(RuleValidationError):
        check_dependency_cycles([a, b])
