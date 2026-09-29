"""Fase 3, segunda parte: hidrantes, acionador manual e saídas sobre evidência do CAD.

A mesma análise sintética (``make_fire_plan``: 1 hidrante, 1 acionador, nenhuma saída
marcada) é reaproveitada mudando só o enquadramento — que é o que decide o que verificar.
"""
from __future__ import annotations

import copy

import pytest
from coscip_evidence import Evidence, EvidenceLocator, EvidenceSet

from coscip_analysis.evidence import plant_evidence
from coscip_cbm import ComplianceStatus, EvidenceSourceType, FindingKind, ReviewStatus
from coscip_normative.verification import (
    CheckValidationError,
    FloorScope,
    ProcessContext,
    compile_verification_plan,
    execute_plan,
    load_catalog,
    parse_check,
)
from tests.integration.test_cad_evidence import CHECKS, _analyze, _by, _findings


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    return _analyze(tmp_path_factory.mktemp("sistemas"))


def com(base, **context):
    analysis = copy.deepcopy(base)
    analysis["context"] = {**analysis["context"], **context}
    return analysis


def test_hidrante_exigido_pelo_analista_e_verificado_no_pavimento(base):
    pe, achados = _findings(com(base, requires_hydrants=True))
    (declarado,) = pe.process_evidence.for_field("hydrant_requirement")
    assert declarado.source_type is EvidenceSourceType.HUMAN and declarado.located
    assert _by(achados, "HID-REQ-001").compliance_status is ComplianceStatus.COMPLIANT
    assert _by(achados, "HID-CAD-001").compliance_status is ComplianceStatus.COMPLIANT
    alcance = _by(achados, "HID-CAD-002")
    assert alcance.compliance_status is ComplianceStatus.COMPLIANT
    assert 0 < alcance.measured.value < 30 and alcance.measured.required == 30.0
    assert alcance.scope_label == "Térreo"


def test_exigencia_de_hidrante_desconhecida_fica_pendente_nunca_dispensada(base):
    _, achados = _findings(base)
    exigencia = _by(achados, "HID-REQ-001")
    assert exigencia.compliance_status is ComplianceStatus.UNDETERMINED
    assert exigencia.kind is FindingKind.DATA_MISSING
    presenca = _by(achados, "HID-CAD-001")
    assert presenca.reason_code == "APPLICABILITY_UNKNOWN"
    assert "context.effective_requirement_hydrants" in presenca.explanation


def test_hidrante_declarado_nao_exigido_nao_vira_pendencia(base):
    _, achados = _findings(com(base, requires_hydrants=False))
    for check in ("HID-CAD-001", "HID-CAD-002"):
        assert _by(achados, check).compliance_status is ComplianceStatus.NOT_APPLICABLE


def test_x_da_tabela_contrariado_pelo_analista_fica_visivel(base):
    """§30: exigência normativa, declaração e exigência efetiva convivem."""
    referencia = {"status": "INDICATIVE", "column": "A/D/E/G",
                  "source": {"document": "Decreto 42/2018", "item": "Anexo III, Tabela 2"},
                  "source_sha256": "a" * 64,
                  "measures": [{"id": "hydrants", "label": "Hidrantes", "cell": "X",
                                "status": "REQUIRED"},
                               {"id": "alarm", "label": "Alarme", "cell": "-",
                                "status": "NOT_MARKED"}]}
    pe, _ = _findings(com(base, requires_hydrants=False, requirements_reference=referencia))
    fatos = pe.context.facts
    assert fatos["context.normative_requirement_hydrants"] is True
    assert fatos["context.human_override_hydrants"] is False
    assert fatos["context.effective_requirement_hydrants"] is False
    assert pe.overrides == ("hydrants",)
    fontes = {e.source_type for e in pe.process_evidence.for_field("hydrant_requirement")}
    assert fontes == {EvidenceSourceType.NORMATIVE_TABLE, EvidenceSourceType.HUMAN}
    # Traço na tabela não é dispensa: alarme continua desconhecido.
    assert "context.effective_requirement_alarm" not in fatos


