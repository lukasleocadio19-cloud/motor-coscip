from enum import StrEnum


class EvaluationStatus(StrEnum):
    """Os cinco estados de avaliação (plano §10).

    Erro de software, timeout e estágio não executado são estados operacionais
    e nunca aparecem aqui. Item normativo não implementado é ``CoverageStatus.UNSUPPORTED``.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    MISSING_DATA = "MISSING_DATA"


UI_LABELS: dict[EvaluationStatus, str] = {
    EvaluationStatus.PASS: "Conforme",
    EvaluationStatus.FAIL: "Pendência",
    EvaluationStatus.REVIEW_REQUIRED: "Revisão humana",
    EvaluationStatus.NOT_APPLICABLE: "Não se aplica",
    EvaluationStatus.MISSING_DATA: "Dado ausente",
}


class CoverageStatus(StrEnum):
    IMPLEMENTED = "IMPLEMENTED"
    ASSISTED = "ASSISTED"
    UNSUPPORTED = "UNSUPPORTED"


class Applicability(StrEnum):
    """Lógica de três valores para aplicabilidade."""

    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class ExecutionState(StrEnum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    WAITING_INPUT = "WAITING_INPUT"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @property
    def is_terminal(self) -> bool:
        return self in {
            ExecutionState.SUCCEEDED,
            ExecutionState.PARTIAL,
            ExecutionState.FAILED,
            ExecutionState.CANCELLED,
        }


class ExtractionQuality(StrEnum):
    """Matriz de suporte (plano §8)."""

    SUPPORTED = "SUPPORTED"  # extração fiel + análise suportada
    INVENTORY_ONLY = "INVENTORY_ONLY"  # extração fiel, sem análise
    VISUAL_ONLY = "VISUAL_ONLY"  # visualização aproximada
    UNSUPPORTED = "UNSUPPORTED"


class Provenance(StrEnum):
    EXTRACTED = "EXTRACTED"
    CALCULATED = "CALCULATED"
    DECLARED = "DECLARED"
    CONFIRMED = "CONFIRMED"
    AI_SUGGESTED = "AI_SUGGESTED"


class SemanticStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    CONFLICT = "CONFLICT"
    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"
    REJECTED = "REJECTED"


class ElementClass(StrEnum):
    SPACE = "SPACE"
    WALL = "WALL"
    DOOR = "DOOR"
    OPENING = "OPENING"
    EXIT = "EXIT"
    EXTINGUISHER = "EXTINGUISHER"
    OBSTACLE = "OBSTACLE"
    STAIR = "STAIR"
    UNKNOWN = "UNKNOWN"


class ReviewDecision(StrEnum):
    CONFIRM = "CONFIRM"
    CONTEST = "CONTEST"
    REQUEST_DATA = "REQUEST_DATA"
    RESOLVED_BY_NEW_REVISION = "RESOLVED_BY_NEW_REVISION"


class ComplianceStatus(StrEnum):
    """Arquitetura v2 §3.A — o que a regra normativa conclui.

    Nunca fundir com ``EvidenceStatus`` nem com ``ReviewStatus``: "não há base para
    concluir" é diferente de "falta evidência" e de "o analista precisa olhar".
    """

    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNDETERMINED = "UNDETERMINED"


class EvidenceStatus(StrEnum):
    """Arquitetura v2 §3.B — qualidade da evidência reunida para o check."""

    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"


class ReviewStatus(StrEnum):
    """Arquitetura v2 §3.C — estado da revisão humana do achado."""

    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CONTESTED = "CONTESTED"
    DATA_REQUESTED = "DATA_REQUESTED"


class Severity(StrEnum):
    """Arquitetura v2 §33. Severidade ordena a tela; não é conformidade."""

    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFORMATIONAL = "INFORMATIONAL"


SEVERITY_ORDER: dict[Severity, int] = {
    Severity.CRITICAL: 0,
    Severity.MAJOR: 1,
    Severity.MINOR: 2,
    Severity.INFORMATIONAL: 3,
}


class FindingKind(StrEnum):
    """Arquitetura v2 §56 — os poucos tipos que o analista vê na tela."""

    NON_COMPLIANT = "NON_COMPLIANT"
    DOCUMENT_INCOMPLETE = "DOCUMENT_INCOMPLETE"
    DOCUMENT_MISSING = "DOCUMENT_MISSING"
    DATA_MISSING = "DATA_MISSING"
    DIVERGENCE = "DIVERGENCE"
    NOT_VERIFIABLE = "NOT_VERIFIABLE"
    ANALYST_REVIEW = "ANALYST_REVIEW"
    NO_PENDING_ISSUE = "NO_PENDING_ISSUE"


FINDING_KIND_LABELS: dict[FindingKind, str] = {
    FindingKind.NON_COMPLIANT: "Não atende",
    FindingKind.DOCUMENT_INCOMPLETE: "Documento incompleto",
    FindingKind.DOCUMENT_MISSING: "Documento ausente",
    FindingKind.DATA_MISSING: "Dado ausente",
    FindingKind.DIVERGENCE: "Divergência",
    FindingKind.NOT_VERIFIABLE: "Não foi possível verificar",
    FindingKind.ANALYST_REVIEW: "Revisão do analista",
    FindingKind.NO_PENDING_ISSUE: "Sem pendência",
}


class EvidenceSourceType(StrEnum):
    """Arquitetura v2 §7 — de onde veio o fato."""

    CAD = "CAD"
    DOCUMENT = "DOCUMENT"
    CALCULATION = "CALCULATION"
    NORMATIVE_TABLE = "NORMATIVE_TABLE"
    HUMAN = "HUMAN"


class ConsensusStatus(StrEnum):
    """Arquitetura v2 §55 — o que várias fontes dizem sobre o mesmo campo."""

    SUPPORTED = "SUPPORTED"
    CONFLICTING = "CONFLICTING"
    SINGLE_SOURCE = "SINGLE_SOURCE"
    MISSING_REQUIRED_SOURCE = "MISSING_REQUIRED_SOURCE"
