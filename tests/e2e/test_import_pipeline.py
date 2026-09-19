"""Jornada mínima (critério dos 30 dias, sem IA): enviar DXF → worker separado →
inventário publicado → diagnóstico visível. Sem unidade declarada → WAITING_INPUT."""

from __future__ import annotations

import hashlib
import time

import pytest
from fastapi.testclient import TestClient

from coscip_api.config import Settings
from coscip_api.main import create_app

PORT = 8766
ORIGIN = f"http://127.0.0.1:{PORT}"


def _run(tmp_path, dxf_path):
    settings = Settings(data_dir=tmp_path / "data", port=PORT, launch_token="t")
    with TestClient(create_app(settings), base_url=ORIGIN) as c:
        c.post("/v1/local/session/exchange", json={"token": "t"}, headers={"Origin": ORIGIN})
        h = {"Origin": ORIGIN, "X-CSRF-Token": c.cookies["coscip_csrf"]}
        p = c.post("/v1/projects", json={"name": "E2E"}, headers=h).json()
        r = c.post(f"/v1/projects/{p['id']}/revisions", headers=h).json()
        data = dxf_path.read_bytes()
        up = c.post(f"/v1/revisions/{r['id']}/uploads", headers=h, json={
            "filename": dxf_path.name, "role": "ANALYTIC_DXF", "size": len(data)}).json()
        c.put(f"/v1/uploads/{up['id']}/parts/1", content=data,
              headers={**h, "X-Part-SHA256": hashlib.sha256(data).hexdigest()})
        c.post(f"/v1/uploads/{up['id']}/complete", headers=h)
        c.post(f"/v1/revisions/{r['id']}/seal", headers=h)
        ex = c.post(f"/v1/revisions/{r['id']}/imports",
                    headers={**h, "Idempotency-Key": "e2e"}).json()
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            state = c.get(f"/v1/executions/{ex['execution_id']}").json()
            if state["state"] in {"SUCCEEDED", "WAITING_INPUT", "FAILED", "CANCELLED"}:
                break
            time.sleep(0.5)
        diag = c.get(f"/v1/revisions/{r['id']}/diagnostics").json()
        return state, diag


@pytest.mark.timeout(120)
def test_import_dxf_end_to_end(tmp_path, floor_dxf):
    state, diag = _run(tmp_path, floor_dxf)
    # Extração concluída, mas a unidade declarada nunca é aceita sem confirmação.
    assert state["state"] == "WAITING_INPUT", state
    assert state["error_code"] == "DRAWING_UNIT_UNCONFIRMED"
    d = diag["items"][0]["diagnostics"]
    assert d["units_declared"] is True
    assert d["entity_counts"]["INSERT"] == 3
    assert d["expanded_count"] > d["entity_counts"]["INSERT"]


def test_missing_units_waits_for_input(tmp_path, floor_dxf_no_units):
    state, _ = _run(tmp_path, floor_dxf_no_units)
    assert state["state"] == "WAITING_INPUT"
    assert state["error_code"] == "DRAWING_UNIT_UNCONFIRMED"
