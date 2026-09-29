"""Fase 3 da arquitetura v2: DXF → análise da planta → Evidence → Plano → Finding.

Tudo sintético (``make_fire_plan``): pavimento 30×12 m com paredes, 2 extintores, hidrante,
acionador, luminária e legenda fora da planta. O critério de aceite da fase é que uma
análise produza ``Finding`` sem depender do texto nem dos vereditos das regras antigas.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
from coscip_evidence import Evidence, EvidenceLocator, EvidenceSet
from coscip_findings import consolidate

from coscip_analysis import AnalysisInput, RuleBinding, parse_dictionary, run
from coscip_analysis.evidence import PlantEvidenceError, plant_evidence, process_context
from coscip_cad.synthetic import make_fire_plan
from coscip_cbm import (
    ComplianceStatus,
    EvidenceSourceType,
    EvidenceStatus,
    FindingKind,
    ReviewStatus,
)
from coscip_normative.package import load_package
from coscip_normative.verification import (
    FloorScope,
    ProcessContext,
    compile_verification_plan,
    execute_plan,
    load_catalog,
)

ROOT = Path(__file__).resolve().parents[2]
CHECKS = ROOT / "normative" / "checks"
BASE = ROOT / "normative" / "base"
TERREO = {"x0": -1, "y0": -1, "x1": 31, "y1": 13}


def _analyze(tmp_path: Path, *, floors=None, risk="PEQUENO"):
    pkg = load_package(BASE)
    dxf = make_fire_plan(tmp_path / "p.dxf")
    floors = [{"id": "floor-0001", "name": "Térreo", "clip": TERREO}] if floors is None \
        else floors
    return run(AnalysisInput(
        dxf=dxf, scale_to_m=1.0, dictionary=parse_dictionary(pkg.symbols),
        rules=[RuleBinding(r) for r in pkg.rules],
        context={"risk_class": risk, "unifamiliar": False, "building_area_m2": 360},
        floors=floors))


def _findings(analysis, process_id="p-sintetico"):
    catalog = load_catalog(CHECKS)
    pe = plant_evidence(analysis, process_id=process_id)
    plan = compile_verification_plan(catalog, pe.context)
    return pe, execute_plan(plan, catalog, pe.process_evidence, pe.context.all_facts(),
                            floors=pe.floors)


def _by(findings, check_id, scope=None):
    out = [f for f in findings if f.check_id == check_id
           and (scope is None or f.scope_label == scope)]
    assert len(out) == 1, [f.ref for f in out]
    return out[0]


@pytest.fixture(scope="module")
def terreo(tmp_path_factory):
    return _analyze(tmp_path_factory.mktemp("terreo"))


def test_cada_extintor_vira_evidencia_localizada_no_desenho(terreo):
    pe = plant_evidence(terreo, process_id="p")
    (floor,) = pe.floors
    ext = floor.evidence.for_field("extinguisher")
    assert len(ext) == 2
    for e in ext:
        assert e.source_type is EvidenceSourceType.CAD
        assert e.source_hash == terreo["drawing"]["sha256"]
        assert e.locator.entity_handle and e.locator.layer == "INC_EXT"
        assert e.locator.floor_id == floor.id
        assert e.status is EvidenceStatus.SUFFICIENT
    # A legenda fica fora do pavimento e nunca vira evidência de extintor.
    assert all("LEGENDA" not in (e.raw_value or "") for e in ext)


def test_percurso_vira_medida_auditavel(terreo):
    (floor,) = plant_evidence(terreo, process_id="p").floors
    (dist,) = floor.evidence.for_field("extinguisher_walk_distance_m")
    assert 11.0 < dist.normalized_value < 13.5
    assert dist.unit == "m" and dist.uncertainty_abs > 0
    assert dist.algorithm == "visibility_graph_bnb" and dist.algorithm_version
    assert set(dist.uncertainty_budget) >= {"metodo", "amostragem", "posicao_do_simbolo",
                                            "unidade_escala", "modelagem_de_parede", "total"}
    assert dist.locator.bbox is not None  # ponto mais distante no desenho
    assert floor.facts["quality.walls_detected"] is True


def test_classe_nao_encontrada_vira_lacuna_de_extracao_nao_ausencia(terreo):
    (floor,) = plant_evidence(terreo, process_id="p").floors
    assert floor.evidence.has_gap("sprinkler")
    assert not floor.evidence.has_gap("extinguisher")


def test_analise_real_produz_achados_de_extintor(terreo):
    _, achados = _findings(terreo)
    presenca = _by(achados, "EXT-CAD-001")
    assert presenca.compliance_status is ComplianceStatus.COMPLIANT
    assert presenca.scope_label == "Térreo" and presenca.ref.startswith("EXT-CAD-001@")
    minimo = _by(achados, "EXT-CAD-002")
    assert minimo.compliance_status is ComplianceStatus.COMPLIANT
    assert minimo.measured.value == 2.0
    distancia = _by(achados, "EXT-CAD-003-PEQUENO")
    assert distancia.compliance_status is ComplianceStatus.COMPLIANT
    assert distancia.measured.algorithm == "visibility_graph_bnb"
    assert distancia.measured.geometry_snapshot_hash == terreo["drawing"]["sha256"]
    assert distancia.evidence_ids == ("cad:floor-floor-00:extinguisher_walk_distance_m",)


def test_risco_grande_reprova_a_distancia(tmp_path):
    _, achados = _findings(_analyze(tmp_path, risk="GRANDE"))
    achado = _by(achados, "EXT-CAD-003-GRANDE")
    assert achado.compliance_status is ComplianceStatus.NON_COMPLIANT
    assert achado.kind is FindingKind.NON_COMPLIANT
    assert achado.measured.required == 10.0
    # Os checks dos outros riscos não se aplicam e não viram pendência.
    assert _by(achados, "EXT-CAD-003-PEQUENO").compliance_status is \
        ComplianceStatus.NOT_APPLICABLE


def test_nao_depende_do_texto_nem_dos_vereditos_antigos(terreo):
    """Critério de aceite da fase 3."""
    _, antes = _findings(terreo)
    sem_legado = copy.deepcopy(terreo)
    sem_legado.pop("results")
    for region in sem_legado["regions"]:
        region.pop("map_svg", None)
    _, depois = _findings(sem_legado)
    assert [f.content_sha256 for f in antes] == [f.content_sha256 for f in depois]


def test_mesma_analise_mesmos_achados(terreo):
    _, a = _findings(terreo)
    _, b = _findings(terreo)
    assert [f.content_sha256 for f in a] == [f.content_sha256 for f in b]


def test_contagem_e_por_pavimento_nao_pela_planta_inteira(tmp_path):
    """Dois pavimentos com um extintor cada: o processo tem 2, mas cada pavimento tem 1."""
    floors = [{"id": "floor-oeste", "name": "Oeste", "clip": {**TERREO, "x1": 12.5}},
              {"id": "floor-leste", "name": "Leste", "clip": {**TERREO, "x0": 12.5}}]
    _, achados = _findings(_analyze(tmp_path, floors=floors))
    for lado in ("Oeste", "Leste"):
        minimo = _by(achados, "EXT-CAD-002", lado)
        assert minimo.compliance_status is ComplianceStatus.NON_COMPLIANT, lado
        assert minimo.measured.value == 1.0
    grupo = next(g for g in consolidate(achados).groups if g.group_key == "extintores/minimo")
    assert set(grupo.scopes) == {"Oeste", "Leste"}
    assert len(grupo.finding_ids) == 2


def test_pavimento_sem_extintor_fica_inconclusivo_sem_contaminar_o_outro(tmp_path):
    floors = [{"id": "aaaa0001", "name": "Térreo", "clip": TERREO},
              {"id": "bbbb0002", "name": "Vazio", "clip": {"x0": 35, "y0": -1, "x1": 50,
                                                             "y1": 13}}]
    _, achados = _findings(_analyze(tmp_path, floors=floors))
    vazio = _by(achados, "EXT-CAD-001", "Vazio")
    assert vazio.compliance_status is ComplianceStatus.UNDETERMINED
    assert vazio.kind is FindingKind.DATA_MISSING
    assert vazio.review_status is ReviewStatus.PENDING
    assert "não localizou" in vazio.explanation  # §54: lacuna, não "não existe"
    assert _by(achados, "EXT-CAD-002", "Vazio").reason_code == "DEPENDENCY_UNDETERMINED"
    assert _by(achados, "EXT-CAD-002", "Térreo").compliance_status is \
        ComplianceStatus.COMPLIANT


def test_regiao_automatica_nao_confirmada_nao_conclui(tmp_path):
    _, achados = _findings(_analyze(tmp_path, floors=[]))
    presenca = _by(achados, "EXT-CAD-001")
    assert presenca.compliance_status is ComplianceStatus.UNDETERMINED
    assert presenca.reason_code == "QUALITY_GATE_FAILED"
    assert "quality.region_confirmed" in presenca.explanation
    assert _by(achados, "EXT-CAD-002").reason_code == "DEPENDENCY_UNDETERMINED"


def test_extintor_presumido_nao_conclui_conformidade(terreo):
    presumido = copy.deepcopy(terreo)
    (region,) = [r for r in presumido["regions"] if r["kind"] == "PLAN"]
    for sym in region["symbols"]:
        if sym["class"] == "EXTINTOR":
            sym["attrs"]["presumed"] = True
    region["facts"]["quality.extinguisher.not_presumed"]["value"] = False
    pe, achados = _findings(presumido)
    assert all(e.quality_gate == "quality.extinguisher.not_presumed"
               for e in pe.floors[0].evidence.for_field("extinguisher"))
    presenca = _by(achados, "EXT-CAD-001")
    assert presenca.compliance_status is ComplianceStatus.UNDETERMINED
    assert presenca.review_status is ReviewStatus.PENDING


def test_area_nao_alcancada_pelo_percurso_nao_conclui_distancia(terreo):
    incompleto = copy.deepcopy(terreo)
    (region,) = [r for r in incompleto["regions"] if r["kind"] == "PLAN"]
    region["facts"]["quality.extinguisher.complete"]["value"] = False
    _, achados = _findings(incompleto)
    distancia = _by(achados, "EXT-CAD-003-PEQUENO")
    assert distancia.compliance_status is ComplianceStatus.UNDETERMINED
    assert distancia.reason_code == "QUALITY_GATE_FAILED"


def test_contexto_vem_do_formulario_da_analise(terreo):
    ctx = process_context(terreo, "p")
    assert ctx.risk_class == "PEQUENO"
    assert ctx.all_facts()["context.unifamiliar"] is False


def test_saida_desconhecida_ou_sem_hash_e_recusada(terreo):
    with pytest.raises(PlantEvidenceError):
        plant_evidence({**terreo, "schema_version": "plant-analysis/0.9"}, process_id="p")
    with pytest.raises(PlantEvidenceError):
        plant_evidence({**terreo, "drawing": {}}, process_id="p")


def test_porta_de_qualidade_nao_informada_nao_conclui():
    """Qualidade desconhecida conta como não atendida, como no motor de regras."""
    catalog = load_catalog(CHECKS)
    ctx = ProcessContext(process_id="p", facts={"context.risk_class": "PEQUENO",
                                                "context.unifamiliar": False})
    ext = [Evidence(id=f"x{i}", process_id="p", source_type=EvidenceSourceType.CAD,
                    source_id="d", source_version=1, source_hash="h",
                    locator=EvidenceLocator(entity_handle=f"A{i}"), field="extinguisher",
                    normalized_value=True, extraction_method="CAD_SYMBOL") for i in range(2)]
    floor = FloorScope(id="f1", label="Térreo", evidence=EvidenceSet.build("p", ext),
                       facts={"quality.region_confirmed": True})
    plan = compile_verification_plan(catalog, ctx)
    achados = execute_plan(plan, catalog, EvidenceSet.build("p", ()), ctx.all_facts(),
                           floors=[floor])
    presenca = _by(achados, "EXT-CAD-001")
    assert presenca.compliance_status is ComplianceStatus.UNDETERMINED
    assert "quality.extinguisher.not_presumed (não informada)" in presenca.explanation
