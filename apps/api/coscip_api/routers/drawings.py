"""Desenhos importados: unidade (CAD-02), cena (VIEW-01), origem (VIEW-02),
medição e recorte de pavimento (PREP-01).

Regras:
- nenhuma medida em metros antes da confirmação humana da unidade;
- a confirmação exige uma medida de referência real que concorde com a unidade escolhida;
- confirmação e recorte criam novos snapshots; o histórico da importação é preservado;
- medidas usam vértices exatos das entidades quando o clique foi ajustado a um vértice.
"""

from __future__ import annotations

import json
import math
import struct
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from coscip_api.db import write_tx
from coscip_api.deps import AppState, db, state
from coscip_api.errors import ApiError
from coscip_api.model_state import (
    UNIT_NAMES,
    UNIT_SCALE_M,
    current_frame,
    derive_snapshot,
    latest_snapshot,
    scale_of,
)
from coscip_api.models import (
    AuditEvent,
    CoordinateFrame,
    Correction,
    Drawing,
    Execution,
    Floor,
    Measurement,
    ModelSnapshot,
    RevisionFile,
    new_id,
)

router = APIRouter()

REFERENCE_MAX_DEVIATION = 0.02  # 2 %: separa unidades erradas (×10, ×100…) do arredondamento
SNAP_TOLERANCE = 5e-3  # unidades do desenho; ajuste do clique ao vértice exato da entidade
F32_REL = 6e-8  # erro relativo de quantização Float32 da cena


def _drawing(s: Session, st: AppState, drawing_id: str) -> Drawing:
    d = s.get(Drawing, drawing_id)
    if d is None or d.tenant_id != st.tenant_id:
        raise ApiError(404, "NOT_FOUND", "Desenho não encontrado", resource_id=drawing_id)
    return d


def _logical_name(s: Session, d: Drawing) -> str | None:
    return s.scalar(select(RevisionFile.logical_name).where(
        RevisionFile.revision_id == d.revision_id, RevisionFile.file_id == d.file_id))


def _drawing_out(s: Session, d: Drawing) -> dict[str, Any]:
    frame = current_frame(s, d.id)
    floors = s.scalars(select(Floor).where(Floor.drawing_id == d.id)
                       .order_by(Floor.created_at)).all()
    snap = latest_snapshot(s, d.revision_id) if d.revision_id else None
    diag = d.diagnostics or {}
    return {
        "id": d.id, "revision_id": d.revision_id, "file": _logical_name(s, d),
        "cad_version": d.cad_version,
        "declared_unit": diag.get("insunits_name"),
        "unit_suggestion": diag.get("unit_suggestion"),
        "unit": {
            "confirmed": bool(frame and frame.unit_confirmed),
            "frame_id": frame.id if frame else None,
            "scale_to_m": frame.scale_to_m if frame and frame.unit_confirmed else None,
            "unit": _unit_from_scale(frame),
        },
        "scene_available": bool(d.scene_manifest),
        "floors": [{"id": f.id, "name": f.name, "clip": f.clip, "snapshot_id": f.snapshot_id}
                   for f in floors],
        "model_snapshot": {"id": snap.id, "quality": snap.quality} if snap else None,
    }


def _unit_from_scale(frame: CoordinateFrame | None) -> str | None:
    sc = scale_of(frame)
    if sc is None:
        return None
    return next((u for u, f in UNIT_SCALE_M.items() if math.isclose(f, sc)), None)


@router.get("/revisions/{revision_id}/drawings")
def revision_drawings(revision_id: str, st: AppState = Depends(state),
                      s: Session = Depends(db)) -> dict[str, Any]:
    rows = s.scalars(select(Drawing).where(Drawing.revision_id == revision_id,
                                           Drawing.tenant_id == st.tenant_id)
                     .order_by(Drawing.created_at)).all()
    return {"items": [_drawing_out(s, d) for d in rows]}


@router.get("/drawings/{drawing_id}")
def get_drawing(drawing_id: str, st: AppState = Depends(state),
                s: Session = Depends(db)) -> dict[str, Any]:
    return _drawing_out(s, _drawing(s, st, drawing_id))


