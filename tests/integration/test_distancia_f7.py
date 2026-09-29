"""Cálculo determinístico com incerteza mínima (plano de correção, F7).

Aceite: em DXFs sintéticos com resposta analítica conhecida (corredor em L, sala com pilar,
duas portas), o método vetorial acerta com erro ≤ 0,05 m e incerteza declarada ≤ 0,15 m; o
FMM concorda; divergência entre os métodos fecha a porta ``quality.geometry.consistent``;
a mesma entrada dá a mesma saída (hash canônico).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from coscip_evidence import Evidence, EvidenceLocator, EvidenceSet

from coscip_analysis import AnalysisInput, RuleBinding, parse_dictionary, run
from coscip_analysis.vector_paths import VECTOR_ALGORITHM
from coscip_cad.synthetic import ANALYTIC, make_analytic
from coscip_cbm import ComplianceStatus, EvidenceSourceType
from coscip_normative.package import load_package
from coscip_normative.verification import load_catalog
from coscip_normative.verification.executor import execute_check
from tools.ci import determinismo

ROOT = Path(__file__).resolve().parents[2]
CLIP = [{"id": "f", "name": "Pavimento", "clip": {"x0": -1, "y0": -1, "x1": 25, "y1": 20}}]
PARCELAS = {"metodo", "amostragem", "posicao_do_simbolo", "unidade_escala",
            "modelagem_de_parede", "total"}


@pytest.fixture(scope="module")
def pkg():
    return load_package(ROOT / "normative" / "base")


def _run(pkg, dxf: Path, **extra):
    return run(AnalysisInput(
        dxf=dxf, scale_to_m=1.0, dictionary=parse_dictionary(pkg.symbols),
        rules=[RuleBinding(r) for r in pkg.rules],
        context={"risk_class": "PEQUENO", "unifamiliar": False, "building_area_m2": 360},
        floors=CLIP, **extra))


@pytest.fixture(scope="module", params=ANALYTIC)
def analitico(request, pkg, tmp_path_factory):
    path, exact, worst = make_analytic(
        tmp_path_factory.mktemp(request.param) / "p.dxf", request.param)
    (region,) = _run(pkg, path)["regions"]
    return request.param, exact, worst, region


def test_vetorial_acerta_a_resposta_analitica(analitico):
    kind, exact, worst, region = analitico
    cov = region["coverage"]["extinguisher"]
    assert cov["algorithm"] == VECTOR_ALGORITHM
    assert abs(cov["max_travel_m"] - exact) <= 0.05, (kind, cov["max_travel_m"], exact)
    assert cov["uncertainty_m"] <= 0.15
    # o valor exato cabe na faixa declarada
    assert abs(cov["max_travel_m"] - exact) <= cov["uncertainty_m"]
    assert all(abs(a - b) <= 0.1 for a, b in zip(cov["worst_point"], worst, strict=True))


def test_orcamento_de_incerteza_explicito(analitico):
    _, _, _, region = analitico
    budget = region["coverage"]["extinguisher"]["uncertainty_budget"]
    assert set(budget) == PARCELAS
    assert all(budget[k]["origem"] for k in PARCELAS)
    assert budget["metodo"]["m"] == 0.0  # menor caminho exato
    assert budget["amostragem"]["m"] <= 0.05
    # posição do símbolo = metade do tamanho do bloco (círculo de 10 cm), não 0,30 m fixo
    assert budget["posicao_do_simbolo"]["m"] < 0.1
    soma = sum(budget[k]["m"] for k in PARCELAS - {"total"})
    assert soma <= budget["total"]["m"] < soma + 0.001  # soma arredondada para cima


def test_fmm_e_grade_conferem(analitico):
    kind, exact, _, region = analitico
    cov = region["coverage"]["extinguisher"]
    methods = cov["methods"]
    assert {"grid", "fmm", "vector"} <= set(methods)
    fmm = methods["fmm"]
    assert abs(fmm["value_m"] - exact) <= fmm["uncertainty_m"], kind
    assert cov["consistent"] is True
    assert region["facts"]["quality.geometry.consistent"]["value"] is True
    # a grade continua como conferência, com a incerteza larga de sempre
    assert methods["grid"]["uncertainty_m"] > cov["uncertainty_m"]


def test_escala_nao_confirmada_entra_no_orcamento(pkg, tmp_path):
    path, _, _ = make_analytic(tmp_path / "p.dxf", "corredor_l")
    (region,) = _run(pkg, path, scale_rel_uncertainty=0.005)["regions"]
    budget = region["coverage"]["extinguisher"]["uncertainty_budget"]
    assert budget["unidade_escala"]["m"] == pytest.approx(0.005 * 30.19, abs=0.01)


def test_divergencia_entre_metodos_nao_conclui():
    catalog = load_catalog(ROOT / "normative" / "checks")
    check = catalog.get("EXT-CAD-003-PEQUENO")
    medida = Evidence(
        id="d", process_id="p", source_type=EvidenceSourceType.CAD, source_id="dxf",
        source_version=1, source_hash="h" * 8, field="extinguisher_walk_distance_m",
        normalized_value=10.0, unit="m", uncertainty_abs=0.1, extraction_method="GEOMETRY",
        algorithm=VECTOR_ALGORITHM, locator=EvidenceLocator(floor_id="f", bbox=(1, 1, 1, 1)))
    gates = {"quality.region_confirmed": True, "quality.walls_detected": True,
             "quality.recognition.complete": True, "quality.extinguisher.complete": True,
             "context.risk_class": "PEQUENO", "context.unifamiliar": False}
    ok = execute_check(check, EvidenceSet.build("p", [medida]),
                       {**gates, "quality.geometry.consistent": True})
    assert ok.compliance_status is ComplianceStatus.COMPLIANT
    diverge = execute_check(check, EvidenceSet.build("p", [medida]),
                            {**gates, "quality.geometry.consistent": False})
    assert diverge.compliance_status is ComplianceStatus.UNDETERMINED
    assert "quality.geometry.consistent" in diverge.explanation


def test_mesma_entrada_mesma_saida(tmp_path):
    """F7.4: a análise não depende da ordem de dicionário/conjunto (semente de hash)."""
    out = {}
    for seed in ("1", "2"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        dest = tmp_path / f"seed-{seed}.json"
        subprocess.run([sys.executable, "-m", "tools.ci.determinismo", "--out", str(dest)],
                       check=True, env=env, cwd=ROOT, capture_output=True)
        out[seed] = json.loads(dest.read_text("utf-8"))
    assert set(out["1"]) == {"fire_plan", *ANALYTIC}
    for name in out["1"]:
        assert out["1"][name]["dxf_sha256"] == out["2"][name]["dxf_sha256"]
        assert out["1"][name]["analysis_sha256"] == out["2"][name]["analysis_sha256"], name
    assert determinismo.compare([tmp_path / "seed-1.json", tmp_path / "seed-2.json"]) == 0
    # o hash canônico ignora só o tempo de relógio
    a = {"x": 1, "duration_s": 0.1, "y": [{"duration_s": 2, "z": 1.5}]}
    b = {"y": [{"z": 1.5, "duration_s": 9}], "x": 1, "duration_s": 3}
    assert determinismo.digest(a) == determinismo.digest(b)
    assert json.loads(json.dumps(determinismo.canonical(a))) == {"x": 1, "y": [{"z": 1.5}]}
