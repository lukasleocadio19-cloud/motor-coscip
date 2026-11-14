"""Gera restaurante-400m2-completo.dxf: planta baixa (do motor) + cortes A-A/B-B + 4 fachadas,
em metros, escala 1:1, camadas separadas. As vistas reaproveitam as funcoes de build_pdf.py."""
import sys
from pathlib import Path

import ezdxf

HERE = Path(__file__).parent
SRC = str(Path(__file__).resolve().parents[1] / "saidas" / "restaurante-400m2.dxf")
DST = str(Path(__file__).resolve().parents[1] / "saidas" / "restaurante-400m2-completo.dxf")

src_code = (HERE / "build_pdf.py").read_text(encoding="utf-8")
seg = src_code[src_code.index("def corte_aa"):src_code.index("def prancha2")]

PD, LAJE, PLAT, DOOR, WB, WT = 3.60, 3.80, 4.40, 2.10, 0.90, 2.10
DUCT, CAP, ABRI, ABRI_IN = 5.40, 5.62, 2.40, 2.20
BLACK, GRAY, LGRAY = (0, 0, 0), (0.45, 0.45, 0.45), (0.9, 0.9, 0.9)
RED, GREEN, ORANGE = (0.85, 0.1, 0.1), (0.0, 0.6, 0.25), (0.95, 0.6, 0.0)
BLUE, MAG = (0.78, 0.88, 0.96), (0.75, 0.0, 0.5)

LAYERS = {  # nome: (cor ACI)
    "VISTA_CONTORNO": 7, "VISTA_CORTE": 7, "VISTA_AUX": 8, "VISTA_INCENDIO": 1,
    "VISTA_SINAL": 3, "VISTA_ILUM": 30, "VISTA_VIDRO": 5, "VISTA_TEXTO": 7, "VISTA_COTA": 2,
    "CORTES": 6,
}


def tlen(t, size, font="helv"):  # largura aproximada em mm de papel (Helvetica)
    return len(t) * size * 0.5 / 72 * 25.4


MM = 72 / 25.4


def layer_of(color):
    if color == RED:
        return "VISTA_INCENDIO"
    if color == GREEN:
        return "VISTA_SINAL"
    if color == ORANGE:
        return "VISTA_ILUM"
    if color == GRAY:
        return "VISTA_AUX"
    return "VISTA_CONTORNO"


def lw(w):
    return 50 if w >= 0.8 else 30 if w >= 0.5 else 13


