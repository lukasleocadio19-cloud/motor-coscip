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
