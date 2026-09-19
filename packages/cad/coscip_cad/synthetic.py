"""DXFs sintéticos para testes e demonstração. Nenhum dado real de projeto."""

from __future__ import annotations

from pathlib import Path

import ezdxf


def make_simple_floor(path: Path, *, insunits: int = 6, scale: float = 1.0) -> Path:
    """Sala 10×6 m com porta (bloco) inserida duas vezes — uma espelhada — e um extintor.

    ``scale`` permite gerar a mesma planta em mm (insunits=4, scale=1000).
    """
    doc = ezdxf.new("R2018", setup=True)
    doc.header["$INSUNITS"] = insunits
    for name in ("PAREDES", "PORTAS", "INC_EXT", "TEXTOS"):
        doc.layers.add(name)

    door = doc.blocks.new("PORTA_90")
    door.add_line((0, 0), (0.9 * scale, 0), dxfattribs={"layer": "PORTAS"})
    door.add_arc((0, 0), 0.9 * scale, 0, 90, dxfattribs={"layer": "PORTAS"})

    ext = doc.blocks.new("EXT_ABC")
    ext.add_circle((0, 0), 0.15 * scale, dxfattribs={"layer": "INC_EXT"})
    ext.add_attdef("TIPO", (0.2 * scale, 0), dxfattribs={"height": 0.1 * scale})

    msp = doc.modelspace()
    w, h = 10 * scale, 6 * scale
    msp.add_lwpolyline([(0, 0), (w, 0), (w, h), (0, h)], close=True,
                       dxfattribs={"layer": "PAREDES"})
    msp.add_blockref("PORTA_90", (2 * scale, 0), dxfattribs={"layer": "PORTAS"})
    msp.add_blockref("PORTA_90", (8 * scale, 0),
                     dxfattribs={"layer": "PORTAS", "xscale": -1})  # espelhada
    ref = msp.add_blockref("EXT_ABC", (5 * scale, 3 * scale), dxfattribs={"layer": "INC_EXT"})
    ref.add_auto_attribs({"TIPO": "ABC 6kg"})
    msp.add_text("SALA 01", dxfattribs={"layer": "TEXTOS", "height": 0.3 * scale}).set_placement(
        (4 * scale, 4 * scale))
    msp.add_line((0, 3 * scale), (w, 3 * scale), dxfattribs={"layer": "PAREDES"})
    doc.saveas(path)
    return path
