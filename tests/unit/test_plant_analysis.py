"""Análise automática da planta, base normativa e DSL rules/1.1 (dados 100 % sintéticos)."""

from __future__ import annotations

from pathlib import Path

import pytest

from coscip_analysis import AnalysisInput, RuleBinding, parse_dictionary, run
from coscip_cad import DxfReader
from coscip_cad.synthetic import make_fire_plan
from coscip_cbm import EvaluationStatus
from coscip_normative import parse_markdown, verify_citation
from coscip_normative.package import load_package, verify_package
from coscip_rules.dsl import RuleValidationError, parse_rule
from coscip_rules.engine import EvaluationContext, Fact, evaluate

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "normative" / "base"

# Trechos sintéticos no formato das conversões das NTs (front matter + páginas).
NT_201 = """---
documento: "NT-2-01"
titulo: "NT 2-01 - Extintores (trecho de teste)"
edicao: "2ª edição - 2020"
sha256_pdf: "0000"
---

## Página 3

4.5 Distância máxima a ser percorrida: distância máxima real, em metros, do ponto de fixação \
do extintor a qualquer ponto da área protegida. Devem ser considerados todos os obstáculos \
arquitetônicos, mobiliários e etc.

## Página 4

5.2.4 É permitida a instalação de uma única unidade extintora de pó ABC em edificações do \
risco pequeno com área inferior a 50 m².

5.2.5 Os extintores devem ser adequados, de forma que haja, no mínimo, 02 (dois) extintores \
de incêndio.

## Página 5

6.4 Para instalações especiais, tais como casa de máquinas, casa de bombas, devendo os \
referidos extintores não distar mais do que 5 m da instalação a proteger.

| Tabela 3 - Determinação da unidade extintora mínima |  |
| Extintor / risco | Pequeno | Médio | Grande |
| Área máxima protegida por 01 (uma) unidade extintora | 250 m² | 150 m² | 100 m² |
| Distância máxima percorrida | 20 m | 15 m | 10 m |
"""


def _sources():
    t = parse_markdown(NT_201.encode("utf-8"), "nt-2-01.md")
    return {t.document: t}


def test_ingest_indexes_items_pages_and_hash():
    t = parse_markdown(NT_201.encode("utf-8"), "x.md")
    assert t.document == "NT 2-01" and t.edition.startswith("2ª")
    assert {"4.5", "5.2.4", "5.2.5", "6.4", "Tabela 3"} <= set(t.items)
    assert t.items["Tabela 3"][0].page == 5 and t.items["5.2.4"][0].page == 4
    assert len(t.text_sha256) == 64


def test_citation_requires_every_quoted_term():
    src = _sources()
    ok = verify_citation(src, "NT-2-01", "Tabela 3", ("Distância máxima percorrida", "20 m"))
    assert ok.verified and ok.page == 5 and "20 m" in ok.excerpt
    bad = verify_citation(src, "NT 2-01", "Tabela 3", ("25 m",))
    assert not bad.verified and bad.missing_terms == ("25 m",)
    assert verify_citation(src, "NT 2-01", "9.9").problem == "item não encontrado no texto"
    assert verify_citation(src, "NT 2-02", "5.6.1").problem == "documento ausente da base"


def test_multipart_document_ids_do_not_collide():
    a = parse_markdown(b'---\ndocumento: "NT-2-03-PARTE-1"\n---\n5.1 Texto\n', "a.md")
    b = parse_markdown(b'---\ndocumento: "NT-2-03-PARTE-2"\n---\n5.1 Texto\n', "b.md")
    assert (a.document, b.document) == ("NT 2-03 P1", "NT 2-03 P2")


def test_bundled_package_loads_and_refuses_unverifiable_citations():
    pkg = load_package(BASE)
    assert pkg.publication_state == "DRAFT"
    assert not any(r.production_eligible for r in pkg.rules)
    rep = verify_package(pkg, _sources())
    # Só a NT 2-01 sintética está na base: as demais citações não podem passar.
    assert not rep["verified"]
    assert any("NT 2-02" in f and "ausente" in f for f in rep["failures"])
    ext = next(r for r in rep["rules"] if r["id"] == "NT201_EXT_DISTANCIA")
    assert all(c["verified"] for c in ext["citations"])


def test_rules_11_require_quote_terms_and_single_required_form():
    data = load_package(BASE).rules[0].model_dump(mode="json")
    data["source"]["quote"] = []
    with pytest.raises(RuleValidationError, match="sem termos"):
        parse_rule(data)
    data = load_package(BASE).rules[0].model_dump(mode="json")
    data["calculation"]["required"] = {"value": 1, "table": {"key": "context.risk_class",
                                                             "values": {"PEQUENO": 1}}}
    with pytest.raises(RuleValidationError, match="exatamente um"):
        parse_rule(data)


def _rule(rule_id: str):
    return next(r for r in load_package(BASE).rules if r.id == rule_id)


def test_required_table_and_ceil_div_are_traced():
    rule = _rule("NT201_EXT_AREA")
    facts = {"floor.count.extinguishers": Fact(2, 0.0), "floor.area_m2": Fact(301, 5.0),
             "context.risk_class": Fact("MEDIO"), "context.unifamiliar": Fact(False),
             "quality.walls_detected": Fact(True), "quality.region_confirmed": Fact(True)}
    out = evaluate(rule, EvaluationContext("f", facts))
    assert out.status is EvaluationStatus.FAIL
    assert out.trace["required"] == "3" and "⌈" in out.trace["required_steps"][-1]
    facts["context.risk_class"] = Fact("DESCONHECIDO")
    out = evaluate(rule, EvaluationContext("f", facts))
    assert out.status is EvaluationStatus.MISSING_DATA
    assert out.reason_code == "REQUIRED_TABLE_KEY_UNKNOWN"


