"""Identificação sem contagem em dobro e sem omissão (plano de correção, F5).

Um DXF sintético por armadilha (``coscip_cad.synthetic.make_trap``). Cada teste afirma a
contagem exata e o motivo de cada elemento ignorado; o balanço fecha em todos: toda inserção
e todo texto curto termina em exatamente um destino.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from coscip_analysis import AnalysisInput, parse_dictionary, run
from coscip_analysis.plan import load_plan
from coscip_cad.synthetic import TRAPS, make_trap
from coscip_normative.package import load_package

BASE = Path(__file__).resolve().parents[2] / "normative" / "base"
FLOOR = [{"id": "f1", "name": "Térreo", "clip": {"x0": -1, "y0": -1, "x1": 21, "y1": 11}}]


@pytest.fixture(scope="module")
def dictionary():
    return parse_dictionary(load_package(BASE).symbols)


def analyze(tmp_path, dictionary, kind, **kw):
    dxf = make_trap(tmp_path / f"{kind}.dxf", kind)
    out = run(AnalysisInput(dxf=dxf, scale_to_m=1.0, dictionary=dictionary, rules=[],
                            context={}, floors=FLOOR, **kw))
    return out, out["recognition_ledger"], out["regions"][0]


def protective(region, cls):
    return [s for s in region["symbols"] if s["class"] == cls and s["excluded"] is None]


@pytest.mark.parametrize("kind", TRAPS)
def test_balance_closes_for_every_trap(tmp_path, dictionary, kind):
    kw = {"legend_regions": [[29, 6, 31, 9]]} if kind == "legenda" else {}
    out, ledger, _ = analyze(tmp_path, dictionary, kind, **kw)
    plan = load_plan(tmp_path / f"{kind}.dxf", 1.0)
    short = [t for t in plan.texts if len(t.text) <= 40]
    skipped_ins = [s for s in plan.skipped if s.entity_type == "INSERT"]
    skipped_txt = [s for s in plan.skipped if s.entity_type in {"TEXT", "MTEXT", "ATTRIB"}]
    assert ledger["inserts"]["total"] == len(plan.inserts) + len(skipped_ins)
    assert sum(ledger["inserts"]["by_destination"].values()) == ledger["inserts"]["total"]
    assert ledger["short_texts"]["total"] == len(short) + len(skipped_txt)
    assert sum(ledger["short_texts"]["by_destination"].values()) == ledger["short_texts"]["total"]
    keys = [s["object_key"] for s in out["regions"][0]["symbols"] if s["excluded"] is None]
    assert len(keys) == len(set(keys)), "objeto contado duas vezes"


def test_minsert_expands_every_cell(tmp_path, dictionary):
    _, ledger, region = analyze(tmp_path, dictionary, "minsert")
    ext = protective(region, "EXTINTOR")
    assert len(ext) == 1 + 12  # referência + matriz 3×4
    handles = {s["handle"] for s in ext}
    assert len(handles) == 13 and any("#2,3" in h for h in handles)
    assert ledger["inserts"]["by_destination"] == {"RECOGNIZED:EXTINTOR": 13}


def test_layer_off_frozen_and_no_plot_are_ignored_with_reason(tmp_path, dictionary):
    _, ledger, region = analyze(tmp_path, dictionary, "camada")
    assert len(protective(region, "EXTINTOR")) == 1
    assert protective(region, "SAIDA") == []
    assert ledger["inserts"]["by_destination"] == {
        "IGNORED:LAYER_FROZEN": 1, "IGNORED:LAYER_NO_PLOT": 1, "IGNORED:LAYER_OFF": 1,
        "RECOGNIZED:EXTINTOR": 1}
    assert ledger["short_texts"]["by_destination"] == {"IGNORED:LAYER_OFF": 1}


def test_duplicate_block_at_same_point_is_one_object(tmp_path, dictionary):
    _, ledger, region = analyze(tmp_path, dictionary, "duplicado")
    ext = protective(region, "EXTINTOR")
    assert len(ext) == 3  # (2,2), (8,5) com duas cópias, (9,5) a 1 m é outro objeto
    keeper = next(s for s in ext if math.isclose(s["x"], 8, abs_tol=0.1))
    assert len(keeper["attrs"]["duplicates"]) == 2
    assert ledger["inserts"]["by_destination"]["IGNORED:DUPLICATE"] == 2


def test_exit_block_text_and_s12_sign_are_one_exit(tmp_path, dictionary):
    _, ledger, region = analyze(tmp_path, dictionary, "saida")
    (exit_,) = protective(region, "SAIDA")
    assert exit_["block"] == "SAIDA_EMERGENCIA"
    assert any("S-12" in e for e in exit_["attrs"]["merged_evidence"])
    assert "SAÍDA" in exit_["attrs"]["labels"]
    assert ledger["short_texts"]["by_destination"] == {"IGNORED:TEXT_AS_ATTRIBUTE": 1}


def test_nested_unknown_block_in_safety_layer_blocks_conclusion(tmp_path, dictionary):
    _, ledger, region = analyze(tmp_path, dictionary, "aninhado")
    nested = [u for u in ledger["unrecognized_blocks"] if u["block"] == "SUB_Y"]
    assert nested == [{"block": "SUB_Y", "layer": "INC_DIVERSOS", "depth": 2, "count": 1,
                       "safety_layer": True}]
    assert not ledger["complete"]
    assert region["facts"]["quality.recognition.complete"]["value"] is False


def test_exploded_extinguisher_is_review_candidate_never_symbol(tmp_path, dictionary):
    _, ledger, region = analyze(tmp_path, dictionary, "explodido")
    assert len(protective(region, "EXTINTOR")) == 1
    (cand,) = ledger["exploded_candidates"]
    assert cand["text"] == "PQS 6KG"
    assert region["facts"]["quality.recognition.complete"]["value"] is False


def test_xref_blocks_conclusion(tmp_path, dictionary):
    _, ledger, region = analyze(tmp_path, dictionary, "xref")
    assert ledger["xrefs"] == ["ARQ_XREF"]
    assert ledger["inserts"]["by_destination"]["IGNORED:XREF"] == 1
    assert not ledger["complete"]
    assert region["facts"]["quality.xref_resolved"]["value"] is False


def test_attrib_gives_agent_and_is_not_loose_text(tmp_path, dictionary):
    _, ledger, region = analyze(tmp_path, dictionary, "atributo")
    ext = protective(region, "EXTINTOR")
    tagged = next(s for s in ext if s["block"] == "EXTINTOR_TAG")
    assert tagged["attrs"]["agent"] == "CO2" and tagged["attrs"]["capacity"] == "6 kg"
    assert protective(region, "SAIDA") == []  # "SAÍDA" era atributo, não placa
    assert ledger["short_texts"]["by_destination"] == {"IGNORED:ATTRIBUTE": 2}


def test_legend_marked_by_analyst_has_priority(tmp_path, dictionary):
    out, ledger, region = analyze(tmp_path, dictionary, "legenda",
                                  legend_regions=[[29, 6, 31, 9]])
    assert len(protective(region, "EXTINTOR")) == 1
    assert ledger["inserts"]["by_destination"]["IGNORED:LEGEND"] == 2
    assert all(s["attrs"]["legend_source"] == "analista" for s in out["legend_symbols"])


@settings(max_examples=12, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(theta=st.floats(0, 2 * math.pi), mirror=st.booleans(),
       dx=st.floats(-500, 500), dy=st.floats(-500, 500), scale=st.sampled_from([1.0, 1000.0]))
def test_counts_invariant_under_rigid_transform(tmp_path, dictionary, theta, mirror, dx, dy,
                                                scale):
    """Espelhar, rotacionar, escalar (unidade) e transladar não muda a contagem nem o
    número de objetos distintos."""
    import ezdxf
    from ezdxf.math import Matrix44

    src = make_trap(tmp_path / "base.dxf", "duplicado")
    doc = ezdxf.readfile(src)
    m = (Matrix44.scale(-scale if mirror else scale, scale, 1) @ Matrix44.z_rotate(theta)
         @ Matrix44.translate(dx * scale, dy * scale, 0))
    for e in doc.modelspace():
        e.transform(m)
    moved = tmp_path / "moved.dxf"
    doc.saveas(moved)
    out = run(AnalysisInput(dxf=moved, scale_to_m=1 / scale, dictionary=dictionary, rules=[],
                            context={}, floors=[]))
    ext = [s for s in (*out["symbols_outside_regions"],
                       *(x for r in out["regions"] for x in r["symbols"]))
           if s["class"] == "EXTINTOR" and s["excluded"] is None]
    keys = {s["object_key"] for s in ext}
    assert len(ext) == 3 and len(keys) == 3
    assert out["recognition_ledger"]["inserts"]["by_destination"]["IGNORED:DUPLICATE"] == 2
