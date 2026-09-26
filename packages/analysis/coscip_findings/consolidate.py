"""Consolidador: transforma achados técnicos em poucas pendências claras (§31, §32, §36).

Internamente podem existir quatro falhas da mesma causa; externamente existe um item só.
A consolidação não muda status: ela agrupa, ordena e conta.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from coscip_cbm import (
    SEVERITY_ORDER,
    ComplianceStatus,
    FindingKind,
    ReviewStatus,
    Severity,
)
from coscip_findings.models import Finding, FindingGroup

# Ordem em que a tela apresenta os blocos (§36).
KIND_ORDER: tuple[FindingKind, ...] = (
    FindingKind.NON_COMPLIANT,
    FindingKind.DOCUMENT_MISSING,
    FindingKind.DOCUMENT_INCOMPLETE,
    FindingKind.DATA_MISSING,
    FindingKind.DIVERGENCE,
    FindingKind.NOT_VERIFIABLE,
    FindingKind.ANALYST_REVIEW,
    FindingKind.NO_PENDING_ISSUE,
)


def _worst_kind(kinds: Iterable[FindingKind]) -> FindingKind:
    return min(kinds, key=KIND_ORDER.index)


def _worst_severity(severities: Iterable[Severity]) -> Severity:
    return min(severities, key=lambda s: SEVERITY_ORDER[s])


def _worst_review(states: Iterable[ReviewStatus]) -> ReviewStatus:
    states = list(states)
    for state in (ReviewStatus.CONTESTED, ReviewStatus.DATA_REQUESTED, ReviewStatus.PENDING,
                  ReviewStatus.CONFIRMED):
        if state in states:
            return state
    return ReviewStatus.NOT_REQUIRED


def group_findings(findings: Sequence[Finding]) -> tuple[FindingGroup, ...]:
    """Agrupa por causa raiz (``group_key``) sem perder nenhum achado (§32)."""
    buckets: dict[str, list[Finding]] = {}
    for finding in findings:
        buckets.setdefault(finding.group_key or finding.check_id, []).append(finding)
    groups = []
    for key, items in buckets.items():
        first = items[0]
        missing: list[str] = []
        for item in items:
            missing.extend(f for f in item.missing if f not in missing)
        citations: list[dict[str, Any]] = []
        for item in items:
            citations.extend(c for c in item.normative_citations if c not in citations)
        groups.append(FindingGroup(
            group_key=key, system=first.system,
            severity=_worst_severity(i.severity for i in items),
            kind=_worst_kind(i.kind for i in items),
            title=first.title, explanation=first.explanation,
            required_action=first.required_action, missing=tuple(missing),
            divergences=tuple(d for i in items for d in i.divergences),
            finding_ids=tuple(i.ref for i in items),
            evidence_ids=tuple(dict.fromkeys(e for i in items for e in i.evidence_ids)),
            normative_citations=tuple(citations),
            review_status=_worst_review(i.review_status for i in items),
            # Só os pavimentos onde a causa do grupo aparece, não os que estão em ordem.
            scopes=tuple(dict.fromkeys(
                i.scope_label or i.scope_id for i in items
                if i.scope_id and i.kind is _worst_kind(j.kind for j in items)))))
    return tuple(sorted(groups, key=lambda g: (KIND_ORDER.index(g.kind),
                                               SEVERITY_ORDER[g.severity], g.system,
                                               g.group_key)))


@dataclass(frozen=True)
class AnalysisSummary:
    """Visão executiva: poucos números antes de qualquer detalhe técnico (§36)."""

    pendencies: int
    missing_data: int
    divergences: int
    review_required: int
    not_verifiable: int
    without_pending_issue: int
    not_applicable: int

    def as_dict(self) -> dict[str, int]:
        return {"pendencies": self.pendencies, "missing_data": self.missing_data,
                "divergences": self.divergences, "review_required": self.review_required,
                "not_verifiable": self.not_verifiable,
                "without_pending_issue": self.without_pending_issue,
                "not_applicable": self.not_applicable}


@dataclass(frozen=True)
class ConsolidatedAnalysis:
    summary: AnalysisSummary
    groups: tuple[FindingGroup, ...]
    findings: tuple[Finding, ...]

    @property
    def pending_groups(self) -> tuple[FindingGroup, ...]:
        return tuple(g for g in self.groups if g.kind is not FindingKind.NO_PENDING_ISSUE)


def consolidate(findings: Sequence[Finding]) -> ConsolidatedAnalysis:
    groups = group_findings(findings)
    pending = [g for g in groups if g.kind is not FindingKind.NO_PENDING_ISSUE]
    summary = AnalysisSummary(
        pendencies=sum(1 for g in pending if g.kind in {
            FindingKind.NON_COMPLIANT, FindingKind.DOCUMENT_MISSING,
            FindingKind.DOCUMENT_INCOMPLETE}),
        missing_data=sum(1 for g in pending if g.kind is FindingKind.DATA_MISSING),
        divergences=sum(1 for g in pending if g.kind is FindingKind.DIVERGENCE),
        review_required=sum(1 for g in pending if g.review_status is ReviewStatus.PENDING),
        not_verifiable=sum(1 for g in pending if g.kind is FindingKind.NOT_VERIFIABLE),
        without_pending_issue=sum(
            1 for f in findings if f.compliance_status is ComplianceStatus.COMPLIANT),
        not_applicable=sum(
            1 for f in findings if f.compliance_status is ComplianceStatus.NOT_APPLICABLE),
    )
    return ConsolidatedAnalysis(summary=summary, groups=groups, findings=tuple(findings))
