"""IA opcional e econômica (plano §15, contratos §11, AI-01..07).

Sem chave configurada e sem habilitação explícita, nada é enviado a provedores externos.
Disponibilidade da IA nunca bloqueia medições determinísticas.
"""

from coscip_ai.budget import BudgetExceeded, BudgetLedger, Reservation
from coscip_ai.providers import (
    AIDisabledError,
    DecisionClassifier,
    DisabledProvider,
    DocumentAssistant,
)

__all__ = [
    "AIDisabledError",
    "BudgetExceeded",
    "BudgetLedger",
    "DecisionClassifier",
    "DisabledProvider",
    "DocumentAssistant",
    "Reservation",
]
