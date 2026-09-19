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


def make_fire_plan(path: Path, *, scale: float = 1.0) -> Path:
    """Pavimento 30×12 m com PPCI sintético, para a análise automática da planta.

    - paredes duplas (0,15 m) no layer PAREDE, porta externa de 1,2 m e porta interna de 1 m;
    - sala 01 (área declarada que confere) e depósito (área declarada que diverge);
    - casa de bombas com contorno fechado, porta de 1 m e extintor mais próximo a ~5,6 m;
    - 2 extintores (só um com placa E-5), 1 hidrante, 1 luminária em bloco dinâmico com um
      estado oculto (``invisible``), 1 acionador manual e uma legenda fora da planta.
    """
    k = scale
    doc = ezdxf.new("R2018", setup=True)
    doc.header["$INSUNITS"] = 6
    for name in ("PAREDE", "AMBIENTES", "INC_EXT", "SINALIZACAO", "TEXTOS", "INC_HID",
                 "LEGENDA", "ILUMINACAO"):
        doc.layers.add(name)

    def block(name: str, layer: str) -> None:
        b = doc.blocks.new(name)
        b.add_circle((0, 0), 0.2 * k, dxfattribs={"layer": layer})

    for name, layer in (("EXTINTOR_PQS_ABC", "INC_EXT"), ("HIDRANTE_SIMPLES", "INC_HID"),
                        ("LUMINARIA_EMERG_NOVA", "ILUMINACAO"),
                        ("LUMINARIA_EMERG_DEMOLIR", "ILUMINACAO"),
                        ("ACIONADOR_MANUAL", "INC_HID"), ("EXTINTOR_CO2_LEGENDA", "LEGENDA"),
                        ("HIDRANTE_LEGENDA", "LEGENDA"), ("ILUMINACAO_LEGENDA", "LEGENDA")):
        block(name, layer)
    dyn = doc.blocks.new_anonymous_block("U")
    dyn.add_blockref("LUMINARIA_EMERG_NOVA", (0, 0))
    hidden = dyn.add_blockref("LUMINARIA_EMERG_DEMOLIR", (0, 0))
    hidden.dxf.invisible = 1

    msp = doc.modelspace()

    def wall(x1: float, y1: float, x2: float, y2: float) -> None:
        msp.add_line((x1 * k, y1 * k), (x2 * k, y2 * k), dxfattribs={"layer": "PAREDE"})

    t = 0.15
    # externas (porta de 1,2 m em x = 14..15,2 na fachada inferior)
    for y in (0, t):
        wall(0, y, 14, y)
        wall(15.2, y, 30, y)
    wall(14, 0, 14, t)
    wall(15.2, 0, 15.2, t)
    for y in (12, 12 - t):
        wall(0, y, 30, y)
    for x in (0, t):
        wall(x, 0, x, 12)
    for x in (30, 30 - t):
        wall(x, 0, x, 12)
    # divisória x = 10 com porta y = 5..6
    for x in (10, 10 + t):
        wall(x, t, x, 5)
        wall(x, 6, x, 12 - t)
    wall(10, 5, 10 + t, 5)
    wall(10, 6, 10 + t, 6)
    # casa de bombas (x 25..30, y 8..12) com porta x = 26..27
    for y in (8, 8 + t):
        wall(25, y, 26, y)
        wall(27, y, 30 - t, y)
    for x in (25, 25 + t):
        wall(x, 8, x, 12 - t)

    def closed(pts: list[tuple[float, float]]) -> None:
        msp.add_lwpolyline([(x * k, y * k) for x, y in pts], close=True,
                           dxfattribs={"layer": "AMBIENTES"})

    closed([(t, t), (10, t), (10, 12 - t), (t, 12 - t)])  # sala 01: 9,85 × 11,7 = 115,245
    closed([(12, 1), (17, 1), (17, 8), (12, 8)])  # depósito: 35 m²
    closed([(25 + t, 8 + t), (30 - t, 8 + t), (30 - t, 12 - t), (25 + t, 12 - t)])

    def text(s: str, x: float, y: float, layer: str = "TEXTOS") -> None:
        msp.add_text(s, dxfattribs={"layer": layer, "height": 0.25 * k}).set_placement(
            (x * k, y * k))

    text("SALA 01", 4, 8)
    text("115,25 m²", 4, 7.6)
    text("DEPÓSITO", 14, 4)
    text("40,00 m²", 14, 3.6)
    text("CASA DE", 26.5, 10.5)
    text("BOMBAS", 26.5, 10.1)
    text("PLANTA BAIXA - TÉRREO", 12, -3)

    msp.add_blockref("EXTINTOR_PQS_ABC", (5 * k, 6 * k), dxfattribs={"layer": "INC_EXT"})
    text("E-5", 5.6, 6.4, "SINALIZACAO")
    msp.add_blockref("EXTINTOR_PQS_ABC", (20 * k, 6 * k), dxfattribs={"layer": "INC_EXT"})
    msp.add_blockref("HIDRANTE_SIMPLES", (12 * k, 11 * k), dxfattribs={"layer": "INC_HID"})
    msp.add_blockref("ACIONADOR_MANUAL", (15 * k, 1 * k), dxfattribs={"layer": "INC_HID"})
    msp.add_blockref(dyn.name, (15 * k, 10 * k), dxfattribs={"layer": "ILUMINACAO"})

    text("LEGENDA", 60, 22, "LEGENDA")
    for i, (name, desc) in enumerate((("EXTINTOR_CO2_LEGENDA", "EXTINTOR DE CO2 6 KG"),
                                      ("HIDRANTE_LEGENDA", "HIDRANTE SIMPLES"),
                                      ("ILUMINACAO_LEGENDA", "ILUMINAÇÃO DE EMERGÊNCIA"))):
        y = 20 - 2 * i
        msp.add_blockref(name, (60 * k, y * k), dxfattribs={"layer": "LEGENDA"})
        text(desc, 61.5, y, "LEGENDA")
    doc.saveas(path)
    return path
