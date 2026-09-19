"""Modelos Pydantic dos contratos lógicos. IDs em produção são UUIDs."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from coscip_cbm.enums import (
    Applicability,
    EvaluationStatus,
    ExecutionState,
    ExtractionQuality,
    Provenance,
    SemanticStatus,
)

Matrix4 = list[list[float]]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CadSourceInstance(_Frozen):
    """Contrato de origem CAD (02 §3).

    A identidade combina arquivo/versão + handle + caminho de instâncias + cadeia
    de XRefs + layout. Handle isolado não é identificador global.
    """

    schema_version: Literal["cad-source/1.0"] = "cad-source/1.0"
    id: str
    file_object_id: str
    file_sha256: str
    drawing_id: str
    layout: str = "Model"
    source_handle: str
    entity_type: str
    instance_path: tuple[str, ...]
    layer: str
    block_name: str | None = None
    coordinate_frame_id: str
    world_transform: Matrix4
    extraction_quality: ExtractionQuality
    raw_artifact_id: str | None = None

    @field_validator("file_sha256")
    @classmethod
    def _sha256(cls, v: str) -> str:
        if len(v) != 64 or any(c not in "0123456789abcdef" for c in v):
            raise ValueError("file_sha256 deve ser SHA-256 hexadecimal minúsculo")
        return v

    @field_validator("world_transform")
    @classmethod
    def _matrix(cls, v: Matrix4) -> Matrix4:
        if len(v) != 4 or any(len(row) != 4 for row in v):
            raise ValueError("world_transform deve ser 4x4")
        return v

    @property
    def identity_key(self) -> str:
        return f"{self.file_sha256}|{self.layout}|{'/'.join(self.instance_path)}"


class Measured(_Frozen):
    """Valor em SI com método, incerteza e procedência.

    ``value=None`` (desconhecido) é distinto de zero e de não aplicável.
    """

    value: float | None
    unit: str
    method: str | None = None
    uncertainty_abs: float | None = None
    provenance: Provenance | None = None
    evidence_ids: tuple[str, ...] = ()
    quality: Literal["OK", "MISSING", "CONFLICT", "UNCERTAIN"] = "OK"


class Floor(_Frozen):
    id: str
    name: str
    elevation_m: float
    coordinate_frame_id: str
    alignment_status: Literal["CANDIDATE", "CONFIRMED"]


class CbmElement(_Frozen):
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    id: str
    floor_id: str
    element_class: str = Field(alias="class")
    geometry_ref: str | None = None
    source_instance_ids: tuple[str, ...] = ()
    semantic_status: SemanticStatus
    properties: dict[str, Measured] = Field(default_factory=dict)
    connects: tuple[str, ...] = ()


class SnapshotQuality(_Frozen):
    units_confirmed: bool
    unresolved_xrefs: int = 0
    unsupported_entity_count: int = 0
    unconfirmed_topology_count: int = 0
    blocking_issue_ids: tuple[str, ...] = ()

    @property
    def blocks_analysis(self) -> bool:
        return not self.units_confirmed or bool(self.blocking_issue_ids)


class CbmSnapshot(_Frozen):
    """Contrato CBM (02 §4). Snapshot é imutável; correção cria outro com ``parent``."""

    schema_version: Literal["cbm/1.0"] = "cbm/1.0"
    snapshot_id: str
    tenant_id: str
    project_id: str
    submission_revision_id: str
    parent_snapshot_id: str | None = None
    units: dict[str, str] = Field(
        default_factory=lambda: {"length": "m", "area": "m2", "angle": "rad"}
    )
    tolerance_profile_id: str
    context_snapshot_id: str
    floors: tuple[Floor, ...]
    elements: tuple[CbmElement, ...]
    quality: SnapshotQuality


class ExecutionManifest(_Frozen):
    """Contrato de execução e reprodutibilidade (02 §5)."""

    input_manifest_hash: str
    model_snapshot_id: str
    context_snapshot_id: str
    rule_package_id: str
    tolerance_profile_id: str
    parser_build: str
    geometry_build: str
    rules_build: str
    semantic_dictionary_version: str
    worker_package_hash: str
    runtime_platform: str
    sqlite_runtime_version: str
    deterministic_seed: int = 0


class Execution(BaseModel):
    execution_id: str
    analysis_id: str | None = None
    state: ExecutionState
    stage: str | None = None
    manifest: ExecutionManifest | None = None
    completed_stages: int = 0
    planned_stages: int = 0
    started_at: datetime | None = None


class RequiredValue(_Frozen):
    value: Decimal
    unit: str
    source: str


class RuleResult(_Frozen):
    """Contrato de resultado (02 §8). Distinto do sucesso técnico e da decisão humana."""

    result_id: str
    analysis_id: str
    rule_id: str
    rule_version: int
    production_eligible: bool
    subject_id: str
    applicability: Applicability
    status: EvaluationStatus
    reason_code: str
    measured: Measured | None = None
    required: RequiredValue | None = None
    operation: str | None = None
    evidence_ids: tuple[str, ...] = ()
    location: dict[str, str] = Field(default_factory=dict)
    review_state: Literal["PENDING", "CONFIRMED", "CONTESTED"] = "PENDING"


class ProblemDetail(BaseModel):
    """Erro estruturado (RFC 9457) — 02 §6."""

    type: str
    title: str
    status: int
    code: str
    trace_id: str | None = None
    resource_id: str | None = None
    required_action: str | None = None
    extra: dict[str, Any] | None = None
