"""Geometria planar em referencial local (metros). Plano §8.

Shapely/GEOS resolve operações planares; a dimensão vertical é modelada à parte (2,5D).
"""

from coscip_geometry.measure import Measurement, area, length
from coscip_geometry.tolerances import ToleranceProfile, compare_minimum
from coscip_geometry.transform import Transform
from coscip_geometry.units import INSUNITS_TO_METERS, UnitError, to_meters

__all__ = [
    "INSUNITS_TO_METERS",
    "Measurement",
    "ToleranceProfile",
    "Transform",
    "UnitError",
    "area",
    "compare_minimum",
    "length",
    "to_meters",
]
