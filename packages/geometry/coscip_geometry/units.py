"""Unidades do desenho → SI.

A unidade declarada no DXF ($INSUNITS) é apenas um indício. Unidade não confirmada
pelo analista bloqueia cálculo dependente (CAD-02).
"""

from __future__ import annotations


class UnitError(ValueError):
    pass


# Códigos $INSUNITS do DXF que fazem sentido em plantas de edificação.
INSUNITS_TO_METERS: dict[int, float] = {
    1: 0.0254,  # polegadas
    2: 0.3048,  # pés
    4: 0.001,  # milímetros
    5: 0.01,  # centímetros
    6: 1.0,  # metros
    14: 0.1,  # decímetros
}

INSUNITS_NAMES: dict[int, str] = {
    0: "sem unidade",
    1: "polegadas",
    2: "pés",
    4: "milímetros",
    5: "centímetros",
    6: "metros",
    14: "decímetros",
}


def to_meters(value: float, insunits: int) -> float:
    try:
        return value * INSUNITS_TO_METERS[insunits]
    except KeyError as exc:
        raise UnitError(f"Unidade $INSUNITS={insunits} não suportada ou indefinida") from exc
