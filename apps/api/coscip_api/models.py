"""Modelo relacional lógico (contratos §2) — perfil local SQLite.

Todas as tabelas de projeto carregam tenant_id para a migração futura; isso NÃO
promete isolamento multiusuário. Tabelas marcadas como futuras não são criadas.
Decimais normativos ficam como TEXT para o NUMERIC do SQLite não virar float.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class _Ids:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class _Tenant(_Ids):
    tenant_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)


# --- organização local ---------------------------------------------------
class Organization(Base, _Ids):
    __tablename__ = "organizations"
    name: Mapped[str] = mapped_column(String(200))
    state: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    retention_policy: Mapped[dict | None] = mapped_column(JSON)
    quota: Mapped[dict | None] = mapped_column(JSON)


class User(Base, _Tenant):
    __tablename__ = "users"
    name: Mapped[str] = mapped_column(String(200))
    state: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    identity_source: Mapped[str] = mapped_column(String(20), default="LOCAL_OS")
    os_account: Mapped[str | None] = mapped_column(String(200))


# --- projetos e revisões -------------------------------------------------
class Project(Base, _Tenant):
    __tablename__ = "projects"
    __table_args__ = (Index("ix_projects_tenant_created", "tenant_id", "created_at"),)
    name: Mapped[str] = mapped_column(String(300))
    external_ref: Mapped[str | None] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(500))
    responsible: Mapped[str | None] = mapped_column(String(200))
    row_version: Mapped[int] = mapped_column(Integer, default=1)


class SubmissionRevision(Base, _Tenant):
    __tablename__ = "submission_revisions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_id", "number"),
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    number: Mapped[int] = mapped_column(Integer)
    previous_id: Mapped[str | None] = mapped_column(ForeignKey("submission_revisions.id"))
    state: Mapped[str] = mapped_column(String(20), default="DRAFT")  # DRAFT → SEALED
    manifest: Mapped[dict | None] = mapped_column(JSON)
    manifest_sha256: Mapped[str | None] = mapped_column(String(64))


class FileObject(Base, _Tenant):
    __tablename__ = "file_objects"
    storage_backend: Mapped[str] = mapped_column(String(20), default="LOCAL_FS")
    key: Mapped[str] = mapped_column(String(500), unique=True)
    logical_version: Mapped[int] = mapped_column(Integer, default=1)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    size: Mapped[int] = mapped_column(Integer)
    mime: Mapped[str | None] = mapped_column(String(100))
    inspection: Mapped[dict | None] = mapped_column(JSON)


class RevisionFile(Base, _Tenant):
    __tablename__ = "revision_files"
    revision_id: Mapped[str] = mapped_column(ForeignKey("submission_revisions.id"))
    file_id: Mapped[str] = mapped_column(ForeignKey("file_objects.id"))
    discipline: Mapped[str | None] = mapped_column(String(50))
    role: Mapped[str] = mapped_column(String(30))  # ANALYTIC_DXF, SOURCE_DWG, DOCUMENT, XREF
    logical_name: Mapped[str] = mapped_column(String(300))


class FileDependency(Base, _Tenant):
    __tablename__ = "file_dependencies"
    source_file_id: Mapped[str] = mapped_column(ForeignKey("file_objects.id"))
    reference: Mapped[str] = mapped_column(String(500))
    resolved_file_id: Mapped[str | None] = mapped_column(ForeignKey("file_objects.id"))
    state: Mapped[str] = mapped_column(String(20))  # RESOLVED, MISSING, CYCLE, REJECTED


class UploadSession(Base, _Tenant):
    __tablename__ = "upload_sessions"
    revision_id: Mapped[str] = mapped_column(ForeignKey("submission_revisions.id"))
    filename: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(30))
    expected_size: Mapped[int] = mapped_column(Integer)
    expected_sha256: Mapped[str | None] = mapped_column(String(64))
    received_parts: Mapped[dict] = mapped_column(JSON, default=dict)
    state: Mapped[str] = mapped_column(String(20), default="OPEN")
    file_id: Mapped[str | None] = mapped_column(ForeignKey("file_objects.id"))


# --- CAD -----------------------------------------------------------------
class Drawing(Base, _Tenant):
    __tablename__ = "drawings"
    revision_id: Mapped[str | None] = mapped_column(ForeignKey("submission_revisions.id"),
                                                   index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("file_objects.id"))
    adapter: Mapped[str] = mapped_column(String(50))
    cad_version: Mapped[str | None] = mapped_column(String(20))
    diagnostics: Mapped[dict | None] = mapped_column(JSON)
    inventory_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("file_objects.id"))
    # nome da saída do worker → file_objects.id (entities.jsonl, scene.bin, …)
    artifacts: Mapped[dict | None] = mapped_column(JSON)
    scene_manifest: Mapped[dict | None] = mapped_column(JSON)


class CoordinateFrame(Base, _Tenant):
    __tablename__ = "coordinate_frames"
    drawing_id: Mapped[str] = mapped_column(ForeignKey("drawings.id"))
    original_unit: Mapped[str | None] = mapped_column(String(20))
    unit_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    scale_to_m: Mapped[str | None] = mapped_column(String(40))
    matrix: Mapped[list] = mapped_column(JSON)
    inverse: Mapped[list] = mapped_column(JSON)
    local_origin: Mapped[list | None] = mapped_column(JSON)


class ModelSnapshot(Base, _Tenant):
    __tablename__ = "model_snapshots"
    revision_id: Mapped[str] = mapped_column(ForeignKey("submission_revisions.id"))
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("model_snapshots.id"))
    cbm_schema: Mapped[str] = mapped_column(String(20), default="cbm/1.0")
    content_sha256: Mapped[str | None] = mapped_column(String(64))
    config: Mapped[dict | None] = mapped_column(JSON)
    quality: Mapped[dict | None] = mapped_column(JSON)


class Floor(Base, _Tenant):
    __tablename__ = "floors"
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("model_snapshots.id"))
    drawing_id: Mapped[str | None] = mapped_column(ForeignKey("drawings.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    elevation_m: Mapped[str | None] = mapped_column(String(40))
    frame_id: Mapped[str | None] = mapped_column(ForeignKey("coordinate_frames.id"))
    clip: Mapped[dict | None] = mapped_column(JSON)


class SourceEntity(Base, _Tenant):
    __tablename__ = "source_entities"
    drawing_id: Mapped[str] = mapped_column(ForeignKey("drawings.id"), index=True)
    handle: Mapped[str] = mapped_column(String(32))
    entity_type: Mapped[str] = mapped_column(String(40))
    layer: Mapped[str] = mapped_column(String(255))
    bbox: Mapped[list | None] = mapped_column(JSON)
    raw_ref: Mapped[str | None] = mapped_column(String(200))


class SourceInstance(Base, _Tenant):
    __tablename__ = "source_instances"
    entity_id: Mapped[str] = mapped_column(ForeignKey("source_entities.id"))
    instance_path: Mapped[list] = mapped_column(JSON)
    transform: Mapped[list] = mapped_column(JSON)
    layout: Mapped[str] = mapped_column(String(100), default="Model")
    extraction_quality: Mapped[str] = mapped_column(String(20))


class Element(Base, _Tenant):
    __tablename__ = "elements"
    __table_args__ = (Index("ix_elements_snapshot_floor", "tenant_id", "snapshot_id", "floor_id"),)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("model_snapshots.id"))
    floor_id: Mapped[str] = mapped_column(ForeignKey("floors.id"))
    element_class: Mapped[str] = mapped_column(String(30))
    geometry_wkb: Mapped[bytes | None] = mapped_column(LargeBinary)
    bbox: Mapped[list | None] = mapped_column(JSON)
    semantic_status: Mapped[str] = mapped_column(String(20))


class ElementSource(Base, _Tenant):
    __tablename__ = "element_sources"
    element_id: Mapped[str] = mapped_column(ForeignKey("elements.id"))
    source_instance_id: Mapped[str] = mapped_column(ForeignKey("source_instances.id"))
    role: Mapped[str] = mapped_column(String(30))


class Fact(Base, _Tenant):
    __tablename__ = "facts"
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("model_snapshots.id"))
    subject_id: Mapped[str] = mapped_column(String(36), index=True)
    property: Mapped[str] = mapped_column(String(100))
    value: Mapped[dict | None] = mapped_column(JSON)  # valor tipado; null ≠ 0 ≠ N/A
    unit: Mapped[str | None] = mapped_column(String(20))
    provenance: Mapped[str] = mapped_column(String(20))
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)


class Measurement(Base, _Tenant):
    __tablename__ = "measurements"
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("model_snapshots.id"))
    subjects: Mapped[list] = mapped_column(JSON)
    value: Mapped[str] = mapped_column(String(40))
    unit: Mapped[str] = mapped_column(String(10))
    uncertainty_abs: Mapped[str] = mapped_column(String(40))
    method: Mapped[str] = mapped_column(String(80))
    dependencies: Mapped[list] = mapped_column(JSON, default=list)


class Correction(Base, _Tenant):
    __tablename__ = "corrections"
    base_snapshot_id: Mapped[str] = mapped_column(ForeignKey("model_snapshots.id"))
    result_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("model_snapshots.id"))
    operation: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[str] = mapped_column(String(36))
    old_value: Mapped[dict | None] = mapped_column(JSON)
    new_value: Mapped[dict | None] = mapped_column(JSON)
    justification: Mapped[str] = mapped_column(Text)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))


class SemanticMappingRow(Base, _Tenant):
    __tablename__ = "semantic_mappings"
    scope: Mapped[str] = mapped_column(String(20))
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"))
    signature: Mapped[str] = mapped_column(String(300))
    element_class: Mapped[str] = mapped_column(String(30))
    state: Mapped[str] = mapped_column(String(20))
    version: Mapped[int] = mapped_column(Integer, default=1)


# --- normativo -----------------------------------------------------------
class NormativeSource(Base, _Ids):
    __tablename__ = "normative_sources"
    document: Mapped[str] = mapped_column(String(100))
    edition: Mapped[str] = mapped_column(String(100))
    amending_act: Mapped[str | None] = mapped_column(String(200))
    url: Mapped[str | None] = mapped_column(String(500))
    file_sha256: Mapped[str | None] = mapped_column(String(64))
    effective_from: Mapped[str | None] = mapped_column(String(10))
    effective_until: Mapped[str | None] = mapped_column(String(10))
    collected_at: Mapped[str | None] = mapped_column(String(10))


class RuleVersion(Base, _Ids):
    __tablename__ = "rule_versions"
    __table_args__ = (UniqueConstraint("rule_id", "version"),)
    rule_id: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer)
    dsl: Mapped[dict] = mapped_column(JSON)
    content_sha256: Mapped[str] = mapped_column(String(64))
    publication_state: Mapped[str] = mapped_column(String(20))
    production_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(200))


class RulePackage(Base, _Ids):
    __tablename__ = "rule_packages"
    name: Mapped[str] = mapped_column(String(200))
    jurisdiction: Mapped[str] = mapped_column(String(50))
    manifest: Mapped[dict] = mapped_column(JSON)
    content_sha256: Mapped[str] = mapped_column(String(64), unique=True)
    state: Mapped[str] = mapped_column(String(20))


# --- execução ------------------------------------------------------------
class Execution(Base, _Tenant):
    __tablename__ = "executions"
    kind: Mapped[str] = mapped_column(String(30))  # IMPORT_DXF, ANALYSIS, REPORT, BACKUP
    analysis_id: Mapped[str | None] = mapped_column(String(36))
    state: Mapped[str] = mapped_column(String(20), default="CREATED")
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("executions.id"))
    runner: Mapped[str] = mapped_column(String(20), default="LOCAL_PROCESS")
    job_id: Mapped[str | None] = mapped_column(String(36))
    stage: Mapped[str | None] = mapped_column(String(40))
    completed_stages: Mapped[int] = mapped_column(Integer, default=0)
    planned_stages: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(60))
    payload: Mapped[dict | None] = mapped_column(JSON)


class ExecutionStage(Base, _Tenant):
    __tablename__ = "execution_stages"
    execution_id: Mapped[str] = mapped_column(ForeignKey("executions.id"))
    stage: Mapped[str] = mapped_column(String(40))
    attempt_token: Mapped[str | None] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(20))
    resources: Mapped[dict | None] = mapped_column(JSON)
    artifacts: Mapped[list | None] = mapped_column(JSON)
    error: Mapped[dict | None] = mapped_column(JSON)


class Analysis(Base, _Tenant):
    __tablename__ = "analyses"
    revision_id: Mapped[str] = mapped_column(ForeignKey("submission_revisions.id"))
    model_snapshot_id: Mapped[str] = mapped_column(ForeignKey("model_snapshots.id"))
    context_snapshot_id: Mapped[str] = mapped_column(String(36))
    rule_package_id: Mapped[str] = mapped_column(ForeignKey("rule_packages.id"))
    tolerance_profile_id: Mapped[str] = mapped_column(String(60))
    runtime_manifest: Mapped[dict | None] = mapped_column(JSON)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    state: Mapped[str] = mapped_column(String(20), default="QUEUED")


class RuleResultRow(Base, _Tenant):
    __tablename__ = "rule_results"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "analysis_id", "rule_version_id", "subject_id", "evaluation_key"
        ),
        Index("ix_results_analysis_status", "tenant_id", "analysis_id", "status"),
        ForeignKeyConstraint(["analysis_id"], ["analyses.id"]),
    )
    analysis_id: Mapped[str] = mapped_column(String(36))
    rule_version_id: Mapped[str] = mapped_column(ForeignKey("rule_versions.id"))
    subject_id: Mapped[str] = mapped_column(String(36))
    evaluation_key: Mapped[str] = mapped_column(String(100), default="default")
    applicability: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20))
    reason_code: Mapped[str] = mapped_column(String(80))
    values: Mapped[dict | None] = mapped_column(JSON)


class Evidence(Base, _Tenant):
    __tablename__ = "evidence"
    kind: Mapped[str] = mapped_column(String(30))
    file_id: Mapped[str | None] = mapped_column(ForeignKey("file_objects.id"))
    source_instance_id: Mapped[str | None] = mapped_column(ForeignKey("source_instances.id"))
    page: Mapped[int | None] = mapped_column(Integer)
    geometry_wkb: Mapped[bytes | None] = mapped_column(LargeBinary)
    calculation: Mapped[dict | None] = mapped_column(JSON)
    content_sha256: Mapped[str | None] = mapped_column(String(64))
    provenance: Mapped[str] = mapped_column(String(20))


class ResultEvidence(Base, _Tenant):
    __tablename__ = "result_evidence"
    result_id: Mapped[str] = mapped_column(ForeignKey("rule_results.id"))
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id"))
    role: Mapped[str] = mapped_column(String(20))  # INPUT, REQUIREMENT, CALCULATION, IMAGE


class ReviewDecisionRow(Base, _Tenant):
    """Append-only: nunca reescreve o resultado automático."""

    __tablename__ = "review_decisions"
    result_id: Mapped[str] = mapped_column(ForeignKey("rule_results.id"))
    decision: Mapped[str] = mapped_column(String(30))
    justification: Mapped[str] = mapped_column(Text)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    extra_evidence_ids: Mapped[list] = mapped_column(JSON, default=list)


class Report(Base, _Tenant):
    __tablename__ = "reports"
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"))
    review_snapshot: Mapped[dict | None] = mapped_column(JSON)
    template: Mapped[str] = mapped_column(String(60))
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("file_objects.id"))
    content_sha256: Mapped[str | None] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(20), default="QUEUED")


# --- operação ------------------------------------------------------------
class AuditEvent(Base, _Ids):
    __tablename__ = "audit_events"
    tenant_id: Mapped[str | None] = mapped_column(String(36))
    actor_id: Mapped[str | None] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(60))
    resource: Mapped[str] = mapped_column(String(100))
    correlation_id: Mapped[str | None] = mapped_column(String(64))
    diff: Mapped[dict | None] = mapped_column(JSON)


class UsageRecord(Base, _Tenant):
    __tablename__ = "usage_records"
    execution_id: Mapped[str | None] = mapped_column(ForeignKey("executions.id"))
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"))
    provider: Mapped[str] = mapped_column(String(40))
    model_returned: Mapped[str | None] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    reasoning_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[str] = mapped_column(String(40))
    tariff_version: Mapped[str] = mapped_column(String(40))
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    call_id: Mapped[str | None] = mapped_column(String(100))


class BudgetReservationRow(Base, _Tenant):
    __tablename__ = "budget_reservations"
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"))
    month: Mapped[str] = mapped_column(String(7))
    request_id: Mapped[str] = mapped_column(String(64), unique=True)
    max_usd: Mapped[str] = mapped_column(String(40))
    settled_usd: Mapped[str | None] = mapped_column(String(40))
    state: Mapped[str] = mapped_column(String(20))  # RESERVED, SETTLED, UNKNOWN


class BackupRecord(Base, _Ids):
    __tablename__ = "backup_records"
    manifest_path: Mapped[str] = mapped_column(String(500))
    destination_label: Mapped[str] = mapped_column(String(200))
    checksums_sha256: Mapped[str | None] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(20))  # RUNNING, VERIFIED, INCOMPLETE
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LocalSetting(Base):
    """Configurações locais; chaves de API NUNCA aqui, só IDs de credencial."""

    __tablename__ = "local_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict | list | str | int | bool | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