# --- origem das entidades (VIEW-02) ----------------------------------------
def _read_entity(st: AppState, d: Drawing, row: int) -> dict[str, Any]:
    arts = d.artifacts or {}
    if "entities.idx" not in arts or row < 0:
        raise ApiError(404, "NOT_FOUND", "Entidade não encontrada")
    from coscip_api.models import FileObject

    with st.session_factory() as s:
        idx = s.get(FileObject, arts["entities.idx"])
        jsonl = s.get(FileObject, arts["entities.jsonl"])
    if row * 8 + 8 > idx.size:
        raise ApiError(404, "NOT_FOUND", "Entidade não encontrada")
    with st.storage.open(idx.key) as fx:
        fx.seek(row * 8)
        (offset,) = struct.unpack("<Q", fx.read(8))
    with st.storage.open(jsonl.key) as fe:
        fe.seek(offset)
        return json.loads(fe.readline())


@router.get("/drawings/{drawing_id}/entities/{row}")
def entity_origin(drawing_id: str, row: int, st: AppState = Depends(state),
                  s: Session = Depends(db)) -> dict[str, Any]:
    d = _drawing(s, st, drawing_id)
    ent = _read_entity(st, d, row)
    from coscip_api.models import FileObject

    src = s.get(FileObject, d.file_id)
    return {
        "row": ent["row"], "handle": ent["handle"], "type": ent["type"],
        "layer": ent["layer"], "source_layer": ent.get("source_layer"),
        "layout": ent["layout"], "instance_path": ent["instance_path"],
        "block": ent["block"], "quality": ent["quality"], "text": ent["text"],
        "vertex_count": len(ent["points"]),
        "source_file": {"id": d.file_id, "name": _logical_name(s, d), "sha256": src.sha256},
    }


# --- pontos e medição ------------------------------------------------------
class PointIn(BaseModel):
    x: float
    y: float
    entity_row: int | None = Field(default=None, ge=0)
    pick_tolerance: float = Field(default=0.0, ge=0)  # unidades do desenho (tamanho do pixel)


def _resolve_point(st: AppState, d: Drawing, p: PointIn) -> tuple[float, float, float, bool]:
    """→ (x, y, incerteza em unidades do desenho, ajustado a vértice exato?)."""
    if not (math.isfinite(p.x) and math.isfinite(p.y)):
        raise ApiError(422, "INVALID_POINT", "Coordenada não finita")
    if p.entity_row is not None:
        pts = _read_entity(st, d, p.entity_row).get("points") or []
        best = min(pts, key=lambda q: math.hypot(q[0] - p.x, q[1] - p.y), default=None)
        if best is not None and math.hypot(best[0] - p.x, best[1] - p.y) <= SNAP_TOLERANCE:
            return float(best[0]), float(best[1]), 0.0, True
    quant = (abs(p.x) + abs(p.y)) * F32_REL
    return p.x, p.y, max(p.pick_tolerance, quant), False


def _check_floor(s: Session, d: Drawing, floor_id: str | None,
                 pts: list[tuple[float, float]]) -> None:
    if floor_id is None:
        return
    f = s.get(Floor, floor_id)
    if f is None or f.drawing_id != d.id:
        raise ApiError(404, "NOT_FOUND", "Pavimento não encontrado neste desenho")
    c = f.clip or {}
    for x, y in pts:
        if not (c["x0"] <= x <= c["x1"] and c["y0"] <= y <= c["y1"]):
            raise ApiError(422, "POINT_OUTSIDE_FLOOR_CLIP",
                           "Ponto fora do recorte do pavimento: não entra na medida",
                           resource_id=floor_id)


class MeasureIn(BaseModel):
    a: PointIn
    b: PointIn
    floor_id: str | None = None
    save: bool = False


@router.post("/drawings/{drawing_id}/measure")
def measure(drawing_id: str, body: MeasureIn, st: AppState = Depends(state)) -> dict[str, Any]:
    with st.session_factory() as s:
        d = _drawing(s, st, drawing_id)
        sc = scale_of(current_frame(s, d.id))
        if sc is None:
            raise ApiError(409, "DRAWING_UNIT_UNCONFIRMED",
                           "A unidade do desenho precisa ser confirmada",
                           resource_id=d.id, required_action="CONFIRM_DRAWING_UNIT")
        ax, ay, ua, sa = _resolve_point(st, d, body.a)
        bx, by, ub, sb = _resolve_point(st, d, body.b)
        _check_floor(s, d, body.floor_id, [(ax, ay), (bx, by)])
        dist = math.hypot(bx - ax, by - ay)
        out = {
            "length_m": dist * sc,
            "uncertainty_m": (ua + ub) * sc + 1e-9,
            "drawing_units": dist,
            "scale_to_m": sc,
            "points": [[ax, ay], [bx, by]],
            "snapped_to_vertex": [sa, sb],
            "method": "point-distance/1.0",
            "exploratory": not (sa and sb),
        }
        revision_id = d.revision_id
    if body.save:
        with write_tx(st.session_factory) as w:
            snap = latest_snapshot(w, revision_id)
            m = Measurement(tenant_id=st.tenant_id, snapshot_id=snap.id,
                            subjects=[drawing_id], value=repr(out["length_m"]), unit="m",
                            uncertainty_abs=repr(out["uncertainty_m"]),
                            method=out["method"],
                            dependencies={"points": out["points"],
                                          "snapped": out["snapped_to_vertex"],
                                          "floor_id": body.floor_id,
                                          "entity_rows": [body.a.entity_row, body.b.entity_row]})
            w.add(m)
            w.flush()
            out["measurement_id"] = m.id
    return out


