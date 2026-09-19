"""Contornos confirmados e larguras medidas separadamente (PREP-03 / GEO-02/03)."""
from __future__ import annotations

import copy
import math
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from shapely.geometry import Polygon
from sqlalchemy.orm import Session

from coscip_api.db import write_tx
from coscip_api.deps import AppState, db, state
from coscip_api.errors import ApiError
from coscip_api.model_state import current_frame, derive_snapshot, latest_snapshot, scale_of
from coscip_api.models import AuditEvent, Correction, Floor, new_id, utcnow
from coscip_api.preparation_geometry import clip_geometry
from coscip_api.routers.drawings import PointIn, _check_floor, _drawing, _resolve_point

router = APIRouter()


class GeometryIn(BaseModel):
    floor_id: str
    expected_snapshot_id: str
    justification: str = Field(min_length=10, max_length=2000)

    @field_validator('justification', mode='before')
    @classmethod
    def trim(cls, v):
        return v.strip() if isinstance(v, str) else v


class ContourIn(GeometryIn):
    name: str = Field(min_length=1, max_length=100)
    points: list[PointIn] = Field(min_length=3, max_length=256)
    replaces_id: str | None = None

    @field_validator('name', mode='before')
    @classmethod
    def trim_name(cls, v):
        return v.strip() if isinstance(v, str) else v


class DoorWidthIn(GeometryIn):
    element_id: str
    kind: Literal['OPENING', 'LEAF', 'CLEAR']
    a: PointIn
    b: PointIn


def _context(s, st, drawing_id, body):
    d = _drawing(s, st, drawing_id)
    frame = current_frame(s, d.id)
    sc = scale_of(frame)
    if sc is None:
        raise ApiError(409, 'DRAWING_UNIT_UNCONFIRMED', 'Confirme a unidade antes de medir')
    base = latest_snapshot(s, d.revision_id)
    if base is None or base.id != body.expected_snapshot_id:
        raise ApiError(409, 'VERSION_CONFLICT', 'O modelo mudou. Recarregue antes de salvar.')
    floor = s.get(Floor, body.floor_id)
    if floor is None or floor.drawing_id != d.id or floor.tenant_id != st.tenant_id:
        raise ApiError(404, 'NOT_FOUND', 'Pavimento não encontrado neste desenho')
    return d, frame, sc, base, floor


def _save(s, st, d, base, bucket, key, item, justification):
    values = copy.deepcopy((base.config or {}).get(bucket, {}))
    old = values.get(key)
    values[key] = item
    snap = derive_snapshot(s, st.tenant_id, d.revision_id,
                           reason='ANALYTICAL_GEOMETRY_CONFIRMED', extra_config={bucket: values})
    s.add(Correction(tenant_id=st.tenant_id, base_snapshot_id=base.id,
                     result_snapshot_id=snap.id, operation='CONFIRM_ANALYTICAL_GEOMETRY',
                     target_id=item['id'], old_value=old, new_value=item,
                     justification=justification, author_id=st.operator_id))
    s.add(AuditEvent(tenant_id=st.tenant_id, actor_id=st.operator_id,
                     action='geometry.confirmed', resource=item['id'],
                     diff={'kind': bucket, 'snapshot_id': snap.id}))
    return {'model_snapshot_id': snap.id, 'item': item}


@router.get('/drawings/{drawing_id}/preparation')
def preparation_state(drawing_id: str, st: AppState = Depends(state), s: Session = Depends(db)):
    d = _drawing(s, st, drawing_id)
    snap = latest_snapshot(s, d.revision_id)
    cfg = snap.config or {} if snap else {}
    return {'model_snapshot_id': snap.id if snap else None,
            **{key: [e for e in cfg.get(key, {}).values() if e['drawing_id'] == d.id]
               for key in ('semantic_elements', 'analytical_contours', 'door_widths')}}


