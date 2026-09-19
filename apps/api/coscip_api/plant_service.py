"""Análise automática da planta: criação do job, manifesto do worker, publicação e relatório.

Invariantes:
- só roda com unidade confirmada (escala do quadro vigente) e pacote com citações verificadas;
- o worker recebe regras, dicionário e contexto congelados no manifesto (reprodutível);
- a saída (analysis.json) é guardada com hash e cada resultado vira linha em rule_results;
- o relatório HTML é uma emissão imutável com ID e SHA-256 próprios.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field
from sqlalchemy import select

from coscip_api.db import write_tx
from coscip_api.model_state import current_frame, latest_snapshot, scale_of
from coscip_api.models import (
    Analysis,
    AuditEvent,
    Drawing,
    Evidence,
    Execution,
    FileObject,
    Floor,
    Project,
    Report,
    ResultEvidence,
    ReviewDecisionRow,
    RevisionFile,
    RulePackage,
    RuleResultRow,
    RuleVersion,
    SubmissionRevision,
    new_id,
    utcnow,
)
from coscip_cbm.enums import UI_LABELS, EvaluationStatus
from coscip_jobs import JobQueue

TEMPLATES = Path(__file__).resolve().parent / "templates"
REPORT_TEMPLATE = "plant-analysis/1.0"


class PlantContext(BaseModel):
    """Dados do enquadramento que a planta não traz (vêm do processo / do analista)."""

    risk_class: Literal["PEQUENO", "MEDIO", "GRANDE"] | None = None
    unifamiliar: bool = False
    occupancy: str | None = Field(default=None, max_length=20)
    # De onde veio a classe de risco (ex.: "NT 1-04, Anexo B: F-8 → MÉDIO 1"), ou vazio.
    risk_basis: str | None = Field(default=None, max_length=300)
    requires_hydrants: bool | None = None
    requires_alarm: bool | None = None
    requires_lighting: bool | None = None
    exit_max_distance_m: float | None = Field(default=None, gt=0, le=300)
    exits_confirmed: bool = False


class PlantAnalysisIn(BaseModel):
    rule_package_id: str
    context: PlantContext = PlantContext()
    use_floors: bool = True
    floor_ids: list[str] | None = None
    obstacle_layers: list[str] | None = Field(default=None, max_length=200)
    symbol_overrides: dict[str, str] = Field(default_factory=dict, max_length=200)


class PlantError(Exception):
    def __init__(self, status: int, code: str, title: str, action: str | None = None) -> None:
        super().__init__(title)
        self.status, self.code, self.title, self.action = status, code, title, action


def create(st, drawing_id: str, body: PlantAnalysisIn, key: str) -> dict[str, Any]:  # noqa: ANN001
    with write_tx(st.session_factory) as s:
        d = s.get(Drawing, drawing_id)
        if d is None or d.tenant_id != st.tenant_id:
            raise PlantError(404, "NOT_FOUND", "Desenho não encontrado")
        frame = current_frame(s, d.id)
        scale = scale_of(frame)
        if scale is None:
            raise PlantError(409, "DRAWING_UNIT_UNCONFIRMED",
                             "A unidade do desenho precisa ser confirmada antes da análise",
                             "CONFIRM_DRAWING_UNIT")
        pkg = s.get(RulePackage, body.rule_package_id)
        if pkg is None or not (pkg.manifest or {}).get("verified"):
            raise PlantError(422, "RULE_PACKAGE_NOT_VERIFIED",
                             "Pacote normativo inexistente ou sem citações verificadas",
                             "IMPORT_RULE_PACKAGE")
        classes = set(((pkg.manifest or {}).get("symbols") or {}).get("classes", {}))
        bad = sorted(v for v in body.symbol_overrides.values() if v not in classes)
        if bad:
            raise PlantError(422, "UNKNOWN_SYMBOL_CLASS",
                             f"Classes inexistentes no dicionário: {', '.join(bad)}")
        floors = []
        if body.use_floors:
            q = select(Floor).where(Floor.drawing_id == d.id).order_by(Floor.created_at)
            floors = [f for f in s.scalars(q).all()
                      if body.floor_ids is None or f.id in body.floor_ids]
        stale = [f.name for f in floors if f.frame_id and frame and f.frame_id != frame.id]
        if stale:
            raise PlantError(409, "FLOOR_FRAME_STALE",
                             f"Recortes feitos em outro quadro de coordenadas: {', '.join(stale)}",
                             "REDRAW_FLOORS")
        rev = s.get(SubmissionRevision, d.revision_id)
        snap = latest_snapshot(s, d.revision_id)
        fo = s.get(FileObject, d.file_id)
        context = body.context.model_dump()
        ctx_hash = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()
        a = Analysis(tenant_id=st.tenant_id, revision_id=d.revision_id,
                     model_snapshot_id=snap.id, context_snapshot_id=ctx_hash[:36],
                     rule_package_id=pkg.id, tolerance_profile_id="tolerances-experimental/1",
                     drawing_id=d.id, state="QUEUED",
                     runtime_manifest={"kind": "PLANT_ANALYSIS", "context": context,
                                       "context_sha256": ctx_hash, "scale_to_m": scale,
                                       "frame_id": frame.id, "floors": [f.id for f in floors],
                                       "use_floors": body.use_floors,
                                       "obstacle_layers": body.obstacle_layers,
                                       "symbol_overrides": body.symbol_overrides,
                                       "package_sha256": pkg.content_sha256})
        s.add(a)
        s.flush()
        ex = Execution(tenant_id=st.tenant_id, kind="PLANT_ANALYSIS", state="QUEUED",
                       idempotency_key=f"plant:{key}", analysis_id=a.id, planned_stages=2,
                       payload={"drawing_id": d.id})
        s.add(ex)
        s.flush()
        a.execution_id = ex.id
        payload = {"execution_id": ex.id, "analysis_id": a.id, "drawing_id": d.id,
                   "project_id": rev.project_id, "revision_id": rev.id, "file_key": fo.key,
                   "file_sha256": fo.sha256, "scale_to_m": scale, "rule_package_id": pkg.id,
                   "context": context, "symbol_overrides": body.symbol_overrides,
                   "obstacle_layers": body.obstacle_layers,
                   "floors": [{"id": f.id, "name": f.name, "clip": f.clip} for f in floors]}
        raw = s.connection().connection.driver_connection
        ex.job_id = JobQueue(raw).enqueue("PLANT_ANALYSIS", payload, f"plant:{key}")
        s.add(AuditEvent(tenant_id=st.tenant_id, actor_id=st.operator_id,
                         action="analysis.plant_requested", resource=a.id,
                         diff={"drawing_id": d.id, "rule_package_id": pkg.id,
                               "context_sha256": ctx_hash}))
        return {"analysis_id": a.id, "execution_id": ex.id, "state": "QUEUED"}


def worker_manifest(factory, p: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN001
    with factory() as s:
        pkg = s.get(RulePackage, p["rule_package_id"])
        m = pkg.manifest or {}
        rules = []
        for b in m.get("rules", []):
            rv = s.get(RuleVersion, b["rule_version_id"])
            rules.append({"rule_version_id": rv.id, "dsl": rv.dsl, "citations": b["citations"]})
    return {"analysis_id": p["analysis_id"], "scale_to_m": p["scale_to_m"],
            "symbols": m["symbols"], "rules": rules, "context": p["context"],
            "floors": p["floors"], "symbol_overrides": p.get("symbol_overrides") or {},
            "obstacle_layers": p.get("obstacle_layers")}


def set_analysis_state(factory, analysis_id: str, value: str) -> None:  # noqa: ANN001
    with write_tx(factory) as s:
        a = s.get(Analysis, analysis_id)
        if a is not None:
            a.state = value


def publish(factory, storage, tenant_id: str, p: dict[str, Any], path: Path) -> None:  # noqa: ANN001
    base = f"projects/{p['project_id']}/analyses/{p['analysis_id']}"
    with open(path, "rb") as fh:
        obj = storage.write_stream(f"{base}/analysis.json", fh)
    data = json.loads(path.read_text(encoding="utf-8"))
    with write_tx(factory) as s:
        fo = FileObject(tenant_id=tenant_id, key=obj.key, sha256=obj.sha256, size=obj.size,
                        mime="application/json",
                        inspection={"kind": "PLANT_ANALYSIS", "analysis_id": p["analysis_id"]})
        s.add(fo)
        s.flush()
        ev = Evidence(tenant_id=tenant_id, kind="ANALYSIS_OUTPUT", file_id=fo.id,
                      content_sha256=obj.sha256, provenance="COMPUTED",
                      calculation={"schema_version": data["schema_version"],
                                   "dictionary": data["dictionary"],
                                   "obstacles": data["obstacles"]})
        s.add(ev)
        s.flush()
        for res in data["results"]:
            row = RuleResultRow(
                tenant_id=tenant_id, analysis_id=p["analysis_id"],
                rule_version_id=res["rule_version_id"], subject_id=res["subject_id"][:36],
                evaluation_key=res["region_id"][:100], applicability=res["applicability"],
                status=res["status"], reason_code=res["reason_code"],
                values={"trace": res["trace"], "title": res["title"],
                        "measure": res["measure"], "subject_type": res["subject_type"],
                        "subject_label": res["subject_label"],
                        "region_name": res["region_name"], "rule_id": res["rule_id"],
                        "measured_fact": res.get("measured_fact")})
            s.add(row)
            s.flush()
            s.add(ResultEvidence(tenant_id=tenant_id, result_id=row.id, evidence_id=ev.id,
                                 role="CALCULATION"))
        a = s.get(Analysis, p["analysis_id"])
        a.state = "SUCCEEDED"
        a.runtime_manifest = {**(a.runtime_manifest or {}), "analysis_artifact_id": fo.id,
                              "analysis_sha256": obj.sha256, "summary": data["summary"],
                              "warnings": data["warnings"], "duration_s": data["duration_s"]}
    issue_report(factory, storage, tenant_id, p["analysis_id"])


# --- relatório --------------------------------------------------------------------
STATUS_ORDER = ["FAIL", "REVIEW_REQUIRED", "MISSING_DATA", "PASS", "NOT_APPLICABLE"]
REASONS = {
    "MEASURED_INTERVAL_SATISFIES": "medida (com incerteza) atende ao limite",
    "MEASURED_INTERVAL_VIOLATES": "medida (com incerteza) não atende ao limite",
    "UNCERTAINTY_CROSSES_LIMIT": "a incerteza atravessa o limite",
    "QUALITY_GATE_NOT_MET": "condição de qualidade não atendida",
    "HEURISTIC_EVIDENCE_VIOLATES": "evidência heurística indica falta; conferir",
    "REQUIRED_INPUT_MISSING": "dado necessário ausente",
    "REQUIRED_TABLE_KEY_UNKNOWN": "enquadramento necessário não informado",
    "APPLICABILITY_FALSE": "condição de aplicação não ocorre",
    "APPLICABILITY_UNKNOWN": "aplicabilidade não determinada",
    "INPUT_CONFLICT": "dados conflitantes",
    "UNCERTAINTY_UNKNOWN": "incerteza desconhecida",
}
GATES = {
    "quality.region_confirmed": "região automática (pavimento não recortado pelo analista)",
    "quality.walls_detected": "paredes não reconhecidas por layer",
    "quality.extinguisher.complete": "há área sem acesso a extintor pelo modelo de paredes",
    "quality.hydrant.complete": "há área sem acesso a hidrante pelo modelo de paredes",
    "quality.manual_call_point.complete": "há área sem acesso a acionador",
    "quality.exit.complete": "há área sem acesso a saída",
    "context.exits_confirmed": "saídas não confirmadas pelo analista",
    "quality.extinguisher.not_presumed": "extintor presumido pela placa E-5 + E-17 (sem símbolo)",
}
CLASS_LABELS = {
    "EXTINTOR": "Extintores", "HIDRANTE": "Hidrantes", "MANGOTINHO": "Mangotinhos",
    "HIDRANTE_URBANO": "Hidrante urbano", "REGISTRO_RECALQUE": "Registro de recalque",
    "BOMBA_INCENDIO": "Bombas de incêndio", "ACIONADOR_BOMBA": "Acionador de bomba",
    "RESERVA_TECNICA": "Reserva técnica", "SPRINKLER": "Sprinklers",
    "ILUMINACAO_EMERGENCIA": "Iluminação de emergência", "DETECTOR": "Detectores",
    "ACIONADOR_MANUAL": "Acionadores manuais", "AVISADOR": "Avisadores",
    "CENTRAL_ALARME": "Central de alarme", "CENTRAL_GLP": "Central de GLP",
    "SAIDA": "Saídas (marcações)", "SINALIZACAO": "Placas de sinalização",
}


def _fmt(v: Any) -> str:
    """Número em formato brasileiro (vírgula); inteiro sem casas; texto como está."""
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f.is_integer():
        return str(int(f))
    return f"{f:.2f}".replace(".", ",")


def result_key(rule_version_id: str, subject_id: str, region_id: str) -> str:
    """Liga o resultado do analysis.json à linha em rule_results (mesmos cortes da gravação)."""
    return f"{rule_version_id}|{subject_id[:36]}|{region_id[:100]}"


DECISION_LABELS = {"CONFIRM": "confirmado", "CONTEST": "contestado",
                   "REQUEST_DATA": "dado solicitado",
                   "RESOLVED_BY_NEW_REVISION": "resolvido em nova revisão"}


def review_state(s, analysis_id: str) -> dict[str, dict[str, Any]]:  # noqa: ANN001
    """Por resultado: id da linha, estado automático e histórico de decisões (mais nova 1º)."""
    rows = s.scalars(select(RuleResultRow).where(RuleResultRow.analysis_id == analysis_id)).all()
    by_id = {r.id: r for r in rows}
    decisions: dict[str, list[dict[str, Any]]] = {}
    if by_id:
        q = (select(ReviewDecisionRow).where(ReviewDecisionRow.result_id.in_(by_id))
             .order_by(ReviewDecisionRow.created_at.desc()))
        for d in s.scalars(q).all():
            decisions.setdefault(d.result_id, []).append({
                "id": d.id, "decision": d.decision, "final_status": d.final_status,
                "justification": d.justification, "author_id": d.author_id,
                "created_at": d.created_at.isoformat() if d.created_at else None})
    return {result_key(r.rule_version_id, r.subject_id, r.evaluation_key): {
        "result_id": r.id, "status": r.status, "decisions": decisions.get(r.id, [])}
        for r in rows}


def issue_report(factory, storage, tenant_id: str, analysis_id: str) -> dict[str, Any]:  # noqa: ANN001
    with factory() as s:
        a = s.get(Analysis, analysis_id)
        rm = a.runtime_manifest or {}
        fo = s.get(FileObject, rm["analysis_artifact_id"])
        with storage.open(fo.key) as fh:
            raw = fh.read()
        if hashlib.sha256(raw).hexdigest() != fo.sha256:
            raise RuntimeError("analysis.json não confere com o hash gravado")
        data = json.loads(raw)
        d = s.get(Drawing, a.drawing_id)
        rev = s.get(SubmissionRevision, a.revision_id)
        project = s.get(Project, rev.project_id)
        dfile = s.get(FileObject, d.file_id)
        name = s.scalar(select(RevisionFile.logical_name).where(
            RevisionFile.revision_id == rev.id, RevisionFile.file_id == d.file_id))
        pkg = s.get(RulePackage, a.rule_package_id)
        manifest = pkg.manifest or {}
        report_id = new_id()
        issued_at = utcnow().isoformat(timespec="seconds")
        env = Environment(loader=FileSystemLoader(TEMPLATES),
                          autoescape=select_autoescape(["html"]))
        env.filters["num"] = _fmt
        by_rule: dict[str, dict[str, Any]] = {r["rule_id"]: r for r in manifest.get("rules", [])}
        summary = data["summary"]["by_status"]
        reviews = review_state(s, analysis_id)
        latest: dict[str, dict[str, Any]] = {}
        for res in data["results"]:
            k = result_key(res["rule_version_id"], res["subject_id"], res["region_id"])
            hist = (reviews.get(k) or {}).get("decisions") or []
            if hist:
                latest[k] = hist[0]
            res["review_key"] = k
        after = dict.fromkeys(STATUS_ORDER, 0)
        after["PENDING"] = 0
        for res in data["results"]:
            dec = latest.get(res["review_key"])
            if dec and dec["final_status"]:
                after[dec["final_status"]] += 1
            elif res["status"] in ("REVIEW_REQUIRED", "MISSING_DATA"):
                after["PENDING"] += 1
            else:
                after[res["status"]] += 1
        review_snapshot = {
            "decisions": {k: {x: v[x] for x in ("id", "decision", "final_status", "created_at")}
                          for k, v in latest.items()},
            "reviewed": len(latest), "total": len(data["results"]), "after_review": after}
        html = env.get_template("plant-analysis-report.html").render(
            report_id=report_id, issued_at=issued_at, project=project, revision=rev,
            drawing_name=name, drawing_sha256=dfile.sha256, analysis=a, data=data,
            analysis_sha256=fo.sha256, package=pkg, manifest=manifest, by_rule=by_rule,
            summary=summary, status_order=STATUS_ORDER,
            labels={k.value: v for k, v in UI_LABELS.items()}, reasons=REASONS,
            gates=GATES, class_labels=CLASS_LABELS,
            status_values=[e.value for e in EvaluationStatus], reviews=latest,
            review_snapshot=review_snapshot, decision_labels=DECISION_LABELS)
        key = f"projects/{project.id}/reports/{report_id}.html"
    obj = storage.write_stream(key, [html.encode("utf-8")])
    with write_tx(factory) as s:
        rfo = FileObject(tenant_id=tenant_id, key=obj.key, sha256=obj.sha256, size=obj.size,
                         mime="text/html",
                         inspection={"report_id": report_id, "analysis_id": analysis_id,
                                     "kind": "PLANT_ANALYSIS", "issued_at": issued_at})
        s.add(rfo)
        s.flush()
        rep = Report(id=report_id, tenant_id=tenant_id, analysis_id=analysis_id,
                     template=REPORT_TEMPLATE, artifact_id=rfo.id, content_sha256=obj.sha256,
                     state="SUCCEEDED", review_snapshot=review_snapshot)
        s.add(rep)
        s.add(AuditEvent(tenant_id=tenant_id, action="report.plant_analysis_created",
                         resource=report_id,
                         diff={"analysis_id": analysis_id, "artifact_id": rfo.id,
                               "sha256": obj.sha256}))
        return {"id": report_id, "artifact_id": rfo.id, "sha256": obj.sha256,
                "reviewed": review_snapshot["reviewed"],
                "content_url": f"/v1/artifacts/{rfo.id}/content", "issued_at": issued_at}


def analysis_out(s, a: Analysis) -> dict[str, Any]:  # noqa: ANN001
    rm = a.runtime_manifest or {}
    reports = s.scalars(select(Report).where(Report.analysis_id == a.id)
                        .order_by(Report.created_at.desc())).all()
    ex = s.get(Execution, a.execution_id) if a.execution_id else None
    return {
        "id": a.id, "state": a.state, "drawing_id": a.drawing_id,
        "model_snapshot_id": a.model_snapshot_id, "rule_package_id": a.rule_package_id,
        "created_at": a.created_at, "context": rm.get("context"),
        "summary": rm.get("summary"), "warnings": rm.get("warnings", []),
        "duration_s": rm.get("duration_s"), "execution_id": a.execution_id,
        "execution": {"state": ex.state, "stage": ex.stage, "error_code": ex.error_code}
        if ex else None,
        "analysis_artifact_url": (f"/v1/artifacts/{rm['analysis_artifact_id']}/content"
                                  if rm.get("analysis_artifact_id") else None),
        "reports": [{"id": r.id, "sha256": r.content_sha256, "created_at": r.created_at,
                     "reviewed": (r.review_snapshot or {}).get("reviewed", 0),
                     "content_url": f"/v1/artifacts/{r.artifact_id}/content"}
                    for r in reports],
    }