def test_quality_gate_keeps_indicative_verdict():
    rule = _rule("NT201_EXT_DISTANCIA")
    facts = {"floor.extinguisher.max_travel_m": Fact(25.0, 1.0),
             "context.risk_class": Fact("PEQUENO"), "context.unifamiliar": Fact(False),
             "quality.walls_detected": Fact(True), "quality.region_confirmed": Fact(False),
             "quality.extinguisher.complete": Fact(True)}
    out = evaluate(rule, EvaluationContext("f", facts))
    assert out.status is EvaluationStatus.REVIEW_REQUIRED
    assert out.reason_code == "QUALITY_GATE_NOT_MET" and out.trace["indicative"] == "FAIL"


def test_reader_skips_hidden_visibility_states(tmp_path):
    p = make_fire_plan(tmp_path / "p.dxf")
    reader = DxfReader()
    names = [e.block_name for e in reader.entities(reader.open(p)) if e.entity_type == "INSERT"]
    assert "LUMINARIA_EMERG_NOVA" in names and "LUMINARIA_EMERG_DEMOLIR" not in names
    assert reader.invisible_skipped == 1


def _analyze(tmp_path: Path, *, floors=True, context=None, scale=1.0):
    pkg = load_package(BASE)
    p = make_fire_plan(tmp_path / "p.dxf", scale=scale)
    clip = {"x0": -1 * scale, "y0": -1 * scale, "x1": 31 * scale, "y1": 13 * scale}
    inp = AnalysisInput(
        dxf=p, scale_to_m=1.0 / scale, dictionary=parse_dictionary(pkg.symbols),
        rules=[RuleBinding(r) for r in pkg.rules],
        context=context or {"risk_class": "PEQUENO", "unifamiliar": False},
        floors=[{"id": "floor-0001", "name": "Térreo", "clip": clip}] if floors else [])
    return run(inp)


def _result(out, rule_id, subject_type="FLOOR"):
    return [r for r in out["results"] if r["rule_id"] == rule_id
            and r["subject_type"] == subject_type]


def test_plan_analysis_counts_symbols_and_excludes_legend(tmp_path):
    out = _analyze(tmp_path)
    region = out["regions"][0]
    assert region["counts"]["EXTINTOR"] == 2
    assert region["counts"]["ILUMINACAO_EMERGENCIA"] == 1  # estado oculto ignorado
    assert out["symbol_totals"]["EXTINTOR"]["legend"] == 1
    ext = [s for s in region["symbols"] if s["class"] == "EXTINTOR"]
    assert all(s["attrs"].get("agent") == "PQS_ABC" and s["handle"] for s in ext)
    assert region["geometry"]["walls_detected"]
    assert 320 < region["geometry"]["interior_m2"] < 350


def test_travel_distance_uses_walls_and_risk_table(tmp_path):
    small = _result(_analyze(tmp_path), "NT201_EXT_DISTANCIA")[0]
    assert small["status"] == "PASS"
    # Pior ponto na casa de bombas: contorna a divisória pela porta; > linha reta (~10,6 m).
    assert 11.0 < small["trace"]["measured"] < 13.5
    big = _result(_analyze(tmp_path, context={"risk_class": "GRANDE", "unifamiliar": False}),
                  "NT201_EXT_DISTANCIA")[0]
    assert big["status"] == "FAIL" and big["trace"]["required"] == "10"


def test_special_room_signs_and_area_checks(tmp_path):
    out = _analyze(tmp_path)
    room = _result(out, "NT201_EXT_INSTALACAO_ESPECIAL", "ROOM")[0]
    assert room["subject_label"] == "CASA DE BOMBAS" and room["status"] == "FAIL"
    signs = {r["status"] for r in _result(out, "NT205_PLACA_EXTINTOR", "SYMBOL")}
    assert signs == {"PASS", "REVIEW_REQUIRED"}  # sem placa → revisão, nunca FAIL
    checks = {c["label"]: c["status"] for c in out["regions"][0]["area_checks"]}
    assert checks == {"SALA 01": "CONFERE", "DEPÓSITO": "DIVERGE"}
    exit_rule = _result(out, "NT208_SAIDA_DISTANCIA")[0]
    assert exit_rule["status"] == "MISSING_DATA"  # limite do Anexo C não informado


def test_same_plan_in_millimetres_gives_same_measurements(tmp_path):
    m = _result(_analyze(tmp_path), "NT201_EXT_DISTANCIA")[0]["trace"]["measured"]
    mm = _result(_analyze(tmp_path, scale=1000), "NT201_EXT_DISTANCIA")[0]["trace"]["measured"]
    assert abs(m - mm) < 0.3


def test_auto_regions_without_floor_stay_in_review(tmp_path):
    out = _analyze(tmp_path, floors=False)
    plans = [r for r in out["regions"] if r["kind"] == "PLAN"]
    assert len(plans) == 1 and plans[0]["source"] == "AUTO"
    assert plans[0]["name"] == "PLANTA BAIXA - TÉRREO"
    dist = _result(out, "NT201_EXT_DISTANCIA")[0]
    assert dist["status"] == "REVIEW_REQUIRED" and dist["trace"]["indicative"] == "PASS"
    assert any("automaticamente" in w for w in out["warnings"])
