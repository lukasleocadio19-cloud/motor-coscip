"""Relatório HTML imutável de preparação; não emite avaliação normativa."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select

from coscip_api.db import write_tx
from coscip_api.deps import AppState, state
from coscip_api.models import (
    AuditEvent,
    Correction,
    FileObject,
    Project,
    RevisionFile,
    SubmissionRevision,
    new_id,
    utcnow,
)
from coscip_api.routers.drawings import snapshot_for

router = APIRouter()
TEMPLATES = Path(__file__).resolve().parents[1] / 'templates'


@router.post('/models/{model_id}/preparation-report', status_code=201)
def preparation_report(model_id: str, st: AppState = Depends(state)):
    with st.session_factory() as s:
        model = snapshot_for(s, st, model_id)
        rev = s.get(SubmissionRevision, model.revision_id)
        project = s.get(Project, rev.project_id)
        cfg = model.config or {}
        drawings = []
        for did, drawing in cfg.get('drawings', {}).items():
            file = s.get(FileObject, drawing['file_id'])
            name = s.scalar(select(RevisionFile.logical_name).where(
                RevisionFile.revision_id == rev.id, RevisionFile.file_id == file.id))
            corrections = s.scalars(select(Correction).where(
                Correction.tenant_id == st.tenant_id, Correction.target_id == did)
                .order_by(Correction.created_at.desc())).all()
            confirmation = next((c for c in corrections if c.operation == 'CONFIRM_DRAWING_UNIT'
                                 and (c.new_value or {}).get('frame_id') == drawing['frame_id']),
                                None)
            review = next((c for c in corrections if c.operation == 'REVIEW_DRAWING_UNIT'
                           and (c.new_value or {}).get('confirmation_id') ==
                           (confirmation.id if confirmation else None)), None)
            drawings.append({'id': did, 'name': name, 'sha256': file.sha256, **drawing,
                             'confirmation': confirmation, 'review': review})
        report_id = new_id()
        issued_at = utcnow().isoformat()
        details = json.dumps({'model_snapshot_id': model.id,
                              'model_sha256': model.content_sha256,
                              'config': cfg, 'quality': model.quality},
                             ensure_ascii=False, indent=2)
        env = Environment(loader=FileSystemLoader(TEMPLATES),
                          autoescape=select_autoescape(['html']))
        html = env.get_template('preparation-report.html').render(
            report_id=report_id, issued_at=issued_at, project=project, revision=rev,
            model=model, drawings=drawings, cfg=cfg, details=details)
        key = f'projects/{project.id}/reports/{report_id}.html'
    obj = st.storage.write_stream(key, [html.encode('utf-8')])
    with write_tx(st.session_factory) as s:
        file = FileObject(tenant_id=st.tenant_id, key=obj.key, sha256=obj.sha256,
                          size=obj.size, mime='text/html', inspection={
                              'report_id': report_id, 'model_snapshot_id': model_id,
                              'kind': 'PREPARATION', 'issued_at': issued_at})
        s.add(file)
        s.flush()
        s.add(AuditEvent(tenant_id=st.tenant_id, actor_id=st.operator_id,
                         action='report.preparation_created', resource=report_id,
                         diff={'model_snapshot_id': model_id, 'artifact_id': file.id,
                               'sha256': obj.sha256}))
        return {'id': report_id, 'artifact_id': file.id, 'sha256': obj.sha256,
                'model_snapshot_id': model_id, 'content_url': f'/v1/artifacts/{file.id}/content'}
