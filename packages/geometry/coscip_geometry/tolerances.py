"""Perfis de tolerância versionados (plano §8, GEO-01).

Os valores padrão (2 mm / 3 mm) vêm do documento-base como SUGESTÃO para experimento,
não como tolerâncias normativas aprovadas.

Tolerância de representação, tolerância de reparo e incerteza de medição são distintas.
Uma junção geométrica nunca autoriza tolerar descumprimento de requisito.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

Comparison = Literal["PASS", "FAIL", "REVIEW_REQUIRED"]


@dataclass(frozen=True)
class ToleranceProfile:
    id: str
    version: int
    coincidence_m: float = 0.002
    closure_m: float = 0.003
    angle_rad: float = 1e-4
    curve_chord_error_m: float = 0.001
    numeric_eps_m: float = 1e-9
    approved: bool = False  # perfil experimental até homologação


EXPERIMENTAL_PROFILE = ToleranceProfile(id="tolerances-experimental", version=1)


def compare_minimum(
    measured: float, uncertainty_abs: float, required: Decimal | float
) -> Comparison:
    """Compara uma medida com incerteza contra um mínimo exigido.

    - intervalo inteiro abaixo do mínimo → FAIL
    - intervalo inteiro no mínimo ou acima → PASS
    - intervalo atravessa o limite → REVIEW_REQUIRED
    """
    if uncertainty_abs < 0:
        raise ValueError("incerteza negativa")
    req = float(required)
    upper = measured + uncertainty_abs
    lower = measured - uncertainty_abs
    if upper < req:
        return "FAIL"
    if lower >= req:
        return "PASS"
    return "REVIEW_REQUIRED"


def compare_maximum(
    measured: float, uncertainty_abs: float, allowed: Decimal | float
) -> Comparison:
    lim = float(allowed)
    if measured - uncertainty_abs > lim:
        return "FAIL"
    if measured + uncertainty_abs <= lim:
        return "PASS"
    return "REVIEW_REQUIRED"
