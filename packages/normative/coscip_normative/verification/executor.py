"""Executor do Plano de Verificação: Check + Evidence → Finding (§5, §8, §25, §54, §55).

Regras de segurança que o executor nunca quebra:

- ausência de evidência não vira conformidade (§74);
- ausência de extração não vira ausência documental (§54);
- dependência inconclusiva não libera o dependente (§20);
- porta de qualidade reprovada ou não informada mostra o número, mas não conclui
  conformidade (§25).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from coscip_evidence import Consensus, EvidenceSet
from coscip_findings.models import Divergence, Finding, MeasuredResult
from coscip_findings.wording import compose_explanation, criterion_block, evidence_summary

from coscip_cbm import (
    Applicability,
    ComplianceStatus,
    ConsensusStatus,
    EvidenceSourceType,
    EvidenceStatus,
    FindingKind,
    ReviewStatus,
)
from coscip_geometry.tolerances import compare_maximum, compare_minimum
from coscip_normative.verification.catalog import CheckCatalog
from coscip_normative.verification.compiler import PlanItem, VerificationPlan
from coscip_normative.verification.dependencies import dependency_gate
from coscip_normative.verification.models import CheckDefinition, Question


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
    criterion = check.interpretation.as_dict() if check.interpretation else None
    if explanation_extra:
        base = f"{base}\n\n{explanation_extra}".strip()
    if criterion:
        base = f"{base}\n\n{criterion_block(criterion)}".strip()
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
        normative_citations=_citations(check), adopted_criterion=criterion,
        group_key=check.grouping)


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


def _failed_gates(check: CheckDefinition, context_facts: dict[str, Any]) -> list[str]:
    """Portas não atendidas. Porta sem fato informado conta como não atendida: qualidade
    desconhecida não sustenta conformidade (mesma regra do motor de regras)."""
    gates = check.question.gates if check.question else ()
    return [g if context_facts.get(g) is False else f"{g} (não informada)"
            for g in gates if context_facts.get(g) is not True]


def execute_check(check: CheckDefinition, evidence: EvidenceSet,
                  context_facts: dict[str, Any]) -> Finding:
    """Responde um check executável a partir das evidências reunidas."""
    question = check.question
    assert question is not None  # checks manuais não chegam aqui
    if failed := _failed_gates(check, context_facts):
        return _finding(
            check, compliance=check.result_rules.quality_gate_failed,
            evidence=EvidenceStatus.PARTIAL, review=_review_for(check, forced=True),
            kind=FindingKind.NOT_VERIFIABLE, reason_code="QUALITY_GATE_FAILED",
            explanation_extra=f"Porta de qualidade não atendida: {', '.join(failed)}.")
    match question.kind:
        case "required_fields":
            return _required_fields(check, evidence)
        case "consistency":
            return _consistency(check, evidence)
        case "presence" | "minimum_count":
            return _counting(check, evidence)
        case "minimum_value" | "maximum_value":
            return _comparison(check, evidence, context_facts)
        case "composition":
            return _composition(check, evidence)
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


def _fits(objects: list[frozenset[str]], slots: tuple[tuple[str, ...], ...]) -> bool:
    """Cada vaga recebe um objeto distinto que atende todas as suas classes (emparelhamento
    por busca exaustiva: poucos objetos por pavimento)."""
    def place(i: int, used: frozenset[int]) -> bool:
        if i == len(slots):
            return True
        need = set(slots[i])
        return any(j not in used and need <= objects[j] and place(i + 1, used | {j})
                   for j in range(len(objects)))
    return place(0, frozenset())


def _composition(check: CheckDefinition, evidence: EvidenceSet) -> Finding:
    """Composição mínima (ex.: NT 2-01 5.2.5: um A e um B/C, ou dois ABC).

    Valor fora de ``value_classes`` (agente não identificado) não atende vaga nenhuma. Se as
    conhecidas já bastam, conclui; se não bastam e há desconhecidas, fica inconclusivo —
    desconhecido nunca vira conformidade nem reprovação."""
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
    known = [frozenset(question.value_classes[str(e.normalized_value)]) for e in found
             if str(e.normalized_value) in question.value_classes]
    unknown = [e for e in found if str(e.normalized_value) not in question.value_classes]
    shown = ", ".join(sorted(str(e.normalized_value) for e in found))
    if any(_fits(known, alt) for alt in question.alternatives):
        return _satisfied(check, ids, sources)
    if unknown:
        return _finding(
            check, compliance=check.result_rules.missing_required_field,
            evidence=EvidenceStatus.PARTIAL, review=_review_for(check, forced=True),
            kind=FindingKind.DATA_MISSING, reason_code="VALUE_NOT_IDENTIFIED",
            missing=(question.field,), evidence_ids=ids, sources=sources,
            explanation_extra=(f"{len(unknown)} de {len(found)} sem identificação ({shown}); "
                               "com os identificados a composição não se completa."))
    return _finding(
        check, compliance=check.result_rules.not_satisfied,
        evidence=EvidenceStatus.SUFFICIENT, review=_review_for(check),
        kind=FindingKind.NON_COMPLIANT, reason_code="COMPOSITION_NOT_MET",
        evidence_ids=ids, sources=sources,
        explanation_extra=f"Localizados: {shown}.")


def _positive(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int | float) and value > 0


def _required_limits(question: Question, facts: dict[str, Any]) -> tuple[float, ...] | None:
    """Limites possíveis. Mais de um quando o enquadramento ainda não decide qual vale
    (ex.: Anexo C da NT 2-08 sem saber se o pavimento é o de descarga)."""
    if question.required_fact is None:
        return (float(question.required_value or 0),)
    value = facts.get(question.required_fact)
    if _positive(value):
        return (float(value),)
    if isinstance(value, list | tuple) and value and all(_positive(v) for v in value):
        return tuple(sorted({float(v) for v in value}))
    return None


def _comparison(check: CheckDefinition, evidence: EvidenceSet,
                facts: dict[str, Any]) -> Finding:
    question = check.question
    assert question is not None and question.field is not None
    found = [e for e in evidence.for_field(question.field, subject=question.subject)
             if e.located and e.normalized_value is not None]
    ids = tuple(e.id for e in found)
    sources = _sources_of(evidence, ids)
    limits = _required_limits(question, facts)
    if limits is None:
        # O limite depende do analista (ex.: tabela em imagem): sem ele, nada conclui,
        # mas a medida já apurada continua no achado.
        return _finding(
            check, compliance=check.result_rules.missing_required_field,
            evidence=EvidenceStatus.PARTIAL if found else EvidenceStatus.MISSING,
            review=_review_for(check, forced=True), kind=FindingKind.DATA_MISSING,
            reason_code="REQUIRED_LIMIT_MISSING", missing=(question.required_fact or "",),
            evidence_ids=ids, sources=sources,
            explanation_extra=(f"O limite exigido ({question.required_fact}) é informado "
                               "pelo analista e ainda não foi informado."))
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
    # Limite vindo do enquadramento: o achado diz de onde (tabela conferida ou analista).
    origin = (facts.get(f"{question.required_fact}_source") or question.required_fact
              if question.required_fact else None)
    compare = compare_minimum if question.kind == "minimum_value" else compare_maximum
    # Com vários limites possíveis, conclui só o que vale para TODOS: atende o mais
    # exigente ⇒ atende; não atende nem o mais brando ⇒ não atende; o resto fica aberto.
    strict, loose = ((limits[0], limits[-1]) if question.kind == "maximum_value"
                     else (limits[-1], limits[0]))
    if compare(value, uncertainty, strict) == "PASS":
        verdict, required = "PASS", strict
    elif compare(value, uncertainty, loose) == "FAIL":
        verdict, required = "FAIL", loose
    elif len(limits) > 1:
        verdict, required = "LIMIT_OPEN", strict
    else:
        verdict, required = "REVIEW_REQUIRED", strict
    measured = MeasuredResult(
        value=value, unit=question.unit or worst.unit or "", required=required,
        required_candidates=limits if len(limits) > 1 else (),
        required_source=origin,
        uncertainty_abs=uncertainty, algorithm=worst.algorithm,
        algorithm_version=worst.algorithm_version, quality_gate=worst.quality_gate,
        # §27: medida do CAD aponta o desenho exato de onde saiu a geometria.
        geometry_snapshot_hash=(worst.source_hash
                                if worst.source_type is EvidenceSourceType.CAD else None))
    if verdict == "LIMIT_OPEN":
        shown = " ou ".join(f"{v:g}" for v in limits)
        return _finding(
            check, compliance=ComplianceStatus.UNDETERMINED,
            evidence=EvidenceStatus.PARTIAL, review=_review_for(check, forced=True),
            kind=FindingKind.NOT_VERIFIABLE, reason_code="LIMIT_NOT_DETERMINED",
            evidence_ids=ids, sources=sources, measured=measured,
            explanation_extra=(f"O limite aplicável pode ser {shown} {measured.unit} e a "
                               "medida, com sua incerteza, atende a um e não ao outro; "
                               "é preciso definir qual limite vale."))
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


@dataclass(frozen=True)
class FloorScope:
    """Um pavimento analisado: suas evidências e seus fatos de qualidade.

    Checks de escopo ``FLOOR`` rodam uma vez por pavimento, só com o que foi extraído
    dele. Os fatos do pavimento se somam aos do processo e prevalecem sobre eles.
    """

    id: str
    label: str
    evidence: EvidenceSet
    facts: dict[str, Any] = field(default_factory=dict)


def _aggregate(statuses: list[ComplianceStatus]) -> ComplianceStatus:
    """Conclusão de um check de pavimento vista pelo processo, para as dependências."""
    if not statuses or any(s is ComplianceStatus.UNDETERMINED for s in statuses):
        return ComplianceStatus.UNDETERMINED
    if all(s is ComplianceStatus.NOT_APPLICABLE for s in statuses):
        return ComplianceStatus.NOT_APPLICABLE
    if any(s is ComplianceStatus.NON_COMPLIANT for s in statuses):
        return ComplianceStatus.NON_COMPLIANT
    return ComplianceStatus.COMPLIANT


def execute_plan(plan: VerificationPlan, catalog: CheckCatalog, evidence: EvidenceSet,
                 context_facts: dict[str, Any] | None = None,
                 floors: Sequence[FloorScope] = ()) -> tuple[Finding, ...]:
    """Executa o plano na ordem das dependências. Mesmo plano + mesmas evidências ⇒
    mesmos achados.

    Sem ``floors``, todo check responde sobre o conjunto do processo. Com ``floors``,
    cada check de escopo ``FLOOR`` produz um achado por pavimento.
    """
    facts = context_facts or {}
    by_id = {item.check_id: item for item in plan.items}
    concluded: dict[str, ComplianceStatus] = {}
    per_floor: dict[str, dict[str, ComplianceStatus]] = {f.id: {} for f in floors}
    findings: list[Finding] = []
    for check_id in plan.execution_order:
        check = catalog.get(check_id)
        item = by_id[check_id]
        if floors and check.scope == "FLOOR":
            statuses = []
            for floor in floors:
                done = {**concluded, **per_floor[floor.id]}
                finding = _run_item(check, item, done, floor.evidence,
                                    {**facts, **floor.facts})
                finding = finding.model_copy(update={"scope_id": floor.id,
                                                     "scope_label": floor.label})
                per_floor[floor.id][check_id] = finding.compliance_status
                statuses.append(finding.compliance_status)
                findings.append(finding)
            concluded[check_id] = _aggregate(statuses)
            continue
        finding = _run_item(check, item, concluded, evidence, facts)
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


def _run_item(check: CheckDefinition, item: PlanItem, concluded: dict[str, ComplianceStatus],
              evidence: EvidenceSet, facts: dict[str, Any]) -> Finding:
    gate = dependency_gate(check.depends_on, concluded)
    if item.applicability is Applicability.UNKNOWN:
        return _not_executed(
            check, compliance=ComplianceStatus.UNDETERMINED,
            kind=FindingKind.NOT_VERIFIABLE, reason_code="APPLICABILITY_UNKNOWN",
            reason=("Faltam dados do enquadramento para decidir se este item se aplica: "
                    + ", ".join(item.missing_facts)) if item.missing_facts else (
                    "Enquadramento insuficiente para decidir a aplicabilidade."),
            review=ReviewStatus.PENDING)
    if gate is not None:
        state, reason = gate
        return _not_executed(
            check,
            compliance=(ComplianceStatus.NOT_APPLICABLE if state == "NOT_APPLICABLE"
                        else ComplianceStatus.UNDETERMINED),
            kind=(FindingKind.NO_PENDING_ISSUE if state == "NOT_APPLICABLE"
                  else FindingKind.NOT_VERIFIABLE),
            reason_code=f"DEPENDENCY_{state}",
            reason=f"Não executado porque {reason}.",
            review=(ReviewStatus.NOT_REQUIRED if state == "NOT_APPLICABLE"
                    else ReviewStatus.PENDING))
    if check.manual:
        return _not_executed(
            check, compliance=ComplianceStatus.UNDETERMINED,
            kind=FindingKind.ANALYST_REVIEW, reason_code="MANUAL_CONFIRMATION",
            reason="Item de confirmação humana: o motor não conclui sozinho.",
            review=ReviewStatus.PENDING)
    return execute_check(check, evidence, facts)
