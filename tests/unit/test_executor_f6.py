"""Executor conta objetos, não evidências (plano de correção, F6)."""

from __future__ import annotations

from pathlib import Path

import pytest
from coscip_evidence import Evidence, EvidenceLocator, EvidenceSet

from coscip_cbm import ComplianceStatus, EvidenceSourceType, EvidenceStatus, FindingKind
from coscip_normative.verification import load_catalog
from coscip_normative.verification.catalog import parse_check
from coscip_normative.verification.executor import execute_check

CHECKS = Path(__file__).resolve().parents[2] / "normative" / "checks"
GATES = {"quality.extinguisher.not_presumed": True, "quality.region_confirmed": True,
         "quality.recognition.complete": True, "quality.extinguisher.complete": True,
         "quality.walls_detected": True}


@pytest.fixture(scope="module")
def catalog():
    return load_catalog(CHECKS)


def ev(i, *, source=EvidenceSourceType.CAD, category="", key=None, value=True,
       field="extinguisher", unc=None, handle=True):
    return Evidence(id=f"{source.value}:{i}", process_id="p", source_type=source,
                    source_category=category, source_id=f"src-{source.value}",
                    source_version=1, source_hash="h" * 8, field=field,
                    locator=EvidenceLocator(entity_handle=f"H{i}" if handle else None,
                                            page=1 if not handle else None, object_key=key),
                    normalized_value=value, uncertainty_abs=unc,
                    extraction_method="TEST")


def test_same_extinguisher_in_cad_and_memorial_counts_once(catalog):
    check = catalog.get("EXT-CAD-002")
    one = [ev(1, key="obj-1"),
           ev(1, source=EvidenceSourceType.HUMAN, key="obj-1", handle=False)]
    f = execute_check(check, EvidenceSet.build("p", one), GATES)
    assert f.compliance_status is ComplianceStatus.NON_COMPLIANT  # 1 objeto, não 2
    assert f.measured.value == 1.0


def test_source_not_accepted_is_ignored_and_recorded(catalog):
    check = catalog.get("EXT-CAD-002")  # aceita CAD e HUMAN
    items = [ev(1, key="a"), ev(2, source=EvidenceSourceType.DOCUMENT, category="MEMORIAL",
                                key="b", handle=False)]
    f = execute_check(check, EvidenceSet.build("p", items), GATES)
    assert f.measured.value == 1.0 and f.compliance_status is ComplianceStatus.NON_COMPLIANT
    assert "fonte não aceita" in f.explanation and "MEMORIAL" in f.explanation


def test_document_category_is_accepted_where_declared(catalog):
    check = catalog.get("EXT-CAD-001")  # aceita CAD, DOCUMENT e HUMAN
    items = [ev(1, source=EvidenceSourceType.DOCUMENT, category="MEMORIAL", key="a",
                handle=False)]
    f = execute_check(check, EvidenceSet.build("p", items), GATES)
    assert f.compliance_status is ComplianceStatus.COMPLIANT


def test_count_divergence_between_sources_is_never_compliant(catalog):
    check = catalog.get("EXT-CAD-002")
    items = [ev(1, key="a"),  # CAD: 1 objeto
             ev(9, source=EvidenceSourceType.HUMAN, value=3, handle=False)]  # declara 3
    f = execute_check(check, EvidenceSet.build("p", items), GATES)
    assert f.kind is FindingKind.DIVERGENCE
    assert f.compliance_status is ComplianceStatus.UNDETERMINED
    assert f.evidence_status is EvidenceStatus.CONFLICTING
    assert f.reason_code == "COUNT_DIVERGENCE"
    assert set(f.divergences[0].values) == {"1", "3"}


def test_worst_measure_considers_uncertainty(catalog):
    check = catalog.get("EXT-CAD-003-PEQUENO")  # máximo 20 m
    items = [ev(1, field="extinguisher_walk_distance_m", value=19.0, unc=0.2),
             ev(2, field="extinguisher_walk_distance_m", value=18.5, unc=2.0)]
    f = execute_check(check, EvidenceSet.build("p", items), GATES)
    # 18,5 ± 2,0 (até 20,5) é pior que 19,0 ± 0,2 (até 19,2): atravessa o limite
    assert f.measured.value == 18.5 and f.measured.uncertainty_abs == 2.0
    assert f.compliance_status is ComplianceStatus.UNDETERMINED
    assert f.reason_code == "WITHIN_UNCERTAINTY"


def test_minimum_uses_value_minus_uncertainty():
    check = parse_check({
        "schema_version": "checks/1.0", "id": "X-MIN", "version": 1, "title": "x",
        "system": "S", "type": "CAD_DIMENSION", "publication_state": "DRAFT",
        "question": {"kind": "minimum_value", "field": "width_m", "required_value": 1.2,
                     "unit": "m", "accepted_evidence": ["CAD"]},
        "normative_basis": [{"document": "EXEMPLO", "edition": "x", "item": "1"}],
        "wording": {"title": "x"}})
    items = [ev(1, field="width_m", value=1.25, unc=0.01),
             ev(2, field="width_m", value=1.30, unc=0.2)]
    f = execute_check(check, EvidenceSet.build("p", items), {})
    assert f.measured.value == 1.30  # 1,30 − 0,20 = 1,10 é o pior caso


def test_synonym_in_accepted_evidence_is_refused():
    data = {"schema_version": "checks/1.0", "id": "X", "version": 1, "title": "x",
            "system": "S", "type": "CAD_COUNT", "publication_state": "DRAFT",
            "question": {"kind": "minimum_count", "field": "f", "required_value": 1,
                         "accepted_evidence": ["CAD", "HUMANO"]},
            "normative_basis": [{"document": "EXEMPLO", "edition": "x", "item": "1"}],
            "wording": {"title": "x"}}
    with pytest.raises(Exception, match="use 'HUMAN'"):
        parse_check(data)