# --- confirmação de unidade (CAD-02) ---------------------------------------
class UnitConfirmationIn(BaseModel):
    unit: Literal["m", "dm", "cm", "mm", "in", "ft"]
    reference_a: PointIn
    reference_b: PointIn
    real_length_m: float = Field(gt=0, lt=100_000)
    justification: str = Field(min_length=10, max_length=2000)
    expected_frame_id: str | None = None


@router.post("/drawings/{drawing_id}/unit-confirmation", status_code=201)
def confirm_unit(drawing_id: str, body: UnitConfirmationIn,
                 st: AppState = Depends(state)) -> dict[str, Any]:
    if not math.isfinite(body.real_length_m):
        raise ApiError(422, "INVALID_REFERENCE", "Medida real deve ser finita e positiva")
    with st.session_factory() as s:
        d = _drawing(s, st, drawing_id)
        ax, ay, ua, _ = _resolve_point(st, d, body.reference_a)
        bx, by, ub, _ = _resolve_point(st, d, body.reference_b)
    dist_units = math.hypot(bx - ax, by - ay)
    if dist_units <= 0:
        raise ApiError(422, "INVALID_REFERENCE", "Os dois pontos de referência coincidem")
    scale = UNIT_SCALE_M[body.unit]
    measured_m = dist_units * scale
    deviation = abs(measured_m - body.real_length_m) / body.real_length_m
    implied = body.real_length_m / dist_units
    if deviation > REFERENCE_MAX_DEVIATION:
        raise ApiError(
            422, "UNIT_REFERENCE_MISMATCH",
            f"Em {UNIT_NAMES[body.unit]}, a referência mede {measured_m:.4g} m, não "
            f"{body.real_length_m:g} m (desvio {deviation:.0%}). Escala implícita: "
            f"{implied:.6g} m por unidade do desenho.",
            resource_id=drawing_id, required_action="CHECK_UNIT_OR_REFERENCE")

    with write_tx(st.session_factory) as s:
        d = _drawing(s, st, drawing_id)
        if d.revision_id is None:
            raise ApiError(409, "DRAWING_WITHOUT_REVISION",
                           "Desenho de versão antiga do importador: reimportar a revisão")
        old = current_frame(s, d.id)
        if body.expected_frame_id and (old is None or old.id != body.expected_frame_id):
            raise ApiError(409, "VERSION_CONFLICT",
                           "O quadro de coordenadas mudou; recarregue antes de confirmar")
        base = latest_snapshot(s, d.revision_id)
        frame = CoordinateFrame(
            tenant_id=st.tenant_id, drawing_id=d.id,
            original_unit=old.original_unit if old else None, unit_confirmed=True,
            scale_to_m=repr(scale), matrix=old.matrix if old else None,
            inverse=old.inverse if old else None,
            local_origin=old.local_origin if old else None)
        s.add(frame)
        s.flush()
        snap = derive_snapshot(s, st.tenant_id, d.revision_id, reason="UNIT_CONFIRMED")
        reference = {"a": [ax, ay], "b": [bx, by], "drawing_units": dist_units,
                     "measured_m": measured_m, "real_length_m": body.real_length_m,
                     "deviation": deviation,
                     "entity_rows": [body.reference_a.entity_row, body.reference_b.entity_row],
                     "uncertainty_units": ua + ub}
        s.add(Measurement(tenant_id=st.tenant_id, snapshot_id=snap.id, subjects=[d.id],
                          value=repr(measured_m), unit="m",
                          uncertainty_abs=repr((ua + ub) * scale + 1e-9),
                          method="unit-reference/1.0", dependencies=reference))
        s.add(Correction(
            tenant_id=st.tenant_id, base_snapshot_id=base.id if base else snap.id,
            result_snapshot_id=snap.id, operation="CONFIRM_DRAWING_UNIT", target_id=d.id,
            old_value={"frame_id": old.id if old else None,
                       "declared_unit": old.original_unit if old else None,
                       "confirmed": bool(old and old.unit_confirmed)},
            new_value={"frame_id": frame.id, "unit": body.unit, "scale_to_m": scale,
                       "reference": reference},
            justification=body.justification, author_id=st.operator_id))
        # Só a importação DESTE desenho sai de WAITING_INPUT.
        for ex in s.scalars(select(Execution).where(
                Execution.kind == "IMPORT_DXF", Execution.state == "WAITING_INPUT",
                Execution.tenant_id == st.tenant_id)):
            if (ex.payload or {}).get("file_id") == d.file_id and \
                    ex.payload.get("revision_id") == d.revision_id:
                ex.state, ex.error_code = "SUCCEEDED", None
        s.add(AuditEvent(tenant_id=st.tenant_id, actor_id=st.operator_id,
                         action="drawing.unit_confirmed", resource=d.id,
                         diff={"unit": body.unit, "deviation": deviation}))
        s.flush()
        return {"frame_id": frame.id, "unit": body.unit, "scale_to_m": scale,
                "reference_measured_m": measured_m, "deviation": deviation,
                "model_snapshot_id": snap.id, "quality": snap.quality}