def test_acionador_manual_verificado_quando_alarme_exigido(base):
    _, achados = _findings(com(base, requires_alarm=True))
    assert _by(achados, "ALA-CAD-001").compliance_status is ComplianceStatus.COMPLIANT
    distancia = _by(achados, "ALA-CAD-002")
    assert distancia.compliance_status is ComplianceStatus.COMPLIANT
    assert distancia.measured.algorithm == "grid_dijkstra_16"


def test_saidas_nao_confirmadas_nao_concluem(base):
    _, achados = _findings(com(base, occupancy="D-2", exit_max_distance_m=40,
                               layout_defined=True))
    presenca = _by(achados, "SAI-CAD-001")
    assert presenca.compliance_status is ComplianceStatus.UNDETERMINED
    assert "context.exits_confirmed" in presenca.explanation
    assert _by(achados, "SAI-CAD-002").reason_code == "DEPENDENCY_UNDETERMINED"


def test_saida_nao_marcada_e_lacuna_de_extracao(base):
    _, achados = _findings(com(base, occupancy="D-2", exits_confirmed=True))
    presenca = _by(achados, "SAI-CAD-001")
    assert presenca.kind is FindingKind.DATA_MISSING
    assert "não localizou" in presenca.explanation


def test_apartamento_mede_da_porta_da_unidade_e_vai_ao_analista(base):
    _, achados = _findings(com(base, occupancy="A-2", exits_confirmed=True))
    assert _by(achados, "SAI-CAD-002").compliance_status is ComplianceStatus.NOT_APPLICABLE
    manual = _by(achados, "SAI-MAN-001")
    assert manual.kind is FindingKind.ANALYST_REVIEW
    assert manual.review_status is ReviewStatus.PENDING and manual.scope_label == "Térreo"


def test_ocupacao_desconhecida_nao_decide_a_distancia_ate_a_saida(base):
    _, achados = _findings(com(base, exits_confirmed=True))
    distancia = _by(achados, "SAI-CAD-002")
    assert distancia.reason_code == "APPLICABILITY_UNKNOWN"
    assert "context.occupancy" in distancia.explanation


# --- limite informado pelo analista (Anexo C da NT 2-08 está como imagem) ------------

def _saida(limite=None, medida=18.0, origem=None):
    catalog = load_catalog(CHECKS)
    fatos = {"context.unifamiliar": False, "context.occupancy": "D-2",
             "context.exits_confirmed": True, "context.layout_defined": True}
    if limite is not None:
        fatos["context.effective_exit_max_distance_m"] = limite
    if origem is not None:
        fatos["context.effective_exit_max_distance_m_source"] = origem
    ctx = ProcessContext(process_id="p", facts=fatos)
    itens = [
        Evidence(id="s1", process_id="p", source_type=EvidenceSourceType.CAD, source_id="d",
                 source_version=1, source_hash="h", locator=EvidenceLocator(entity_handle="S1"),
                 field="exit", normalized_value=True, extraction_method="CAD_SYMBOL"),
        Evidence(id="s2", process_id="p", source_type=EvidenceSourceType.CAD, source_id="d",
                 source_version=1, source_hash="h", locator=EvidenceLocator(floor_id="f1"),
                 field="exit_walk_distance_m", normalized_value=medida, unit="m",
                 uncertainty_abs=0.5, extraction_method="CAD_GEOMETRY"),
    ]
    piso = FloorScope(id="f1", label="Térreo", evidence=EvidenceSet.build("p", itens),
                      facts={"quality.region_confirmed": True, "quality.walls_detected": True,
                             "quality.recognition.complete": True,
                             "quality.exit.complete": True})
    plano = compile_verification_plan(catalog, ctx)
    achados = execute_plan(plano, catalog, EvidenceSet.build("p", ()), ctx.all_facts(),
                           floors=[piso])
    return _by(achados, "SAI-CAD-002")


