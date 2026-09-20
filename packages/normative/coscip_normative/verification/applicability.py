"""Aplicabilidade de um check ao enquadramento do processo (§18).

Três valores, como nas regras: um fato desconhecido não vira "não se aplica". Um check
cuja aplicabilidade é desconhecida entra no plano e termina inconclusivo, em revisão.
"""

from __future__ import annotations

from coscip_cbm import Applicability
from coscip_normative.verification.context import ProcessContext
from coscip_normative.verification.models import CheckDefinition
from coscip_rules import evaluate_condition


def check_applicability(check: CheckDefinition, context: ProcessContext) -> Applicability:
    return evaluate_condition(check.applies_when, context.evaluation_context())


def unknown_facts(check: CheckDefinition, context: ProcessContext) -> tuple[str, ...]:
    """Fatos que faltam para decidir a aplicabilidade — o que pedir ao analista."""
    known = context.all_facts()
    wanted = [p.fact for p in (*check.applies_when.all, *check.applies_when.any)]
    return tuple(dict.fromkeys(f for f in wanted if f not in known))
