"""Dicionário de símbolos (symbols/1.0): classes, padrões e atributos, versionado por hash."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SCHEMA = "symbols/1.0"


class DictionaryError(ValueError):
    pass


def _rx(patterns: list[str] | None) -> tuple[re.Pattern[str], ...]:
    try:
        return tuple(re.compile(p, re.I) for p in (patterns or []))
    except re.error as exc:
        raise DictionaryError(f"padrão inválido: {exc}") from exc


@dataclass(frozen=True)
class SymbolClass:
    id: str
    label: str
    system: str
    block: tuple[re.Pattern[str], ...] = ()
    layer: tuple[re.Pattern[str], ...] = ()
    text: tuple[re.Pattern[str], ...] = ()
    exclude: tuple[re.Pattern[str], ...] = ()
    sign_codes: tuple[str, ...] = ()

    def excluded(self, name: str) -> bool:
        return any(p.search(name) for p in self.exclude)


@dataclass
class SymbolDictionary:
    id: str
    version: int
    sha256: str
    classes: dict[str, SymbolClass]
    agent: dict[str, tuple[re.Pattern[str], ...]]
    state: dict[str, tuple[re.Pattern[str], ...]]
    capacity: re.Pattern[str]
    rating: re.Pattern[str]
    attribute_radius_m: float
    legend_titles: tuple[re.Pattern[str], ...]
    obstacle_layers: tuple[re.Pattern[str], ...]
    non_obstacle_layers: tuple[re.Pattern[str], ...]
    special_rooms: tuple[re.Pattern[str], ...]
    region_titles: tuple[re.Pattern[str], ...]
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    def is_obstacle_layer(self, layer: str) -> bool:
        return (any(p.search(layer) for p in self.obstacle_layers)
                and not any(p.search(layer) for p in self.non_obstacle_layers))


def parse_dictionary(data: dict[str, Any]) -> SymbolDictionary:
    if data.get("schema_version") != SCHEMA:
        raise DictionaryError(f"esquema esperado {SCHEMA}")
    classes = {}
    for cid, spec in (data.get("classes") or {}).items():
        classes[cid] = SymbolClass(
            id=cid, label=spec.get("label", cid), system=spec.get("system", ""),
            block=_rx(spec.get("block")), layer=_rx(spec.get("layer")),
            text=_rx(spec.get("text")), exclude=_rx(spec.get("exclude")),
            sign_codes=tuple(spec.get("sign_codes") or ()),
        )
    if not classes:
        raise DictionaryError("dicionário sem classes")
    attrs = data.get("attributes") or {}
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return SymbolDictionary(
        id=str(data.get("id", "SIMBOLOS")), version=int(data.get("version", 1)),
        sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        classes=classes,
        agent={k: _rx(v) for k, v in (attrs.get("agent") or {}).items()},
        state={k: _rx(v) for k, v in (attrs.get("state") or {}).items()},
        capacity=re.compile(attrs.get("capacity", r"(\d+)\s*(KG|L)\b"), re.I),
        rating=re.compile(attrs.get("rating", r"(\d+-?A)?\s*:?\s*(\d+-?B)\s*:?\s*C"), re.I),
        attribute_radius_m=float(attrs.get("attribute_radius_m", 1.5)),
        legend_titles=_rx(data.get("legend_titles")),
        obstacle_layers=_rx(data.get("obstacle_layers")),
        non_obstacle_layers=_rx(data.get("non_obstacle_layers")),
        special_rooms=_rx(data.get("special_rooms")),
        region_titles=_rx(data.get("region_titles")),
        raw=data,
    )


def load_dictionary(path: str | Path) -> SymbolDictionary:
    with open(path, encoding="utf-8") as fh:
        return parse_dictionary(yaml.safe_load(fh))
