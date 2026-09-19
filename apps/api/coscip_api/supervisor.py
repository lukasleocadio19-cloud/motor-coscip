"""Supervisor interno: reclama jobs e executa cada estágio pesado em processo separado.

O worker recebe manifesto + pasta temporária, NÃO tem acesso ao banco nem às chaves de IA.
Só este processo confiável publica no banco, e somente com o token da tentativa vigente.
Separação de processo não é sandbox de segurança (ver SAFE-05).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

from pydantic import ValidationError

from coscip_api.config import Settings
from coscip_api.db import write_tx
from coscip_api.models import Drawing, Execution, FileObject
from coscip_jobs import Claim, JobQueue, StaleAttemptError
from coscip_storage import DataLayout, LocalFileStorage
from coscip_worker.contracts import ImportResult

log = logging.getLogger("coscip.supervisor")


class Supervisor:
    def __init__(self, settings: Settings, layout: DataLayout, storage: LocalFileStorage,
                 session_factory, tenant_id: str) -> None:  # noqa: ANN001
        self.settings = settings
        self.layout = layout
        self.storage = storage
        self.factory = session_factory
        self.tenant_id = tenant_id
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.layout.database, isolation_level=None, timeout=15)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=15000")
        return conn

    def start(self) -> None:
        conn = self._conn()
        recovered = JobQueue(conn).recover_interrupted()
        conn.close()
        if recovered:
            log.warning("jobs interrompidos devolvidos à fila: %s", recovered)
            with write_tx(self.factory) as s:
                for ex in s.query(Execution).filter(Execution.job_id.in_(recovered)):
                    ex.state, ex.error_code = "QUEUED", "WORKER_INTERRUPTED"
        self._reconcile_temps()
        self._thread = threading.Thread(target=self._loop, name="coscip-supervisor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)

    def _reconcile_temps(self) -> None:
        for p in self.storage.find_orphan_temps():
            log.warning("temporário órfão removido: %s", p.name)
            p.unlink(missing_ok=True)

    def _loop(self) -> None:
        conn = self._conn()
        queue = JobQueue(conn)
        while not self._stop.is_set():
            claim = queue.claim(os.getpid())
            if claim is None:
                self._stop.wait(1.0)
                continue
            try:
                self._run(queue, claim)
            except StaleAttemptError:
                log.error("tentativa vencida descartada: %s", claim.job_id)
            except Exception:  # noqa: BLE001 — falha técnica nunca vira sucesso
                log.exception("falha no job %s", claim.job_id)
                self._finish(queue, claim, "FAILED", "INTERNAL_ERROR")
        conn.close()

    def _set_exec(self, execution_id: str, **fields) -> None:  # noqa: ANN003
        with write_tx(self.factory) as s:
            ex = s.get(Execution, execution_id)
            for k, v in fields.items():
                setattr(ex, k, v)

    def _finish(self, queue: JobQueue, claim: Claim, state: str, code: str | None) -> None:
        queue.complete(claim.job_id, claim.attempt_token, state, code)
        self._set_exec(claim.payload["execution_id"], state=state, error_code=code)

    def _run(self, queue: JobQueue, claim: Claim) -> None:
        if claim.kind != "IMPORT_DXF":
            self._finish(queue, claim, "FAILED", "UNKNOWN_JOB_KIND")
            return
        p = claim.payload
        self._set_exec(p["execution_id"], state="RUNNING", stage="EXTRACT")

        work = self.layout.staging / claim.job_id / claim.attempt_token
        (work / "in").mkdir(parents=True)
        (work / "out").mkdir()
        # Cópia para o diretório do job: o worker só enxerga a própria pasta.
        shutil.copy2(self.storage.resolve(p["file_key"]), work / "in" / "drawing.dxf")
        manifest = {"job_id": claim.job_id, "attempt_token": claim.attempt_token,
                    "input": "in/drawing.dxf", "input_sha256": p["file_sha256"],
                    "output_dir": "out", "max_expanded": self.settings.max_expanded_entities}
        (work / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        proc = subprocess.Popen(
            [sys.executable, "-m", "coscip_worker.main", str(work / "manifest.json")],
            cwd=work, env=_worker_env(work),
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        deadline = time.monotonic() + self.settings.worker_timeout_s
        while proc.poll() is None:
            if queue.state(claim.job_id) == "CANCEL_REQUESTED":
                proc.kill()
                proc.wait()
                self._finish(queue, claim, "CANCELLED", None)
                return
            if time.monotonic() > deadline:
                proc.kill()
                proc.wait()
                self._finish(queue, claim, "FAILED", "WORKER_TIMEOUT")
                return
            queue.heartbeat(claim.job_id, claim.attempt_token)
            time.sleep(1.0)

        if proc.returncode != 0:
            err = (proc.stderr.read() or b"")[-2000:].decode("utf-8", "replace")
            log.error("worker falhou (%s): %s", proc.returncode, err)
            self._finish(queue, claim, "FAILED", "WORKER_FAILED")
            return

        # Valida esquema, limites e checksums ANTES de publicar.
        try:
            result = ImportResult.model_validate_json(
                (work / "out" / "result.json").read_text(encoding="utf-8"))
        except (OSError, ValidationError):
            self._finish(queue, claim, "FAILED", "WORKER_OUTPUT_INVALID")
            return
        if result.input_sha256 != p["file_sha256"] or result.attempt_token != claim.attempt_token:
            self._finish(queue, claim, "FAILED", "WORKER_OUTPUT_MISMATCH")
            return

        queue.heartbeat(claim.job_id, claim.attempt_token)  # ainda é a tentativa vigente?
        self._set_exec(p["execution_id"], stage="PUBLISH", completed_stages=1)
        inv_key = (f"projects/{p['project_id']}/normalized/{p['revision_id']}/"
                   f"{claim.job_id}-inventory.json")
        with open(work / "out" / "inventory.json", "rb") as fh:
            inv_obj = self.storage.write_stream(inv_key, fh)
        with write_tx(self.factory) as s:
            fo = FileObject(tenant_id=self.tenant_id, key=inv_key, sha256=inv_obj.sha256,
                            size=inv_obj.size, mime="application/json")
            s.add(fo)
            s.flush()
            s.add(Drawing(tenant_id=self.tenant_id, file_id=p["file_id"], adapter="ezdxf",
                          cad_version=result.inventory.dxf_version,
                          diagnostics=result.inventory.model_dump(),
                          inventory_artifact_id=fo.id))
        # A unidade SEMPRE exige confirmação humana: no corpus de 19/09, $INSUNITS estava
        # errado em 5 de 5 desenhos. O job termina aqui; nenhum worker fica reservado esperando.
        final, code = "WAITING_INPUT", "DRAWING_UNIT_UNCONFIRMED"
        queue.complete(claim.job_id, claim.attempt_token, final, code)
        self._set_exec(p["execution_id"], state=final, error_code=code, completed_stages=2,
                       stage=None)
        shutil.rmtree(work, ignore_errors=True)


def _worker_env(workdir: Path) -> dict[str, str]:
    """Ambiente mínimo: sem variáveis de credencial nem pasta do perfil do usuário."""
    keep = {"PATH", "SYSTEMROOT", "PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"}
    env = {k: v for k, v in os.environ.items() if k.upper() in keep}
    for var in ("TEMP", "TMP", "HOME", "USERPROFILE", "XDG_CONFIG_HOME", "XDG_CACHE_HOME"):
        env[var] = str(workdir)  # ezdxf e temporários ficam dentro da pasta do job
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [*map(str, _src_paths()),
                                                      env.get("PYTHONPATH", "")]))
    return env


def _src_paths() -> list[Path]:
    root = Path(__file__).resolve().parents[3]
    return [root / "workers" / "local", *(p for p in (root / "packages").iterdir() if p.is_dir())]
