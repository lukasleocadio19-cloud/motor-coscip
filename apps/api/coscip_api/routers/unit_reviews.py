"""Revisão humana da referência de unidade, vinculada ao quadro confirmado."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from coscip_api.db import write_tx
from coscip_api.deps import AppState, db, state
from coscip_api.errors import ApiError
from coscip_api.model_state import current_frame, latest_snapshot
from coscip_api.models import AuditEvent, Correction, Drawing, Project, SubmissionRevision, User
from coscip_api.routers.drawings import _drawing, _drawing_out

router = APIRouter()


def review_details(s: Session, d: Drawing) -> dict:
    frame = current_frame(s, d.id)
    events = s.scalars(select(Correction).where(
        Correction.tenant_id == d.tenant_id, Correction.target_id == d.id,
        Correction.operation.in_(["CONFIRM_DRAWING_UNIT", "REVIEW_DRAWING_UNIT"]),
    ).order_by(Correction.created_at.desc(), Correction.id.desc())).all()
    confirmation = next((c for c in events if c.operation == "CONFIRM_DRAWING_UNIT"
                         and (c.new_value or {}).get("frame_id") == (frame.id if frame else None)),
                        None)
    review = next((c for c in events if c.operation == "REVIEW_DRAWING_UNIT"
                   and (c.new_value or {}).get("confirmation_id") ==
                   (confirmation.id if confirmation else None)), None)
    author = s.get(User, confirmation.author_id) if confirmation else None
    return {
        "confirmation": None if confirmation is None else {
            "id": confirmation.id, "frame_id": frame.id,
            "author": author.name if author else "Operador local",
            "author_id": confirmation.author_id,
            "created_at": confirmation.created_at.isoformat(),
            "justification": confirmation.justification,
            "reference": (confirmation.new_value or {}).get("reference"),
        },
        "review": None if review is None else {
            "id": review.id, "reviewer_name": review.new_value["reviewer_name"],
            "justification": review.justification, "created_at": review.created_at.isoformat(),
        },
        "status": "ACCEPTED" if review else "PENDING" if confirmation else "UNCONFIRMED",
    }


@router.get("/unit-reviews")
def list_unit_reviews(st: AppState = Depends(state), s: Session = Depends(db),
                      offset: int = Query(default=0, ge=0),
                      limit: int = Query(default=50, ge=1, le=100)):
    rows = s.execute(select(Drawing, SubmissionRevision, Project)
                     .join(SubmissionRevision, Drawing.revision_id == SubmissionRevision.id)
                     .join(Project, SubmissionRevision.project_id == Project.id)
                     .where(Drawing.tenant_id == st.tenant_id,
                            SubmissionRevision.tenant_id == st.tenant_id,
                            Project.tenant_id == st.tenant_id)
                     .order_by(Project.name, SubmissionRevision.number, Drawing.id)
                     .offset(offset).limit(limit + 1)).all()
    return {"items": [{**_drawing_out(s, d), **review_details(s, d),
                       "project_name": p.name, "revision_number": rev.number}
                      for d, rev, p in rows[:limit]],
            "next_offset": offset + limit if len(rows) > limit else None}


class UnitReviewIn(BaseModel):
    expected_frame_id: str
    confirmation_id: str
    reviewer_name: str = Field(min_length=3, max_length=200)
    justification: str = Field(min_length=10, max_length=2000)
    reference_checked: Literal[True]

    @field_validator("reviewer_name", "justification", mode="before")
    @classmethod
    def trim(cls, value):
        return value.strip() if isinstance(value, str) else value


@router.post("/drawings/{drawing_id}/unit-review", status_code=201)
def accept_unit(drawing_id: str, body: UnitReviewIn, st: AppState = Depends(state)):
    with write_tx(st.session_factory) as s:
        d = _drawing(s, st, drawing_id)
        detail = review_details(s, d)
        confirmation = detail["confirmation"]
        if confirmation is None:
            raise ApiError(409, "DRAWING_UNIT_UNCONFIRMED", "Confirme a unidade antes de revisar")
        if (confirmation["frame_id"] != body.expected_frame_id
                or confirmation["id"] != body.confirmation_id):
            raise ApiError(409, "VERSION_CONFLICT",
                           "A confirmação mudou. Recarregue e confira a nova referência.")
        if detail["review"]:
            return detail  # repetição não gera uma segunda aceitação
        snap = latest_snapshot(s, d.revision_id)
        s.add(Correction(
            tenant_id=st.tenant_id, base_snapshot_id=snap.id, result_snapshot_id=snap.id,
            operation="REVIEW_DRAWING_UNIT", target_id=d.id,
            old_value={"status": "PENDING"},
            new_value={"frame_id": body.expected_frame_id,
                       "confirmation_id": body.confirmation_id,
                       "reviewer_name": body.reviewer_name, "reference_checked": True},
            justification=body.justification, author_id=st.operator_id,
        ))
        s.add(AuditEvent(tenant_id=st.tenant_id, actor_id=st.operator_id,
                         action="drawing.unit_reviewed", resource=d.id,
                         diff={"frame_id": body.expected_frame_id,
                               "reviewer_name": body.reviewer_name}))
        s.flush()
        return review_details(s, d)
