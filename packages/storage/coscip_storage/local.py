from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

CHUNK = 1024 * 1024


class PathOutsideRootError(PermissionError):
    pass


@dataclass(frozen=True)
class StoredObject:
    key: str  # chave relativa interna, nunca caminho absoluto exposto ao navegador
    sha256: str
    size: int


@dataclass(frozen=True)
class DataLayout:
    """Estrutura da pasta local de dados (plano §13)."""

    root: Path

    @property
    def database(self) -> Path:
        return self.root / "database" / "app.db"

    def project(self, project_id: str) -> Path:
        return self.root / "projects" / project_id

    @property
    def quarantine(self) -> Path:
        return self.root / "quarantine"

    @property
    def staging(self) -> Path:
        return self.root / "jobs" / "staging"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def backup_manifests(self) -> Path:
        return self.root / "backup-manifests"

    @property
    def normative_packages(self) -> Path:
        return self.root / "normative" / "packages"

    @property
    def settings_file(self) -> Path:
        return self.root / "config" / "settings.json"

    def ensure(self) -> None:
        for p in (
            self.database.parent,
            self.root / "projects",
            self.quarantine,
            self.staging,
            self.logs,
            self.backup_manifests,
            self.normative_packages,
            self.settings_file.parent,
        ):
            p.mkdir(parents=True, exist_ok=True)


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    # --- resolução segura -------------------------------------------------
    def resolve(self, key: str) -> Path:
        """Resolve chave interna → caminho, rejeitando traversal e links para fora."""
        if not key or key.startswith(("/", "\\")) or ":" in key:
            raise PathOutsideRootError(f"chave inválida: {key!r}")
        candidate = (self.root / key).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise PathOutsideRootError(f"chave fora da pasta de dados: {key!r}")
        return candidate

    # --- escrita ----------------------------------------------------------
    def write_stream(self, key: str, chunks: Iterable[bytes] | BinaryIO) -> StoredObject:
        """Grava em temporário no mesmo volume, sincroniza e renomeia (publicação atômica).

        O destino é imutável: se já existir, a escrita é recusada.
        """
        dest = self.resolve(key)
        if dest.exists():
            raise FileExistsError(f"objeto imutável já existe: {key}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(f".{dest.name}.{uuid.uuid4().hex}.tmp")
        h = hashlib.sha256()
        size = 0
        it = iter(lambda: chunks.read(CHUNK), b"") if hasattr(chunks, "read") else chunks
        try:
            with open(tmp, "xb") as out:
                for chunk in it:
                    h.update(chunk)
                    size += len(chunk)
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            os.replace(tmp, dest)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
        return StoredObject(key=key, sha256=h.hexdigest(), size=size)

    def open(self, key: str) -> BinaryIO:
        return open(self.resolve(key), "rb")

    def sha256_of(self, key: str) -> str:
        h = hashlib.sha256()
        with self.open(key) as fh:
            for chunk in iter(lambda: fh.read(CHUNK), b""):
                h.update(chunk)
        return h.hexdigest()

    def free_bytes(self) -> int:
        return shutil.disk_usage(self.root).free

    def find_orphan_temps(self) -> list[Path]:
        """Temporários deixados por interrupção; reconciliados na inicialização."""
        return [p for p in self.root.rglob(".*.tmp") if p.is_file()]
