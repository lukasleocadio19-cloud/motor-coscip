"""Base normativa + análise da planta pela API, com worker real e relatório (sintético)."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest
import yaml

from coscip_api import normative_base, plant_findings
from coscip_cad.synthetic import make_fire_plan
from tests.integration.test_drawings import JUST, Env
from tests.unit.test_exit_distances import NT_208
from tests.unit.test_plant_analysis import BASE, NT_201
from tests.unit.test_requirements import requirement_sources

NT201_RULES = ("NT201_EXT_DISTANCIA", "NT201_EXT_AREA", "NT201_EXT_MINIMO",
               "NT201_EXT_INSTALACAO_ESPECIAL")


@pytest.fixture
def env(tmp_path):
    e = Env(tmp_path / "data", "tok")
    yield e
    e.close()


def _nt201_package(tmp: Path) -> Path:
    """Pacote só com as regras da NT 2-01 (a única NT desta base de teste)."""
    root = tmp / "pacote"
    (root / "regras").mkdir(parents=True)
    raw = yaml.safe_load((BASE / "pacote.yaml").read_text(encoding="utf-8"))
    raw["rules"] = [f"regras/{r}.yaml" for r in NT201_RULES]
    raw.pop("requirements", None)
    raw.pop("requirements_height", None)  # Tabelas 5–21 do Decreto, ausente desta base
    raw.pop("exit_distances", None)  # cita a NT 2-08, ausente desta base
    raw.pop("classification", None)  # a tabela cita a NT 1-04, ausente desta base
    raw["coverage"] = [c for c in raw["coverage"] if c["document"] == "NT 2-01"
                       and c["item"] in {"5.2.4", "6.4"}]
    for r in NT201_RULES:
        shutil.copy(BASE / "regras" / f"{r}.yaml", root / "regras")
    sym = yaml.safe_load((BASE / "simbolos.yaml").read_text(encoding="utf-8"))
    sym.pop("source")
    (root / "simbolos.yaml").write_text(yaml.safe_dump(sym, allow_unicode=True), "utf-8")
    (root / "pacote.yaml").write_text(yaml.safe_dump(raw, allow_unicode=True), "utf-8")
    return root


def _ingest(env: Env, text: str = NT_201):
    return env.tc.post("/v1/normative/sources", headers=env.h,
                       files=[("files", ("nt-2-01.md", text.encode("utf-8"), "text/markdown"))])


def _wait(env: Env, execution_id: str) -> dict:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        ex = env.get(f"/v1/executions/{execution_id}").json()
        if ex["state"] not in ("QUEUED", "RUNNING"):
            return ex
        time.sleep(0.3)
    raise AssertionError("análise não terminou")


def test_sources_are_ingested_once_and_bundled_package_needs_every_nt(env):
    first = _ingest(env)
    assert first.status_code == 201, first.text
    assert first.json()["items"][0]["status"] == "INGESTED"
    assert _ingest(env).json()["items"][0]["status"] == "ALREADY_PRESENT"
    items = env.get("/v1/normative/sources").json()["items"]
    assert [i["document"] for i in items] == ["NT 2-01"] and items[0]["current"]
    r = env.post("/v1/rule-packages/import")
    assert r.status_code == 422 and r.json()["code"] == "CITATIONS_NOT_VERIFIED"
    assert any("NT 2-02" in f for f in r.json()["details"]["failures"])
    bad = env.tc.post("/v1/normative/sources", headers=env.h,
                      files=[("files", ("x.pdf", b"%PDF", "application/pdf"))])
    assert bad.status_code == 422


def test_plant_analysis_end_to_end(env, tmp_path, monkeypatch):
    package_dir = _nt201_package(tmp_path)
    manifest_path = package_dir / "pacote.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["requirements"] = "sistemas-exigidos.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    shutil.copy(BASE / "sistemas-exigidos.yaml", package_dir)
    manifest["exit_distances"] = "distancias-saida.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    shutil.copy(BASE / "distancias-saida.yaml", package_dir)
    table = yaml.safe_load((BASE / "sistemas-exigidos.yaml").read_text(encoding="utf-8"))
    decree = requirement_sources(table)["Decreto 42/2018"]
    assert _ingest(env, decree.text).status_code == 201
    assert env.tc.post("/v1/normative/sources", headers=env.h, files=[(
        "files", ("nt-2-08.md", NT_208.encode("utf-8"), "text/markdown"))]).status_code == 201
    monkeypatch.setattr(normative_base, "BUNDLED_BASE", package_dir)
    assert _ingest(env).status_code == 201
    pkg = env.post("/v1/rule-packages/import")
    assert pkg.status_code == 201, pkg.text
    pkg_id = pkg.json()["id"]
    assert env.post("/v1/rule-packages/import").json()["status"] == "ALREADY_PRESENT"

    rev, states = env.import_revision([make_fire_plan(tmp_path / "ppci.dxf")])
    d = env.get(f"/v1/revisions/{rev}/drawings").json()["items"][0]
    context = {"risk_class": "PEQUENO", "occupancy": "D-2", "building_area_m2": 396,
               "building_floors": 1, "single_occupancy": True, "requires_lighting": False}
    query = env.post(f"/v1/rule-packages/{pkg_id}/requirements-query", context)
    assert query.status_code == 200 and query.json()["column"] == "A/D/E/G"
    assert env.post(f"/v1/rule-packages/{pkg_id}/requirements-query",
                    {**context, "building_floors": 1.5}).status_code == 422
    assert env.post("/v1/rule-packages/unknown/requirements-query", context).status_code == 422
    body = {"rule_package_id": pkg_id, "context": context}
    blocked = env.post(f"/v1/drawings/{d['id']}/plant-analyses", body)
    assert blocked.status_code == 409 and blocked.json()["code"] == "DRAWING_UNIT_UNCONFIRMED"

    ok = env.post(f"/v1/drawings/{d['id']}/unit-confirmation", {
        "unit": "m", "reference_a": {"x": 0, "y": 0}, "reference_b": {"x": 14, "y": 0},
        "real_length_m": 14.0, "justification": JUST})
    assert ok.status_code == 201, ok.text
    assert env.post(f"/v1/drawings/{d['id']}/floors", {
        "name": "Térreo", "clip": {"x0": -1, "y0": -1, "x1": 31, "y1": 13}}).status_code == 201
    opts = env.get(f"/v1/drawings/{d['id']}/plant-analysis-options").json()
    assert opts["packages"][0]["id"] == pkg_id and opts["floors"][0]["name"] == "Térreo"
    assert any(lay["name"] == "PAREDE" and lay["suggested_obstacle"] for lay in opts["layers"])
    wrong = env.post(f"/v1/drawings/{d['id']}/plant-analyses",
                     {**body, "symbol_overrides": {"X": "NAO_EXISTE"}})
    assert wrong.status_code == 422

    started = env.post(f"/v1/drawings/{d['id']}/plant-analyses", body)
    assert started.status_code == 202, started.text
    assert _wait(env, started.json()["execution_id"])["state"] == "SUCCEEDED"
    a = env.get(f"/v1/plant-analyses/{started.json()['analysis_id']}").json()
    assert a["state"] == "SUCCEEDED" and a["summary"]["plan_regions"] == 1
    assert a["context"]["requirements_reference"]["column"] == "A/D/E/G"
    assert a["context"]["requires_lighting"] is False
    # Anexo C conferido no pacote: faltam os dados de linha/coluna neste formulário.
    assert a["context"]["exit_distance_reference"]["status"] == "MISSING_DATA"
    exit_ctx = {**context, "construction_type": "GAMA", "sprinklers_or_detection": False,
                "multiple_exits": True, "layout_defined": True}
    found = env.post(f"/v1/rule-packages/{pkg_id}/exit-distance-query", exit_ctx).json()
    assert found["status"] == "FOUND" and found["limit_m"] == 40 and found["page"] == 22
    assert env.post(f"/v1/rule-packages/{pkg_id}/exit-distance-query",
                    {**exit_ctx, "construction_type": "DELTA"}).status_code == 422
    results = env.get(f"/v1/analyses/{a['id']}/results").json()["items"]
    by_rule = {r["values"]["rule_id"]: r["status"] for r in results
               if r["values"]["subject_type"] != "SYMBOL"}
    assert by_rule == {"NT201_EXT_DISTANCIA": "PASS", "NT201_EXT_AREA": "PASS",
                       "NT201_EXT_MINIMO": "PASS", "NT201_EXT_INSTALACAO_ESPECIAL": "FAIL"}
    _v2_findings_from_stored_analysis(env, a["id"], tmp_path)

    report = env.get(a["reports"][0]["content_url"])
    assert report.status_code == 200
    assert report.headers["X-Content-SHA256"] == a["reports"][0]["sha256"]
    html = report.text
    assert "Análise automática da planta" in html and "CASA DE BOMBAS" in html
    assert "Referência do Anexo III" in html and "A/D/E/G" in html
    assert "Não assinalado nesta tabela" in html and "396" in html
    assert "Divergência:" in html and "Iluminação" in html
    assert "sem valor normativo" in html and "<svg" in html and "<script" not in html
    again = env.post(f"/v1/plant-analyses/{a['id']}/reports")
    assert again.status_code == 201 and again.json()["id"] != a["reports"][0]["id"]

    # Revisão humana: append-only, com veredito, e refletida na nova emissão.
    special = next(r for r in results if r["values"]["rule_id"] == "NT201_EXT_INSTALACAO_ESPECIAL")
    bad = env.post(f"/v1/results/{special['id']}/reviews",
                   {"decision": "CONTEST", "justification": "sem veredito"})
    assert bad.status_code == 422 and bad.json()["code"] == "INVALID_REVIEW"
    assert env.post(f"/v1/results/{special['id']}/reviews", {
        "decision": "REQUEST_DATA", "justification": "pedir planta de detalhe"}).status_code == 201
    assert env.post(f"/v1/results/{special['id']}/reviews", {
        "decision": "CONTEST", "final_status": "PASS",
        "justification": "extintor junto à porta da casa de bombas no detalhe"}).status_code == 201
    state = env.get(f"/v1/plant-analyses/{a['id']}/reviews").json()["items"]
    item = next(v for v in state.values() if v["result_id"] == special["id"])
    assert [d["decision"] for d in item["decisions"]] == ["CONTEST", "REQUEST_DATA"]
    assert item["status"] == "FAIL" and item["decisions"][0]["final_status"] == "PASS"
    third = env.post(f"/v1/plant-analyses/{a['id']}/reports").json()
    assert third["reviewed"] == 1
    html = env.get(third["content_url"]).text
    assert "extintor junto à porta da casa de bombas" in html and "contestado" in html
    assert env.get(f"/v1/plant-analyses/{a['id']}").json()["reports"][0]["reviewed"] == 1


def _extinguisher_catalog(tmp: Path) -> Path:
    """Só os checks de extintor: a base de teste tem apenas a NT 2-01."""
    root = tmp / "checks"
    shutil.copytree(plant_findings.CHECKS_DIR / "extintores", root / "extintores")
    raw = yaml.safe_load((plant_findings.CHECKS_DIR / "catalogo.yaml").read_text("utf-8"))
    raw["checks"] = [c for c in raw["checks"] if c.startswith("extintores/")]
    (root / "catalogo.yaml").write_text(yaml.safe_dump(raw, allow_unicode=True), "utf-8")
    return root


def _v2_findings_from_stored_analysis(env: Env, analysis_id: str, tmp: Path) -> None:
    """Fase 3: a análise gravada vira Finding lendo o analysis.json, não o relatório."""
    st = env.tc.app.state.coscip
    # O catálogo inteiro cita NTs ausentes desta base: recusado, nunca executado pela metade.
    with pytest.raises(plant_findings.VerificationRefused) as refused:
        plant_findings.findings_for_analysis(st.session_factory, st.storage, analysis_id)
    assert any("NT 2-04" in d for d in refused.value.details)
    with pytest.raises(LookupError):
        plant_findings.findings_for_analysis(st.session_factory, st.storage, "nao-existe")

    out = plant_findings.findings_for_analysis(
        st.session_factory, st.storage, analysis_id, checks_dir=_extinguisher_catalog(tmp))
    assert out["normative_value"] is False and [f["label"] for f in out["floors"]] == ["Térreo"]
    by_check = {f["check_id"]: f for f in out["findings"]}
    assert by_check["EXT-CAD-001"]["compliance_status"] == "COMPLIANT"
    assert by_check["EXT-CAD-002"]["measured"]["value"] == 2.0
    dist = by_check["EXT-CAD-003-PEQUENO"]
    assert dist["compliance_status"] == "COMPLIANT" and dist["scope_label"] == "Térreo"
    assert dist["measured"]["geometry_snapshot_hash"] == out["drawing_sha256"]
    assert by_check["EXT-CAD-003-GRANDE"]["compliance_status"] == "NOT_APPLICABLE"
    ext = [e for e in out["evidence"] if e["field"] == "extinguisher"]
    assert len(ext) == 2 and all(e["locator"]["entity_handle"] for e in ext)
    # F8: v2-findings --out carrega os mesmos achados no contrato comum das skills
    import json

    import jsonschema
    root = Path(__file__).resolve().parents[2]
    schema = json.loads((root / "skills" / "_comum" / "achado.schema.json").read_text("utf-8"))
    assert len(out["achados"]) == len(out["findings"])
    for achado in out["achados"]:
        jsonschema.validate(achado, schema)
    by_id = {a["id"]: a for a in out["achados"]}
    for f in out["findings"]:
        assert by_id[f["ref"]]["compliance_status"] == f["compliance_status"]


def test_source_index_item_text_and_search(env):
    source_id = _ingest(env).json()["items"][0]["id"]
    detail = env.get(f"/v1/normative/sources/{source_id}")
    assert detail.status_code == 200, detail.text
    ids = [i["id"] for i in detail.json()["items"]]
    assert "5.2.4" in ids and "Tabela 3" in ids
    item = env.tc.get(f"/v1/normative/sources/{source_id}/item", params={"item": "5.2.4"}).json()
    assert item["document"] == "NT 2-01" and item["occurrences"][0]["page"]
    assert env.tc.get(f"/v1/normative/sources/{source_id}/item",
                   params={"item": "99.9"}).status_code == 404
    hits = env.tc.get("/v1/normative/search", params={"q": "unidade extintora"}).json()["items"]
    assert hits and all(h["document"] == "NT 2-01" for h in hits)
    # radical: "percorrer" encontra "percorrida"
    stem = env.tc.get("/v1/normative/search", params={"q": "distância percorrer"}).json()
    assert any(h["item"] == "Tabela 3" for h in stem["items"])
    assert env.tc.get("/v1/normative/search", params={"q": "palavrainexistente"}).json()[
        "items"] == []
    assert env.get("/v1/rule-packages").json() == {"items": []}