def test_sem_limite_informado_a_medida_aparece_mas_nao_conclui():
    achado = _saida()
    assert achado.compliance_status is ComplianceStatus.UNDETERMINED
    assert achado.reason_code == "REQUIRED_LIMIT_MISSING"
    assert achado.missing == ("context.effective_exit_max_distance_m",)
    assert achado.evidence_ids  # a medida já apurada fica no achado


def test_limite_informado_decide_a_distancia():
    assert _saida(limite=40).compliance_status is ComplianceStatus.COMPLIANT
    fora = _saida(limite=15, origem="NT 2-08, Anexo C, linha BETA")
    assert fora.compliance_status is ComplianceStatus.NON_COMPLIANT
    assert fora.measured.required == 15.0
    assert fora.measured.required_source == "NT 2-08, Anexo C, linha BETA"


ANEXO_C_40 = {"status": "FOUND", "limit_m": 40, "row": "GAMA-CDEFHILM-DESCARGA",
              "column": "UNPROTECTED_MULTIPLE", "page": 22,
              "source": {"document": "NT 2-08", "item": "Anexo C"}}


def test_limite_da_tabela_vira_limite_efetivo_com_origem(base):
    pe = plant_evidence(com(base, exit_distance_reference=ANEXO_C_40), process_id="p")
    fatos = pe.context.facts
    assert fatos["context.normative_exit_max_distance_m"] == 40
    assert fatos["context.effective_exit_max_distance_m"] == 40
    origem = fatos["context.effective_exit_max_distance_m_source"]
    assert "Anexo C" in origem and "GAMA-CDEFHILM-DESCARGA" in origem and "p. 22" in origem
    assert pe.overrides == ()


def test_limite_do_analista_diferente_da_tabela_fica_visivel(base):
    pe = plant_evidence(com(base, exit_distance_reference=ANEXO_C_40, exit_max_distance_m=30),
                        process_id="p")
    fatos = pe.context.facts
    assert fatos["context.normative_exit_max_distance_m"] == 40
    assert fatos["context.human_override_exit_max_distance_m"] == 30
    assert fatos["context.effective_exit_max_distance_m"] == 30
    assert fatos["context.effective_exit_max_distance_m_source"] == "informado pelo analista"
    assert pe.overrides == ("exit_max_distance_m",)


def test_consulta_sem_limite_nao_inventa_limite(base):
    for sem in ({"status": "MISSING_DATA", "limit_m": None},
                {"status": "REVIEW_REQUIRED", "limit_m": None}):
        fatos = plant_evidence(com(base, exit_distance_reference=sem),
                               process_id="p").context.facts
        assert "context.effective_exit_max_distance_m" not in fatos


# --- opção B: piso de descarga não identificado → faixa de limites --------------------

POR_PISO = {"status": "DEPENDS_ON_FLOOR", "limit_m": None,
            "by_floor_m": {"DISCHARGE": 40, "OTHER": 35},
            "rows": {"DISCHARGE": "GAMA-CDEFHILM-DESCARGA", "OTHER": "GAMA-CDEFHILM-DEMAIS"},
            "column": "UNPROTECTED_MULTIPLE", "page": 22,
            "source": {"document": "NT 2-08", "item": "Anexo C"}}


def test_piso_indefinido_leva_os_dois_limites_com_origem(base):
    pe = plant_evidence(com(base, exit_distance_reference=POR_PISO), process_id="p")
    fatos = pe.context.facts
    assert fatos["context.effective_exit_max_distance_m"] == [35, 40]
    origem = fatos["context.effective_exit_max_distance_m_source"]
    assert "40 m no piso de descarga" in origem and "35 m nos demais" in origem
    assert pe.overrides == ()


def test_limite_do_analista_fora_da_faixa_fica_visivel(base):
    fora = plant_evidence(com(base, exit_distance_reference=POR_PISO, exit_max_distance_m=38),
                          process_id="p")
    assert fora.overrides == ("exit_max_distance_m",)
    assert fora.context.facts["context.effective_exit_max_distance_m"] == 38
    dentro = plant_evidence(com(base, exit_distance_reference=POR_PISO, exit_max_distance_m=40),
                            process_id="p")
    assert dentro.overrides == ()


