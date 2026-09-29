"""Check: uma pergunta normativa verificável (arquitetura v2 §5, §6, §19, §20).

O catálogo é versionado, determinístico e separado da interface, da LLM e do Jev. Um
check declara o que responde a pergunta (``question``), de onde vem a base normativa e
o que concluir quando falta evidência — nunca o texto final da pendência.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from coscip_cbm import ComplianceStatus, Severity
from coscip_rules.dsl import Condition, Interpretation, Source

CHECK_SCHEMA = "checks/1.0"

# Taxonomia do §6: o catálogo pode declarar um tipo ainda sem execução determinística.
CHECK_TYPES = (
    "DOCUMENT_PRESENCE", "DOCUMENT_FIELD", "DOCUMENT_SCOPE", "CAD_PRESENCE", "CAD_COUNT",
    "CAD_DISTANCE", "CAD_COVERAGE", "CAD_DIMENSION", "CALCULATION", "NORMATIVE_TABLE",
    "CROSS_DOCUMENT", "CAD_DOCUMENT_CROSS", "CONSISTENCY", "MANUAL_CONFIRMATION",
    "QUALITY_GATE",
)

# Conjunto FECHADO de perguntas executáveis. Sem ``question`` o check é manual: entra no
# plano, vai para o analista e nunca é concluído pelo motor.
QUESTION_KINDS = (
    "presence", "required_fields", "minimum_count", "minimum_value", "maximum_value",
    "consistency", "composition",
)

CheckType = Literal[CHECK_TYPES]
CheckScope = Literal["PROCESS", "BUILDING", "FLOOR", "SYSTEM", "SUBJECT"]


class CheckValidationError(ValueError):
    pass


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Question(_Strict):
    """Como o motor responde ao check a partir das evidências reunidas."""

    kind: Literal[QUESTION_KINDS]
    # Objeto a que o check se refere; vazio = o processo inteiro.
    subject: str = ""
    field: str | None = None
    required_fields: tuple[str, ...] = ()
    # Categorias documentais/fontes que precisam informar o campo (§24 matriz de evidências).
    required_sources: tuple[str, ...] = ()
    accepted_evidence: tuple[str, ...] = ()
    required_value: float | None = None
    # Limite que o analista informa no enquadramento (ex.: Anexo C da NT 2-08, que está
    # como imagem). Usado no lugar de ``required_value``; sem o fato, nada conclui.
    required_fact: str | None = None
    unit: str | None = None
    # Porta de qualidade: sem ela o resultado numérico aparece, mas não vira conformidade.
    quality_gate: str | None = None
    # Portas adicionais, todas obrigatórias (ex.: pavimento confirmado, área toda alcançada).
    quality_gates: tuple[str, ...] = ()
    # composition: cada alternativa é uma lista de "vagas"; cada vaga, as classes de fogo
    # que UM objeto distinto precisa atender. Basta uma alternativa atendida.
    alternatives: tuple[tuple[tuple[str, ...], ...], ...] = ()
    # composition: valor da evidência (ex.: agente) → classes que ele atende.
    value_classes: dict[str, tuple[str, ...]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _composition(self) -> Question:
        if self.kind == "composition" and not (self.alternatives and self.value_classes
                                               and self.field):
            raise ValueError("composition exige field, alternatives e value_classes")
        return self

    @property
    def gates(self) -> tuple[str, ...]:
        first = (self.quality_gate,) if self.quality_gate else ()
        return tuple(dict.fromkeys((*first, *self.quality_gates)))


class HumanReview(_Strict):
    """Quando o achado nasce com ``review_status`` PENDING (§5)."""

    always: bool = False
    on_conflict: bool = True
    on_missing: bool = False
    confidence_below: float | None = Field(default=None, ge=0, le=1)


class ResultRules(_Strict):
    """O que concluir em cada situação. Ausência nunca vira COMPLIANT."""

    missing_required_field: ComplianceStatus = ComplianceStatus.UNDETERMINED
    conflicting_values: ComplianceStatus = ComplianceStatus.UNDETERMINED
    quality_gate_failed: ComplianceStatus = ComplianceStatus.UNDETERMINED
    not_satisfied: ComplianceStatus = ComplianceStatus.NON_COMPLIANT
    satisfied: Literal[ComplianceStatus.COMPLIANT] = ComplianceStatus.COMPLIANT

    @model_validator(mode="after")
    def _no_silent_pass(self) -> ResultRules:
        forbidden = ComplianceStatus.COMPLIANT
        for name in ("missing_required_field", "conflicting_values", "quality_gate_failed"):
            if getattr(self, name) is forbidden:
                raise ValueError(f"{name} não pode concluir COMPLIANT")
        return self


class Wording(_Strict):
    """Texto determinístico do achado (§57, §58). Não acrescenta nem retira requisito.

    Preferência inicial por template: o texto sai do check, não de um prompt.
    """

    title: str
    explanation: str = ""
    required_action: str = ""
    # Nome de campo → como o campo aparece para o analista ("manufacturer" → "fabricante").
    field_labels: dict[str, str] = Field(default_factory=dict)


class CheckDefinition(_Strict):
    schema_version: Literal[CHECK_SCHEMA]
    id: str
    version: int = Field(ge=1)
    title: str
    system: str
    type: CheckType
    scope: CheckScope = "PROCESS"
    severity: Severity = Severity.MAJOR
    publication_state: Literal["DRAFT", "TEST_ONLY", "HOMOLOGATED", "PUBLISHED", "DEPRECATED"]
    production_eligible: bool = False
    applies_when: Condition = Condition()
    depends_on: tuple[str, ...] = ()
    question: Question | None = None
    result_rules: ResultRules = ResultRules()
    human_review: HumanReview = HumanReview()
    normative_basis: tuple[Source, ...] = ()
    # Critério adotado além da literalidade (F4.1): conferido e mostrado à parte.
    interpretation: Interpretation | None = None
    # Achados com a mesma causa raiz são agrupados por esta chave (§32).
    group_key: str = ""
    wording: Wording

    @property
    def manual(self) -> bool:
        return self.question is None

    @property
    def content_hash(self) -> str:
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def grouping(self) -> str:
        return self.group_key or f"{self.system}/{self.id}"
