"""CAD-02 (unidade), VIEW-01/02 (cena e origem) e PREP-01 (recorte) com o pipeline real.

Planta sintética em metros: sala 10×6 m, porta (bloco PORTA_90, folha de 0,90 m) em (2,0)
e cópia espelhada em (8,0), extintor em (5,3).
"""

from __future__ import annotations

import hashlib
import struct
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from coscip_api.config import Settings
from coscip_api.main import create_app
from coscip_cad.synthetic import make_simple_floor

PORT = 8771
ORIGIN = f"http://127.0.0.1:{PORT}"
JUST = "Porta de 0,90 m conferida na cota do projeto"


class Env:
    def __init__(self, data_dir: Path, token: str) -> None:
        settings = Settings(data_dir=data_dir, port=PORT, launch_token=token)
        self.tc = TestClient(create_app(settings), base_url=ORIGIN)
        self.tc.__enter__()
        self.tc.post("/v1/local/session/exchange", json={"token": token},
                     headers={"Origin": ORIGIN})
        self.h = {"Origin": ORIGIN, "X-CSRF-Token": self.tc.cookies["coscip_csrf"]}

    def close(self) -> None:
        self.tc.__exit__(None, None, None)

    def get(self, url: str):
        return self.tc.get(url)

    def post(self, url: str, json=None, **headers):
        return self.tc.post(url, json=json, headers={**self.h, **headers})

    def import_revision(self, dxfs: list[Path]) -> tuple[str, list[dict]]:
        p = self.post("/v1/projects", {"name": "Teste"}).json()
        r = self.post(f"/v1/projects/{p['id']}/revisions").json()
        for dxf in dxfs:
            data = dxf.read_bytes()
            up = self.post(f"/v1/revisions/{r['id']}/uploads", {
                "filename": dxf.name, "role": "ANALYTIC_DXF", "size": len(data)}).json()
            self.tc.put(f"/v1/uploads/{up['id']}/parts/1", content=data,
                        headers={**self.h, "X-Part-SHA256": hashlib.sha256(data).hexdigest()})
            self.post(f"/v1/uploads/{up['id']}/complete")
        self.post(f"/v1/revisions/{r['id']}/seal")
        started = self.post(f"/v1/revisions/{r['id']}/imports",
                            **{"Idempotency-Key": f"imp-{r['id']}"}).json()
        ids = [e["execution_id"] for e in started["executions"]]
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            states = [self.get(f"/v1/executions/{i}").json() for i in ids]
            if all(s["state"] not in ("QUEUED", "RUNNING") for s in states):
                break
            time.sleep(0.3)
        return r["id"], states


@pytest.fixture
def env(tmp_path):
    e = Env(tmp_path / "data", "tok")
    yield e
    e.close()


@pytest.fixture
def one_drawing(env, floor_dxf):
    rev, states = env.import_revision([floor_dxf])
    assert states[0]["state"] == "WAITING_INPUT"
    d = env.get(f"/v1/revisions/{rev}/drawings").json()["items"][0]
    return rev, d, states[0]["execution_id"]


def _door_reference():
    # Folha da porta: LINE de (2,0) a (2,9,0) no desenho em metros.
    return {"reference_a": {"x": 2.0, "y": 0.0}, "reference_b": {"x": 2.9, "y": 0.0}}


# --- CAD-02 -------------------------------------------------------------------
def test_blocked_before_confirmation(env, one_drawing):
    _, d, _ = one_drawing
    assert d["unit"]["confirmed"] is False
    assert d["model_snapshot"]["quality"]["units_confirmed"] is False
    r = env.post(f"/v1/drawings/{d['id']}/measure",
                 {"a": {"x": 0, "y": 0}, "b": {"x": 1, "y": 0}})
    assert r.status_code == 409 and r.json()["code"] == "DRAWING_UNIT_UNCONFIRMED"


@pytest.mark.parametrize(("patch", "code"), [
    ({"unit": "mm"}, "UNIT_REFERENCE_MISMATCH"),  # unidade errada: 0,0009 m ≠ 0,90 m
    ({"real_length_m": 2.0}, "UNIT_REFERENCE_MISMATCH"),  # referência não bate
    ({"reference_b": {"x": 2.0, "y": 0.0}}, "INVALID_REFERENCE"),  # pontos coincidentes
])
def test_invalid_reference_rejected(env, one_drawing, patch, code):
    _, d, _ = one_drawing
    body = {"unit": "m", **_door_reference(), "real_length_m": 0.9, "justification": JUST,
            **patch}
    r = env.post(f"/v1/drawings/{d['id']}/unit-confirmation", body)
    assert r.status_code == 422 and r.json()["code"] == code
    assert env.get(f"/v1/drawings/{d['id']}").json()["unit"]["confirmed"] is False


