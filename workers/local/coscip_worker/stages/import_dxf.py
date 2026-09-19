"""Estágio IMPORT_DXF: inventário + dump de entidades com identidade de origem."""

from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from pathlib import Path

from coscip_cad import DxfReader
from coscip_cad.unit_evidence import suggest_unit
from coscip_worker.contracts import ImportResult, InventoryOut


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(manifest: dict, workdir: Path) -> ImportResult:
    t0 = time.monotonic()
    src = workdir / manifest["input"]
    out = workdir / manifest["output_dir"]
    if _sha256(src) != manifest["input_sha256"]:
        raise RuntimeError("entrada não confere com o SHA-256 do manifesto")

    reader = DxfReader(max_expanded=manifest["max_expanded"])
    doc = reader.open(src)
    inv = reader.inventory(doc)

    quality = Counter()
    xs: list[float] = []
    ys: list[float] = []
    entities_path = out / "entities.jsonl"
    with open(entities_path, "w", encoding="utf-8") as fh:
        for e in reader.entities(doc):
            quality[e.quality.value] += 1
            for x, y in e.points:
                xs.append(x)
                ys.append(y)
            fh.write(json.dumps({
                "handle": e.handle, "type": e.entity_type, "layer": e.layer,
                "layout": e.layout, "instance_path": list(e.instance_path),
                "block": e.block_name, "transform": e.world_transform,
                "quality": e.quality.value, "points": e.points, "text": e.text,
            }, ensure_ascii=False) + "\n")

    inventory = InventoryOut(
        dxf_version=inv.dxf_version, insunits=inv.insunits, insunits_name=inv.insunits_name,
        units_declared=inv.units_declared, layouts=inv.layouts, layers=inv.layers,
        blocks=inv.blocks, xrefs=inv.xrefs, entity_counts=inv.entity_counts,
        expanded_count=sum(quality.values()), quality_counts=dict(quality),
        unsupported_counts=inv.unsupported_counts,
        extents=[min(xs), min(ys), max(xs), max(ys)] if xs else None,
        warnings=inv.warnings,
        layout_entity_counts=inv.layout_entity_counts,
        proxy_object_count=inv.proxy_object_count,
        unit_suggestion=suggest_unit(doc).as_dict(),
    )
    (out / "inventory.json").write_text(inventory.model_dump_json(indent=2), encoding="utf-8")

    peak = None
    try:
        import resource  # indisponível no Windows

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    except ImportError:
        pass

    return ImportResult(
        job_id=manifest["job_id"], attempt_token=manifest["attempt_token"],
        input_sha256=manifest["input_sha256"], inventory=inventory,
        entities_file="entities.jsonl", entities_sha256=_sha256(entities_path),
        duration_s=round(time.monotonic() - t0, 3), peak_memory_mb=peak,
    )
