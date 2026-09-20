"""Motor normativo (plano §10, contratos §7).

YAML/JSON é apenas representação: o compilador valida um conjunto FECHADO de operadores.
Não há eval, Python livre nem prompt como DSL.
"""

from coscip_rules.dsl import Condition, Predicate, RuleDefinition, RuleValidationError, load_rule
from coscip_rules.engine import EvaluationContext, evaluate, evaluate_condition

__all__ = [
    "Condition",
    "EvaluationContext",
    "Predicate",
    "RuleDefinition",
    "RuleValidationError",
    "evaluate",
    "evaluate_condition",
    "load_rule",
]
