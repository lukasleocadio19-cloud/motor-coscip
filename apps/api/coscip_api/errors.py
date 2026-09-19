"""Erros estruturados (contratos §6). Nenhum erro vira conformidade."""

from __future__ import annotations

import uuid

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        title: str,
        *,
        resource_id: str | None = None,
        required_action: str | None = None,
    ) -> None:
        super().__init__(title)
        self.status = status
        self.code = code
        self.title = title
        self.resource_id = resource_id
        self.required_action = required_action


def not_implemented(backlog_id: str) -> ApiError:
    return ApiError(501, "NOT_IMPLEMENTED", f"Ainda não implementado (backlog {backlog_id})")


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    trace = request.headers.get("X-Trace-Id") or uuid.uuid4().hex[:16]
    body = {
        "type": f"urn:coscip:error:{exc.code.lower().replace('_', '-')}",
        "title": exc.title,
        "status": exc.status,
        "code": exc.code,
        "trace_id": trace,
        "resource_id": exc.resource_id,
        "required_action": exc.required_action,
    }
    return JSONResponse(body, status_code=exc.status, media_type="application/problem+json")
