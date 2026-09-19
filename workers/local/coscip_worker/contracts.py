"""Saída do worker validada pelo supervisor antes de qualquer publicação."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Arquivos que o estágio de importação precisa produzir em ``out/``.
OUTPUT_FILES = (
    "inventory.json", "entities.jsonl", "entities.idx", "scene.json", "scene.bin",
    "scene_ids.bin",
)


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

    schema_version: str = "worker-import/2.0"
    job_id: str
    attempt_token: str
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    inventory: InventoryOut
    outputs: dict[str, str]  # nome → SHA-256
    scene_segment_count: int = Field(ge=0)
    scene_max_sagitta: float = Field(ge=0)
    duration_s: float
    peak_memory_mb: float | None = None

    @field_validator("outputs")
    @classmethod
    def _all_outputs(cls, v: dict[str, str]) -> dict[str, str]:
        if set(v) != set(OUTPUT_FILES):
            raise ValueError(f"saídas esperadas: {OUTPUT_FILES}")
        for sha in v.values():
            if len(sha) != 64:
                raise ValueError("hash inválido")
        return v


# --- análise da planta -------------------------------------------------------------
PLANT_OUTPUT_FILES = ("analysis.json",)


class PlantAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "worker-plant-analysis/1.0"
    job_id: str
    attempt_token: str
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    outputs: dict[str, str]  # nome → SHA-256
    summary: dict
    duration_s: float

    @field_validator("outputs")
    @classmethod
    def _all_outputs(cls, v: dict[str, str]) -> dict[str, str]:
        if set(v) != set(PLANT_OUTPUT_FILES):
            raise ValueError(f"saídas esperadas: {PLANT_OUTPUT_FILES}")
        if any(len(sha) != 64 for sha in v.values()):
            raise ValueError("hash inválido")
        return v