# V (classe do PDF) e reescrita aqui com as mesmas chamadas, saindo em DXF (metros)
class VC:
    TXT = 0.0441  # altura em m por pt, para texto a 1:125

    def __init__(self, msp, ox, gy, k=8.0):
        self.msp, self.ox, self.gy, self.k = msp, ox, gy, k

    def X(self, x):
        return self.ox + x

    def Y(self, h):
        return self.gy + h

    def line(self, x0, h0, x1, h1, w=0.5, color=BLACK, dash=None):
        self.msp.add_line((self.X(x0), self.Y(h0)), (self.X(x1), self.Y(h1)), dxfattribs={
            "layer": layer_of(color), "lineweight": lw(w), **({"linetype": "DASHED"} if dash else {})})

    def rect(self, x0, h0, x1, h1, fill=None, w=0.5, color=BLACK):
        layer = "VISTA_VIDRO" if fill == BLUE else layer_of(color)
        self.msp.add_lwpolyline(
            [(self.X(x0), self.Y(h0)), (self.X(x1), self.Y(h0)), (self.X(x1), self.Y(h1)), (self.X(x0), self.Y(h1))],
            close=True, dxfattribs={"layer": layer, "lineweight": lw(w)})

    def poly(self, pts, fill=None, w=0.5, color=BLACK):
        self.msp.add_lwpolyline([(self.X(x), self.Y(h)) for x, h in pts], close=True,
                                dxfattribs={"layer": layer_of(color), "lineweight": lw(w)})

    def hatch(self, x0, h0, x1, h1, gap=0.16, fill=LGRAY):
        self.msp.add_lwpolyline(
            [(self.X(x0), self.Y(h0)), (self.X(x1), self.Y(h0)), (self.X(x1), self.Y(h1)), (self.X(x0), self.Y(h1))],
            close=True, dxfattribs={"layer": "VISTA_CORTE", "lineweight": 30})
        h = self.msp.add_hatch(dxfattribs={"layer": "VISTA_CORTE"})
        h.set_pattern_fill("ANSI31", scale=max(0.02, gap / 3.175))
        h.paths.add_polyline_path(
            [(self.X(x0), self.Y(h0)), (self.X(x1), self.Y(h0)), (self.X(x1), self.Y(h1)), (self.X(x0), self.Y(h1))],
            is_closed=True)

    def t(self, x, h, txt, size=5.5, font="helv", color=BLACK, center=False, rot=0):
        if not txt:
            return
        e = self.msp.add_text(txt, height=size * self.TXT, rotation=rot,
                              dxfattribs={"layer": layer_of(color) if color != BLACK else "VISTA_TEXTO"})
        e.set_placement((self.X(x), self.Y(h)), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER if center
                        else ezdxf.enums.TextEntityAlignment.LEFT)

    def dim_h(self, x0, x1, h, txt, size=5.5):
        self.msp.add_line((self.X(x0), self.Y(h)), (self.X(x1), self.Y(h)), dxfattribs={"layer": "VISTA_COTA"})
        for x in (x0, x1):
            self.msp.add_line((self.X(x), self.Y(h - 0.12)), (self.X(x), self.Y(h + 0.12)), dxfattribs={"layer": "VISTA_COTA"})
            self.msp.add_line((self.X(x - 0.08), self.Y(h - 0.08)), (self.X(x + 0.08), self.Y(h + 0.08)),
                              dxfattribs={"layer": "VISTA_COTA", "lineweight": 30})
        self.t((x0 + x1) / 2, h + 0.18, txt, size, center=True)

    def dim_v(self, x, h0, h1, txt, size=5.5):
        self.msp.add_line((self.X(x), self.Y(h0)), (self.X(x), self.Y(h1)), dxfattribs={"layer": "VISTA_COTA"})
        for h in (h0, h1):
            self.msp.add_line((self.X(x - 0.12), self.Y(h)), (self.X(x + 0.12), self.Y(h)), dxfattribs={"layer": "VISTA_COTA"})
            self.msp.add_line((self.X(x - 0.08), self.Y(h - 0.08)), (self.X(x + 0.08), self.Y(h + 0.08)),
                              dxfattribs={"layer": "VISTA_COTA", "lineweight": 30})
        self.t(x - 0.2, (h0 + h1) / 2, txt, size, rot=90)

    def ground(self, x0, x1):
        self.line(x0, 0, x1, 0, w=1.1)
        x = x0
        while x < x1:
            self.line(x, 0, x - 0.25, -0.25, w=0.15, color=GRAY)
            x += 0.4

    def wall(self, x0, x1, top, openings=()):
        cur = 0.0
        for a, b in sorted(openings):
            if a > cur:
                self.hatch(x0, cur, x1, a)
            cur = b
        if top > cur:
            self.hatch(x0, cur, x1, top)

    def ie(self, x, h=2.5):
        self.rect(x - 0.15, h, x + 0.15, h + 0.13, fill=(1, 0.85, 0.5), w=0.4, color=ORANGE)
        self.line(x, h + 0.13, x, PD, w=0.3, color=ORANGE)

    def ext(self, x, h0=0.95, label=""):
        self.rect(x - 0.15, h0, x + 0.15, h0 + 0.55, fill=(1, 0.8, 0.8), w=0.6, color=RED)
        self.rect(x - 0.07, h0 + 0.55, x + 0.07, h0 + 0.68, fill=RED, w=0.3, color=RED)
        self.rect(x - 0.2, h0 + 0.85, x + 0.2, h0 + 1.25, fill=(1, 0.9, 0.9), w=0.5, color=RED)
        if label:
            self.t(x, h0 + 1.38, label, 4.5, center=True, color=RED)

    def sign(self, x, h, txt, color=GREEN, w=0.5):
        self.rect(x - w / 2, h, x + w / 2, h + 0.4, fill=(0.8, 0.95, 0.85), w=0.5, color=color)
        self.t(x, h + 0.14, txt, 3.8, center=True, color=color)


