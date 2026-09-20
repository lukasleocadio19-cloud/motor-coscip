"""Executor do Plano de Verificação: Check + Evidence → Finding (§5, §8, §25, §54, §55).

Regras de segurança que o executor nunca quebra:

- ausência de evidência não vira conformidade (§74);
- ausência de extração não vira ausência documental (§54);
- dependência inconclusiva não libera o dependente (§20);
- porta de qualidade reprovada mostra o número, mas não conclui conformidade (§25).
"""

from __future__ import annotations

from typing import Any

from coscip_evidence import Consensus, EvidenceSet
from coscip_findings.models import Divergence, Finding, MeasuredResult
from coscip_findings.wording import compose_explanation, evidence_summary

from coscip_cbm import (
    Applicability,
    ComplianceStatus,
    ConsensusStatus,
    EvidenceStatus,
    FindingKind,
    ReviewStatus,
)
from coscip_geometry.tolerances import compare_maximum, compare_minimum
from coscip_normative.verification.catalog import CheckCatalog
from coscip_normative.verification.compiler import VerificationPlan
from coscip_normative.verification.dependencies import dependency_gate
from coscip_normative.verification.models import CheckDefinition


def _citations(check: CheckDefinition) -> tuple[dict[str, Any], ...]:
    return tuple({"document": s.document, "edition": s.edition, "item": s.item,
                  "page": s.page} for s in check.normative_basis)


def _finding(check: CheckDefinition, *, compliance: ComplianceStatus,
             evidence: EvidenceStatus, review: ReviewStatus, kind: FindingKind,
             reason_code: str, missing: tuple[str, ...] = (),
             divergences: tuple[Divergence, ...] = (), evidence_ids: tuple[str, ...] = (),
             sources: tuple[str, ...] = (), measured: MeasuredResult | None = None,
             explanation_extra: str = "") -> Finding:
    labels = check.wording.field_labels
    base = check.wording.explanation
    if explanation_extra:
        base = f"{base}\n\n{explanation_extra}".strip()
    return Finding(
        check_id=check.id, check_version=check.version, system=check.system,
        subject=check.question.subject if check.question else "",
        compliance_status=compliance, evidence_status=evidence, review_status=review,
        severity=check.severity, kind=kind, reason_code=reason_code,
        title=check.wording.title,
        explanation=compose_explanation(base, missing, divergences, labels),
        required_action=check.wording.required_action,
        evidence_summary=evidence_summary(sources), missing=missing,
        divergences=divergences, measured=measured, evidence_ids=evidence_ids,
        normative_citations=_citations(check), group_key=check.grouping)


def _review_for(check: CheckDefinition, *, conflict: bool = False,
                missing: bool = False, forced: bool = False) -> ReviewStatus:
    rules = check.human_review
    if forced or rules.always or (conflict and rules.on_conflict) or (
            missing and rules.on_missing):
        return ReviewStatus.PENDING
    return ReviewStatus.NOT_REQUIRED


def _sources_of(evidence: EvidenceSet, ids: tuple[str, ...]) -> tuple[str, ...]:
    by_id = {e.id: e for e in evidence}
    return tuple(by_id[i].describe_source() for i in ids if i in by_id)


def _quality_failed(check: CheckDefinition, context_facts: dict[str, Any]) -> bool:
    gate = check.question.quality_gate if check.question else None
    return bool(gate) and context_facts.get(gate) is False


def execute_check(check: CheckDefinition, evidence: EvidenceSet,
                  context_facts: dict[str, Any]) -> Finding:
    """Responde um check executável a partir das evidências reunidas."""
    question = check.question
    assert question is not None  # checks manuais não chegam aqui
    if _quality_failed(check, context_facts):
        return _finding(
            check, compliance=check.result_rules.quality_gate_failed,
            evidence=EvidenceStatus.PARTIAL, review=_review_for(check, forced=True),
            kind=FindingKind.NOT_VERIFIABLE, reason_code="QUALITY_GATE_FAILED",
            explanation_extra=f"Porta de qualidade não atendida: {question.quality_gate}.")
    match question.kind:
        case "required_fields":
            return _required_fields(check, evidence)
        case "consistency":
            return _consistency(check, evidence)
        case "presence" | "minimum_count":
            return _counting(check, evidence)
        case "minimum_value" | "maximum_value":
            return _comparison(check, evidence)
    raise AssertionError(f"pergunta não compilada: {question.kind}")


