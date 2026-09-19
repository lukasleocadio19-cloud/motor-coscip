"""POC-04/POC-05: origem por arquivo/handle/instância e transformações."""

from __future__ import annotations

import math

from coscip_cad import DxfReader
from coscip_cbm import ExtractionQuality


def test_inventory(floor_dxf):
    r = DxfReader()
    inv = r.inventory(r.open(floor_dxf))
    assert inv.insunits == 6 and inv.units_declared
    assert {"PAREDES", "PORTAS", "INC_EXT"} <= set(inv.layers)
    assert inv.entity_counts["INSERT"] == 3
    assert inv.layout_entity_counts["Model"] == 6
    assert not any("XRef" in w or "proxy" in w for w in inv.warnings)


def test_missing_units_warns(floor_dxf_no_units):
    r = DxfReader()
    inv = r.inventory(r.open(floor_dxf_no_units))
    assert not inv.units_declared
    assert any("Unidade" in w for w in inv.warnings)


def test_two_inserts_of_same_block_have_distinct_identity(floor_dxf):
    r = DxfReader()
    ents = list(r.entities(r.open(floor_dxf)))
    door_lines = [e for e in ents if e.block_name == "PORTA_90" and e.entity_type == "LINE"]
    assert len(door_lines) == 2
    # Mesmo handle de definição no bloco, caminhos de instância diferentes.
    assert door_lines[0].handle == door_lines[1].handle
    assert door_lines[0].instance_path != door_lines[1].instance_path


def test_block_transform_applied_including_mirror(floor_dxf):
    r = DxfReader()
    ents = list(r.entities(r.open(floor_dxf)))
    lines = sorted(
        (e for e in ents if e.block_name == "PORTA_90" and e.entity_type == "LINE"),
        key=lambda e: e.points[0][0],
    )
    (a0, a1), (b0, b1) = lines[0].points, lines[1].points
    assert a0 == (2.0, 0.0) and math.isclose(a1[0], 2.9)
    assert b0 == (8.0, 0.0) and math.isclose(b1[0], 7.1)  # espelhada
    for ln in lines:
        assert math.isclose(math.dist(*ln.points), 0.9)


def test_attributes_extracted(floor_dxf):
    r = DxfReader()
    attribs = [e for e in r.entities(r.open(floor_dxf)) if e.entity_type == "ATTRIB"]
    assert [a.text for a in attribs] == ["ABC 6kg"]


def test_unit_scale_does_not_change_geometry_in_meters(floor_dxf, floor_dxf_mm):
    from coscip_geometry import to_meters

    r = DxfReader()
    m = [e for e in r.entities(r.open(floor_dxf)) if e.entity_type == "LWPOLYLINE"][0]
    mm = [e for e in r.entities(r.open(floor_dxf_mm)) if e.entity_type == "LWPOLYLINE"][0]
    assert [(to_meters(x, 4), to_meters(y, 4)) for x, y in mm.points] == list(m.points)


def test_unsupported_entities_are_inventoried(floor_dxf):
    r = DxfReader()
    q = {e.quality for e in r.entities(r.open(floor_dxf))}
    assert ExtractionQuality.SUPPORTED in q
