"""Sugestão de unidade pelas cotas: $INSUNITS errado não engana a sugestão."""

from __future__ import annotations

import ezdxf

from coscip_cad import DxfReader
from coscip_cad.unit_evidence import suggest_unit


def _drawing(path, *, insunits: int, scale: float, n_dims: int = 12, dimlfac: float = 1.0):
    """Desenho feito em `scale` unidades por metro, com cotas exibindo o valor geométrico."""
    doc = ezdxf.new("R2018", setup=True)
    doc.header["$INSUNITS"] = insunits
    msp = doc.modelspace()
    for i in range(n_dims):
        length = (0.8 + 0.25 * i) * scale  # 0,80 m, 1,05 m, …
        y = i * 2 * scale
        msp.add_linear_dim(base=(0, y + 0.5 * scale), p1=(0, y), p2=(length, y),
                           override={"dimdec": 2, "dimlfac": dimlfac}).render()
    doc.saveas(path)
    return DxfReader().open(path)


def test_meters_detected_even_when_declared_mm(tmp_path):
    s = suggest_unit(_drawing(tmp_path / "m.dxf", insunits=4, scale=1.0))
    assert s.unit == "m" and s.insunits == 6 and s.strength == "forte"


def test_centimeters(tmp_path):
    s = suggest_unit(_drawing(tmp_path / "cm.dxf", insunits=1, scale=100.0))
    assert s.unit == "cm"


def test_meters_drawn_with_dimensions_shown_in_cm(tmp_path):
    # Caso real do corpus: desenho em metros, cotas exibidas em cm (DIMLFAC=100).
    s = suggest_unit(_drawing(tmp_path / "m_cm.dxf", insunits=4, scale=1.0, dimlfac=100))
    assert s.unit == "m" and s.ratio_mode == 100


def test_no_dimensions_no_suggestion(floor_dxf):
    s = suggest_unit(DxfReader().open(floor_dxf))
    assert s.unit is None and s.strength == "sem indício"


def test_few_dimensions_is_weak(tmp_path):
    s = suggest_unit(_drawing(tmp_path / "poucas.dxf", insunits=0, scale=1.0, n_dims=3))
    assert s.unit == "m" and s.strength == "fraco"


def test_declared_unit_still_warns(floor_dxf):
    r = DxfReader()
    inv = r.inventory(r.open(floor_dxf))
    assert any("só indício" in w for w in inv.warnings)


def test_number_parsing_accepts_leading_separator():
    from coscip_cad.unit_evidence import NUM

    def parse(s):
        return float(NUM.search(s).group(1).replace(",", "."))

    assert parse(".91") == 0.91
    assert parse("0,85m") == 0.85
    assert parse(".90 A 1.10m") == 0.90
    assert parse("90") == 90.0
    assert parse("2.30") == 2.30
