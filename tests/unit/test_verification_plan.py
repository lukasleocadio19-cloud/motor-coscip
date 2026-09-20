"""Plano de Verificação: aplicabilidade de três valores, dependências e determinismo."""
from __future__ import annotations

from pathlib import Path

import pytest

from coscip_cbm import Applicability, ComplianceStatus
from coscip_normative.verification import (
    ProcessContext,
    compile_verification_plan,
    dependency_gate,
    effective_requirement,
    execution_order,
    load_catalog,
)

CHECKS = Path(__file__).resolve().parents[2] / "normative" / "checks"


@pytest.fixture
def catalogo():
    return load_catalog(CHECKS)


def contexto(**fatos) -> ProcessContext:
    return ProcessContext(process_id="p1", facts=fatos)


def test_plano_e_deterministico(catalogo):
    ctx = contexto(**{"context.risk_class": "GRANDE", "context.unifamiliar": False,
                      "context.effective_requirement_hydrants": True,
                      "context.has_fire_pump": True})
    primeiro = compile_verification_plan(catalogo, ctx)
    segundo = compile_verification_plan(catalogo, ctx)
    assert primeiro.plan_sha256 == segundo.plan_sha256
    assert primeiro.execution_order == segundo.execution_order
    assert primeiro.catalog_sha256 == catalogo.content_sha256


def test_apenas_o_check_do_risco_do_processo_se_aplica(catalogo):
    plano = compile_verification_plan(catalogo, contexto(**{
        "context.risk_class": "GRANDE", "context.unifamiliar": False,
        "context.effective_requirement_hydrants": False}))
    assert "EXT-CAD-003-GRANDE" in plano.applicable_checks
    assert "EXT-CAD-003-PEQUENO" in plano.not_applicable_checks
    assert "EXT-CAD-003-MEDIO" in plano.not_applicable_checks


def test_exigencia_falsa_torna_os_checks_do_sistema_inaplicaveis(catalogo):
    plano = compile_verification_plan(catalogo, contexto(**{
        "context.risk_class": "PEQUENO", "context.unifamiliar": False,
        "context.effective_requirement_hydrants": False}))
    for check in ("HID-DOC-001", "HID-DOC-004", "HID-CROSS-002"):
        assert check in plano.not_applicable_checks
    # A porta de entrada continua aplicável: a exigência é conhecida (e é "não exige").
    assert "HID-REQ-001" in plano.applicable_checks


def test_fato_desconhecido_nao_vira_nao_se_aplica(catalogo):
    """Enquadramento incompleto deixa o check inconclusivo, nunca dispensado."""
    plano = compile_verification_plan(catalogo, contexto())
    assert "EXT-CAD-001" in plano.undetermined_checks
    assert "EXT-CAD-001" not in plano.not_applicable_checks
    item = next(i for i in plano.items if i.check_id == "EXT-CAD-001")
    assert item.applicability is Applicability.UNKNOWN
    assert "context.unifamiliar" in item.missing_facts


def test_check_manual_entra_no_plano_em_lista_propria(catalogo):
    plano = compile_verification_plan(catalogo, contexto())
    assert plano.manual_checks == ("QG-CAD-WALLS",)
    assert "QG-CAD-WALLS" not in plano.applicable_checks


def test_inconclusivo_e_manual_entram_na_execucao_nada_e_descartado(catalogo):
    plano = compile_verification_plan(catalogo, contexto())
    assert set(plano.execution_order) == {i.check_id for i in plano.items}


def test_dependencia_vem_antes_do_dependente(catalogo):
    ctx = contexto(**{"context.risk_class": "MEDIO", "context.unifamiliar": False,
                      "context.effective_requirement_hydrants": True,
                      "context.has_fire_pump": True})
    ordem = compile_verification_plan(catalogo, ctx).execution_order
    assert ordem.index("EXT-CAD-001") < ordem.index("EXT-CAD-002")
    assert ordem.index("HID-REQ-001") < ordem.index("HID-DOC-004")
    # O cruzamento depende só da exigência do sistema, não da identificação completa.
    assert ordem.index("HID-REQ-001") < ordem.index("HID-CROSS-002")


def test_ordem_de_execucao_ignora_check_fora_do_conjunto(catalogo):
    assert execution_order(catalogo, ["EXT-CAD-002"]) == ("EXT-CAD-002",)


def test_dependencia_inconclusiva_nao_libera_o_dependente():
    assert dependency_gate(["A"], {}) == ("UNDETERMINED",
                                          "o check A não foi executado nesta análise")
    assert dependency_gate(["A"], {"A": ComplianceStatus.UNDETERMINED})[0] == "UNDETERMINED"
    assert dependency_gate(["A"], {"A": ComplianceStatus.NOT_APPLICABLE})[0] == "NOT_APPLICABLE"
    assert dependency_gate(["A"], {"A": ComplianceStatus.COMPLIANT}) is None
    assert dependency_gate(["A"], {"A": ComplianceStatus.NON_COMPLIANT}) is None


def test_contexto_nao_inventa_fato_ausente():
    ctx = ProcessContext(process_id="p1", occupancy="M-2", building_floors=1)
    fatos = ctx.all_facts()
    assert fatos["occupancy"] == "M-2"
    assert "building_height_m" not in fatos


def test_condicao_especial_vira_fato():
    ctx = ProcessContext(process_id="p1", special_conditions=("glp",))
    assert ctx.all_facts()["condition_glp"] is True


def test_hash_do_contexto_muda_com_o_enquadramento():
    a = ProcessContext(process_id="p1", occupancy="M-2")
    b = ProcessContext(process_id="p2", occupancy="M-2")
    c = ProcessContext(process_id="p1", occupancy="A-2")
    assert a.content_sha256 == b.content_sha256
    assert a.content_sha256 != c.content_sha256


def test_override_humano_nunca_apaga_a_exigencia_normativa():
    """§30: exigência normativa, override e exigência efetiva convivem."""
    assert effective_requirement(True, None) == {
        "normative_requirement": True, "human_override": None, "effective_requirement": True}
    com_override = effective_requirement(True, False)
    assert com_override["normative_requirement"] is True
    assert com_override["effective_requirement"] is False
