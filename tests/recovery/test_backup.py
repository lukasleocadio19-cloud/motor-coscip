"""SAFE-01/SAFE-02: backup consistente, verificação por hash e restauração em pasta separada."""

from __future__ import annotations

import sqlite3

import pytest

from coscip_api.backup import BackupIncomplete, create_backup, restore_backup, verify_backup
from coscip_api.db import migrate
from coscip_storage import DataLayout, LocalFileStorage


@pytest.fixture
def layout(tmp_path):
    lay = DataLayout(tmp_path / "data")
    lay.ensure()
    migrate(f"sqlite:///{lay.database.as_posix()}")
    obj = LocalFileStorage(lay.root).write_stream("projects/p/originals/r/a.dxf", [b"conteudo"])
    con = sqlite3.connect(lay.database)
    con.execute("PRAGMA foreign_keys=OFF")
    con.execute("INSERT INTO organizations (id, name, state, created_at) "
                "VALUES ('o', 'Org', 'ACTIVE', '2026-09-19')")
    con.execute("INSERT INTO file_objects (id, tenant_id, created_at, storage_backend, key, "
                "logical_version, sha256, size) "
                "VALUES ('f', 'o', '2026-09-19', 'LOCAL_FS', ?, 1, ?, ?)",
                (obj.key, obj.sha256, obj.size))
    con.commit()
    con.close()
    return lay


def test_backup_verify_restore(layout, tmp_path):
    out = create_backup(layout, tmp_path / "externo")
    assert verify_backup(out) == []
    restored = restore_backup(out, tmp_path / "restaurado")
    con = sqlite3.connect(restored.database)
    assert con.execute("SELECT count(*) FROM file_objects").fetchone()[0] == 1
    con.close()
    assert (restored.root / "projects/p/originals/r/a.dxf").read_bytes() == b"conteudo"


def test_tampered_backup_detected(layout, tmp_path):
    out = create_backup(layout, tmp_path / "externo")
    (out / "data/projects/p/originals/r/a.dxf").write_bytes(b"alterado")
    assert verify_backup(out)
    with pytest.raises(BackupIncomplete):
        restore_backup(out, tmp_path / "restaurado")


def test_restore_refuses_non_empty_target(layout, tmp_path):
    out = create_backup(layout, tmp_path / "externo")
    target = tmp_path / "ocupado"
    target.mkdir()
    (target / "x").write_text("1")
    with pytest.raises(FileExistsError):
        restore_backup(out, target)
