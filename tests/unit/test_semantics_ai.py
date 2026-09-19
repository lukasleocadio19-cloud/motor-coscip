from __future__ import annotations

from decimal import Decimal

import pytest

from coscip_ai import AIDisabledError, BudgetExceeded, BudgetLedger, DisabledProvider
from coscip_ai.providers import Extraction, verify_evidence
from coscip_semantics import SemanticMapping, classify
from coscip_semantics.classify import has_conflict


def test_layer_name_is_only_a_hint():
    c = classify(layer="EXTINTORES", block_name=None, attributes={}, mappings=[])
    assert c[0].element_class == "EXTINGUISHER" and c[0].stage == "name_hint"
    assert c[0].rank_score < 1.0


def test_project_mapping_beats_global_and_conflicts_are_kept():
    maps = [
        SemanticMapping("GLOBAL", "block:EXT_ABC", "EXTINGUISHER", True),
        SemanticMapping("PROJECT", "block:EXT_ABC", "OBSTACLE", True),
    ]
    c = classify(layer="0", block_name="EXT_ABC", attributes={}, mappings=maps)
    assert c[0].element_class == "OBSTACLE"
    assert has_conflict(c)


def test_ai_disabled_by_default():
    with pytest.raises(AIDisabledError):
        DisabledProvider().decide({}, ["A", "B"])


def test_budget_reserves_before_call_and_never_auto_raises():
    ledger = BudgetLedger()
    r = ledger.reserve("a1", Decimal("0.20"))
    with pytest.raises(BudgetExceeded):
        ledger.reserve("a1", Decimal("0.10"))
    ledger.settle(r.request_id, Decimal("0.05"))
    ledger.reserve("a1", Decimal("0.10"))


def test_unknown_charge_stays_reserved():
    ledger = BudgetLedger(per_analysis_usd=Decimal("0.25"))
    r = ledger.reserve("a1", Decimal("0.20"))
    ledger.mark_unknown(r.request_id)
    with pytest.raises(BudgetExceeded):
        ledger.reserve("a1", Decimal("0.10"))


def test_monthly_cap():
    ledger = BudgetLedger(per_analysis_usd=Decimal("1"), per_month_usd=Decimal("0.30"))
    ledger.reserve("a1", Decimal("0.20"))
    with pytest.raises(BudgetExceeded):
        ledger.reserve("a2", Decimal("0.20"))


def test_extractions_without_verifiable_evidence_dropped():
    xs = [
        Extraction("area", 10, ("ev-1",), "m", "p1"),
        Extraction("area", 11, (), "m", "p1"),
        Extraction("area", 12, ("ev-inventada",), "m", "p1"),
    ]
    assert [x.value for x in verify_evidence(xs, {"ev-1"})] == [10]