ns = dict(V=VC, tlen=tlen, MM=MM, PD=PD, LAJE=LAJE, PLAT=PLAT, DOOR=DOOR, WB=WB, WT=WT, DUCT=DUCT, CAP=CAP,
          ABRI=ABRI, ABRI_IN=ABRI_IN, BLACK=BLACK, GRAY=GRAY, LGRAY=LGRAY, RED=RED, GREEN=GREEN,
          ORANGE=ORANGE, BLUE=BLUE, MAG=MAG)
exec(seg, ns)  # noqa: S102 - codigo proprio, do build_pdf.py ao lado

doc = ezdxf.readfile(SRC)
for name, aci in LAYERS.items():
    if name not in doc.layers:
        doc.layers.add(name, color=aci)
msp = doc.modelspace()

# linhas de corte na planta (A-A em y = 7,60; B-B em x = 9,80)
for a, b in (((-1.2, 7.6), (26.0, 7.6)), ((9.8, -2.3), (9.8, 20.0))):
    msp.add_line(a, b, dxfattribs={"layer": "CORTES", "linetype": "DASHDOT", "lineweight": 30})

# vistas, ao lado da planta (a partir de x = 55 m)
LX, RX = 55 + 1.8, 98 + 1.8
ROW = (52.0, 34.0, 16.0)  # cota 0,00 de cada linha (y)
ns["corte_aa"](msp, LX, ROW[0])
ns["fach_sul"](msp, LX, ROW[1])
ns["fach_norte"](msp, LX, ROW[2])
ns["corte_bb"](msp, RX, ROW[0])
ns["fach_oeste"](msp, RX - 0.8, ROW[1])
ns["fach_leste"](msp, RX - 0.8, ROW[2])
msp.add_text("CORTES E FACHADAS - ESCALA 1:125 (desenhados em metros, 1:1) - ESQUEMATICO",
             height=0.5, dxfattribs={"layer": "VISTA_TEXTO"}).set_placement((55, 60))
msp.add_text("PROJETO FICTICIO - RASCUNHO SEM VALOR NORMATIVO - NAO PROTOCOLAR", height=0.4,
             dxfattribs={"layer": "VISTA_INCENDIO"}).set_placement((55, 59))

def ajustar_vista(d):
    """Deixa o arquivo abrindo no Model, com zoom na extensao do desenho (sem isso a vista
    ativa fica em (0,0) com 1000 m de altura e o desenho some)."""
    from ezdxf import bbox, zoom
    m = d.modelspace()
    ext = bbox.extents(m)
    d.header["$EXTMIN"] = (ext.extmin.x, ext.extmin.y, 0.0)
    d.header["$EXTMAX"] = (ext.extmax.x, ext.extmax.y, 0.0)
    d.header["$LIMMIN"] = (ext.extmin.x, ext.extmin.y)
    d.header["$LIMMAX"] = (ext.extmax.x, ext.extmax.y)
    d.header["$TILEMODE"] = 1  # aba Model ativa
    d.header["$INSUNITS"] = 6
    zoom.extents(m, factor=1.05)


ajustar_vista(doc)
doc.saveas(DST)
chk = ezdxf.readfile(DST)
vp = chk.viewports.get("*Active")[0]
print("salvo", DST, "entidades no Model", len(chk.modelspace()), "versao", chk.dxfversion)
print("extensao", chk.header["$EXTMIN"], chk.header["$EXTMAX"], "vista", tuple(vp.dxf.center), vp.dxf.height)

# a planta sozinha (gerada pelo motor) tambem ganha a vista correta; as entidades nao mudam
solo = ezdxf.readfile(SRC)
n0 = len(solo.modelspace())
ajustar_vista(solo)
solo.saveas(SRC)
print("planta do motor ajustada:", n0, "entidades")
