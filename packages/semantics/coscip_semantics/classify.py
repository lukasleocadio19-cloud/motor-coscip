from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Scope = Literal["PROJECT", "ORGANIZATION", "GLOBAL"]


@dataclass(frozen=True)
class SemanticMapping:
    scope: Scope
    signature: str  # ex.: "layer:INC_EXT" ou "block:EXT_ABC"
    element_class: str
    confirmed: bool
    version: int = 1


@dataclass(frozen=True)
class Candidate:
    element_class: str
    stage: str
    evidence: str
    # Pontuação heurística de ordenação — NÃO é probabilidade calibrada.
    rank_score: float


LAYER_HINTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"EXT(INT|_)|EXTINTOR", re.I), "EXTINGUISHER"),
    (re.compile(r"PORTA|DOOR", re.I), "DOOR"),
    (re.compile(r"PAREDE|WALL", re.I), "WALL"),
    (re.compile(r"SA[IÍ]DA|EXIT", re.I), "EXIT"),
    (re.compile(r"AMBIENTE|ROOM|SPACE|SALA", re.I), "SPACE"),
    (re.compile(r"ESCADA|STAIR", re.I), "STAIR"),
)


def classify(
    *,
    layer: str,
    block_name: str | None,
    attributes: dict[str, str],
    mappings: list[SemanticMapping],
) -> list[Candidate]:
    """Devolve TODOS os candidatos relevantes; conflito vai para revisão humana."""
    out: list[Candidate] = []
    if cls := attributes.get("CLASSE") or attributes.get("CLASS"):
        out.append(Candidate(cls.upper(), "explicit_attribute", f"atributo={cls}", 1.0))

    sigs = {f"layer:{layer}", *( [f"block:{block_name}"] if block_name else [])}
    # Projeto sobrepõe organização, que sobrepõe global.
    for scope, weight in (("PROJECT", 0.9), ("ORGANIZATION", 0.8), ("GLOBAL", 0.7)):
        for m in mappings:
            if m.scope == scope and m.confirmed and m.signature in sigs:
                out.append(Candidate(m.element_class, f"mapping_{scope.lower()}",
                                     m.signature, weight))

    for name in filter(None, (layer, block_name)):
        for pattern, cls in LAYER_HINTS:
            if pattern.search(name):
                out.append(Candidate(cls, "name_hint", name, 0.4))

    out.sort(key=lambda c: -c.rank_score)
    return out


def has_conflict(candidates: list[Candidate]) -> bool:
    return len({c.element_class for c in candidates}) > 1
