"""Base normativa (REG-01/REG-02): textos das NTs e pacotes de regras verificados."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from coscip_api.deps import AppState, db, state
from coscip_api.errors import ApiError
from coscip_api.models import RulePackage
from coscip_api.normative_base import (
    MAX_SOURCE_BYTES,
    NormativeError,
    _pkg_out,
    import_package,
    ingest_sources,
    list_sources,
)

router = APIRouter()
MAX_FILES = 80


@router.get("/normative/sources")
def get_sources(s: Session = Depends(db)) -> dict[str, Any]:
    return {"items": list_sources(s)}


@router.post("/normative/sources", status_code=201)
async def post_sources(files: list[UploadFile] = File(...),
                       st: AppState = Depends(state)) -> dict[str, Any]:
    if not files or len(files) > MAX_FILES:
        raise ApiError(422, "INVALID_FILES", f"Envie de 1 a {MAX_FILES} arquivos .md")
    payload = []
    for f in files:
        name = f.filename or "fonte.md"
        if not name.lower().endswith((".md", ".markdown", ".txt")):
            raise ApiError(422, "UNSUPPORTED_SOURCE",
                           f"{name}: envie o texto da NT em Markdown (.md) com front matter")
        payload.append((name, await f.read(MAX_SOURCE_BYTES + 1)))
    return {"items": ingest_sources(st.session_factory, st.storage, payload, st.operator_id)}


@router.post("/rule-packages/import", status_code=201)
def post_import_package(st: AppState = Depends(state)) -> dict[str, Any]:
    """Importa o pacote que acompanha o motor (normative/base), conferindo cada citação."""
    try:
        return import_package(st.session_factory, st.storage, actor_id=st.operator_id)
    except NormativeError as exc:
        raise ApiError(422, "CITATIONS_NOT_VERIFIED", str(exc),
                       required_action="INGEST_NORMATIVE_SOURCES",
                       extra={"failures": exc.details}) from exc


@router.get("/rule-packages/{package_id}")
def get_rule_package(package_id: str, s: Session = Depends(db)) -> dict[str, Any]:
    p = s.get(RulePackage, package_id)
    if p is None:
        raise ApiError(404, "NOT_FOUND", "Pacote não encontrado")
    m = p.manifest or {}
    return {"id": p.id, **_pkg_out(p), "manifest": {k: m.get(k) for k in (
        "package", "rules", "coverage", "sources", "symbols_citation", "sources_sha256")}}


def list_packages(s: Session) -> list[dict[str, Any]]:
    rows = s.scalars(select(RulePackage).order_by(RulePackage.created_at.desc())).all()
    return [{"id": p.id, **_pkg_out(p)} for p in rows]