@pytest.mark.parametrize(("medida", "status", "motivo", "exigido"), [
    (20.0, ComplianceStatus.COMPLIANT, "SATISFIED", 35.0),        # atende até o menor
    (50.0, ComplianceStatus.NON_COMPLIANT, "OUT_OF_LIMIT", 40.0),  # passa até do maior
    (37.0, ComplianceStatus.UNDETERMINED, "LIMIT_NOT_DETERMINED", 35.0),
    (34.8, ComplianceStatus.UNDETERMINED, "LIMIT_NOT_DETERMINED", 35.0),  # incerteza 0,5
    (40.3, ComplianceStatus.UNDETERMINED, "LIMIT_NOT_DETERMINED", 35.0),  # idem no maior
])
def test_faixa_de_limites_so_conclui_o_que_vale_para_os_dois(medida, status, motivo, exigido):
    achado = _saida(limite=[35, 40], medida=medida)
    assert achado.compliance_status is status
    assert achado.reason_code == motivo
    assert achado.measured.required == exigido
    assert achado.measured.required_candidates == (35.0, 40.0)
    if status is ComplianceStatus.UNDETERMINED:
        assert achado.review_status is ReviewStatus.PENDING
        assert "35 ou 40 m" in achado.explanation


def test_limite_unico_continua_como_antes():
    achado = _saida(limite=35, medida=35.2)  # incerteza 0,5 atravessa o limite
    assert achado.reason_code == "WITHIN_UNCERTAINTY"
    assert achado.measured.required_candidates == ()


def test_faixa_invalida_nao_vira_limite():
    assert _saida(limite=[35, 0]).reason_code == "REQUIRED_LIMIT_MISSING"
    assert _saida(limite=[]).reason_code == "REQUIRED_LIMIT_MISSING"


def test_pergunta_de_limite_exige_valor_ou_fato_mas_nao_os_dois():
    base_check = {
        "schema_version": "checks/1.0", "id": "X-1", "version": 1, "title": "x",
        "system": "X", "type": "CAD_DISTANCE", "publication_state": "DRAFT",
        "normative_basis": [{"document": "NT 2-08", "edition": "1", "item": "1",
                             "quote": ["x"]}],
        "wording": {"title": "x"},
    }
    for question in ({"kind": "maximum_value", "field": "d"},
                     {"kind": "maximum_value", "field": "d", "required_value": 1,
                      "required_fact": "context.x"},
                     {"kind": "presence", "field": "d", "required_fact": "context.x"}):
        with pytest.raises(CheckValidationError):
            parse_check({**base_check, "question": question})
    assert parse_check({**base_check, "question": {
        "kind": "maximum_value", "field": "d", "required_fact": "context.x"}})


def test_catalogo_inteiro_sem_enquadramento_nunca_conclui_conformidade(base):
    """Sem nada informado, nenhum check de hidrante, alarme ou saída conclui COMPLIANT."""
    pe = plant_evidence(base, process_id="p")
    assert pe.overrides == ()
    _, achados = _findings(base)
    for f in achados:
        if f.system in {"HIDRANTES", "ALARME", "SAIDAS"}:
            assert f.compliance_status is not ComplianceStatus.COMPLIANT, f.ref


# --- NT 2-08 5.3.3.3: sem leiaute, distância direta e limite reduzido em 30% -----------

