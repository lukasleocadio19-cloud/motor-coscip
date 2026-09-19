"""Medidas no modelo de cálculo. Nunca sobre a cena visual simplificada."""

from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry.base import BaseGeometry


@dataclass(frozen=True)
class Measurement:
    value: float
    unit: str
    method: str
    uncertainty_abs: float


def length(geom: BaseGeometry, uncertainty_abs: float) -> Measurement:
    if geom.is_empty:
        raise ValueError("geometria vazia")
    return Measurement(geom.length, "m", "shapely-length/1.0", uncertainty_abs)


def area(geom: BaseGeometry, uncertainty_abs: float) -> Measurement:
    if not geom.is_valid:
        raise ValueError("polígono inválido: corrigir contorno antes de medir área")
    return Measurement(geom.area, "m2", "shapely-area/1.0", uncertainty_abs)
