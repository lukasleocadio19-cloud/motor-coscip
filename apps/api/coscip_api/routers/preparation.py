"""Classificação assistida de entidades com confirmação por propriedade (PREP-02)."""
from __future__ import annotations

import copy
import json
import struct
from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from coscip_api.db import write_tx
from coscip_api.deps import AppState, db, state
from coscip_api.errors import ApiError
from coscip_api.model_state import current_frame, derive_snapshot, latest_snapshot, scale_of
from coscip_api.models import AuditEvent, Correction, FileObject, Floor, new_id, utcnow
from coscip_api.routers.drawings import _drawing, _read_entity
from coscip_cbm.enums import ElementClass
from coscip_semantics.classify import classify, has_conflict

router = APIRouter()


def suggestions(ent: dict) -> dict:
    candidates = classify(layer=ent['layer'], block_name=ent.get('block'),
                          attributes={}, mappings=[])
    return {'candidates': [asdict(c) for c in candidates], 'conflict': has_conflict(candidates)}


@router.get('/drawings/{drawing_id}/classification-candidates')
def candidates(drawing_id: str, cursor: int = Query(default=0, ge=0),
               limit: int = Query(default=100, ge=1, le=500),
               st: AppState = Depends(state), s: Session = Depends(db)):
    d = _drawing(s, st, drawing_id)
    arts = d.artifacts or {}
    if 'entities.idx' not in arts:
        raise ApiError(409, 'ENTITIES_NOT_AVAILABLE', 'Reimporte o desenho para classificar')
    idx, data = s.get(FileObject, arts['entities.idx']), s.get(FileObject, arts['entities.jsonl'])
    total = idx.size // 8
    if cursor >= total:
        return {'items': [], 'next_cursor': None, 'total_entities': total}
    with st.storage.open(idx.key) as fi, st.storage.open(data.key) as fe:
        fi.seek(cursor * 8)
        fe.seek(struct.unpack('<Q', fi.read(8))[0])
        items = []
        stop = min(cursor + limit, total)
        for _ in range(cursor, stop):
            ent = json.loads(fe.readline())
            hint = suggestions(ent)
            if hint['candidates'] and ent['type'] in {
                    'LINE', 'LWPOLYLINE', 'POLYLINE', 'ARC', 'CIRCLE', 'ELLIPSE', 'SPLINE'}:
                items.append({'row': ent['row'], 'type': ent['type'], 'handle': ent['handle'],
                              'layer': ent['layer'], 'block': ent.get('block'), **hint})
    return {'items': items, 'next_cursor': stop if stop < total else None,
            'total_entities': total}


@router.get('/drawings/{drawing_id}/entities/{row}/classification')
def classification(drawing_id: str, row: int, st: AppState = Depends(state),
                   s: Session = Depends(db)):
    d = _drawing(s, st, drawing_id)
    ent = _read_entity(st, d, row)
    snap = latest_snapshot(s, d.revision_id)
    elements = (snap.config or {}).get('semantic_elements', {}) if snap else {}
    return {**suggestions(ent), 'model_snapshot_id': snap.id if snap else None,
            'items': [e for e in elements.values()
                      if e['drawing_id'] == d.id and e['entity_row'] == row]}


class PropertyIn(BaseModel):
    floor_id: str
    expected_snapshot_id: str
    property: Literal['element_class', 'name']
    value: str = Field(min_length=1, max_length=200)
    justification: str = Field(min_length=10, max_length=2000)
    source_checked: Literal[True]

    @field_validator('value', 'justification', mode='before')
    @classmethod
    def trim(cls, v):
        return v.strip() if isinstance(v, str) else v


