"""Análise automática da planta: pedido, acompanhamento, resultados e relatório."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from coscip_api import plant_service
from coscip_api.deps import AppState, db, state
from coscip_api.errors import ApiError
from coscip_api.models import Analysis, Drawing, Floor, RulePackage
from coscip_api.plant_service import PlantAnalysisIn, PlantContext, PlantError
from coscip_api.routers.normative import list_packages
from coscip_normative.requirements import consult_requirements

router = APIRouter()


@router.post("/rule-packages/{package_id}/requirements-query")
def requirements_query(package_id: str, body: PlantContext,
                       s: Session = Depends(db)) -> dict[str, Any]:
    """Consulta sem gravação, sempre no pacote escolhido para a análise."""
    pkg = s.get(RulePackage, package_id)
    if pkg is None or not (pkg.manifest or {}).get("verified"):
        raise ApiError(422, "RULE_PACKAGE_NOT_VERIFIED", "Pacote sem citações verificadas")
    return consult_requirements((pkg.manifest or {}).get("requirements"), body.model_dump())


def _raise(exc: PlantError) -> ApiError:
    return ApiError(exc.status, exc.code, exc.title, required_action=exc.action)


@router.post("/drawings/{drawing_id}/plant-analyses", status_code=202)
def create_plant_analysis(drawing_id: str, body: PlantAnalysisIn,
                          idempotency_key: str | None = Header(default=None,
                                                               alias="Idempotency-Key"),
                          st: AppState = Depends(state)) -> dict[str, Any]:
    try:
        return plant_service.create(st, drawing_id, body, idempotency_key or uuid.uuid4().hex)
    except PlantError as exc:
        raise _raise(exc) from exc


@router.get("/drawings/{drawing_id}/plant-analyses")
def list_plant_analyses(drawing_id: str, st: AppState = Depends(state),
                        s: Session = Depends(db)) -> dict[str, Any]:
    rows = s.scalars(select(Analysis).where(Analysis.tenant_id == st.tenant_id,
                                            Analysis.drawing_id == drawing_id)
                     .order_by(Analysis.created_at.desc()).limit(50)).all()
    return {"items": [plant_service.analysis_out(s, a) for a in rows]}


@router.get("/drawings/{drawing_id}/plant-analysis-options")
def plant_analysis_options(drawing_id: str, st: AppState = Depends(state),
                           s: Session = Depends(db)) -> dict[str, Any]:
    """O que a tela precisa para montar o pedido: pacotes, pavimentos e camadas sugeridas."""
    d = s.get(Drawing, drawing_id)
    if d is None or d.tenant_id != st.tenant_id:
        raise ApiError(404, "NOT_FOUND", "Desenho não encontrado")
    packages = [p for p in list_packages(s) if p["verified"]]
    suggest = None
    classes: list[dict[str, str]] = []
    classification = None
    if packages:
        from coscip_analysis import parse_dictionary

        pkg = s.get(RulePackage, packages[0]["id"])
        dic = parse_dictionary((pkg.manifest or {})["symbols"])
        suggest = dic.is_obstacle_layer
        classes = [{"id": c.id, "label": c.label} for c in dic.classes.values()]
        cl = (pkg.manifest or {}).get("classification")
        if cl:
            classification = {
                "source": cl["source"], "risk_to_rules": cl["risk_to_rules"],
                "notes": cl["notes"],
                "divisions": [{k: d.get(k) for k in ("id", "group", "description", "risk",
                                                     "page", "merged_from")}
                              for d in cl["divisions"] if d.get("verified")]}
    layers = [{"name": lay["name"], "segments": lay["count"],
               "suggested_obstacle": bool(suggest and suggest(lay["name"]))}
              for lay in (d.scene_manifest or {}).get("layers", [])]
    floors = s.scalars(select(Floor).where(Floor.drawing_id == d.id)
                       .order_by(Floor.created_at)).all()
    return {"packages": packages, "classes": classes, "classification": classification,
            "floors": [{"id": f.id, "name": f.name} for f in floors],
            "layers": sorted(layers, key=lambda x: (not x["suggested_obstacle"], x["name"]))}


@router.get("/plant-analyses/{analysis_id}")
def get_plant_analysis(analysis_id: str, st: AppState = Depends(state),
                       s: Session = Depends(db)) -> dict[str, Any]:
    a = s.get(Analysis, analysis_id)
    if a is None or a.tenant_id != st.tenant_id or a.drawing_id is None:
        raise ApiError(404, "NOT_FOUND", "Análise não encontrada")
    return plant_service.analysis_out(s, a)


@router.get("/plant-analyses/{analysis_id}/reviews")
def get_reviews(analysis_id: str, st: AppState = Depends(state),
                s: Session = Depends(db)) -> dict[str, Any]:
    """Estado da revisão humana por resultado (chave: regra|sujeito|região do analysis.json)."""
    a = s.get(Analysis, analysis_id)
    if a is None or a.tenant_id != st.tenant_id or a.drawing_id is None:
        raise ApiError(404, "NOT_FOUND", "Análise não encontrada")
    return {"items": plant_service.review_state(s, analysis_id)}


@router.post("/plant-analyses/{analysis_id}/reports", status_code=201)
def reissue_report(analysis_id: str, st: AppState = Depends(state)) -> dict[str, Any]:
    """Nova emissão do relatório (novo ID e hash); a anterior permanece."""
    with st.session_factory() as s:
        a = s.get(Analysis, analysis_id)
        if a is None or a.tenant_id != st.tenant_id or a.drawing_id is None:
            raise ApiError(404, "NOT_FOUND", "Análise não encontrada")
        if a.state != "SUCCEEDED":
            raise ApiError(409, "ANALYSIS_NOT_FINISHED", "A análise ainda não terminou")
    return plant_service.issue_report(st.session_factory, st.storage, st.tenant_id,
                                      analysis_id)
