"""Camada de evidências da arquitetura v2 (§7, §22, §53, §54, §55).

Resultado de CAD, documento, cálculo ou declaração humana vira ``Evidence``; o check lê
evidências, nunca texto de relatório.
"""

from coscip_evidence.claims import Claim, claims_from_evidence
from coscip_evidence.models import EVIDENCE_SCHEMA, Evidence, EvidenceLocator
from coscip_evidence.registry import Consensus, EvidenceSet, ExtractionGap

__all__ = [
    "EVIDENCE_SCHEMA",
    "Claim",
    "Consensus",
    "Evidence",
    "EvidenceLocator",
    "EvidenceSet",
    "ExtractionGap",
    "claims_from_evidence",
]
