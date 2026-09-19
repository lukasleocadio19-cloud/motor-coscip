"""Saída do worker validada pelo supervisor antes de qualquer publicação."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class InventoryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dxf_version: str
    insunits: int
    insunits_name: str
    units_declared: bool
    layouts: list[str]
    layers: list[str]
    blocks: list[str]
    xrefs: list[str]
    entity_counts: dict[str, int]
    expanded_count: int = Field(ge=0)
    quality_counts: dict[str, int]
    unsupported_counts: dict[str, int]
    extents: list[float] | None = None
    warnings: list[str]
    layout_entity_counts: dict[str, int] = Field(default_factory=dict)
    proxy_object_count: int = 0
    unit_suggestion: dict | None = None  # indício; confirmação humana obrigatória


class ImportResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "worker-import/1.0"
    job_id: str
    attempt_token: str
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    inventory: InventoryOut
    entities_file: str
    entities_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    duration_s: float
    peak_memory_mb: float | None = None
