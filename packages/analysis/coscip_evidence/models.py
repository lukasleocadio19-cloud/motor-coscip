"""Evidence: qualquer fato usado para responder a um check (arquitetura v2 §7 e §27).

Toda evidência é imutável e guarda de onde veio. Vale a regra §53: **sem localizador
não há evidência** — um valor extraído automaticamente que não aponte para a página, o
trecho ou a entidade de origem nasce ``UNVERIFIED`` e nunca sustenta conformidade.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from coscip_cbm import EvidenceSourceType, EvidenceStatus

EVIDENCE_SCHEMA = "evidence/1.0"

# Métodos que produzem um fato sem origem apontável no documento/desenho e que, por isso,
# dispensam localizador: a própria declaração humana e o cálculo sobre outras evidências.
_SELF_LOCATING = frozenset({"MANUAL", "CALCULATION"})


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceLocator(_Strict):
    """Onde exatamente o fato foi encontrado. Campos vazios = não localizado."""

    page: int | None = Field(default=None, gt=0)
    bbox: tuple[float, float, float, float] | None = None
    text_span: str | None = None
    entity_handle: str | None = None
    layer: str | None = None
    floor_id: str | None = None
    table_row: str | None = None
    # Objeto físico a que a evidência se refere (F5.2): a mesma coisa vista por fontes
    # diferentes tem o mesmo ``object_key`` e conta uma vez só (F6).
    object_key: str | None = None

    @property
    def is_empty(self) -> bool:
        # object_key identifica o objeto, não diz ONDE o fato está: não localiza sozinho
        return not any(getattr(self, name) is not None
                       for name in type(self).model_fields if name != "object_key")

    def describe(self) -> str:
        parts = []
        if self.page is not None:
            parts.append(f"página {self.page}")
        if self.table_row:
            parts.append(f"linha {self.table_row}")
        if self.entity_handle:
            parts.append(f"entidade {self.entity_handle}")
        if self.layer:
            parts.append(f"camada {self.layer}")
        if self.floor_id:
            parts.append(f"pavimento {self.floor_id}")
        return ", ".join(parts)


class Evidence(_Strict):
    """Fato imutável com origem, versão, hash, local exato e método de extração."""

    schema_version: str = EVIDENCE_SCHEMA
    id: str
    process_id: str
    source_type: EvidenceSourceType
    # Categoria documental do §10 (ART, RRT, MEMORIAL, CURVA_BOMBA...). Vazia fora de
    # documentos. É o que permite exigir que DUAS categorias informem o mesmo campo.
    source_category: str = ""
    source_id: str
    source_version: int = Field(ge=1)
    source_hash: str
    locator: EvidenceLocator = EvidenceLocator()
    # O que o fato afirma: ``subject`` é o objeto (ex.: "bomba-principal"), ``field`` a
    # propriedade (ex.: "pump_flow_l_min"). Subject vazio = fato do processo inteiro.
    subject: str = ""
    field: str
    raw_value: Any = None
    normalized_value: Any = None
    unit: str | None = None
    uncertainty_abs: float | None = Field(default=None, ge=0)
    extraction_method: str
    extraction_schema: str | None = None
    algorithm: str | None = None
    algorithm_version: str | None = None
    quality_gate: str | None = None
    semantic_validation: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    ai_run_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _no_value_without_field(self) -> Evidence:
        if not self.field.strip():
            raise ValueError("evidência sem campo")
        return self

    @property
    def located(self) -> bool:
        """§53: valor com origem apontável (ou produzido por declaração/cálculo)."""
        return self.extraction_method in _SELF_LOCATING or not self.locator.is_empty

    @property
    def status(self) -> EvidenceStatus:
        if self.normalized_value is None and self.raw_value is None:
            return EvidenceStatus.MISSING
        if not self.located:
            return EvidenceStatus.UNVERIFIED
        return EvidenceStatus.SUFFICIENT

    @property
    def content_sha256(self) -> str:
        payload = self.model_dump(mode="json", exclude={"id", "created_at"})
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def describe_source(self) -> str:
        where = self.locator.describe()
        return f"{self.source_id} ({where})" if where else self.source_id