@pytest.mark.parametrize("patch", [
    {"real_length_m": 0}, {"real_length_m": -1}, {"justification": "curta"},
    {"unit": "furlong"},
])
def test_malformed_confirmation_rejected(env, one_drawing, patch):
    _, d, _ = one_drawing
    body = {"unit": "m", **_door_reference(), "real_length_m": 0.9, "justification": JUST,
            **patch}
    assert env.post(f"/v1/drawings/{d['id']}/unit-confirmation", body).status_code == 422


def test_unknown_drawing_and_missing_session(env, one_drawing):
    _, d, _ = one_drawing
    body = {"unit": "m", **_door_reference(), "real_length_m": 0.9, "justification": JUST}
    assert env.post("/v1/drawings/nao-existe/unit-confirmation", body).status_code == 404
    anon = TestClient(env.tc.app, base_url=ORIGIN)
    r = anon.post(f"/v1/drawings/{d['id']}/unit-confirmation", json=body,
                  headers={"Origin": ORIGIN})
    assert r.status_code == 401


def test_confirmation_releases_and_keeps_history(env, one_drawing):
    rev, d, ex_id = one_drawing
    snap_before = d["model_snapshot"]["id"]
    body = {"unit": "m", **_door_reference(), "real_length_m": 0.9, "justification": JUST,
            "expected_frame_id": d["unit"]["frame_id"]}
    r = env.post(f"/v1/drawings/{d['id']}/unit-confirmation", body)
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["quality"]["units_confirmed"] is True
    assert abs(out["reference_measured_m"] - 0.9) < 1e-9

    assert env.get(f"/v1/executions/{ex_id}").json()["state"] == "SUCCEEDED"
    model = env.get(f"/v1/models/{out['model_snapshot_id']}").json()
    assert model["parent_id"] == snap_before  # novo snapshot, anterior preservado
    assert env.get(f"/v1/models/{snap_before}").json()["quality"]["units_confirmed"] is False

    m = env.post(f"/v1/drawings/{d['id']}/measure",
                 {"a": {"x": 0, "y": 0}, "b": {"x": 10, "y": 0}, "save": True}).json()
    assert abs(m["length_m"] - 10.0) < 1e-6 and "measurement_id" in m

    # Reconfirmar com quadro esperado antigo → conflito, sem sobrescrever.
    stale = env.post(f"/v1/drawings/{d['id']}/unit-confirmation", body)
    assert stale.status_code == 409 and stale.json()["code"] == "VERSION_CONFLICT"


def test_confirming_one_drawing_does_not_release_others(env, tmp_path):
    a = make_simple_floor(tmp_path / "a.dxf")
    b = make_simple_floor(tmp_path / "b.dxf", insunits=4, scale=1000)  # mesma planta em mm
    rev, states = env.import_revision([a, b])
    assert [s["state"] for s in states] == ["WAITING_INPUT", "WAITING_INPUT"]
    drawings = env.get(f"/v1/revisions/{rev}/drawings").json()["items"]
    first = next(x for x in drawings if x["file"] == "a.dxf")
    body = {"unit": "m", **_door_reference(), "real_length_m": 0.9, "justification": JUST}
    out = env.post(f"/v1/drawings/{first['id']}/unit-confirmation", body).json()
    assert out["quality"]["units_confirmed"] is False
    assert any(i.startswith("UNIT_UNCONFIRMED") for i in out["quality"]["blocking_issue_ids"])
    after = [env.get(f"/v1/executions/{s['execution_id']}").json()["state"] for s in states]
    assert sorted(after) == ["SUCCEEDED", "WAITING_INPUT"]

    second = next(x for x in drawings if x["file"] == "b.dxf")
    body_mm = {"unit": "mm", "reference_a": {"x": 2000, "y": 0},
               "reference_b": {"x": 2900, "y": 0}, "real_length_m": 0.9, "justification": JUST}
    done = env.post(f"/v1/drawings/{second['id']}/unit-confirmation", body_mm).json()
    assert done["quality"]["units_confirmed"] is True


def test_confirmation_survives_reopen(tmp_path, floor_dxf):
    e1 = Env(tmp_path / "data", "t1")
    rev, _ = e1.import_revision([floor_dxf])
    d = e1.get(f"/v1/revisions/{rev}/drawings").json()["items"][0]
    body = {"unit": "m", **_door_reference(), "real_length_m": 0.9, "justification": JUST}
    assert e1.post(f"/v1/drawings/{d['id']}/unit-confirmation", body).status_code == 201
    e1.close()
    e2 = Env(tmp_path / "data", "t2")
    try:
        again = e2.get(f"/v1/drawings/{d['id']}").json()
        assert again["unit"]["confirmed"] is True and again["unit"]["unit"] == "m"
        m = e2.post(f"/v1/drawings/{d['id']}/measure",
                    {"a": {"x": 0, "y": 0}, "b": {"x": 0, "y": 6}}).json()
        assert abs(m["length_m"] - 6.0) < 1e-6
    finally:
        e2.close()


