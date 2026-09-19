"""Estágio PLANT_ANALYSIS: símbolos, áreas, percursos e regras sobre o DXF confirmado.

Recebe tudo pelo manifesto (regras DSL, dicionário, contexto, recortes, escala); não acessa
banco nem rede. A saída é um único ``analysis.json`` conferido por hash pelo supervisor.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from coscip_analysis import AnalysisInput, RuleBinding, parse_dictionary
from coscip_analysis import run as analyze
from coscip_rules.dsl import parse_rule
from coscip_worker.contracts import PlantAnalysisResult


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(manifest: dict, workdir: Path) -> PlantAnalysisResult:
    t0 = time.monotonic()
    src = workdir / manifest["input"]
    out = workdir / manifest["output_dir"]
    if _sha256(src) != manifest["input_sha256"]:
        raise RuntimeError("entrada não confere com o SHA-256 do manifesto")
    inp = AnalysisInput(
        dxf=src,
        scale_to_m=float(manifest["scale_to_m"]),
        dictionary=parse_dictionary(manifest["symbols"]),
        rules=[RuleBinding(parse_rule(r["dsl"]), r["rule_version_id"], r["citations"])
               for r in manifest["rules"]],
        context=manifest["context"],
        floors=manifest.get("floors") or [],
        symbol_overrides=manifest.get("symbol_overrides") or {},
        obstacle_layers=manifest.get("obstacle_layers"),
        max_expanded=int(manifest["max_expanded"]),
    )
    data = analyze(inp)
    data["analysis_id"] = manifest["analysis_id"]
    path = out / "analysis.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return PlantAnalysisResult(
        job_id=manifest["job_id"], attempt_token=manifest["attempt_token"],
        input_sha256=manifest["input_sha256"], outputs={"analysis.json": _sha256(path)},
        summary=data["summary"], duration_s=round(time.monotonic() - t0, 3),
    )
