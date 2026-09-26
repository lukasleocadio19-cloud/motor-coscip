"""Plano de Verificação COSCIP — núcleo da arquitetura v2 (§2, §18).

A análise começa pelo enquadramento: "o que o COSCIP exige verificar neste processo?".
O compilador responde isso de forma determinística; o executor responde cada pergunta
com as evidências reunidas.
"""

from coscip_normative.verification.applicability import check_applicability, unknown_facts
from coscip_normative.verification.catalog import (
    CATALOG_SCHEMA,
    CatalogError,
    CheckCatalog,
    load_catalog,
    parse_check,
    verify_catalog,
)
from coscip_normative.verification.compiler import (
    PLAN_SCHEMA,
    PlanItem,
    VerificationPlan,
    compile_verification_plan,
)
from coscip_normative.verification.context import (
    CONTEXT_SCHEMA,
    ProcessContext,
    effective_requirement,
)
from coscip_normative.verification.dependencies import dependency_gate, execution_order
from coscip_normative.verification.executor import FloorScope, execute_check, execute_plan
from coscip_normative.verification.models import (
    CHECK_SCHEMA,
    CheckDefinition,
    CheckValidationError,
    Question,
    Wording,
)

__all__ = [
    "CATALOG_SCHEMA",
    "CHECK_SCHEMA",
    "CONTEXT_SCHEMA",
    "PLAN_SCHEMA",
    "CatalogError",
    "CheckCatalog",
    "CheckDefinition",
    "CheckValidationError",
    "FloorScope",
    "PlanItem",
    "ProcessContext",
    "Question",
    "VerificationPlan",
    "Wording",
    "check_applicability",
    "compile_verification_plan",
    "dependency_gate",
    "effective_requirement",
    "execute_check",
    "execute_plan",
    "execution_order",
    "load_catalog",
    "parse_check",
    "unknown_facts",
    "verify_catalog",
]
