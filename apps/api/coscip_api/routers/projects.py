"""Projetos, revisões, upload em partes, selagem e importação DXF."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from coscip_api.db import write_tx
from coscip_api.deps import AppState, db, state
from coscip_api.errors import ApiError
from coscip_api.models import (
    AuditEvent,
    Drawing,
    Execution,
    FileObject,
    Project,
    RevisionFile,
    SubmissionRevision,
    UploadSession,
)
from coscip_jobs import JobQueue

router = APIRouter()

ROLES = {"ANALYTIC_DXF", "XREF_DXF", "SOURCE_DWG", "DOCUMENT"}
ALLOWED_EXT = {"ANALYTIC_DXF": {".dxf"}, "XREF_DXF": {".dxf"}, "SOURCE_DWG": {".dwg"},
               "DOCUMENT": {".pdf", ".txt"}}
MAX_PART = 16 * 1024 * 1024


def _project(s: Session, st: AppState, project_id: str) -> Project:
    p = s.get(Project, project_id)
    if p is None or p.tenant_id != st.tenant_id:
        raise ApiError(404, "NOT_FOUND", "Projeto não encontrado", resource_id=project_id)
    return p


def _revision(s: Session, st: AppState, revision_id: str) -> SubmissionRevision:
    r = s.get(SubmissionRevision, revision_id)
    if r is None or r.tenant_id != st.tenant_id:
        raise ApiError(404, "NOT_FOUND", "Revisão não encontrada", resource_id=revision_id)
    return r


def _project_out(p: Project) -> dict[str, Any]:
    return {"id": p.id, "name": p.name, "external_ref": p.external_ref, "address": p.address,
            "responsible": p.responsible, "row_version": p.row_version,
            "created_at": p.created_at}


# --- projetos --------------------------------------------------------------
class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    external_ref: str | None = None
    address: str | None = None
    responsible: str | None = None


@router.get("/projects")
def list_projects(
    q: str | None = None, limit: int = 50, cursor: str | None = None,
    st: AppState = Depends(state), s: Session = Depends(db),
) -> dict[str, Any]:
    stmt = select(Project).where(Project.tenant_id == st.tenant_id)
    if q:
        stmt = stmt.where(Project.name.ilike(f"%{q}%"))
    if cursor:
        stmt = stmt.where(Project.created_at < cursor)
    rows = s.scalars(stmt.order_by(Project.created_at.desc()).limit(min(limit, 200))).all()
    nxt = rows[-1].created_at.isoformat() if len(rows) == min(limit, 200) else None
    return {"items": [_project_out(p) for p in rows], "next_cursor": nxt}


@router.post("/projects", status_code=201)
def create_project(body: ProjectIn, st: AppState = Depends(state)) -> dict[str, Any]:
    with write_tx(st.session_factory) as s:
        p = Project(tenant_id=st.tenant_id, **body.model_dump())
        s.add(p)
        s.flush()
        s.add(AuditEvent(tenant_id=st.tenant_id, actor_id=st.operator_id,
                         action="project.create", resource=p.id))
        return _project_out(p)


@router.patch("/projects/{project_id}")
def patch_project(
    project_id: str, body: dict[str, Any], if_match: int = Header(alias="If-Match"),
    st: AppState = Depends(state),
) -> dict[str, Any]:
    allowed = {"name", "external_ref", "address", "responsible"}
    if set(body) - allowed:
        raise ApiError(422, "FIELD_NOT_EDITABLE", "Campo não editável")
    with write_tx(st.session_factory) as s:
        p = _project(s, st, project_id)
        if p.row_version != if_match:
            raise ApiError(409, "VERSION_CONFLICT", "Projeto alterado por outra operação",
                           resource_id=project_id)
        for k, v in body.items():
            setattr(p, k, v)
        p.row_version += 1
        return _project_out(p)


# --- revisões --------------------------------------------------------------
@router.post("/projects/{project_id}/revisions", status_code=201)
def create_revision(project_id: str, st: AppState = Depends(state)) -> dict[str, Any]:
    with write_tx(st.session_factory) as s:
        _project(s, st, project_id)
        last = s.scalar(
            select(func.max(SubmissionRevision.number))
            .where(SubmissionRevision.project_id == project_id)
        )
        prev = s.scalars(
            select(SubmissionRevision).where(SubmissionRevision.project_id == project_id,
                                             SubmissionRevision.number == last)
        ).first() if last else None
        r = SubmissionRevision(tenant_id=st.tenant_id, project_id=project_id,
                               number=(last or 0) + 1, previous_id=prev.id if prev else None)
        s.add(r)
        s.flush()
        return {"id": r.id, "number": r.number, "state": r.state}


@router.get("/projects/{project_id}/revisions")
def list_revisions(project_id: str, st: AppState = Depends(state),
                   s: Session = Depends(db)) -> dict[str, Any]:
    _project(s, st, project_id)
    rows = s.scalars(select(SubmissionRevision).where(
        SubmissionRevision.project_id == project_id).order_by(SubmissionRevision.number)).all()
    return {"items": [{"id": r.id, "number": r.number, "state": r.state,
                       "manifest_sha256": r.manifest_sha256} for r in rows]}


# --- upload ----------------------------------------------------------------
class UploadIn(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    role: str
    size: int = Field(gt=0)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


@router.post("/revisions/{revision_id}/uploads", status_code=201)
def create_upload(revision_id: str, body: UploadIn,
                  st: AppState = Depends(state)) -> dict[str, Any]:
    if body.role not in ROLES:
        raise ApiError(422, "INVALID_ROLE", f"Função inválida: {body.role}")
    ext = Path(body.filename).suffix.lower()
    if ext not in ALLOWED_EXT[body.role]:
        code = "UNSUPPORTED_DWG_INPUT" if ext == ".dwg" else "UNSUPPORTED_FILE_TYPE"
        raise ApiError(422, code, f"Extensão {ext} não aceita para {body.role}",
                       required_action="EXPORT_DXF" if ext == ".dwg" else None)
    if body.size > st.settings.max_upload_bytes:
        raise ApiError(413, "FILE_TOO_LARGE", "Arquivo acima do perfil suportado")
    if st.storage.free_bytes() < body.size * st.settings.disk_reserve_factor:
        raise ApiError(507, "DISK_SPACE_LOW", "Espaço insuficiente para original e derivados")
    with write_tx(st.session_factory) as s:
        r = _revision(s, st, revision_id)
        if r.state != "DRAFT":
            raise ApiError(409, "REVISION_SEALED", "Revisão já selada é imutável")
        u = UploadSession(tenant_id=st.tenant_id, revision_id=revision_id,
                          filename=body.filename, role=body.role, expected_size=body.size,
                          expected_sha256=body.sha256, received_parts={})
        s.add(u)
        s.flush()
        return {"id": u.id, "max_part_bytes": MAX_PART}


def _part_path(st: AppState, upload_id: str, n: int) -> Path:
    d = st.layout.quarantine / upload_id
    d.mkdir(parents=True, exist_ok=True)
    return d / f"part-{n:05d}"


@router.put("/uploads/{upload_id}/parts/{number}")
async def put_part(upload_id: str, number: int, request: Request,
                   x_part_sha256: str = Header(alias="X-Part-SHA256"),
                   st: AppState = Depends(state)) -> dict[str, Any]:
    if not 1 <= number <= 10_000:
        raise ApiError(422, "INVALID_PART", "Número de parte inválido")
    with st.session_factory() as s:
        u = s.get(UploadSession, upload_id)
        if u is None or u.tenant_id != st.tenant_id or u.state != "OPEN":
            raise ApiError(404, "NOT_FOUND", "Sessão de upload inexistente ou encerrada")
    dest = _part_path(st, upload_id, number)
    tmp = dest.with_suffix(".tmp")
    h, size = hashlib.sha256(), 0
    with open(tmp, "wb") as out:
        async for chunk in request.stream():  # streaming: não carrega o arquivo inteiro
            size += len(chunk)
            if size > MAX_PART:
                out.close()
                tmp.unlink(missing_ok=True)
                raise ApiError(413, "PART_TOO_LARGE", "Parte acima do limite")
            h.update(chunk)
            out.write(chunk)
    if h.hexdigest() != x_part_sha256.lower():
        tmp.unlink(missing_ok=True)
        raise ApiError(422, "PART_CHECKSUM_MISMATCH", "Checksum da parte não confere")
    tmp.replace(dest)
    with write_tx(st.session_factory) as s:
        u = s.get(UploadSession, upload_id)
        parts = dict(u.received_parts)
        parts[str(number)] = {"sha256": h.hexdigest(), "size": size}
        u.received_parts = parts
    return {"number": number, "size": size}


@router.post("/uploads/{upload_id}/complete")
def complete_upload(upload_id: str, st: AppState = Depends(state)) -> dict[str, Any]:
    with st.session_factory() as s:
        u = s.get(UploadSession, upload_id)
        if u is None or u.tenant_id != st.tenant_id or u.state != "OPEN":
            raise ApiError(404, "NOT_FOUND", "Sessão de upload inexistente ou encerrada")
        rev = s.get(SubmissionRevision, u.revision_id)
        numbers = sorted(int(n) for n in u.received_parts)
        role, filename = u.role, u.filename
        expected_size, expected_sha = u.expected_size, u.expected_sha256
    if numbers != list(range(1, len(numbers) + 1)) or not numbers:
        raise ApiError(409, "PARTS_INCOMPLETE", "Partes ausentes ou fora de sequência")

    def chunks() -> Iterator[bytes]:
        for n in numbers:
            with open(_part_path(st, upload_id, n), "rb") as fh:
                yield from iter(lambda: fh.read(1024 * 1024), b"")

    ext = Path(filename).suffix.lower()
    key = f"projects/{rev.project_id}/originals/{rev.id}/{uuid.uuid4().hex}{ext}"
    obj = st.storage.write_stream(key, chunks())
    if obj.size != expected_size or (expected_sha and obj.sha256 != expected_sha):
        st.storage.resolve(key).unlink(missing_ok=True)
        raise ApiError(422, "FILE_CHECKSUM_MISMATCH", "Tamanho ou SHA-256 não confere")

    with write_tx(st.session_factory) as s:
        fo = FileObject(tenant_id=st.tenant_id, key=key, sha256=obj.sha256, size=obj.size,
                        mime="application/dxf" if ext == ".dxf" else None)
        s.add(fo)
        s.flush()
        s.add(RevisionFile(tenant_id=st.tenant_id, revision_id=rev.id, file_id=fo.id,
                           role=role, logical_name=_safe_name(filename)))
        u = s.get(UploadSession, upload_id)
        u.state, u.file_id = "COMPLETED", fo.id
    for n in numbers:
        _part_path(st, upload_id, n).unlink(missing_ok=True)
    # "complete" não significa arquivo liberado: a inspeção ocorre na importação.
    return {"file_id": fo.id, "sha256": obj.sha256, "size": obj.size, "state": "QUARANTINED"}


@router.post("/uploads/{upload_id}/abort", status_code=204)
def abort_upload(upload_id: str, st: AppState = Depends(state)) -> None:
    with write_tx(st.session_factory) as s:
        u = s.get(UploadSession, upload_id)
        if u is None or u.tenant_id != st.tenant_id:
            raise ApiError(404, "NOT_FOUND", "Sessão de upload inexistente")
        u.state = "ABORTED"
        numbers = [int(n) for n in u.received_parts]
    for n in numbers:
        _part_path(st, upload_id, n).unlink(missing_ok=True)


def _safe_name(name: str) -> str:
    return re.sub(r"[^\w.\- ]", "_", Path(name).name)[:255]


# --- selagem e importação -------------------------------------------------
@router.post("/revisions/{revision_id}/seal")
def seal_revision(revision_id: str, st: AppState = Depends(state)) -> dict[str, Any]:
    with write_tx(st.session_factory) as s:
        r = _revision(s, st, revision_id)
        if r.state != "DRAFT":
            raise ApiError(409, "REVISION_SEALED", "Revisão já selada")
        files = s.execute(
            select(RevisionFile, FileObject).join(FileObject, RevisionFile.file_id == FileObject.id)
            .where(RevisionFile.revision_id == revision_id)
        ).all()
        if not any(rf.role == "ANALYTIC_DXF" for rf, _ in files):
            raise ApiError(422, "NO_ANALYTIC_DXF", "Revisão sem DXF analítico",
                           required_action="UPLOAD_DXF")
        manifest = {
            "revision_id": r.id,
            "files": sorted(
                ({"file_id": fo.id, "role": rf.role, "name": rf.logical_name,
                  "sha256": fo.sha256, "size": fo.size} for rf, fo in files),
                key=lambda f: f["file_id"],
            ),
        }
        r.manifest = manifest
        r.manifest_sha256 = hashlib.sha256(
            json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        r.state = "SEALED"
        return {"id": r.id, "state": r.state, "manifest_sha256": r.manifest_sha256}


@router.post("/revisions/{revision_id}/imports", status_code=202)
def start_import(revision_id: str, idempotency_key: str = Header(alias="Idempotency-Key"),
                 st: AppState = Depends(state)) -> dict[str, Any]:
    with write_tx(st.session_factory) as s:
        r = _revision(s, st, revision_id)
        if r.state != "SEALED":
            raise ApiError(409, "REVISION_NOT_SEALED", "Selar a revisão antes de importar",
                           required_action="SEAL_REVISION")
        existing = s.scalars(select(Execution).where(
            Execution.idempotency_key.like(f"{idempotency_key}:%"))).all()
        if existing:
            if any(e.payload.get("revision_id") != revision_id for e in existing):
                raise ApiError(409, "IDEMPOTENCY_CONFLICT", "Chave reutilizada com outro corpo")
            return _import_out(existing)
        dxfs = s.execute(
            select(RevisionFile, FileObject).join(FileObject, RevisionFile.file_id == FileObject.id)
            .where(RevisionFile.revision_id == revision_id, RevisionFile.role == "ANALYTIC_DXF")
            .order_by(FileObject.id)
        ).all()
        raw = s.connection().connection.driver_connection
        created = []
        # Uma execução por DXF analítico: cada desenho tem estado e confirmação próprios.
        for _rf, fo in dxfs:
            payload = {"revision_id": r.id, "project_id": r.project_id, "file_id": fo.id,
                       "file_key": fo.key, "file_sha256": fo.sha256}
            key = f"{idempotency_key}:{fo.id}"
            ex = Execution(tenant_id=st.tenant_id, kind="IMPORT_DXF", state="QUEUED",
                           idempotency_key=key, payload=payload, planned_stages=2)
            s.add(ex)
            s.flush()
            # Intenção de job na MESMA transação dos metadados.
            ex.job_id = JobQueue(raw).enqueue("IMPORT_DXF", {"execution_id": ex.id, **payload},
                                              f"import:{key}")
            created.append(ex)
        return _import_out(created)


def _import_out(executions: list[Execution]) -> dict[str, Any]:
    first = _exec_out(executions[0])
    return {**first, "executions": [_exec_out(e) for e in executions]}


def _exec_out(ex: Execution) -> dict[str, Any]:
    return {"execution_id": ex.id, "state": ex.state, "runner": ex.runner,
            "status_url": f"/v1/executions/{ex.id}"}


@router.get("/revisions/{revision_id}/diagnostics")
def diagnostics(revision_id: str, st: AppState = Depends(state),
                s: Session = Depends(db)) -> dict[str, Any]:
    _revision(s, st, revision_id)
    rows = s.execute(
        select(Drawing, RevisionFile).join(RevisionFile, RevisionFile.file_id == Drawing.file_id)
        .where(RevisionFile.revision_id == revision_id)
    ).all()
    return {"items": [{"drawing_id": d.id, "file": rf.logical_name, "adapter": d.adapter,
                       "cad_version": d.cad_version, "diagnostics": d.diagnostics}
                      for d, rf in rows]}