@router.post('/drawings/{drawing_id}/entities/{row}/classification', status_code=201)
def confirm_property(drawing_id: str, row: int, body: PropertyIn,
                     st: AppState = Depends(state)):
    if body.property == 'element_class' and body.value not in {e.value for e in ElementClass}:
        raise ApiError(422, 'INVALID_ELEMENT_CLASS', 'Classe de elemento desconhecida')
    with write_tx(st.session_factory) as s:
        d = _drawing(s, st, drawing_id)
        frame = current_frame(s, d.id)
        if scale_of(frame) is None:
            raise ApiError(409, 'DRAWING_UNIT_UNCONFIRMED', 'Confirme a unidade antes de preparar')
        floor = s.get(Floor, body.floor_id)
        if floor is None or floor.tenant_id != st.tenant_id or floor.drawing_id != d.id:
            raise ApiError(404, 'NOT_FOUND', 'Pavimento não encontrado neste desenho')
        base = latest_snapshot(s, d.revision_id)
        if base is None or base.id != body.expected_snapshot_id:
            raise ApiError(409, 'VERSION_CONFLICT',
                           'A planta mudou. Recarregue antes de confirmar.')
        ent = _read_entity(st, d, row)
        from coscip_api.preparation_geometry import clip_geometry, entity_footprint

        shape = entity_footprint(ent)
        placement_method = 'source-vertices'
        if shape is None:
            # Curvas antigas não possuem vértices exatos no inventário. Usa-se uma caixa
            # conservadora da cena SOMENTE para verificar inclusão no pavimento.
            # Essa caixa não produz áreas nem larguras e a aproximação fica registrada.
            import numpy as np
            from shapely.geometry import box

            arts = d.artifacts or {}
            if 'scene.bin' in arts and 'scene_ids.bin' in arts:
                coords_file = s.get(FileObject, arts['scene.bin'])
                ids_file = s.get(FileObject, arts['scene_ids.bin'])
                with st.storage.open(coords_file.key) as fc, st.storage.open(ids_file.key) as fi:
                    coords = np.frombuffer(fc.read(), dtype='<f4').reshape(-1, 4)
                    ids = np.frombuffer(fi.read(), dtype='<u4')
                selected = coords[ids == row].reshape(-1, 2).astype(float)
                if len(selected):
                    selected += d.scene_manifest['local_origin']
                    lo, hi = selected.min(axis=0), selected.max(axis=0)
                    error = float(d.scene_manifest.get('max_sagitta', 0))
                    error += float(np.max(np.abs(selected))) * 6e-8
                    shape = box(lo[0] - error, lo[1] - error, hi[0] + error, hi[1] + error)
                    placement_method = 'conservative-scene-bounds' 
        if shape is None or not clip_geometry(floor.clip).covers(shape):
            raise ApiError(422, 'ENTITY_OUTSIDE_FLOOR_CLIP',
                           'A entidade precisa estar inteiramente no recorte escolhido')
        elements = copy.deepcopy((base.config or {}).get('semantic_elements', {}))
        key = f'{drawing_id}:{row}:{floor.id}'
        source = s.get(FileObject, d.file_id)
        item = elements.get(key) or {
            'id': new_id(), 'drawing_id': d.id, 'entity_row': row, 'floor_id': floor.id,
            'source': {'file_id': source.id, 'sha256': source.sha256, 'handle': ent['handle'],
                       'instance_path': ent['instance_path'], 'layer': ent['layer'],
                       'block': ent.get('block'), 'layout': ent['layout'],
                       'placement_method': placement_method}, 'properties': {},
        }
        old = copy.deepcopy(item['properties'].get(body.property))
        item['properties'][body.property] = {
            'value': body.value, 'status': 'HUMAN_CONFIRMED', 'provenance': 'CONFIRMED',
            'author_id': st.operator_id, 'confirmed_at': utcnow().isoformat(),
            'justification': body.justification, 'frame_id': frame.id,
        }
        elements[key] = item
        snap = derive_snapshot(s, st.tenant_id, d.revision_id, reason='PROPERTY_CONFIRMED',
                               extra_config={'semantic_elements': elements})
        s.add(Correction(tenant_id=st.tenant_id, base_snapshot_id=base.id,
                         result_snapshot_id=snap.id, operation='CONFIRM_ELEMENT_PROPERTY',
                         target_id=item['id'], old_value=old,
                         new_value={'property': body.property,
                                    **item['properties'][body.property]},
                         justification=body.justification, author_id=st.operator_id))
        s.add(AuditEvent(tenant_id=st.tenant_id, actor_id=st.operator_id,
                         action='element.property_confirmed', resource=item['id'],
                         diff={'property': body.property, 'snapshot_id': snap.id}))
        return {'model_snapshot_id': snap.id, 'element': item}
