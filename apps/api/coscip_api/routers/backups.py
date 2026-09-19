from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from coscip_api.backup import BackupIncomplete, create_backup
from coscip_api.db import write_tx
from coscip_api.deps import AppState, db, state
from coscip_api.errors import ApiError
from coscip_api.models import BackupRecord, LocalSetting

router = APIRouter()


@router.post("/backups", status_code=201)
def run_backup(st: AppState = Depends(state), s: Session = Depends(db)) -> dict[str, Any]:
    """Cópia para destino PREVIAMENTE cadastrado localmente; a página não envia caminho."""
    dest_row = s.get(LocalSetting, "backup_destination_path")
    if dest_row is None or not dest_row.value:
        raise ApiError(409, "BACKUP_DESTINATION_MISSING",
                       "Cadastre o destino de backup pelo launcher",
                       required_action="CONFIGURE_BACKUP_DESTINATION")
    dest_root = Path(str(dest_row.value))
    label_row = s.get(LocalSetting, "backup_destination_label")
    label = str(label_row.value) if label_row else dest_root.name
    try:
        out = create_backup(st.layout, dest_root)
        state_, verified = "VERIFIED", datetime.now(UTC)
    except (BackupIncomplete, OSError) as exc:
        with write_tx(st.session_factory) as w:
            w.add(BackupRecord(manifest_path="", destination_label=label, state="INCOMPLETE"))
        raise ApiError(500, "BACKUP_INCOMPLETE", f"Backup incompleto: {exc}") from exc
    with write_tx(st.session_factory) as w:
        rec = BackupRecord(manifest_path=str(out / "manifest.json"), destination_label=label,
                           state=state_, verified_at=verified)
        w.add(rec)
        w.flush()
        return {"id": rec.id, "state": rec.state, "destination_label": label,
                "verified_at": verified}


@router.get("/backups/{backup_id}")
def get_backup(backup_id: str, s: Session = Depends(db)) -> dict[str, Any]:
    rec = s.get(BackupRecord, backup_id)
    if rec is None:
        raise ApiError(404, "NOT_FOUND", "Backup não encontrado")
    return {"id": rec.id, "state": rec.state, "destination_label": rec.destination_label,
            "verified_at": rec.verified_at, "created_at": rec.created_at}
