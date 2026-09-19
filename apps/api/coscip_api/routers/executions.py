"""Estado de execuções, eventos SSE e cancelamento. Progresso por estágio, sem % inventada."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from coscip_api.db import write_tx
from coscip_api.deps import AppState, state
from coscip_api.errors import ApiError
from coscip_api.models import Execution
from coscip_cbm import ExecutionState
from coscip_jobs import JobQueue

router = APIRouter()


def _out(ex: Execution) -> dict[str, Any]:
    return {
        "execution_id": ex.id, "kind": ex.kind, "analysis_id": ex.analysis_id,
        "state": ex.state, "stage": ex.stage, "error_code": ex.error_code,
        "progress": {"completed_stages": ex.completed_stages,
                     "planned_stages": ex.planned_stages},
        "created_at": ex.created_at,
    }


def _get(st: AppState, execution_id: str) -> dict[str, Any]:
    with st.session_factory() as s:
        ex = s.get(Execution, execution_id)
        if ex is None or ex.tenant_id != st.tenant_id:
            raise ApiError(404, "NOT_FOUND", "Execução não encontrada", resource_id=execution_id)
        return _out(ex)


@router.get("/executions/{execution_id}")
def get_execution(execution_id: str, st: AppState = Depends(state)) -> dict[str, Any]:
    return _get(st, execution_id)


@router.get("/executions/{execution_id}/events")
async def execution_events(execution_id: str, request: Request,
                           st: AppState = Depends(state)) -> StreamingResponse:
    _get(st, execution_id)

    async def stream():
        seq, last = 0, None
        while not await request.is_disconnected():
            cur = _get(st, execution_id)
            snap = (cur["state"], cur["stage"], cur["progress"]["completed_stages"])
            if snap != last:
                seq += 1
                last = snap
                yield f"id: {seq}\nevent: state\ndata: {json.dumps(cur, default=str)}\n\n"
                if ExecutionState(cur["state"]).is_terminal:
                    return
            await asyncio.sleep(1.0)

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/executions/{execution_id}/cancel", status_code=202)
def cancel_execution(execution_id: str, st: AppState = Depends(state)) -> dict[str, Any]:
    with write_tx(st.session_factory) as s:
        ex = s.get(Execution, execution_id)
        if ex is None or ex.tenant_id != st.tenant_id:
            raise ApiError(404, "NOT_FOUND", "Execução não encontrada")
        if ExecutionState(ex.state).is_terminal:
            return _out(ex)
        ex.state = "CANCEL_REQUESTED" if ex.state == "RUNNING" else "CANCELLED"
        if ex.job_id:
            JobQueue(s.connection().connection.driver_connection).request_cancel(ex.job_id)
        return _out(ex)
