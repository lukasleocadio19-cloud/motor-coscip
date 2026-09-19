"""Modelos, análises, resultados, revisão humana, relatórios, regras, consumo e artefatos.

Rotas ainda não construídas respondem 501 com o ID do backlog correspondente.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from coscip_api.db import write_tx
from coscip_api.deps import AppState, db, state
from coscip_api.errors import ApiError, not_implemented
from coscip_api.models import (
    Analysis,
    AuditEvent,
    FileObject,
    ModelSnapshot,
    ReviewDecisionRow,
    RulePackage,
    RuleResultRow,
    SubmissionRevision,
    UsageRecord,
)
from coscip_cbm import ReviewDecision

router = APIRouter()


# --- modelos (CAD-04, PREP-01..04) ----------------------------------------
@router.get("/models/{model_id}")
def get_model(model_id: str, st: AppState = Depends(state), s: Session = Depends(db)):
    m = s.get(ModelSnapshot, model_id)
    if m is None or m.tenant_id != st.tenant_id:
        raise ApiError(404, "NOT_FOUND", "Modelo não encontrado")
    return {"id": m.id, "parent_id": m.parent_id, "cbm_schema": m.cbm_schema,
            "quality": m.quality, "content_sha256": m.content_sha256}


@router.get("/models/{model_id}/floors")
def model_floors(model_id: str, st: AppState = Depends(state), s: Session = Depends(db)):
    from coscip_api.routers.drawings import snapshot_for

    m = snapshot_for(s, st, model_id)
    return {"model_snapshot_id": m.id, "items": (m.config or {}).get("floors", [])}


@router.get("/models/{model_id}/elements")
def model_elements(model_id: str, floor: str | None = None, bbox: str | None = None,
                   cls: str | None = None, cursor: int = 0,
                   st: AppState = Depends(state), s: Session = Depends(db)):
    from coscip_api.routers.drawings import snapshot_for

    m = snapshot_for(s, st, model_id)
    if bbox is not None:
        raise ApiError(422, "UNSUPPORTED_FILTER", "Use o filtro de pavimento")
    if cursor < 0:
        raise ApiError(422, "INVALID_CURSOR", "Página inválida")
    items = list((m.config or {}).get("semantic_elements", {}).values())
    if floor:
        items = [e for e in items if e["floor_id"] == floor]
    if cls:
        items = [e for e in items
                 if e["properties"].get("element_class", {}).get("value") == cls]
    return {"model_snapshot_id": m.id, "items": items[cursor:cursor + 100],
            "next_cursor": cursor + 100 if len(items) > cursor + 100 else None}


@router.get("/models/{model_id}/scene")
def model_scene(model_id: str, st: AppState = Depends(state), s: Session = Depends(db)):
    """Cenas dos desenhos do snapshot; cada uma é servida por /drawings/{id}/scene."""
    from coscip_api.routers.drawings import snapshot_for

    m = snapshot_for(s, st, model_id)
    drawings = (m.config or {}).get("drawings", {})
    return {"model_snapshot_id": m.id,
            "items": [{"drawing_id": did, "scene_url": f"/v1/drawings/{did}/scene",
                       "unit_confirmed": cfg.get("unit_confirmed")}
                      for did, cfg in drawings.items()]}


@router.get("/elements/{element_id}/sources")
def element_sources(element_id: str):
    raise not_implemented("VIEW-02")


@router.post("/models/{model_id}/corrections")
def model_corrections(model_id: str):
    raise not_implemented("PREP-03")


@router.post("/models/{model_id}/confirmations")
def model_confirmations(model_id: str):
    raise not_implemented("PREP-02")


# --- análises -------------------------------------------------------------
class AnalysisIn(BaseModel):
    project_id: str
    submission_revision_id: str
    model_snapshot_id: str
    context_snapshot_id: str
    rule_package_id: str
    mode: str = "ASSISTED"
    ai_enabled: bool = False
    ai_policy_id: str | None = None


@router.post("/analyses", status_code=202)
def create_analysis(body: AnalysisIn, idempotency_key: str = Header(alias="Idempotency-Key"),
                    st: AppState = Depends(state)) -> dict[str, Any]:
    with write_tx(st.session_factory) as s:
        rev = s.get(SubmissionRevision, body.submission_revision_id)
        model = s.get(ModelSnapshot, body.model_snapshot_id)
        pkg = s.get(RulePackage, body.rule_package_id)
        if not rev or rev.tenant_id != st.tenant_id or rev.project_id != body.project_id:
            raise ApiError(422, "INCOHERENT_REFERENCES", "Revisão não pertence ao projeto")
        if not model or model.revision_id != rev.id:
            raise ApiError(422, "INCOHERENT_REFERENCES", "Modelo não pertence à revisão")
        if not pkg:
            raise ApiError(422, "INCOHERENT_REFERENCES", "Pacote normativo inexistente")
        quality = model.quality or {}
        if not quality.get("units_confirmed"):
            raise ApiError(409, "DRAWING_UNIT_UNCONFIRMED",
                           "A unidade do desenho precisa ser confirmada",
                           resource_id=model.id, required_action="CONFIRM_DRAWING_UNIT")
        if quality.get("blocking_issue_ids"):
            raise ApiError(409, "MODEL_HAS_BLOCKING_ISSUES", "Modelo com bloqueios abertos",
                           resource_id=model.id, required_action="RESOLVE_BLOCKING_ISSUES")
        if body.ai_enabled and not body.ai_policy_id:
            raise ApiError(422, "AI_POLICY_REQUIRED", "IA habilitada exige política cadastrada")
    # Execução do motor de regras sobre o modelo congelado: REG-04..REG-06.
    raise not_implemented("REG-04")


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: str, st: AppState = Depends(state), s: Session = Depends(db)):
    a = s.get(Analysis, analysis_id)
    if a is None or a.tenant_id != st.tenant_id:
        raise ApiError(404, "NOT_FOUND", "Análise não encontrada")
    return {"id": a.id, "state": a.state, "model_snapshot_id": a.model_snapshot_id,
            "rule_package_id": a.rule_package_id, "ai_enabled": a.ai_enabled}


@router.get("/analyses/{analysis_id}/results")
def analysis_results(analysis_id: str, status: str | None = None, limit: int = 100,
                     st: AppState = Depends(state), s: Session = Depends(db)):
    stmt = select(RuleResultRow).where(RuleResultRow.tenant_id == st.tenant_id,
                                       RuleResultRow.analysis_id == analysis_id)
    if status:
        stmt = stmt.where(RuleResultRow.status == status)
    rows = s.scalars(stmt.limit(min(limit, 500))).all()
    return {"items": [{"id": r.id, "subject_id": r.subject_id, "status": r.status,
                       "applicability": r.applicability, "reason_code": r.reason_code,
                       "values": r.values} for r in rows]}


@router.get("/results/{result_id}/evidence")
def result_evidence(result_id: str):
    raise not_implemented("REG-06")


class ReviewIn(BaseModel):
    decision: ReviewDecision
    # Veredito do analista: obrigatório ao confirmar/contestar, ausente ao pedir dado.
    final_status: Literal["PASS", "FAIL", "NOT_APPLICABLE"] | None = None
    justification: str = Field(min_length=3, max_length=2000)
    extra_evidence_ids: list[str] = []


@router.post("/results/{result_id}/reviews", status_code=201)
def add_review(result_id: str, body: ReviewIn, st: AppState = Depends(state)):
    """Append-only: a decisão humana não reescreve o cálculo."""
    with write_tx(st.session_factory) as s:
        r = s.get(RuleResultRow, result_id)
        if r is None or r.tenant_id != st.tenant_id:
            raise ApiError(404, "NOT_FOUND", "Resultado não encontrado")
        needs_verdict = body.decision in (ReviewDecision.CONFIRM, ReviewDecision.CONTEST)
        if needs_verdict != (body.final_status is not None):
            raise ApiError(422, "INVALID_REVIEW",
                           "Confirmar ou contestar exige o veredito; pedir dado não leva veredito")
        d = ReviewDecisionRow(tenant_id=st.tenant_id, result_id=result_id,
                              decision=body.decision, final_status=body.final_status,
                              justification=body.justification.strip(),
                              author_id=st.operator_id,
                              extra_evidence_ids=body.extra_evidence_ids)
        s.add(d)
        s.flush()
        s.add(AuditEvent(tenant_id=st.tenant_id, actor_id=st.operator_id,
                         action="review.decision_added", resource=result_id,
                         diff={"decision": d.decision, "final_status": d.final_status}))
        return {"id": d.id, "decision": d.decision, "final_status": d.final_status}


# --- relatórios, regras, consumo -----------------------------------------
@router.post("/reports", status_code=202)
def create_report():
    raise not_implemented("REP-01")


@router.get("/reports/{report_id}")
def get_report(report_id: str):
    raise not_implemented("REP-01")


@router.post("/rule-packages/{package_id}/publish")
def publish_rule_package(package_id: str):
    raise not_implemented("REG-06")


@router.get("/projects/{project_id}/usage")
def project_usage(project_id: str, st: AppState = Depends(state), s: Session = Depends(db)):
    rows = s.scalars(select(UsageRecord).where(UsageRecord.tenant_id == st.tenant_id,
                                               UsageRecord.project_id == project_id)).all()
    return {"items": [{"provider": u.provider, "model": u.model_returned,
                       "cost_usd": u.cost_usd, "created_at": u.created_at} for u in rows],
            "ai_enabled": st.settings.ai_enabled}


# --- artefatos -----------------------------------------------------------
@router.get("/artifacts/{artifact_id}/content")
def artifact_content(artifact_id: str, st: AppState = Depends(state),
                     s: Session = Depends(db)) -> StreamingResponse:
    """Download mediado por ID; o navegador nunca recebe caminho do disco."""
    fo = s.get(FileObject, artifact_id)
    if fo is None or fo.tenant_id != st.tenant_id:
        raise ApiError(404, "NOT_FOUND", "Artefato não encontrado")
    fh = st.storage.open(fo.key)
    return StreamingResponse(iter(lambda: fh.read(1024 * 1024), b""),
                             media_type=fo.mime or "application/octet-stream",
                             headers={"X-Content-SHA256": fo.sha256})
