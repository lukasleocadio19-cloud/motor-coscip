"""GEO-06: translação/rotação não alteram medidas; unidade correta preserva resultados."""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from shapely.geometry import LineString, Polygon

from coscip_geometry import Transform, area, compare_minimum, length, to_meters
from coscip_geometry.units import UnitError
from coscip_topology import Connection, FloorGraph
from coscip_topology.graph import UnconfirmedTopologyError

ROOM = np.array([(0, 0), (10, 0), (10, 6), (0, 6)], dtype=float)
coord = st.floats(-1e6, 1e6, allow_nan=False)
angle = st.floats(0, 2 * math.pi, allow_nan=False)


def _apply(t: Transform, pts: np.ndarray) -> list[tuple[float, float]]:
    return [(x, y) for x, y, _ in t.apply(pts)]


@settings(max_examples=200)
@given(dx=coord, dy=coord, theta=angle)
def test_area_and_length_invariant(dx, dy, theta):
    t = Transform.translation(dx, dy) @ Transform.rotation_z(theta)
    moved = _apply(t, ROOM)
    assert area(Polygon(moved), 0.0).value == pytest.approx(60.0, abs=1e-6)
    assert length(LineString(moved[:2]), 0.0).value == pytest.approx(10.0, abs=1e-6)


def test_inverse_roundtrip_with_mirror_and_nonuniform_scale():
    t = Transform.translation(5, -3) @ Transform.scale(-2, 3)
    assert t.is_mirrored and not t.is_uniform_scale
    back = t.inverse().apply(t.apply(ROOM))[:, :2]
    np.testing.assert_allclose(back, ROOM, atol=1e-12)


def test_units_mm_to_m():
    assert to_meters(900, 4) == pytest.approx(0.9)
    with pytest.raises(UnitError):
        to_meters(1, 0)


def test_invalid_polygon_refused():
    bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
    with pytest.raises(ValueError):
        area(bowtie, 0.0)


@pytest.mark.parametrize(
    ("m", "u", "req", "exp"),
    [(0.87, 0.002, "0.90", "FAIL"), (0.9, 0.002, "0.90", "REVIEW_REQUIRED"),
     (0.905, 0.002, "0.90", "PASS"), (0.9, 0.0, "0.90", "PASS")],
)
def test_compare_minimum(m, u, req, exp):
    from decimal import Decimal

    assert compare_minimum(m, u, Decimal(req)) == exp


def test_route_requires_confirmed_topology():
    g = FloorGraph("floor-1")
    g.add(Connection("sala", "corredor", "DOOR", 4.0, True, True))
    g.add(Connection("corredor", "saida", "OPENING", 6.0, True, True))
    route = g.shortest_route("sala", "saida")
    assert route and route.cost_m == 10.0
    g.add(Connection("sala", "saida", "DOOR", 1.0, True, confirmed=False))
    with pytest.raises(UnconfirmedTopologyError):
        g.shortest_route("sala", "saida")


def test_route_never_crosses_non_traversable():
    g = FloorGraph("floor-1")
    g.add(Connection("sala", "saida", "WALL_GAP", 1.0, traversable=False, confirmed=True))
    assert g.shortest_route("sala", "saida") is None