# --- cena (VIEW-01) -----------------------------------------------------------
@router.get("/drawings/{drawing_id}/scene")
def drawing_scene(drawing_id: str, st: AppState = Depends(state),
                  s: Session = Depends(db)) -> dict[str, Any]:
    d = _drawing(s, st, drawing_id)
    if not d.scene_manifest:
        raise ApiError(404, "SCENE_NOT_AVAILABLE",
                       "Cena indisponível: reimportar com a versão atual do worker")
    arts = d.artifacts or {}
    return {**d.scene_manifest, "drawing_id": d.id,
            "segments_artifact_id": arts["scene.bin"],
            "entity_ids_artifact_id": arts["scene_ids.bin"]}


# --- pavimentos (PREP-01) -----------------------------------------------------
class ClipIn(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class FloorIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    clip: ClipIn
    elevation_m: float | None = None


@router.post("/drawings/{drawing_id}/floors", status_code=201)
def create_floor(drawing_id: str, body: FloorIn,
                 st: AppState = Depends(state)) -> dict[str, Any]:
    c = body.clip
    vals = (c.x0, c.y0, c.x1, c.y1)
    if not all(math.isfinite(v) for v in vals) or c.x1 <= c.x0 or c.y1 <= c.y0:
        raise ApiError(422, "INVALID_CLIP", "Recorte deve ser um retângulo válido e não vazio")
    with write_tx(st.session_factory) as s:
        d = _drawing(s, st, drawing_id)
        if d.revision_id is None:
            raise ApiError(409, "DRAWING_WITHOUT_REVISION",
                           "Desenho de versão antiga do importador: reimportar a revisão")
        frame = current_frame(s, d.id)
        fid = new_id()
        clip = {"type": "RECT", **c.model_dump()}
        snap = derive_snapshot(s, st.tenant_id, d.revision_id, reason="FLOOR_CLIP",
                               extra_floor={"id": fid, "name": body.name, "drawing_id": d.id,
                                            "clip": clip, "frame_id": frame.id if frame else None})
        f = Floor(id=fid, tenant_id=st.tenant_id, snapshot_id=snap.id, drawing_id=d.id,
                  name=body.name, clip=clip, frame_id=frame.id if frame else None,
                  elevation_m=None if body.elevation_m is None else repr(body.elevation_m))
        s.add(f)
        s.add(AuditEvent(tenant_id=st.tenant_id, actor_id=st.operator_id,
                         action="floor.create", resource=fid, diff={"clip": clip}))
        s.flush()
        return {"id": fid, "name": body.name, "clip": clip, "model_snapshot_id": snap.id}


# --- vistas por snapshot ------------------------------------------------------
def snapshot_for(s: Session, st: AppState, model_id: str) -> ModelSnapshot:
    m = s.get(ModelSnapshot, model_id)
    if m is None or m.tenant_id != st.tenant_id:
        raise ApiError(404, "NOT_FOUND", "Modelo não encontrado")
    return m
