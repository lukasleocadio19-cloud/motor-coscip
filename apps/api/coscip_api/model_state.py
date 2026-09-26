"""Estado do modelo por revisão: desenhos, quadros de coordenadas, pavimentos e snapshots.

Invariantes (contratos §1):
- snapshot é imutável; toda mudança (importação, confirmação de unidade, recorte) gera um
  novo snapshot com ``parent_id`` apontando para o anterior;
- o quadro de coordenadas também é versionado: confirmar a unidade cria um quadro novo,
  preservando o quadro da importação;
- ``quality.units_confirmed`` só é verdadeiro quando TODOS os DXF analíticos da revisão
  foram importados e tiveram a unidade confirmada. Confirmar um desenho não libera os demais.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any

from sqlalchemy import literal_column, select
from sqlalchemy.orm import Session

from coscip_api.models import (
    CoordinateFrame,
    Drawing,
    Floor,
    ModelSnapshot,
    RevisionFile,
)

IDENTITY = [[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 1.0, 0], [0, 0, 0, 1.0]]

UNIT_SCALE_M: dict[str, float] = {
    "m": 1.0, "dm": 0.1, "cm": 0.01, "mm": 0.001, "in": 0.0254, "ft": 0.3048,
}
UNIT_NAMES = {"m": "metros", "dm": "decímetros", "cm": "centímetros", "mm": "milímetros",
              "in": "polegadas", "ft": "pés"}


def _inserted_last(model):  # noqa: ANN001, ANN202
    """Desempate pela ordem de inserção. No Windows dois registros seguidos podem ter o
    mesmo ``created_at``; desempatar pelo id (UUID aleatório) escolhia ao acaso."""
    return literal_column(f"{model.__tablename__}.rowid").desc()


def current_frame(s: Session, drawing_id: str) -> CoordinateFrame | None:
    return s.scalars(
        select(CoordinateFrame).where(CoordinateFrame.drawing_id == drawing_id)
        .order_by(CoordinateFrame.created_at.desc(), _inserted_last(CoordinateFrame)).limit(1)
    ).first()


def latest_snapshot(s: Session, revision_id: str) -> ModelSnapshot | None:
    return s.scalars(
        select(ModelSnapshot).where(ModelSnapshot.revision_id == revision_id)
        .order_by(ModelSnapshot.created_at.desc(), _inserted_last(ModelSnapshot)).limit(1)
    ).first()


def scale_of(frame: CoordinateFrame | None) -> float | None:
    if frame is None or not frame.unit_confirmed or frame.scale_to_m is None:
        return None
    return float(frame.scale_to_m)


def derive_snapshot(s: Session, tenant_id: str, revision_id: str, reason: str,
                    extra_floor: dict[str, Any] | None = None,
                    extra_config: dict[str, Any] | None = None) -> ModelSnapshot:
    """Cria um novo snapshot refletindo o estado atual da revisão."""
    analytic_files = s.scalars(select(RevisionFile.file_id).where(
        RevisionFile.revision_id == revision_id, RevisionFile.role == "ANALYTIC_DXF")).all()
    drawings = s.scalars(select(Drawing).where(Drawing.revision_id == revision_id)
                         .order_by(Drawing.created_at)).all()
    by_file = {d.file_id: d for d in drawings}

    drawings_cfg: dict[str, Any] = {}
    blocking: list[str] = []
    for fid in analytic_files:
        d = by_file.get(fid)
        if d is None:
            blocking.append(f"IMPORT_PENDING:{fid}")
            continue
        frame = current_frame(s, d.id)
        confirmed = bool(frame and frame.unit_confirmed)
        drawings_cfg[d.id] = {
            "file_id": fid,
            "frame_id": frame.id if frame else None,
            "unit_confirmed": confirmed,
            "scale_to_m": frame.scale_to_m if confirmed else None,
        }
        if not confirmed:
            blocking.append(f"UNIT_UNCONFIRMED:{d.id}")

    floors = [
        {"id": f.id, "name": f.name, "drawing_id": f.drawing_id, "clip": f.clip,
         "frame_id": f.frame_id}
        for f in s.scalars(select(Floor).where(Floor.drawing_id.in_(list(drawings_cfg)))
                           .order_by(Floor.created_at)).all()
    ]
    if extra_floor:
        floors.append(extra_floor)

    parent = latest_snapshot(s, revision_id)
    config = copy.deepcopy(parent.config or {}) if parent else {}
    config.update({"reason": reason, "drawings": drawings_cfg, "floors": floors})
    if extra_config:
        config.update(extra_config)
    # Uma nova unidade exige rever fatos dependentes do referencial anterior.
    for item in config.get("semantic_elements", {}).values():
        current = drawings_cfg.get(item["drawing_id"], {}).get("frame_id")
        for prop in item["properties"].values():
            if prop.get("frame_id") != current:
                prop["status"] = "REVIEW_REQUIRED"
                issue = f"SEMANTICS_STALE:{item['id']}"
                if issue not in blocking:
                    blocking.append(issue)
    for bucket in ("analytical_contours", "door_widths"):
        for item in config.get(bucket, {}).values():
            current = drawings_cfg.get(item["drawing_id"], {}).get("frame_id")
            if item.get("frame_id") != current:
                item["status"] = "REVIEW_REQUIRED"
                blocking.append(f"GEOMETRY_STALE:{item['id']}")
    quality = {
        "units_confirmed": bool(drawings_cfg) and not any(
            b.startswith(("UNIT_UNCONFIRMED", "IMPORT_PENDING")) for b in blocking),
        "blocking_issue_ids": blocking,
        "floor_count": len(floors),
    }
    snap = ModelSnapshot(
        tenant_id=tenant_id, revision_id=revision_id,
        parent_id=parent.id if parent else None, config=config, quality=quality,
        content_sha256=hashlib.sha256(
            json.dumps({"config": config, "quality": quality}, sort_keys=True).encode()
        ).hexdigest(),
    )
    s.add(snap)
    s.flush()
    return snap


def finite_point(p: Any) -> tuple[float, float] | None:
    try:
        x, y = float(p[0]), float(p[1])
    except (TypeError, ValueError, IndexError):
        return None
    return (x, y) if math.isfinite(x) and math.isfinite(y) else None
