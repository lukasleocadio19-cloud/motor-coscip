"""Achados da arquitetura v2 (§8, §31, §32, §33, §36, §57).

O Finding estruturado é a fonte da verdade; o texto é representação dele.
"""

from coscip_findings.consolidate import (
    KIND_ORDER,
    AnalysisSummary,
    ConsolidatedAnalysis,
    consolidate,
    group_findings,
)
from coscip_findings.models import (
    FINDING_SCHEMA,
    Divergence,
    Finding,
    FindingGroup,
    MeasuredResult,
)

__all__ = [
    "FINDING_SCHEMA",
    "KIND_ORDER",
    "AnalysisSummary",
    "ConsolidatedAnalysis",
    "Divergence",
    "Finding",
    "FindingGroup",
    "MeasuredResult",
    "consolidate",
    "group_findings",
]