# --- VIEW-01/02 ----------------------------------------------------------------
def _scene(env, drawing_id):
    sc = env.get(f"/v1/drawings/{drawing_id}/scene").json()
    seg = env.get(f"/v1/artifacts/{sc['segments_artifact_id']}/content").content
    ids = env.get(f"/v1/artifacts/{sc['entity_ids_artifact_id']}/content").content
    n = sc["segment_count"]
    assert len(seg) == n * 16 and len(ids) == n * 4
    coords = struct.unpack(f"<{n * 4}f", seg)
    rows = struct.unpack(f"<{n}I", ids)
    ox, oy = sc["local_origin"]
    segs = [(coords[i * 4] + ox, coords[i * 4 + 1] + oy, coords[i * 4 + 2] + ox,
             coords[i * 4 + 3] + oy, rows[i]) for i in range(n)]
    return sc, segs


def _find(segs, x1, y1, x2, y2, tol=1e-4):
    for a, b, c, d, row in segs:
        if (abs(a - x1) < tol and abs(b - y1) < tol and abs(c - x2) < tol
                and abs(d - y2) < tol):
            return row
    return None


def test_scene_layers_and_origin_of_selection(env, one_drawing):
    _, d, _ = one_drawing
    sc, segs = _scene(env, d["id"])
    names = {lay["name"] for lay in sc["layers"]}
    assert {"PAREDES", "PORTAS", "INC_EXT"} <= names
    assert sc["max_sagitta"] > 0  # arco da porta e círculo do extintor discretizados
    assert sum(lay["count"] for lay in sc["layers"]) == sc["segment_count"]

    row_a = _find(segs, 2.0, 0.0, 2.9, 0.0)
    row_b = _find(segs, 8.0, 0.0, 7.1, 0.0)  # cópia espelhada
    assert row_a is not None and row_b is not None and row_a != row_b
    ea = env.get(f"/v1/drawings/{d['id']}/entities/{row_a}").json()
    eb = env.get(f"/v1/drawings/{d['id']}/entities/{row_b}").json()
    assert ea["type"] == "LINE" and ea["block"] == "PORTA_90" and ea["layer"] == "PORTAS"
    assert ea["handle"] == eb["handle"] and ea["instance_path"] != eb["instance_path"]
    assert len(ea["source_file"]["sha256"]) == 64
    assert env.get(f"/v1/drawings/{d['id']}/entities/999999").status_code == 404


def test_snap_to_exact_vertex(env, one_drawing):
    _, d, _ = one_drawing
    _, segs = _scene(env, d["id"])
    row = _find(segs, 2.0, 0.0, 2.9, 0.0)
    env.post(f"/v1/drawings/{d['id']}/unit-confirmation",
             {"unit": "m", **_door_reference(), "real_length_m": 0.9, "justification": JUST})
    m = env.post(f"/v1/drawings/{d['id']}/measure", {
        "a": {"x": 2.0004, "y": 0.0003, "entity_row": row, "pick_tolerance": 0.01},
        "b": {"x": 2.8998, "y": -0.0002, "entity_row": row, "pick_tolerance": 0.01},
    }).json()
    assert m["snapped_to_vertex"] == [True, True] and m["exploratory"] is False
    assert m["length_m"] == pytest.approx(0.9, abs=1e-12)


# --- PREP-01 -------------------------------------------------------------------
def test_floor_clip_limits_measurements(env, one_drawing):
    _, d, _ = one_drawing
    env.post(f"/v1/drawings/{d['id']}/unit-confirmation",
             {"unit": "m", **_door_reference(), "real_length_m": 0.9, "justification": JUST})
    bad = env.post(f"/v1/drawings/{d['id']}/floors",
                   {"name": "Térreo", "clip": {"x0": 5, "y0": 0, "x1": 1, "y1": 6}})
    assert bad.status_code == 422 and bad.json()["code"] == "INVALID_CLIP"
    f = env.post(f"/v1/drawings/{d['id']}/floors",
                 {"name": "Térreo", "clip": {"x0": -0.1, "y0": -0.1, "x1": 5, "y1": 6.1}}).json()
    floors = env.get(f"/v1/models/{f['model_snapshot_id']}/floors").json()["items"]
    assert [x["name"] for x in floors] == ["Térreo"]

    inside = env.post(f"/v1/drawings/{d['id']}/measure", {
        "a": {"x": 0, "y": 0}, "b": {"x": 5, "y": 0}, "floor_id": f["id"]})
    assert inside.status_code == 200
    outside = env.post(f"/v1/drawings/{d['id']}/measure", {
        "a": {"x": 0, "y": 0}, "b": {"x": 10, "y": 0}, "floor_id": f["id"]})
    assert outside.status_code == 422 and outside.json()["code"] == "POINT_OUTSIDE_FLOOR_CLIP"
