"""Correções normativas dos extintores (plano de correção, F4).

EXT-CAD-002 por pavimento como critério adotado (interpretação registrada), exceção 5.2.4 no
nível da edificação, composição do 5.2.5 (EXT-CAD-004) e multifamiliar 6.7 (EXT-CAD-005).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from coscip_evidence import Evidence, EvidenceLocator, EvidenceSet

from coscip_cbm import ComplianceStatus, EvidenceSourceType, FindingKind
from coscip_mcp import norms
from coscip_normative.verification import (
    FloorScope,
    ProcessContext,
    compile_verification_plan,
    execute_plan,
    load_catalog,
    verify_catalog,
)
from coscip_normative.verification.catalog import CatalogError, parse_check
from coscip_normative.verification.executor import execute_check

CHECKS = Path(__file__).resolve().parents[2] / "normative" / "checks"
GATES = {"quality.extinguisher.not_presumed": True, "quality.region_confirmed": True,
         "context.unifamiliar": False}


@pytest.fixture(scope="module")
def catalog():
    return load_catalog(CHECKS)


def ext(n: int, agent: str | None = None, floor: str = "f1") -> list[Evidence]:
    out = []
    for i in range(n):
        common = dict(process_id="p", source_type=EvidenceSourceType.CAD, source_id="dxf",
                      source_version=1, source_hash="h" * 8, extraction_method="CAD_SYMBOL",
                      locator=EvidenceLocator(entity_handle=f"H{floor}{i}", floor_id=floor))
        out.append(Evidence(id=f"e:{floor}:{i}", field="extinguisher", normalized_value=True,
                            **common))
        if agent is not None:
            out.append(Evidence(id=f"a:{floor}:{i}", field="extinguisher_agent",
                                normalized_value=agent, **common))
    return out


def agents(*values: str) -> EvidenceSet:
    items = []
    for i, v in enumerate(values):
        items += [e.model_copy(update={"id": f"{e.id}:{i}"}) for e in ext(1, v, floor=f"x{i}")]
    return EvidenceSet.build("p", items)


def run(catalog, facts, floors):
    ctx = ProcessContext(process_id="p", risk_class=facts.get("context.risk_class"),
                         facts={**GATES, **facts})
    plan = compile_verification_plan(catalog, ctx)
    return execute_plan(plan, catalog, EvidenceSet.build("p", []), ctx.all_facts(),
                        floors=floors)


def by(findings, check_id, scope=None):
    out = [f for f in findings if f.check_id == check_id
           and (scope is None or f.scope_id == scope)]
    assert len(out) == 1, [f.ref for f in out]
    return out[0]


def floor(fid: str, evidence: list[Evidence]) -> FloorScope:
    return FloorScope(id=fid, label=fid, evidence=EvidenceSet.build("p", evidence),
                      facts=dict(GATES))


# ------------------------------------------------------------------ EXT-CAD-002 por pavimento

def test_ext_cad_002_counts_per_floor_and_says_criterion(catalog):
    facts = {"context.risk_class": "MEDIO"}
    res = run(catalog, facts, [floor("f1", ext(1, "PQS_ABC", "f1")),
                               floor("f2", ext(2, "PQS_ABC", "f2"))])
    one = by(res, "EXT-CAD-002", "f1")
    two = by(res, "EXT-CAD-002", "f2")
    assert one.compliance_status is ComplianceStatus.NON_COMPLIANT
    assert two.compliance_status is ComplianceStatus.COMPLIANT
    crit = one.adopted_criterion
    assert crit["scope"] == "POR_PAVIMENTO" and crit["decided_by"] == "analista"
    assert crit["decided_on"] == "2026-09-29"
    assert "Critério adotado (analista, 2026-09-29)" in one.explanation
    assert "exige no mínimo duas unidades extintoras por pavimento" not in one.explanation


def test_interpretation_basis_is_verified_like_any_citation(catalog):
    base = norms.load_base()
    report = verify_catalog(catalog, base.sources)
    assert report["verified"], report["failures"]
    ext2 = next(c for c in report["checks"] if c["id"] == "EXT-CAD-002")
    roles = {(c["item"], c["role"]) for c in ext2["citations"]}
    assert ("6.7", "interpretation") in roles and ("5.3", "interpretation") in roles
    assert ext2["interpretation"]["scope"] == "POR_PAVIMENTO"


def test_interpretation_without_basis_is_refused():
    data = {"schema_version": "checks/1.0", "id": "X", "version": 1, "title": "x",
            "system": "S", "type": "MANUAL_CONFIRMATION", "publication_state": "DRAFT",
            "wording": {"title": "x"},
            "interpretation": {"scope": "POR_PAVIMENTO", "basis": [], "decision": "x",
                               "decided_by": "analista", "decided_on": "2026-09-29"}}
    with pytest.raises(Exception, match="texto de apoio"):
        parse_check(data)


# ------------------------------------------------------------------ exceção 5.2.4

def test_exception_524_is_decided_by_building_area_not_floor_area(catalog):
    small = {"context.risk_class": "PEQUENO", "context.building_area_m2": 40}
    res = run(catalog, small, [floor("f1", ext(1, "PQS_ABC"))])
    assert by(res, "EXT-CAD-002").compliance_status is ComplianceStatus.NOT_APPLICABLE
    exc = by(res, "EXT-CAD-002-EXC", "f1")
    assert exc.compliance_status is ComplianceStatus.COMPLIANT  # uma única de pó ABC
    assert any(c["item"] == "5.2.4" for c in exc.normative_citations)
    # edificação grande: pavimento pequeno não dispensa (a área que vale é a da edificação)
    big = {"context.risk_class": "PEQUENO", "context.building_area_m2": 400}
    res = run(catalog, big, [floor("f1", ext(1, "PQS_ABC"))])
    assert by(res, "EXT-CAD-002", "f1").compliance_status is ComplianceStatus.NON_COMPLIANT
    assert by(res, "EXT-CAD-002-EXC").compliance_status is ComplianceStatus.NOT_APPLICABLE


def test_exception_524_needs_abc_and_unknown_area_does_not_dispense(catalog):
    res = run(catalog, {"context.risk_class": "PEQUENO", "context.building_area_m2": 40},
              [floor("f1", ext(1, "CO2"))])
    assert by(res, "EXT-CAD-002-EXC", "f1").compliance_status is ComplianceStatus.NON_COMPLIANT
    res = run(catalog, {"context.risk_class": "PEQUENO"}, [floor("f1", ext(1, "PQS_ABC"))])
    unknown = by(res, "EXT-CAD-002", "f1")
    assert unknown.compliance_status is ComplianceStatus.UNDETERMINED
    assert unknown.reason_code == "APPLICABILITY_UNKNOWN"


# ------------------------------------------------------------------ EXT-CAD-004 composição

@pytest.mark.parametrize(("values", "expected"), [
    (("AGUA", "PQS_BC"), ComplianceStatus.COMPLIANT),          # um A + um B/C
    (("PQS_ABC", "PQS_ABC"), ComplianceStatus.COMPLIANT),      # dois ABC
    (("PQS_ABC", "CO2"), ComplianceStatus.COMPLIANT),          # ABC faz a vaga A
    (("CO2", "PQS_BC"), ComplianceStatus.NON_COMPLIANT),       # falta classe A
    (("PQS_ABC",), ComplianceStatus.NON_COMPLIANT),            # um só objeto, duas vagas
    (("CO2", "DESCONHECIDO"), ComplianceStatus.UNDETERMINED),  # desconhecido decide
    (("AGUA", "CO2", "DESCONHECIDO"), ComplianceStatus.COMPLIANT),  # conhecidos bastam
])
def test_ext_cad_004_composition(catalog, values, expected):
    check = catalog.get("EXT-CAD-004")
    finding = execute_check(check, agents(*values), GATES)
    assert finding.compliance_status is expected, finding.explanation
    if expected is ComplianceStatus.UNDETERMINED:
        assert finding.reason_code == "VALUE_NOT_IDENTIFIED"
        assert finding.kind is FindingKind.DATA_MISSING


def test_ext_cad_004_without_agents_never_passes(catalog):
    check = catalog.get("EXT-CAD-004")
    finding = execute_check(check, EvidenceSet.build("p", ext(3)), GATES)
    assert finding.compliance_status is ComplianceStatus.UNDETERMINED


# ------------------------------------------------------------------ EXT-CAD-005 multifamiliar

def test_ext_cad_005_only_for_multifamily_and_goes_to_analyst(catalog):
    res = run(catalog, {"context.risk_class": "PEQUENO", "context.building_area_m2": 300,
                        "context.occupancy": "A-2"}, [floor("f1", ext(2, "PQS_ABC"))])
    f = by(res, "EXT-CAD-005", "f1")
    assert f.kind is FindingKind.ANALYST_REVIEW
    assert f.compliance_status is ComplianceStatus.UNDETERMINED
    res = run(catalog, {"context.risk_class": "MEDIO", "context.occupancy": "D-2"},
              [floor("f1", ext(2, "PQS_ABC"))])
    assert by(res, "EXT-CAD-005").compliance_status is ComplianceStatus.NOT_APPLICABLE


def test_rules_package_v6_verifies_and_minimum_rule_uses_building_area():
    base = norms.load_base()
    assert base.package.version == 6
    assert base.package_report["verified"], base.package_report["failures"]
    rule = next(r for r in base.package.rules if r.id == "NT201_EXT_MINIMO")
    facts = [p.fact for p in rule.applies_when.any]
    assert "context.building_area_m2" in facts and "floor.area_m2" not in facts
    assert rule.interpretation and rule.interpretation.scope == "POR_PAVIMENTO"
    area = next(r for r in base.package.rules if r.id == "NT201_EXT_AREA")
    assert all(g.fact != "quality.walls_detected" for g in area.quality_gates)


def test_catalog_error_class_still_exported():
    assert issubclass(CatalogError, ValueError)