@router.post('/drawings/{drawing_id}/contours', status_code=201)
def confirm_contour(drawing_id: str, body: ContourIn, st: AppState = Depends(state)):
    with write_tx(st.session_factory) as s:
        d, frame, sc, base, floor = _context(s, st, drawing_id, body)
        resolved = [_resolve_point(st, d, p) for p in body.points]
        pts = [(p[0], p[1]) for p in resolved]
        poly = Polygon(pts)
        if not poly.is_valid or poly.area <= 0 or len(set(pts)) < 3:
            raise ApiError(422, 'INVALID_CONTOUR', 'Contorno inválido, cruzado ou sem área')
        if not clip_geometry(floor.clip).covers(poly):
            raise ApiError(422, 'CONTOUR_OUTSIDE_FLOOR_CLIP', 'Contorno ultrapassa o pavimento')
        cid = body.replaces_id or new_id()
        if body.replaces_id:
            old = (base.config or {}).get('analytical_contours', {}).get(cid)
            if old is None or old['drawing_id'] != d.id or old['floor_id'] != floor.id:
                raise ApiError(404, 'NOT_FOUND', 'Contorno não encontrado neste pavimento')
        radius_m = max(p[2] for p in resolved) * sc
        area_m2 = poly.area * sc * sc
        error = poly.length * sc * radius_m + math.pi * radius_m**2 + 1e-9
        item = {'id': cid, 'drawing_id': d.id, 'floor_id': floor.id, 'frame_id': frame.id,
                'name': body.name, 'points': pts, 'area_m2': area_m2,
                'uncertainty_m2': error, 'perimeter_m': poly.length * sc,
                'method': 'confirmed-polygon/1.0', 'status': 'HUMAN_CONFIRMED',
                'exploratory': not all(p[3] for p in resolved),
                'entity_rows': [p.entity_row for p in body.points],
                'author_id': st.operator_id, 'confirmed_at': utcnow().isoformat(),
                'justification': body.justification}
        return _save(s, st, d, base, 'analytical_contours', cid, item, body.justification)


@router.post('/drawings/{drawing_id}/door-widths', status_code=201)
def confirm_width(drawing_id: str, body: DoorWidthIn, st: AppState = Depends(state)):
    with write_tx(st.session_factory) as s:
        d, frame, sc, base, floor = _context(s, st, drawing_id, body)
        element = next((e for e in (base.config or {}).get('semantic_elements', {}).values()
                        if e['id'] == body.element_id and e['drawing_id'] == d.id
                        and e['floor_id'] == floor.id), None)
        cls = element['properties'].get('element_class', {}) if element else {}
        if cls.get('value') != 'DOOR' or cls.get('status') != 'HUMAN_CONFIRMED':
            raise ApiError(409, 'DOOR_CLASSIFICATION_REQUIRED',
                           'Selecione uma porta com classe confirmada neste pavimento')
        a, b = _resolve_point(st, d, body.a), _resolve_point(st, d, body.b)
        pts = [(a[0], a[1]), (b[0], b[1])]
        _check_floor(s, d, floor.id, pts)
        value = math.dist(pts[0], pts[1]) * sc
        if value <= 0:
            raise ApiError(422, 'INVALID_WIDTH', 'Selecione dois pontos diferentes')
        key = f'{element["id"]}:{body.kind}'
        old = (base.config or {}).get('door_widths', {}).get(key)
        item = {'id': old['id'] if old else new_id(), 'drawing_id': d.id,
                'floor_id': floor.id, 'frame_id': frame.id, 'element_id': element['id'],
                'kind': body.kind, 'value_m': value, 'points': pts,
                'uncertainty_m': (a[2] + b[2]) * sc + 1e-9,
                'method': 'confirmed-door-width/1.0', 'status': 'HUMAN_CONFIRMED',
                'exploratory': not (a[3] and b[3]),
                'entity_rows': [body.a.entity_row, body.b.entity_row],
                'author_id': st.operator_id, 'confirmed_at': utcnow().isoformat(),
                'justification': body.justification}
        return _save(s, st, d, base, 'door_widths', key, item, body.justification)
