"""Contratos do domínio (CBM) independentes de ezdxf e do motor normativo.

Referência: 02 — Contratos de implementação, seções 1, 3, 4, 5 e 8.
"""

from coscip_cbm.enums import (
    Applicability,
    CoverageStatus,
    ElementClass,
    EvaluationStatus,
    ExecutionState,
    ExtractionQuality,
    Provenance,
    ReviewDecision,
    SemanticStatus,
)
from coscip_cbm.models import (
    CadSourceInstance,
    CbmElement,
    CbmSnapshot,
    Execution,
    ExecutionManifest,
    Floor,
    Measured,
    ProblemDetail,
    RequiredValue,
    RuleResult,
    SnapshotQuality,
)

__all__ = [
    "Applicability",
    "CadSourceInstance",
    "CbmElement",
    "CbmSnapshot",
    "CoverageStatus",
    "ElementClass",
    "EvaluationStatus",
    "Execution",
    "ExecutionManifest",
    "ExecutionState",
    "ExtractionQuality",
    "Floor",
    "Measured",
    "ProblemDetail",
    "Provenance",
    "RequiredValue",
    "ReviewDecision",
    "RuleResult",
    "SemanticStatus",
    "SnapshotQuality",
]