@pytest.fixture(scope="module")
def com_saida(tmp_path_factory):
    """A mesma planta com o acionador (15; 1), junto à porta externa, tratado como saída."""
    from coscip_analysis import AnalysisInput, RuleBinding, parse_dictionary, run
    from coscip_cad.synthetic import make_fire_plan
    from coscip_normative.package import load_package
    from tests.integration.test_cad_evidence import BASE, TERREO

    pkg = load_package(BASE)
    dxf = make_fire_plan(tmp_path_factory.mktemp("saida") / "p.dxf")
    return run(AnalysisInput(
        dxf=dxf, scale_to_m=1.0, dictionary=parse_dictionary(pkg.symbols),
        rules=[RuleBinding(r) for r in pkg.rules],
        context={"risk_class": "PEQUENO", "unifamiliar": False, "occupancy": "D-2",
                 "exits_confirmed": True},
        floors=[{"id": "floor-0001", "name": "Térreo", "clip": TERREO}],
        symbol_overrides={"ACIONADOR_MANUAL": "SAIDA"}))


def test_motor_mede_distancia_direta_ate_a_saida(com_saida):
    (floor,) = plant_evidence(com_saida, process_id="p").floors
    (direta,) = floor.evidence.for_field("exit_direct_distance_m")
    (percurso,) = floor.evidence.for_field("exit_walk_distance_m")
    # Canto mais distante (0,15; 11,85) ou (29,85; 11,85) até (15; 1): ≈ 18,4 m.
    assert 17.5 < direta.normalized_value < 19.0
    assert direta.algorithm == "grid_euclidean_nearest" and direta.uncertainty_abs > 0
    assert direta.locator.bbox is not None
    # Linha reta nunca é maior que o percurso contornando paredes.
    assert direta.normalized_value <= percurso.normalized_value


REDUZIDO = {"status": "FOUND", "limit_m": 28, "base_limit_m": 40, "measure": "DIRECT",
            "row": "GAMA-CDEFHILM-DESCARGA", "column": "UNPROTECTED_MULTIPLE", "page": 22,
            "reduction": {"factor": 0.7, "document": "NT 2-08", "item": "5.3.3.3"},
            "source": {"document": "NT 2-08", "item": "Anexo C"}}


def test_sem_leiaute_usa_a_distancia_direta_contra_o_limite_reduzido(com_saida):
    analise = com(com_saida, layout_defined=False, exit_distance_reference=REDUZIDO)
    pe, achados = _findings(analise)
    origem = pe.context.facts["context.effective_exit_max_distance_m_source"]
    assert "reduzido em 30%" in origem and "5.3.3.3" in origem and "40 m" in origem
    direta = _by(achados, "SAI-CAD-003")
    assert direta.compliance_status is ComplianceStatus.COMPLIANT  # ≈18,4 m ≤ 28 m
    assert direta.measured.required == 28.0
    assert direta.measured.algorithm == "grid_euclidean_nearest"
    assert _by(achados, "SAI-CAD-002").compliance_status is ComplianceStatus.NOT_APPLICABLE


def test_sem_leiaute_limite_reduzido_pode_reprovar(com_saida):
    apertado = {**REDUZIDO, "limit_m": 14, "base_limit_m": 20}  # α: 20 × 0,7
    _, achados = _findings(com(com_saida, layout_defined=False,
                               exit_distance_reference=apertado))
    direta = _by(achados, "SAI-CAD-003")
    assert direta.compliance_status is ComplianceStatus.NON_COMPLIANT
    assert direta.measured.required == 14.0


def test_com_leiaute_vale_o_percurso(com_saida):
    inteiro = {**REDUZIDO, "limit_m": 40, "measure": "TRAVEL"}
    inteiro.pop("reduction")
    _, achados = _findings(com(com_saida, layout_defined=True, exit_distance_reference=inteiro))
    assert _by(achados, "SAI-CAD-003").compliance_status is ComplianceStatus.NOT_APPLICABLE
    percurso = _by(achados, "SAI-CAD-002")
    assert percurso.measured.algorithm == "grid_dijkstra_16"


def test_leiaute_desconhecido_nao_escolhe_a_medida(com_saida):
    _, achados = _findings(com_saida)
    for check in ("SAI-CAD-002", "SAI-CAD-003"):
        achado = _by(achados, check)
        assert achado.reason_code == "APPLICABILITY_UNKNOWN"
        assert "context.layout_defined" in achado.explanation
