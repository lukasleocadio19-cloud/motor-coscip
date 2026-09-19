"""Estágio IMPORT_DXF: inventário, entidades com identidade de origem, índice e cena."""

from __future__ import annotations

import hashlib
import json
import struct
import time
from collections import Counter
from pathlib import Path

from coscip_cad import DxfReader
from coscip_cad.scene import SceneBuilder
from coscip_cad.unit_evidence import suggest_unit
from coscip_worker.contracts import OUTPUT_FILES, ImportResult, InventoryOut


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
    scene = SceneBuilder(doc)

    quality: Counter[str] = Counter()
    # entities.jsonl: uma entidade por linha; entities.idx: deslocamento (uint64) de cada linha.
    with open(out / "entities.jsonl", "wb") as fe, open(out / "entities.idx", "wb") as fx:
        for row, e in enumerate(reader.entities(doc)):
            quality[e.quality.value] += 1
            scene.add(row, e)
            fx.write(struct.pack("<Q", fe.tell()))
            fe.write(json.dumps({
                "row": row, "handle": e.handle, "type": e.entity_type, "layer": e.layer,
                "source_layer": e.source_layer, "layout": e.layout,
                "instance_path": list(e.instance_path), "block": e.block_name,
                "transform": e.world_transform, "quality": e.quality.value,
                "points": e.points, "text": e.text, "anchor": e.anchor,
            }, ensure_ascii=False).encode("utf-8") + b"\n")

    scene_manifest = scene.write(out)
    if reader.invisible_skipped:
        inv.warnings.append(
            f"{reader.invisible_skipped} entidade(s) invisível(is) ignorada(s) "
            "(estados ocultos de blocos dinâmicos)")
    inventory = InventoryOut(
        dxf_version=inv.dxf_version, insunits=inv.insunits, insunits_name=inv.insunits_name,
        units_declared=inv.units_declared, layouts=inv.layouts, layers=inv.layers,
        blocks=inv.blocks, xrefs=inv.xrefs, entity_counts=inv.entity_counts,
        expanded_count=sum(quality.values()), quality_counts=dict(quality),
        unsupported_counts=inv.unsupported_counts,
        extents=scene_manifest["bbox"] if scene_manifest["segment_count"] else None,
        warnings=inv.warnings,
        layout_entity_counts=inv.layout_entity_counts,
        proxy_object_count=inv.proxy_object_count,
        unit_suggestion=suggest_unit(doc).as_dict(),
    )
    (out / "inventory.json").write_text(inventory.model_dump_json(indent=2), encoding="utf-8")

    return ImportResult(
        job_id=manifest["job_id"], attempt_token=manifest["attempt_token"],
        input_sha256=manifest["input_sha256"], inventory=inventory,
        outputs={name: _sha256(out / name) for name in OUTPUT_FILES},
        scene_segment_count=scene_manifest["segment_count"],
        scene_max_sagitta=scene_manifest["max_sagitta"],
        duration_s=round(time.monotonic() - t0, 3),
    )
