"""Sessão, status, configurações e credenciais locais."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from coscip_api import __version__
from coscip_api.db import write_tx
from coscip_api.deps import AppState, db, state
from coscip_api.errors import ApiError
from coscip_api.models import AuditEvent, BackupRecord, Execution, LocalSetting, User
from coscip_api.security import CSRF_COOKIE, SESSION_COOKIE

router = APIRouter()

KEYRING_SERVICE = "MotorCoscip"
EDITABLE_SETTINGS = {
    "ai_enabled", "ai_provider", "ai_per_analysis_usd", "ai_per_month_usd",
    "worker_memory_mb", "worker_timeout_s", "backup_destination_label",
}


@router.get("/local/status")
def local_status(st: AppState = Depends(state), s: Session = Depends(db)) -> dict[str, Any]:
    queued = s.scalar(
        select(func.count()).select_from(Execution).where(
            Execution.state.in_(["QUEUED", "RUNNING", "CANCEL_REQUESTED"])
        )
    )
    last_backup = s.scalar(
        select(BackupRecord.verified_at).where(BackupRecord.state == "VERIFIED")
        .order_by(BackupRecord.verified_at.desc()).limit(1)
    )
    return {
        "status": "ok",
        "version": __version__,
        "data_dir_label": st.layout.root.name,  # rótulo, não caminho completo
        "queue": {"active_or_waiting": queued},
        "last_verified_backup_at": last_backup,
        "free_disk_bytes": st.storage.free_bytes(),
        "ai_enabled": st.settings.ai_enabled,
    }


class ExchangeIn(BaseModel):
    token: str


@router.post("/local/session/exchange", status_code=204)
def session_exchange(body: ExchangeIn, request: Request, response: Response) -> None:
    pair = request.app.state.sessions.exchange(body.token)
    if pair is None:
        raise ApiError(401, "LAUNCH_TOKEN_INVALID", "Token de abertura inválido ou já usado")
    sid, csrf = pair
    response.set_cookie(SESSION_COOKIE, sid, httponly=True, samesite="strict", path="/")
    # Cookie legível pelo frontend para double-submit; não dá acesso sozinho.
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, samesite="strict", path="/")


@router.get("/me")
def me(st: AppState = Depends(state), s: Session = Depends(db)) -> dict[str, Any]:
    user = s.get(User, st.operator_id)
    return {"operator": {"id": user.id, "name": user.name}, "organization_id": st.tenant_id}


@router.get("/settings")
def get_settings(st: AppState = Depends(state), s: Session = Depends(db)) -> dict[str, Any]:
    stored = {row.key: row.value for row in s.scalars(select(LocalSetting))}
    return {
        "ai_enabled": stored.get("ai_enabled", st.settings.ai_enabled),
        "ai_provider": stored.get("ai_provider"),
        "ai_per_analysis_usd": stored.get("ai_per_analysis_usd", st.settings.ai_per_analysis_usd),
        "ai_per_month_usd": stored.get("ai_per_month_usd", st.settings.ai_per_month_usd),
        "worker_memory_mb": stored.get("worker_memory_mb", st.settings.worker_memory_mb),
        "worker_timeout_s": stored.get("worker_timeout_s", st.settings.worker_timeout_s),
        "credential_ids": stored.get("credential_ids", []),  # nunca a chave
        "backup_destination_label": stored.get("backup_destination_label"),
    }


@router.patch("/settings")
def patch_settings(changes: dict[str, Any], st: AppState = Depends(state)) -> dict[str, Any]:
    unknown = set(changes) - EDITABLE_SETTINGS
    if unknown:
        raise ApiError(422, "SETTING_NOT_EDITABLE", f"Campos não editáveis: {sorted(unknown)}")
    with write_tx(st.session_factory) as s:
        for k, v in changes.items():
            row = s.get(LocalSetting, k)
            before = row.value if row else None
            if row:
                row.value = v
            else:
                s.add(LocalSetting(key=k, value=v))
            s.add(AuditEvent(tenant_id=st.tenant_id, actor_id=st.operator_id,
                             action="settings.update", resource=k,
                             diff={"before": before, "after": v}))
    return {"updated": sorted(changes)}


class CredentialIn(BaseModel):
    provider: str
    secret: str


@router.post("/credentials", status_code=201)
def add_credential(body: CredentialIn, st: AppState = Depends(state)) -> dict[str, str]:
    """Guarda a chave no cofre do Windows (keyring). Resposta traz só ID e máscara."""
    import keyring

    cred_id = f"{body.provider}-{uuid.uuid4().hex[:8]}"
    keyring.set_password(KEYRING_SERVICE, cred_id, body.secret)
    with write_tx(st.session_factory) as s:
        row = s.get(LocalSetting, "credential_ids")
        ids = list(row.value) if row else []
        ids.append(cred_id)
        if row:
            row.value = ids
        else:
            s.add(LocalSetting(key="credential_ids", value=ids))
        s.add(AuditEvent(tenant_id=st.tenant_id, actor_id=st.operator_id,
                         action="credential.add", resource=cred_id))
    return {"id": cred_id, "mask": f"…{body.secret[-4:]}" if len(body.secret) >= 8 else "…"}


@router.delete("/credentials/{cred_id}", status_code=204)
def delete_credential(cred_id: str, st: AppState = Depends(state)) -> None:
    """Remove localmente; NÃO presume revogação no fornecedor."""
    import keyring
    from keyring.errors import PasswordDeleteError

    try:
        keyring.delete_password(KEYRING_SERVICE, cred_id)
    except PasswordDeleteError:
        pass
    with write_tx(st.session_factory) as s:
        row = s.get(LocalSetting, "credential_ids")
        if row:
            row.value = [i for i in row.value if i != cred_id]
        s.add(AuditEvent(tenant_id=st.tenant_id, actor_id=st.operator_id,
                         action="credential.delete", resource=cred_id))
