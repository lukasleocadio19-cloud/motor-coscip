"""Compilador do Plano de Verificação — o núcleo da arquitetura v2 (§18).

Dado um enquadramento e um catálogo, produz de forma **determinística** a lista do que
precisa ser verificado neste processo, o que não se aplica, o que é manual e o que não
pôde sequer ser enquadrado. O plano é congelado por hash e entra no manifesto da análise.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from coscip_cbm import Applicability
from coscip_normative.verification.applicability import check_applicability, unknown_facts
from coscip_normative.verification.catalog import CheckCatalog
from coscip_normative.verification.context import ProcessContext
from coscip_normative.verification.dependencies import execution_order

PLAN_SCHEMA = "verification-plan/1.0"


@dataclass(frozen=True)
class PlanItem:
    check_id: str
    check_version: int
    system: str
    title: str
    applicability: Applicability
    manual: bool
    reason: str = ""
    missing_facts: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"check_id": self.check_id, "check_version": self.check_version,
                "system": self.system, "title": self.title,
                "applicability": str(self.applicability), "manual": self.manual,
                "reason": self.reason, "missing_facts": list(self.missing_facts)}


@dataclass(frozen=True)
class VerificationPlan:
    schema_version: str
    catalog_id: str
    catalog_version: int
    catalog_sha256: str
    context_sha256: str
    process_id: str
    items: tuple[PlanItem, ...]
    execution_order: tuple[str, ...]

    def _ids(self, *, applicability: Applicability, manual: bool | None = None) -> tuple[str, ...]:
        return tuple(i.check_id for i in self.items
                     if i.applicability is applicability
                     and (manual is None or i.manual is manual))

    @property
    def applicable_checks(self) -> tuple[str, ...]:
        return self._ids(applicability=Applicability.TRUE, manual=False)

    @property
    def manual_checks(self) -> tuple[str, ...]:
        return self._ids(applicability=Applicability.TRUE, manual=True)

    @property
    def not_applicable_checks(self) -> tuple[str, ...]:
        return self._ids(applicability=Applicability.FALSE)

    @property
    def undetermined_checks(self) -> tuple[str, ...]:
        """Enquadramento insuficiente para decidir se o check se aplica."""
        return self._ids(applicability=Applicability.UNKNOWN)

    @property
    def plan_sha256(self) -> str:
        canonical = json.dumps(self.as_dict(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "catalog_id": self.catalog_id,
                "catalog_version": self.catalog_version, "catalog_sha256": self.catalog_sha256,
                "context_sha256": self.context_sha256, "process_id": self.process_id,
                "items": [i.as_dict() for i in self.items],
                "execution_order": list(self.execution_order)}


def compile_verification_plan(catalog: CheckCatalog,
                              context: ProcessContext) -> VerificationPlan:
    """Mesmo catálogo + mesmo contexto ⇒ mesmo plano, incluindo a ordem de execução."""
    items = []
    for check in sorted(catalog.checks, key=lambda c: c.id):
        applies = check_applicability(check, context)
        missing = unknown_facts(check, context) if applies is Applicability.UNKNOWN else ()
        reason = ""
        if applies is Applicability.FALSE:
            reason = "enquadramento do processo não exige esta verificação"
        elif applies is Applicability.UNKNOWN:
            reason = "faltam dados do enquadramento para decidir a aplicabilidade"
        elif check.manual:
            reason = "verificação de confirmação humana"
        items.append(PlanItem(check_id=check.id, check_version=check.version,
                              system=check.system, title=check.title, applicability=applies,
                              manual=check.manual, reason=reason, missing_facts=missing))
    # Executável e inconclusivo entram na execução: nada é silenciosamente descartado.
    to_run = [i.check_id for i in items if i.applicability is not Applicability.FALSE]
    return VerificationPlan(
        schema_version=PLAN_SCHEMA, catalog_id=catalog.id, catalog_version=catalog.version,
        catalog_sha256=catalog.content_sha256, context_sha256=context.content_sha256,
        process_id=context.process_id, items=tuple(items),
        execution_order=execution_order(catalog, to_run))
