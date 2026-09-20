"""Finding: o resultado estruturado de um check (arquitetura v2 §8).

O texto da pendência **não é a fonte da verdade** — é uma representação do Finding. Por
isso os três status vivem aqui separados, e o texto fica em ``wording``.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from coscip_cbm import (
    ComplianceStatus,
    EvidenceStatus,
    FindingKind,
    ReviewStatus,
    Severity,
)

FINDING_SCHEMA = "finding/1.0"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Divergence(_Strict):
    """Mesma propriedade informada com valores diferentes por fontes distintas (§22)."""

    subject: str
    field: str
    values: tuple[Any, ...]
    sources: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()


class MeasuredResult(_Strict):
    """Resultado geométrico com tudo que o §27 exige para ser auditável."""

    value: float
    unit: str
    required: float | None = None
    uncertainty_abs: float | None = Field(default=None, ge=0)
    algorithm: str | None = None
    algorithm_version: str | None = None
    geometry_snapshot_hash: str | None = None
    quality_gate: str | None = None


class Finding(_Strict):
    schema_version: str = FINDING_SCHEMA
    check_id: str
    check_version: int
    system: str
    subject: str = ""
    compliance_status: ComplianceStatus
    evidence_status: EvidenceStatus
    review_status: ReviewStatus
    severity: Severity
    kind: FindingKind
    reason_code: str
    title: str
    explanation: str = ""
    required_action: str = ""
    evidence_summary: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    divergences: tuple[Divergence, ...] = ()
    measured: MeasuredResult | None = None
    evidence_ids: tuple[str, ...] = ()
    normative_citations: tuple[dict[str, Any], ...] = ()
    group_key: str = ""

    @property
    def is_pending(self) -> bool:
        """Entra na lista de pendências que o analista precisa resolver."""
        return self.kind is not FindingKind.NO_PENDING_ISSUE

    @property
    def content_sha256(self) -> str:
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class FindingGroup(_Strict):
    """Vários ``Finding`` da mesma causa raiz vistos como um item só na tela (§32)."""

    group_key: str
    system: str
    severity: Severity
    kind: FindingKind
    title: str
    explanation: str = ""
    required_action: str = ""
    missing: tuple[str, ...] = ()
    divergences: tuple[Divergence, ...] = ()
    finding_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    normative_citations: tuple[dict[str, Any], ...] = ()
    review_status: ReviewStatus = ReviewStatus.NOT_REQUIRED
