"""Fluxo determinístico da arquitetura v2: contexto → plano → evidências → achados.

Reproduz o processo sintético do §76: ART, memorial e curva de bomba com fabricante
ausente e pressão divergente, mais uma planta sem extintor reconhecido.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from coscip_evidence import Evidence, EvidenceLocator, EvidenceSet, ExtractionGap
from coscip_findings import consolidate

from coscip_cbm import (
    ComplianceStatus,
    EvidenceSourceType,
    EvidenceStatus,
    FindingKind,
    ReviewStatus,
)
from coscip_normative.verification import (
    ProcessContext,
    compile_verification_plan,
    execute_plan,
    load_catalog,
)

CHECKS = Path(__file__).resolve().parents[2] / "normative" / "checks"

FATOS = {
    "context.risk_class": "GRANDE",
    "context.unifamiliar": False,
    "context.effective_requirement_hydrants": True,
    "context.has_fire_pump": True,
    "quality.extinguisher.not_presumed": True,
    "quality.walls_detected": True,
    # Portas dos checks de extintor v2: sem elas informadas, nada conclui.
    "quality.region_confirmed": True,
    "quality.extinguisher.complete": True,
}


def doc(id_, campo, valor, *, categoria, fonte, pagina=1, sujeito="fire_pump") -> Evidence:
    return Evidence(
        id=id_, process_id="p-21471", source_type=EvidenceSourceType.DOCUMENT,
        source_category=categoria, source_id=fonte, source_version=1,
        source_hash="h" * 8, locator=EvidenceLocator(page=pagina), subject=sujeito,
        field=campo, raw_value=str(valor), normalized_value=valor,
        extraction_method="MANUAL_TRANSCRIPTION")


@pytest.fixture
def catalogo():
    return load_catalog(CHECKS)


@pytest.fixture
def contexto():
    return ProcessContext(process_id="p-21471", occupancy="M-2", risk_class="GRANDE",
                          building_area_m2=1200, building_floors=1, facts=FATOS)


def extintores(quantidade: int = 2) -> list[Evidence]:
    return [
        Evidence(id=f"x{i}", process_id="p-21471", source_type=EvidenceSourceType.CAD,
                 source_id="475c6532", source_version=1, source_hash="c" * 8,
                 locator=EvidenceLocator(entity_handle=f"1A{i}", layer="EXTINTORES"),
                 field="extinguisher", raw_value="bloco", normalized_value=True,
                 extraction_method="CAD_PARSER")
        for i in range(quantidade)
    ]


@pytest.fixture
def evidencias():
    """ART e memorial informam quase tudo; a curva diverge na pressão; falta fabricante."""
    itens = [
        doc("e1", "hydrant_requirement", "Anexo III, Tabela 2", categoria="NORMATIVE",
            fonte="Consulta Anexo III", sujeito=""),
        doc("e2", "technical_responsibility_document", "ART 0000123", categoria="ART",
            fonte="ART 0000123", sujeito=""),
        doc("e3", "serial_number", "SN-4410", categoria="ART", fonte="ART 0000123"),
        doc("e4", "model", "BP-40", categoria="ART", fonte="ART 0000123"),
        doc("e5", "flow_l_min", 200.0, categoria="ART", fonte="ART 0000123"),
        doc("e6", "pressure_mca", 73.0, categoria="ART", fonte="ART 0000123"),
        doc("e7", "rpm", 3500.0, categoria="ART", fonte="ART 0000123"),
        doc("e8", "impeller_diameter_mm", 165.0, categoria="MEMORIAL", fonte="Memorial"),
        doc("e9", "power_cv", 15.0, categoria="MEMORIAL", fonte="Memorial"),
        doc("e10", "pressure_mca", 65.0, categoria="CURVA_BOMBA", fonte="Curva BP-40",
            pagina=3),
    ]
    lacunas = [ExtractionGap(process_id="p-21471", source_id="ART 0000123",
                             source_version=1, subject="fire_pump", field="manufacturer",
                             extraction_method="MANUAL_TRANSCRIPTION")]
    return EvidenceSet.build("p-21471", itens, lacunas)


def achados_por_check(achados):
    return {a.check_id: a for a in achados}


def test_fluxo_completo_produz_achados_reproduziveis(catalogo, contexto, evidencias):
    plano = compile_verification_plan(catalogo, contexto)
    primeiro = execute_plan(plano, catalogo, evidencias, contexto.all_facts())
    segundo = execute_plan(plano, catalogo, evidencias, contexto.all_facts())
    assert [a.content_sha256 for a in primeiro] == [a.content_sha256 for a in segundo]
    assert len(primeiro) == len(catalogo.checks)


def test_art_incompleta_vira_um_unico_achado_de_documento_incompleto(
        catalogo, contexto, evidencias):
    plano = compile_verification_plan(catalogo, contexto)
    achado = achados_por_check(execute_plan(plano, catalogo, evidencias,
                                            contexto.all_facts()))["HID-DOC-004"]
    assert achado.compliance_status is ComplianceStatus.UNDETERMINED
    # A pressão também diverge entre ART e curva: o achado carrega as duas coisas, mas a
    # providência continua sendo completar a documentação.
    assert achado.evidence_status is EvidenceStatus.CONFLICTING
    assert achado.review_status is ReviewStatus.PENDING
    assert achado.kind is FindingKind.DOCUMENT_INCOMPLETE
    assert achado.missing == ("manufacturer",)
    assert "fabricante" in achado.explanation
    assert achado.normative_citations[0]["item"] == "5.1.21"


def test_pressao_divergente_entre_art_e_curva_vira_divergencia(
        catalogo, contexto, evidencias):
    plano = compile_verification_plan(catalogo, contexto)
    achado = achados_por_check(execute_plan(plano, catalogo, evidencias,
                                            contexto.all_facts()))["HID-CROSS-002"]
    assert achado.kind is FindingKind.DIVERGENCE
    assert achado.compliance_status is ComplianceStatus.UNDETERMINED
    assert achado.evidence_status is EvidenceStatus.CONFLICTING
    assert set(achado.divergences[0].values) == {73.0, 65.0}
    assert set(achado.divergences[0].sources) == {"ART 0000123", "Curva BP-40"}


def test_extintor_ausente_na_planta_fica_inconclusivo_nao_reprovado(
        catalogo, contexto, evidencias):
    """§54 e §74: não achar não é "não existe" e nunca vira conformidade."""
    plano = compile_verification_plan(catalogo, contexto)
    achados = achados_por_check(execute_plan(plano, catalogo, evidencias,
                                             contexto.all_facts()))
    presenca = achados["EXT-CAD-001"]
    assert presenca.compliance_status is ComplianceStatus.UNDETERMINED
    assert presenca.kind is FindingKind.DATA_MISSING
    assert presenca.review_status is ReviewStatus.PENDING
    # O mínimo e a distância dependem da presença: ficam inconclusivos, não reprovados.
    assert achados["EXT-CAD-002"].compliance_status is ComplianceStatus.UNDETERMINED
    assert achados["EXT-CAD-002"].reason_code == "DEPENDENCY_UNDETERMINED"


def test_extintores_suficientes_concluem_conformidade(catalogo, contexto, evidencias):
    conjunto = EvidenceSet.build("p-21471", [*evidencias.items, *extintores()],
                                 evidencias.gaps)
    plano = compile_verification_plan(catalogo, contexto)
    achados = achados_por_check(execute_plan(plano, catalogo, conjunto,
                                             contexto.all_facts()))
    assert achados["EXT-CAD-001"].compliance_status is ComplianceStatus.COMPLIANT
    assert achados["EXT-CAD-002"].compliance_status is ComplianceStatus.COMPLIANT
    assert achados["EXT-CAD-002"].measured.value == 2.0


def test_porta_de_qualidade_reprovada_nao_conclui_conformidade(
        catalogo, contexto, evidencias):
    """§25: o número pode aparecer, a conformidade não é finalizada."""
    fatos = {**contexto.all_facts(), "quality.walls_detected": False}
    conjunto = EvidenceSet.build("p-21471", [*evidencias.items, *extintores()],
                                 evidencias.gaps)
    plano = compile_verification_plan(catalogo, contexto)
    achado = achados_por_check(execute_plan(plano, catalogo, conjunto,
                                            fatos))["EXT-CAD-003-GRANDE"]
    assert achado.compliance_status is ComplianceStatus.UNDETERMINED
    assert achado.reason_code == "QUALITY_GATE_FAILED"
    assert achado.review_status is ReviewStatus.PENDING


def test_distancia_acima_do_limite_reprova(catalogo, contexto, evidencias):
    medida = Evidence(
        id="d1", process_id="p-21471", source_type=EvidenceSourceType.CALCULATION,
        source_id="percurso", source_version=1, source_hash="d" * 8,
        field="extinguisher_walk_distance_m", raw_value="19.7", normalized_value=19.7,
        unit="m", uncertainty_abs=1.1, algorithm="grid_dijkstra_16",
        algorithm_version="2.0", extraction_method="CALCULATION")
    conjunto = EvidenceSet.build("p-21471", [*evidencias.items, *extintores(), medida],
                                 evidencias.gaps)
    plano = compile_verification_plan(catalogo, contexto)
    achado = achados_por_check(execute_plan(plano, catalogo, conjunto,
                                            contexto.all_facts()))["EXT-CAD-003-GRANDE"]
    assert achado.compliance_status is ComplianceStatus.NON_COMPLIANT
    assert achado.kind is FindingKind.NON_COMPLIANT
    assert achado.measured.value == 19.7
    assert achado.measured.required == 10.0
    assert achado.measured.algorithm == "grid_dijkstra_16"


def test_medida_dentro_da_incerteza_nao_conclui(catalogo, contexto, evidencias):
    medida = Evidence(
        id="d1", process_id="p-21471", source_type=EvidenceSourceType.CALCULATION,
        source_id="percurso", source_version=1, source_hash="d" * 8,
        field="extinguisher_walk_distance_m", raw_value="10.2", normalized_value=10.2,
        unit="m", uncertainty_abs=1.1, extraction_method="CALCULATION")
    conjunto = EvidenceSet.build("p-21471", [*evidencias.items, *extintores(), medida],
                                 evidencias.gaps)
    plano = compile_verification_plan(catalogo, contexto)
    achado = achados_por_check(execute_plan(plano, catalogo, conjunto,
                                            contexto.all_facts()))["EXT-CAD-003-GRANDE"]
    assert achado.compliance_status is ComplianceStatus.UNDETERMINED
    assert achado.reason_code == "WITHIN_UNCERTAINTY"


def test_checks_inaplicaveis_nao_viram_pendencia(catalogo, evidencias):
    contexto = ProcessContext(process_id="p-21778", facts={
        **FATOS, "context.risk_class": "PEQUENO",
        "context.effective_requirement_hydrants": False})
    plano = compile_verification_plan(catalogo, contexto)
    achados = achados_por_check(execute_plan(plano, catalogo, evidencias,
                                             contexto.all_facts()))
    for check in ("HID-DOC-001", "HID-DOC-004", "HID-CROSS-002"):
        assert achados[check].compliance_status is ComplianceStatus.NOT_APPLICABLE
        assert achados[check].is_pending is False


def test_consolidacao_entrega_poucos_itens_ao_analista(catalogo, contexto, evidencias):
    plano = compile_verification_plan(catalogo, contexto)
    achados = execute_plan(plano, catalogo, evidencias, contexto.all_facts())
    resultado = consolidate(achados)
    resumo = resultado.summary
    assert resumo.divergences == 1
    assert resumo.missing_data >= 1
    assert resumo.review_required >= 1
    # A tela mostra menos itens do que existem achados técnicos.
    assert len(resultado.pending_groups) < len(achados)
    assert resultado.groups[0].kind is not FindingKind.NO_PENDING_ISSUE
