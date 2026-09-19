"""Fronteira de acesso local (plano §14).

- Serviço somente em loopback; Host validado (anti DNS rebinding).
- Origin validado em toda mutação; CORS restrito.
- Sessão por cookie HttpOnly/SameSite=Strict, obtida trocando token de uso único do launcher.
- CSRF por double-submit (cookie legível + cabeçalho X-CSRF-Token).
Conteúdo de outro site não pode comandar o motor só porque ele escuta em localhost.
"""

from __future__ import annotations

import hmac
import secrets
import threading
from dataclasses import dataclass, field

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

SESSION_COOKIE = "coscip_session"
CSRF_COOKIE = "coscip_csrf"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
PUBLIC_PATHS = {"/v1/local/status", "/v1/local/session/exchange"}


@dataclass
class SessionStore:
    launch_token: str | None
    _sessions: dict[str, str] = field(default_factory=dict)  # sessão → csrf
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def exchange(self, token: str) -> tuple[str, str] | None:
        """Consome o token de uso único e emite sessão + CSRF."""
        with self._lock:
            if not self.launch_token or not hmac.compare_digest(token, self.launch_token):
                return None
            self.launch_token = None
            sid, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            self._sessions[sid] = csrf
            return sid, csrf

    def csrf_for(self, sid: str | None) -> str | None:
        return self._sessions.get(sid) if sid else None


def _deny(status: int, code: str, title: str) -> JSONResponse:
    return JSONResponse(
        {"type": f"urn:coscip:error:{code.lower()}", "title": title, "status": status,
         "code": code},
        status_code=status,
        media_type="application/problem+json",
    )


class LocalBoundaryMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, allowed_hosts: set[str], allowed_origins: set[str],
                 sessions: SessionStore) -> None:  # noqa: ANN001
        super().__init__(app)
        self.allowed_hosts = allowed_hosts
        self.allowed_origins = allowed_origins
        self.sessions = sessions

    async def dispatch(self, request: Request, call_next):  # noqa: ANN001
        host = request.headers.get("host", "")
        if host not in self.allowed_hosts:
            return _deny(403, "HOST_REJECTED", "Host não permitido")

        path = request.url.path
        if not path.startswith("/v1/"):
            return await call_next(request)  # interface estática

        if request.method not in SAFE_METHODS:
            origin = request.headers.get("origin")
            if origin is None or origin not in self.allowed_origins:
                return _deny(403, "ORIGIN_REJECTED", "Origem não permitida")

        if path in PUBLIC_PATHS:
            return await call_next(request)

        sid = request.cookies.get(SESSION_COOKIE)
        csrf = self.sessions.csrf_for(sid)
        if csrf is None:
            return _deny(401, "SESSION_REQUIRED", "Sessão local ausente ou expirada")
        if request.method not in SAFE_METHODS:
            sent = request.headers.get(CSRF_HEADER, "")
            if not hmac.compare_digest(sent, csrf):
                return _deny(403, "CSRF_REJECTED", "Token CSRF inválido")
        return await call_next(request)


def allowed_for(port: int, dev_origin: str | None) -> tuple[set[str], set[str]]:
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    origins = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
    if dev_origin:
        origins.add(dev_origin)
        hosts.add(dev_origin.split("://", 1)[1])
    return hosts, origins