def _required_fields(check: CheckDefinition, evidence: EvidenceSet) -> Finding:
    question = check.question
    assert question is not None
    required_sources = tuple(question.required_sources)
    results = {f: evidence.consensus(f, subject=question.subject,
                                     required_sources=required_sources)
               for f in question.required_fields}
    conflicting = [c for c in results.values() if c.status is ConsensusStatus.CONFLICTING]
    missing = tuple(f for f, c in results.items()
                    if c.status is ConsensusStatus.MISSING_REQUIRED_SOURCE)
    ids = tuple(i for c in results.values() for i in c.evidence_ids)
    sources = _sources_of(evidence, ids)
    divergences = tuple(_divergence(c, evidence) for c in conflicting)
    if missing:
        found_any = bool(ids)
        # Campo ausente e valor divergente convivem: o achado carrega os dois, mas a
        # providência é a mesma — completar a documentação.
        return _finding(
            check, compliance=check.result_rules.missing_required_field,
            evidence=(EvidenceStatus.CONFLICTING if conflicting else
                      EvidenceStatus.PARTIAL if found_any else EvidenceStatus.MISSING),
            review=_review_for(check, conflict=bool(conflicting), missing=True),
            kind=(FindingKind.DOCUMENT_INCOMPLETE if found_any else FindingKind.DATA_MISSING),
            reason_code="MISSING_REQUIRED_FIELD", missing=missing,
            divergences=divergences, evidence_ids=ids, sources=sources)
    if conflicting:
        return _finding(
            check, compliance=check.result_rules.conflicting_values,
            evidence=EvidenceStatus.CONFLICTING, review=_review_for(check, conflict=True),
            kind=FindingKind.DIVERGENCE, reason_code="CONFLICTING_VALUES",
            divergences=divergences, evidence_ids=ids, sources=sources)
    return _satisfied(check, ids, sources)


def _divergence(consensus: Consensus, evidence: EvidenceSet) -> Divergence:
    by_id = {e.id: e for e in evidence}
    sources = tuple(by_id[i].source_id for i in consensus.evidence_ids if i in by_id)
    return Divergence(subject=consensus.subject, field=consensus.field,
                      values=consensus.values, sources=sources,
                      evidence_ids=consensus.evidence_ids)


def _consistency(check: CheckDefinition, evidence: EvidenceSet) -> Finding:
    question = check.question
    assert question is not None and question.field is not None
    consensus = evidence.consensus(question.field, subject=question.subject,
                                   required_sources=tuple(question.required_sources))
    sources = _sources_of(evidence, consensus.evidence_ids)
    if consensus.status is ConsensusStatus.CONFLICTING:
        return _finding(
            check, compliance=check.result_rules.conflicting_values,
            evidence=EvidenceStatus.CONFLICTING, review=_review_for(check, conflict=True),
            kind=FindingKind.DIVERGENCE, reason_code="CONFLICTING_VALUES",
            divergences=(_divergence(consensus, evidence),),
            evidence_ids=consensus.evidence_ids, sources=sources)
    if consensus.status is ConsensusStatus.MISSING_REQUIRED_SOURCE:
        return _finding(
            check, compliance=check.result_rules.missing_required_field,
            evidence=(EvidenceStatus.PARTIAL if consensus.evidence_ids
                      else EvidenceStatus.MISSING),
            review=_review_for(check, missing=True),
            kind=(FindingKind.DOCUMENT_INCOMPLETE if consensus.evidence_ids
                  else FindingKind.DOCUMENT_MISSING),
            reason_code="MISSING_REQUIRED_SOURCE", missing=(question.field,),
            evidence_ids=consensus.evidence_ids, sources=sources)
    if consensus.status is ConsensusStatus.SINGLE_SOURCE:
        # Uma fonte só não confirma nem contradiz: não há cruzamento a fazer.
        return _finding(
            check, compliance=check.result_rules.missing_required_field,
            evidence=EvidenceStatus.PARTIAL, review=_review_for(check, forced=True),
            kind=FindingKind.NOT_VERIFIABLE, reason_code="SINGLE_SOURCE",
            evidence_ids=consensus.evidence_ids, sources=sources,
            explanation_extra="Apenas uma fonte informa o dado; não há cruzamento possível.")
    return _satisfied(check, consensus.evidence_ids, sources)


