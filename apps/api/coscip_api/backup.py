"""Backup e restauração (plano §14, SAFE-01/SAFE-02).

1. Pausa mutações (lock de escrita) enquanto monta o snapshot.
2. Copia o SQLite pela API de backup e roda integrity_check na cópia.
3. Copia artefatos imutáveis referenciados, pacotes de regras e configuração sem segredos.
4. Valida hashes antes de marcar como concluído.
Credenciais de IA nunca entram no pacote.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from coscip_api.db import _write_lock
from coscip_storage import DataLayout


class BackupIncomplete(RuntimeError):
    code = "BACKUP_INCOMPLETE"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def create_backup(layout: DataLayout, dest_root: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    dest = dest_root / f"motor-coscip-backup-{stamp}"
    (dest / "database").mkdir(parents=True)

    with _write_lock:
        src = sqlite3.connect(layout.database)
        try:
            out = sqlite3.connect(dest / "database" / "app.db")
            with out:
                src.backup(out)
            out.close()
            files = src.execute("SELECT key, sha256 FROM file_objects").fetchall()
        finally:
            src.close()

    check = sqlite3.connect(dest / "database" / "app.db")
    try:
        if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise BackupIncomplete("integrity_check falhou na cópia do banco")
    finally:
        check.close()

    manifest: dict = {"created_at": stamp, "database_sha256": _sha256(dest / "database" / "app.db"),
                      "files": []}
    for key, sha in files:
        src_path = layout.root / key
        dst_path = dest / "data" / key
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        got = _sha256(dst_path)
        if got != sha:
            raise BackupIncomplete(f"hash divergente em {key}")
        manifest["files"].append({"key": key, "sha256": sha})

    if layout.normative_packages.exists():
        shutil.copytree(layout.normative_packages, dest / "normative" / "packages")

    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (dest / "COMPLETED").write_text(stamp, encoding="utf-8")
    return dest


def verify_backup(backup_dir: Path) -> list[str]:
    """Devolve lista de problemas; vazia = íntegro."""
    problems: list[str] = []
    if not (backup_dir / "COMPLETED").exists():
        problems.append("backup sem marcador de conclusão")
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
    if _sha256(backup_dir / "database" / "app.db") != manifest["database_sha256"]:
        problems.append("hash do banco divergente")
    for f in manifest["files"]:
        p = backup_dir / "data" / f["key"]
        if not p.exists() or _sha256(p) != f["sha256"]:
            problems.append(f"arquivo ausente/divergente: {f['key']}")
    return problems


def restore_backup(backup_dir: Path, target_root: Path) -> DataLayout:
    """Restaura em pasta SEPARADA; substituir a base ativa é decisão do operador (launcher)."""
    problems = verify_backup(backup_dir)
    if problems:
        raise BackupIncomplete("; ".join(problems))
    if target_root.exists() and any(target_root.iterdir()):
        raise FileExistsError("destino de restauração deve estar vazio")
    layout = DataLayout(target_root)
    layout.ensure()
    shutil.copy2(backup_dir / "database" / "app.db", layout.database)
    if (backup_dir / "data").exists():
        shutil.copytree(backup_dir / "data", target_root, dirs_exist_ok=True)
    if (backup_dir / "normative").exists():
        shutil.copytree(backup_dir / "normative", target_root / "normative", dirs_exist_ok=True)
    return layout
