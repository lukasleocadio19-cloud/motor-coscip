"""Claim: o que uma fonte afirma sobre um objeto (arquitetura v2 §22).

Modelo intermediário entre a evidência e o cruzamento. Aqui ele só projeta evidências;
a resolução de entidades e o motor de cruzamento completo são da fase 7.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from coscip_cbm import EvidenceSourceType
from coscip_evidence.models import Evidence


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject: str
    property: str
    value: Any
    unit: str | None = None
    source: str
    source_type: EvidenceSourceType
    evidence_id: str


def claims_from_evidence(items: list[Evidence]) -> list[Claim]:
    """Projeta evidências localizadas e com valor em afirmações comparáveis."""
    return [
        Claim(subject=e.subject, property=e.field, value=e.normalized_value, unit=e.unit,
              source=e.source_id, source_type=e.source_type, evidence_id=e.id)
        for e in items if e.located and e.normalized_value is not None
    ]
