"""Reserva de orçamento antes de cada chamada.

Padrão proposto ao habilitar IA: US$ 0,25/análise e US$ 5/mês — ajustáveis pelo
operador, nunca aumentados automaticamente. Chamada com consumo desconhecido
permanece reservada (pode já ter sido cobrada) e não é repetida às cegas.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal


class BudgetExceeded(RuntimeError):
    code = "AI_BUDGET_EXCEEDED"


@dataclass
class Reservation:
    request_id: str
    analysis_id: str
    max_usd: Decimal
    settled_usd: Decimal | None = None
    unknown: bool = False


@dataclass
class BudgetLedger:
    per_analysis_usd: Decimal = Decimal("0.25")
    per_month_usd: Decimal = Decimal("5.00")
    _items: list[Reservation] = field(default_factory=list)

    def _committed(self, analysis_id: str | None = None) -> Decimal:
        total = Decimal(0)
        for r in self._items:
            if analysis_id and r.analysis_id != analysis_id:
                continue
            total += r.max_usd if (r.settled_usd is None or r.unknown) else r.settled_usd
        return total

    def reserve(self, analysis_id: str, max_usd: Decimal) -> Reservation:
        if self._committed(analysis_id) + max_usd > self.per_analysis_usd:
            raise BudgetExceeded("teto por análise atingido; tarefas restantes vão à revisão")
        if self._committed() + max_usd > self.per_month_usd:
            raise BudgetExceeded("teto mensal atingido; tarefas restantes vão à revisão")
        r = Reservation(str(uuid.uuid4()), analysis_id, max_usd)
        self._items.append(r)
        return r

    def settle(self, request_id: str, actual_usd: Decimal) -> None:
        r = next(i for i in self._items if i.request_id == request_id)
        r.settled_usd, r.unknown = actual_usd, False

    def mark_unknown(self, request_id: str) -> None:
        next(i for i in self._items if i.request_id == request_id).unknown = True
