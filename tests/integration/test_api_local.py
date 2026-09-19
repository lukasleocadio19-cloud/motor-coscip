"""LOC-02..LOC-06: sessão local, Host/Origin/CSRF, projetos, upload e selagem."""

from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from coscip_api.config import Settings
from coscip_api.main import create_app

PORT = 8765
ORIGIN = f"http://127.0.0.1:{PORT}"


@pytest.fixture
def client(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", port=PORT, launch_token="tok-123")
    app = create_app(settings, start_supervisor=False)
    with TestClient(app, base_url=ORIGIN) as c:
        yield c


def login(c: TestClient) -> dict[str, str]:
    r = c.post("/v1/local/session/exchange", json={"token": "tok-123"}, headers={"Origin": ORIGIN})
    assert r.status_code == 204
    return {"Origin": ORIGIN, "X-CSRF-Token": c.cookies["coscip_csrf"]}


def test_status_is_public_and_has_no_paths(client):
    body = client.get("/v1/local/status").json()
    assert body["status"] == "ok" and "\\" not in body["data_dir_label"]


def test_foreign_host_rejected(client):
    assert client.get("/v1/local/status", headers={"Host": "evil.example"}).status_code == 403


def test_session_required(client):
    assert client.get("/v1/projects").status_code == 401


def test_launch_token_is_single_use(client):
    login(client)
    r = client.post("/v1/local/session/exchange", json={"token": "tok-123"},
                    headers={"Origin": ORIGIN})
    assert r.status_code == 401


def test_mutation_without_origin_or_csrf_rejected(client):
    h = login(client)
    assert client.post("/v1/projects", json={"name": "x"}).status_code == 403
    assert client.post("/v1/projects", json={"name": "x"},
                       headers={"Origin": "http://evil.example",
                                "X-CSRF-Token": h["X-CSRF-Token"]}).status_code == 403
    assert client.post("/v1/projects", json={"name": "x"},
                       headers={"Origin": ORIGIN}).status_code == 403


def test_settings_never_return_secrets(client):
    login(client)
    s = client.get("/v1/settings").json()
    assert "secret" not in str(s).lower()
    assert s["ai_enabled"] is False


def test_project_revision_upload_seal(client, floor_dxf):
    h = login(client)
    p = client.post("/v1/projects", json={"name": "Loja teste"}, headers=h).json()
    r = client.post(f"/v1/projects/{p['id']}/revisions", headers=h).json()
    assert r["number"] == 1

    data = floor_dxf.read_bytes()
    up = client.post(f"/v1/revisions/{r['id']}/uploads", headers=h, json={
        "filename": "planta.dxf", "role": "ANALYTIC_DXF", "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest()}).json()
    half = len(data) // 2
    for n, chunk in enumerate((data[:half], data[half:]), start=1):
        resp = client.put(f"/v1/uploads/{up['id']}/parts/{n}", content=chunk,
                          headers={**h, "X-Part-SHA256": hashlib.sha256(chunk).hexdigest()})
        assert resp.status_code == 200, resp.text
    done = client.post(f"/v1/uploads/{up['id']}/complete", headers=h).json()
    assert done["sha256"] == hashlib.sha256(data).hexdigest()
    assert done["state"] == "QUARANTINED"

    sealed = client.post(f"/v1/revisions/{r['id']}/seal", headers=h).json()
    assert sealed["state"] == "SEALED" and len(sealed["manifest_sha256"]) == 64
    again = client.post(f"/v1/revisions/{r['id']}/uploads", headers=h, json={
        "filename": "b.dxf", "role": "ANALYTIC_DXF", "size": 10})
    assert again.json()["code"] == "REVISION_SEALED"

    ex1 = client.post(f"/v1/revisions/{r['id']}/imports",
                      headers={**h, "Idempotency-Key": "imp-1"}).json()
    ex2 = client.post(f"/v1/revisions/{r['id']}/imports",
                      headers={**h, "Idempotency-Key": "imp-1"}).json()
    assert ex1["execution_id"] == ex2["execution_id"] and ex1["state"] == "QUEUED"


def test_dwg_not_accepted_as_analytic(client):
    h = login(client)
    p = client.post("/v1/projects", json={"name": "x"}, headers=h).json()
    r = client.post(f"/v1/projects/{p['id']}/revisions", headers=h).json()
    resp = client.post(f"/v1/revisions/{r['id']}/uploads", headers=h, json={
        "filename": "a.dwg", "role": "ANALYTIC_DXF", "size": 10})
    assert resp.status_code == 422
    assert resp.json()["code"] == "UNSUPPORTED_DWG_INPUT"
    assert resp.json()["required_action"] == "EXPORT_DXF"


def test_bad_part_checksum_rejected(client):
    h = login(client)
    p = client.post("/v1/projects", json={"name": "x"}, headers=h).json()
    r = client.post(f"/v1/projects/{p['id']}/revisions", headers=h).json()
    up = client.post(f"/v1/revisions/{r['id']}/uploads", headers=h, json={
        "filename": "a.dxf", "role": "ANALYTIC_DXF", "size": 3}).json()
    resp = client.put(f"/v1/uploads/{up['id']}/parts/1", content=b"abc",
                      headers={**h, "X-Part-SHA256": "0" * 64})
    assert resp.json()["code"] == "PART_CHECKSUM_MISMATCH"


def test_optimistic_concurrency_on_project(client):
    h = login(client)
    p = client.post("/v1/projects", json={"name": "x"}, headers=h).json()
    ok = client.patch(f"/v1/projects/{p['id']}", json={"name": "y"},
                      headers={**h, "If-Match": "1"})
    assert ok.status_code == 200
    stale = client.patch(f"/v1/projects/{p['id']}", json={"name": "z"},
                         headers={**h, "If-Match": "1"})
    assert stale.status_code == 409