def _counting(check: CheckDefinition, evidence: EvidenceSet) -> Finding:
    question = check.question
    assert question is not None and question.field is not None
    found = [e for e in evidence.for_field(question.field, subject=question.subject)
             if e.located and e.normalized_value is not None]
    required = int(question.required_value or 1)
    ids = tuple(e.id for e in found)
    sources = _sources_of(evidence, ids)
    if not found:
        # §54: nada encontrado não é "não existe". Fica inconclusivo e vai para revisão.
        gap = evidence.has_gap(question.field, subject=question.subject)
        return _finding(
            check, compliance=check.result_rules.missing_required_field,
            evidence=EvidenceStatus.MISSING, review=_review_for(check, forced=True),
            kind=FindingKind.DATA_MISSING, reason_code="NO_EVIDENCE",
            missing=(question.field,),
            explanation_extra=("A extração rodou e não localizou o elemento; confirmar na "
                               "fonte antes de concluir ausência."
                               if gap else "Nenhuma evidência foi reunida para este item."))
    if len(found) < required:
        return _finding(
            check, compliance=check.result_rules.not_satisfied,
            evidence=EvidenceStatus.SUFFICIENT, review=_review_for(check),
            kind=FindingKind.NON_COMPLIANT, reason_code="BELOW_MINIMUM_COUNT",
            evidence_ids=ids, sources=sources,
            measured=MeasuredResult(value=float(len(found)), unit="un",
                                    required=float(required)),
            explanation_extra=f"Localizados {len(found)}; exigidos {required}.")
    return _satisfied(check, ids, sources,
                      measured=MeasuredResult(value=float(len(found)), unit="un",
                                              required=float(required)))


def _comparison(check: CheckDefinition, evidence: EvidenceSet) -> Finding:
    question = check.question
    assert question is not None and question.field is not None
    found = [e for e in evidence.for_field(question.field, subject=question.subject)
             if e.located and e.normalized_value is not None]
    ids = tuple(e.id for e in found)
    sources = _sources_of(evidence, ids)
    if not found:
        return _finding(
            check, compliance=check.result_rules.missing_required_field,
            evidence=EvidenceStatus.MISSING, review=_review_for(check, forced=True),
            kind=FindingKind.DATA_MISSING, reason_code="NO_EVIDENCE",
            missing=(question.field,))
    worst = max(found, key=lambda e: float(e.normalized_value))
    if question.kind == "minimum_value":
        worst = min(found, key=lambda e: float(e.normalized_value))
    value = float(worst.normalized_value)
    uncertainty = worst.uncertainty_abs or 0.0
    required = float(question.required_value or 0)
    compare = compare_minimum if question.kind == "minimum_value" else compare_maximum
    verdict = compare(value, uncertainty, required)
    measured = MeasuredResult(
        value=value, unit=question.unit or worst.unit or "", required=required,
        uncertainty_abs=uncertainty, algorithm=worst.algorithm,
        algorithm_version=worst.algorithm_version, quality_gate=worst.quality_gate)
    if verdict == "REVIEW_REQUIRED":
        return _finding(
            check, compliance=ComplianceStatus.UNDETERMINED,
            evidence=EvidenceStatus.PARTIAL, review=_review_for(check, forced=True),
            kind=FindingKind.NOT_VERIFIABLE, reason_code="WITHIN_UNCERTAINTY",
            evidence_ids=ids, sources=sources, measured=measured,
            explanation_extra=("A medida com sua incerteza atravessa o limite exigido; "
                               "não é possível concluir."))
    if verdict == "FAIL":
        return _finding(
            check, compliance=check.result_rules.not_satisfied,
            evidence=EvidenceStatus.SUFFICIENT, review=_review_for(check),
            kind=FindingKind.NON_COMPLIANT, reason_code="OUT_OF_LIMIT",
            evidence_ids=ids, sources=sources, measured=measured)
    return _satisfied(check, ids, sources, measured=measured)


