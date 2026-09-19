"""Gate B: fechar e reabrir preserva dados; migração é idempotente."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from coscip_api.config import Settings
from coscip_api.db import migrate
from coscip_api.main import create_app

MIGRATIONS = Path(migrate.__code__.co_filename).parent / "migrations"


def test_migrate_twice_records_version(tmp_path):
    url = f"sqlite:///{(tmp_path / 'app.db').as_posix()}"
    migrate(url)
    migrate(url)
    con = sqlite3.connect(tmp_path / "app.db")
    versions = sorted(f.name[:4] for f in (MIGRATIONS / "versions").glob("0*.py"))
    assert con.execute("SELECT version_num FROM alembic_version").fetchall() == [(versions[-1],)]
    con.close()


def test_reopen_keeps_projects_and_identity(tmp_path):
    origin = "http://127.0.0.1:8770"
    ids = []
    for token in ("a", "b"):
        settings = Settings(data_dir=tmp_path / "data", port=8770, launch_token=token)
        with TestClient(create_app(settings, start_supervisor=False), base_url=origin) as c:
            c.post("/v1/local/session/exchange", json={"token": token},
                   headers={"Origin": origin})
            h = {"Origin": origin, "X-CSRF-Token": c.cookies["coscip_csrf"]}
            if token == "a":
                c.post("/v1/projects", json={"name": "Persistente"}, headers=h)
            ids.append(c.get("/v1/me").json()["organization_id"])
            names = [p["name"] for p in c.get("/v1/projects").json()["items"]]
    assert names == ["Persistente"]
    assert ids[0] == ids[1]
