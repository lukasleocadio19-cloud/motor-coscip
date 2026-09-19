"""Benchmark do corpus (POC-02/POC-05/POC-07): roda o worker real em cada DXF e mede
tempo, pico de memória e expansão. Os dados reais ficam fora do repositório; aqui só o código.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil

from coscip_api.supervisor import _worker_env

PROFILE_MAX_MB = 50
PROFILE_MAX_ENTITIES = 100_000


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_one(dxf: Path, max_expanded: int = 2_000_000, timeout_s: int = 1800) -> dict:
    work = Path(tempfile.mkdtemp(prefix="coscip-bench-"))
    try:
        (work / "in").mkdir()
        (work / "out").mkdir()
        shutil.copy2(dxf, work / "in" / "drawing.dxf")
        sha = _sha256(dxf)
        manifest = {"job_id": "bench", "attempt_token": "bench", "input": "in/drawing.dxf",
                    "input_sha256": sha, "output_dir": "out", "max_expanded": max_expanded}
        (work / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        t0 = time.monotonic()
        proc = subprocess.Popen([sys.executable, "-m", "coscip_worker.main",
                                 str(work / "manifest.json")], cwd=work, env=_worker_env(work),
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        ps = psutil.Process(proc.pid)
        peak = 0
        while proc.poll() is None:
            # No Windows o python.exe do venv é um lançador: o trabalho roda num processo filho.
            try:
                tree = [ps, *ps.children(recursive=True)]
                peak = max(peak, sum(p.memory_info().rss for p in tree if p.is_running()))
            except psutil.NoSuchProcess:
                pass
            if time.monotonic() - t0 > timeout_s:
                proc.kill()
                break
            time.sleep(0.2)
        elapsed = time.monotonic() - t0
        row: dict = {"file": dxf.name, "size_mb": round(dxf.stat().st_size / 2**20, 1),
                     "sha256": sha, "seconds": round(elapsed, 1),
                     "peak_rss_mb": round(peak / 2**20)}
        if proc.returncode != 0:
            row["error"] = (proc.stderr.read() or b"")[-800:].decode("utf-8", "replace")
            return row
        res = json.loads((work / "out" / "result.json").read_text(encoding="utf-8"))
        inv = res["inventory"]
        top_level = sum(inv["entity_counts"].values())
        row.update({
            "dxf_version": inv["dxf_version"], "insunits": inv["insunits_name"],
            "units_declared": inv["units_declared"], "layers": len(inv["layers"]),
            "blocks": len(inv["blocks"]), "xrefs": inv["xrefs"], "layouts": inv["layouts"],
            "top_level_entities": top_level, "expanded_entities": inv["expanded_count"],
            "entity_counts": inv["entity_counts"], "quality_counts": inv["quality_counts"],
            "unsupported_counts": inv["unsupported_counts"], "extents": inv["extents"],
            "warnings": inv["warnings"],
            "layout_entity_counts": inv["layout_entity_counts"],
            "unit_suggestion": inv["unit_suggestion"],
            "within_profile": (dxf.stat().st_size <= PROFILE_MAX_MB * 2**20
                               and top_level <= PROFILE_MAX_ENTITIES),
        })
        return row
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_corpus(folder: Path) -> list[dict]:
    rows = []
    for dxf in sorted(folder.glob("*.dxf")):
        print(f"… {dxf.name}", flush=True)
        rows.append(run_one(dxf))
    return rows