def _satisfied(check: CheckDefinition, ids: tuple[str, ...], sources: tuple[str, ...],
               measured: MeasuredResult | None = None) -> Finding:
    return _finding(check, compliance=ComplianceStatus.COMPLIANT,
                    evidence=EvidenceStatus.SUFFICIENT, review=_review_for(check),
                    kind=FindingKind.NO_PENDING_ISSUE, reason_code="SATISFIED",
                    evidence_ids=ids, sources=sources, measured=measured)


def _not_executed(check: CheckDefinition, *, compliance: ComplianceStatus,
                  kind: FindingKind, reason_code: str, reason: str,
                  review: ReviewStatus) -> Finding:
    return _finding(check, compliance=compliance, evidence=EvidenceStatus.MISSING,
                    review=review, kind=kind, reason_code=reason_code,
                    explanation_extra=reason)


def execute_plan(plan: VerificationPlan, catalog: CheckCatalog, evidence: EvidenceSet,
                 context_facts: dict[str, Any] | None = None) -> tuple[Finding, ...]:
    """Executa o plano na ordem das dependências. Mesmo plano + mesmas evidências ⇒
    mesmos achados."""
    facts = context_facts or {}
    by_id = {item.check_id: item for item in plan.items}
    concluded: dict[str, ComplianceStatus] = {}
    findings: list[Finding] = []
    for check_id in plan.execution_order:
        check = catalog.get(check_id)
        item = by_id[check_id]
        gate = dependency_gate(check.depends_on, concluded)
        if item.applicability is Applicability.UNKNOWN:
            finding = _not_executed(
                check, compliance=ComplianceStatus.UNDETERMINED,
                kind=FindingKind.NOT_VERIFIABLE, reason_code="APPLICABILITY_UNKNOWN",
                reason=("Faltam dados do enquadramento para decidir se este item se aplica: "
                        + ", ".join(item.missing_facts)) if item.missing_facts else (
                        "Enquadramento insuficiente para decidir a aplicabilidade."),
                review=ReviewStatus.PENDING)
        elif gate is not None:
            state, reason = gate
            finding = _not_executed(
                check,
                compliance=(ComplianceStatus.NOT_APPLICABLE if state == "NOT_APPLICABLE"
                            else ComplianceStatus.UNDETERMINED),
                kind=(FindingKind.NO_PENDING_ISSUE if state == "NOT_APPLICABLE"
                      else FindingKind.NOT_VERIFIABLE),
                reason_code=f"DEPENDENCY_{state}",
                reason=f"Não executado porque {reason}.",
                review=(ReviewStatus.NOT_REQUIRED if state == "NOT_APPLICABLE"
                        else ReviewStatus.PENDING))
        elif check.manual:
            finding = _not_executed(
                check, compliance=ComplianceStatus.UNDETERMINED,
                kind=FindingKind.ANALYST_REVIEW, reason_code="MANUAL_CONFIRMATION",
                reason="Item de confirmação humana: o motor não conclui sozinho.",
                review=ReviewStatus.PENDING)
        else:
            finding = execute_check(check, evidence, facts)
        concluded[check_id] = finding.compliance_status
        findings.append(finding)
    for item in plan.items:
        if item.applicability is Applicability.FALSE:
            check = catalog.get(item.check_id)
            findings.append(_not_executed(
                check, compliance=ComplianceStatus.NOT_APPLICABLE,
                kind=FindingKind.NO_PENDING_ISSUE, reason_code="NOT_APPLICABLE",
                reason=item.reason, review=ReviewStatus.NOT_REQUIRED))
    return tuple(findings)
