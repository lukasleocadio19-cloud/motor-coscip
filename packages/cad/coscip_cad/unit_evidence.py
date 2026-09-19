"""Sugestão de unidade a partir das cotas (apoio ao CAD-02).

Descoberto no corpus de 19/09/2026: nos 5 projetos, $INSUNITS estava errado ou ausente
(mm/polegadas declarados em desenhos feitos em metros). As cotas trazem um indício melhor:

1. razão = valor exibido na cota / distância geométrica entre os pontos cotados;
2. ordem de grandeza dos valores exibidos (portas ~0,8 m, 80 cm ou 800 mm).

O resultado é SUGESTÃO para o analista confirmar com uma medida conhecida.
Não é probabilidade calibrada e nunca substitui a confirmação.
"""

from __future__ import annotations

import math
import re
import statistics
from collections import Counter
from dataclasses import dataclass, field

from ezdxf.document import Drawing

# Aceita ".91" e "0,85": cotas sem zero inicial são comuns em projetos brasileiros.
NUM = re.compile(r"(\d*[.,]\d+|\d+)")

# Unidade dos números exibidos, pela mediana dos valores das cotas de planta.
_DISPLAY_BANDS = ((50.0, "m", 1.0), (5_000.0, "cm", 0.01), (math.inf, "mm", 0.001))
_INSUNITS_FOR = {"m": 6, "cm": 5, "mm": 4}


@dataclass
class UnitSuggestion:
    unit: str | None  # "m", "cm", "mm" ou None
    insunits: int | None
    meters_per_unit: float | None
    strength: str  # "forte", "fraco", "sem indício"
    dimensions_used: int
    ratio_mode: float | None
    displayed_median: float | None
    samples: list[float] = field(default_factory=list)
    note: str = ""

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def _shown(doc: Drawing, dim) -> float | None:  # noqa: ANN001
    txt = dim.dxf.get("text", "")
    if txt and txt not in ("<>", " "):
        m = NUM.search(txt.replace("<>", ""))
        return float(m.group(1).replace(",", ".")) if m else None
    name = dim.dxf.get("geometry")
    if not name or name not in doc.blocks:
        return None
    for e in doc.blocks[name]:
        if e.dxftype() in ("MTEXT", "TEXT"):
            s = e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text
            if m := NUM.search(s):
                return float(m.group(1).replace(",", "."))
    return None


def _geo(dim) -> float | None:  # noqa: ANN001
    p2, p3 = dim.dxf.get("defpoint2"), dim.dxf.get("defpoint3")
    t = dim.dimtype
    if p2 is None or p3 is None or t not in (0, 1):
        return None
    if t == 1:
        return math.hypot(p3.x - p2.x, p3.y - p2.y)
    a = math.radians(dim.dxf.get("angle", 0))
    return abs((p3.x - p2.x) * math.cos(a) + (p3.y - p2.y) * math.sin(a))


def suggest_unit(doc: Drawing, min_dims: int = 10) -> UnitSuggestion:
    pairs: list[tuple[float, float]] = []
    for dim in doc.modelspace().query("DIMENSION"):
        try:
            g, s = _geo(dim), _shown(doc, dim)
        except (AttributeError, ValueError, TypeError):
            continue
        if g and s and g > 1e-9:
            pairs.append((s, g))
    if not pairs:
        return UnitSuggestion(None, None, None, "sem indício", 0, None, None,
                              note="Sem cotas lineares legíveis no Model")

    ratios = Counter(round(s / g, 2) for s, g in pairs)
    ratio, ratio_n = ratios.most_common(1)[0]
    consistent = [s for s, g in pairs if round(s / g, 2) == ratio]
    displayed = statistics.median(consistent)
    disp_unit, disp_m = next((u, f) for lim, u, f in _DISPLAY_BANDS if displayed < lim)

    # Uma unidade do desenho vale `ratio` unidades exibidas.
    meters_per_unit = ratio * disp_m
    unit = next((u for u, f in (("m", 1.0), ("cm", 0.01), ("mm", 0.001))
                 if math.isclose(meters_per_unit, f, rel_tol=0.01)), None)
    agreement = ratio_n / len(pairs)
    strong = unit is not None and len(pairs) >= min_dims and agreement >= 0.8
    note = (f"{ratio_n} de {len(pairs)} cotas com razão {ratio}; números exibidos parecem "
            f"estar em {disp_unit} (mediana {displayed:g})")
    return UnitSuggestion(
        unit=unit,
        insunits=_INSUNITS_FOR.get(unit) if unit else None,
        meters_per_unit=meters_per_unit,
        strength="forte" if strong else "fraco",
        dimensions_used=len(pairs),
        ratio_mode=ratio,
        displayed_median=displayed,
        samples=sorted({round(s, 3) for s in consistent})[:8],
        note=note,
    )
