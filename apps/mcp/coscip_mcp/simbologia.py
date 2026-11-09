"""Catálogo da simbologia do COSCIP para desenhar plantas pelo MCP.

Fontes (textos em ``normative/fontes``):

- **NT 1-03, Anexo A** (2ª ed., 2023): os 104 símbolos de projeto, páginas 4 a 12, desenhados aqui
  em vetor a partir das páginas do anexo. Os nomes são os oficiais; a forma é um redesenho
  fiel ao desenho da tabela, não o arquivo original do CBMERJ (sem proporção oficial).
- **NT 2-05, Anexo B**: as placas de sinalização (P, A, S, E). São **esquemáticas**: forma e cor
  da tabela (circular vermelha, triangular, retangular verde, quadrada vermelha) e o código;
  o pictograma interno NÃO é reproduzido. E-17 (sinalização de solo) segue as medidas da norma.

Cada entrada guarda o nome do bloco que o dicionário do motor (``normative/base/simbolos.yaml``)
reconhece e a classe que ele reconhece; um teste confere que bloco e classe batem para todas.
Entradas sem classe (tanques, elevadores, dampers…) são desenhadas normalmente, mas o motor
não as conta como equipamento de segurança.

Cada bloco é desenhado na camada ``0`` (herda a camada da inserção, como em CAD), em unidades
em que o corpo do símbolo mede ~1: a inserção multiplica por ``tamanho_m``.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

Pt = tuple[float, float]
P1_03 = "NT 1-03, Anexo A"
P2_05 = "NT 2-05, Anexo B"


# --- mini linguagem de desenho ---------------------------------------------------------------


class Glyph:
    """Lista de primitivas em coordenadas do símbolo (y para cima, corpo ~1)."""

    def __init__(self) -> None:
        self.ops: list[tuple[str, tuple, int | None]] = []

    def line(self, *pts: Pt, c: int | None = None) -> Glyph:
        self.ops.append(("line", pts, c))
        return self

    def poly(self, *pts: Pt, c: int | None = None) -> Glyph:
        self.ops.append(("poly", pts, c))
        return self

    def fill(self, *pts: Pt, c: int | None = None) -> Glyph:
        self.ops.append(("fill", pts, c))
        return self

    def hatch(self, *pts: Pt, c: int | None = None) -> Glyph:
        self.ops.append(("hatch", pts, c))
        return self

    def circle(self, cx: float, cy: float, r: float, c: int | None = None) -> Glyph:
        self.ops.append(("circle", (cx, cy, r), c))
        return self

    def disk(self, cx: float, cy: float, r: float, c: int | None = None) -> Glyph:
        self.ops.append(("disk", (cx, cy, r), c))
        return self

    def arc(self, cx: float, cy: float, r: float, a0: float, a1: float,
            c: int | None = None) -> Glyph:
        self.ops.append(("arc", (cx, cy, r, a0, a1), c))
        return self

    def text(self, s: str, x: float, y: float, h: float = 0.25, c: int | None = None) -> Glyph:
        self.ops.append(("text", (s, x, y, h), c))
        return self


def emit(block: Any, g: Glyph) -> None:
    """Escreve o desenho num bloco do ezdxf (camada 0, herdando a da inserção)."""
    for kind, a, color in g.ops:
        attrs: dict[str, Any] = {"layer": "0"}
        if color is not None:
            attrs["color"] = color
        if kind == "line":
            block.add_lwpolyline(list(a), dxfattribs=attrs)
        elif kind == "poly":
            block.add_lwpolyline(list(a), close=True, dxfattribs=attrs)
        elif kind == "circle":
            block.add_circle((a[0], a[1]), a[2], dxfattribs=attrs)
        elif kind == "arc":
            block.add_arc((a[0], a[1]), a[2], a[3], a[4], dxfattribs=attrs)
        elif kind in ("fill", "disk"):
            # Preenchimento sólido + contorno: visualizadores sem suporte a HATCH ainda mostram
            # a forma (o contorno de um símbolo cheio é invisível a olho nu no CAD).
            h = block.add_hatch(color=color if color is not None else 7, dxfattribs={"layer": "0"})
            h.set_solid_fill()
            if kind == "fill":
                h.paths.add_polyline_path(list(a), is_closed=True)
                block.add_lwpolyline(list(a), close=True, dxfattribs=attrs)
            else:
                h.paths.add_edge_path().add_arc((a[0], a[1]), a[2], 0, 360)
                block.add_circle((a[0], a[1]), a[2], dxfattribs=attrs)
        elif kind == "hatch":
            h = block.add_hatch(color=color if color is not None else 7, dxfattribs={"layer": "0"})
            h.set_pattern_fill("ANSI31", scale=0.04)
            h.paths.add_polyline_path(list(a), is_closed=True)
        elif kind == "text":
            t = block.add_text(a[0], dxfattribs={**attrs, "height": a[3]})
            from ezdxf.enums import TextEntityAlignment

            t.set_placement((a[1], a[2]), align=TextEntityAlignment.MIDDLE_CENTER)


def ngon(cx: float, cy: float, r: float, n: int, rot: float = 90.0) -> list[Pt]:
    return [(cx + r * math.cos(math.radians(rot + 360 * i / n)),
             cy + r * math.sin(math.radians(rot + 360 * i / n))) for i in range(n)]


def rect(x0: float, y0: float, x1: float, y1: float) -> list[Pt]:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def dashed(g: Glyph, p: Pt, q: Pt, dash: float = 0.12, gap: float = 0.08) -> None:
    length = math.dist(p, q)
    ux, uy = (q[0] - p[0]) / length, (q[1] - p[1]) / length
    t = 0.0
    while t < length:
        e = min(t + dash, length)
        g.line((p[0] + ux * t, p[1] + uy * t), (p[0] + ux * e, p[1] + uy * e))
        t += dash + gap


def arrow(g: Glyph, p: Pt, q: Pt, head: float = 0.09, c: int | None = None) -> None:
    g.line(p, q, c=c)
    a = math.atan2(q[1] - p[1], q[0] - p[0])
    g.fill(q, (q[0] - head * math.cos(a - 0.4), q[1] - head * math.sin(a - 0.4)),
           (q[0] - head * math.cos(a + 0.4), q[1] - head * math.sin(a + 0.4)), c=c)


def xcirc(g: Glyph, cx: float, cy: float, r: float, ext: float = 1.5) -> None:
    """Círculo com X (as diagonais passam um pouco do contorno)."""
    g.circle(cx, cy, r)
    d = r * ext * math.cos(math.radians(45))
    g.line((cx - d, cy - d), (cx + d, cy + d))
    g.line((cx - d, cy + d), (cx + d, cy - d))


def triangle(g: Glyph, cx: float, cy: float, w: float, h: float, fill: bool = False) -> None:
    pts = ((cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx, cy + h / 2))
    (g.fill if fill else g.poly)(*pts)


def dome(g: Glyph, cx: float, cy: float, r: float, base: float) -> None:
    """Abrigo em arco sobre uma base reta (hidrantes, estações, acionadores)."""
    g.line((cx - r, base), (cx - r, cy), (cx - r, cy))
    g.arc(cx, cy, r, 0, 180)
    g.line((cx + r, cy), (cx + r, base), (cx - r, base))


def valve(g: Glyph, cx: float, cy: float, s: float) -> None:
    g.fill((cx - s, cy + s / 2), (cx - s, cy - s / 2), (cx, cy))
    g.fill((cx + s, cy + s / 2), (cx + s, cy - s / 2), (cx, cy))


def bolt(g: Glyph, cx: float, cy: float, s: float) -> None:
    top, left, mid = (cx + 0.15 * s, cy + 0.5 * s), (cx - 0.25 * s, cy - 0.05 * s), cy - 0.05 * s
    tip = (cx - 0.2 * s, cy - 0.5 * s)
    g.line(top, left, (cx + 0.1 * s, mid), tip)
    g.line(top, (cx + 0.3 * s, cy + 0.1 * s), (cx + 0.05 * s, cy + 0.1 * s),
           (cx + 0.3 * s, cy - 0.3 * s), tip)


def fan(g: Glyph, cx: float, cy: float, s: float) -> None:
    """Hélice de ventilador/exaustor: duas pás em 8 e a seta do fluxo."""
    g.circle(cx, cy + s * 0.22, s * 0.2)
    g.circle(cx, cy - s * 0.22, s * 0.2)
    arrow(g, (cx - s * 0.4, cy), (cx + s * 0.45, cy), head=s * 0.16)


def lamp(g: Glyph, cx: float, cy: float, s: float) -> None:
    """Ponto de iluminação: círculo sobre barra preenchida (símbolo da NT 1-03)."""
    g.circle(cx, cy + 0.38 * s, 0.1 * s)
    g.hatch(*rect(cx - 0.09 * s, cy - 0.42 * s, cx + 0.09 * s, cy + 0.22 * s))
    g.poly(*rect(cx - 0.09 * s, cy - 0.42 * s, cx + 0.09 * s, cy + 0.22 * s))


def stadium(g: Glyph, cx: float, cy: float, w: float, h: float, cut: float,
            dash: str = "") -> None:
    """Contorno alongado de cantos cortados (tanques). ``dash``: 'baixo' ou 'tudo'."""
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    top = [(x0 + cut, y1), (x1 - cut, y1), (x1, y1 - cut), (x1, y0 + cut)]
    bottom = [(x1, y0 + cut), (x1 - cut, y0), (x0 + cut, y0), (x0, y0 + cut)]
    left = [(x0, y0 + cut), (x0, y1 - cut), (x0 + cut, y1)]
    if dash == "tudo":
        for seg in (top, bottom, left):
            for p, q in zip(seg, seg[1:], strict=False):
                dashed(g, p, q, 0.1, 0.07)
    elif dash == "baixo":
        g.line(*top)
        g.line(*left)
        for p, q in zip(bottom, bottom[1:], strict=False):
            dashed(g, p, q, 0.1, 0.07)
    else:
        g.poly(*top, *bottom[1:], *left[:-1])


# --- catálogo -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Entrada:
    id: str  # = nome do bloco
    nome: str
    grupo: str
    subgrupo: str
    fonte: str
    pagina: int | None
    camada: str
    classe: str | None  # classe do dicionário do motor que reconhece o bloco (ou None)
    glyph: Callable[[], Glyph] = field(repr=False, compare=False)
    tamanho_m: float = 0.5
    esquematico: bool = False
    extra_classes: tuple[str, ...] = ()  # classes adicionais que o motor deriva (ex.: S-12 → SAIDA)
    uso: str = "bloco"  # bloco | parede | porta (como o motor desenha ao usar a operação)

    def resumo(self) -> dict[str, Any]:
        return {"id": self.id, "nome": self.nome, "grupo": self.grupo,
                "subgrupo": self.subgrupo, "fonte": self.fonte, "pagina": self.pagina,
                "classe_no_motor": self.classe, "camada": self.camada,
                "tamanho_padrao_m": self.tamanho_m, "esquematico": self.esquematico,
                **({"uso": self.uso} if self.uso != "bloco" else {})}


CATALOGO: dict[str, Entrada] = {}


def _add(id_: str, nome: str, grupo: str, sub: str, page: int, layer: str, cls: str | None,
         glyph: Callable[[Glyph], None], size: float = 0.5, uso: str = "bloco") -> None:
    def build() -> Glyph:
        g = Glyph()
        glyph(g)
        return g

    CATALOGO[id_] = Entrada(id_, nome, grupo, sub, P1_03, page, layer, cls, build, size,
                            uso=uso)


# 1. Extintores (p. 4) -----------------------------------------------------------------------

def _ext(marker: str, wheels: bool) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        g.poly((-0.5, -0.42), (0.5, -0.42), (0.0, 0.5))
        if marker == "co2":
            g.fill((-0.1, -0.2), (0.1, -0.2), (0.0, 0.0))
        elif marker == "ap":
            xcirc(g, 0.0, -0.12, 0.1)
        elif marker == "espuma":
            g.disk(0.0, -0.12, 0.11)
        elif marker == "bc":
            g.poly(*rect(-0.1, -0.22, 0.1, -0.02))
            g.line((-0.1, -0.22), (0.1, -0.02))
            g.line((-0.1, -0.02), (0.1, -0.22))
        elif marker == "abc":
            g.fill(*rect(-0.1, -0.22, 0.1, -0.02))
        else:  # pó D
            g.poly(*rect(-0.1, -0.22, 0.1, -0.02))
        if wheels:
            g.line((-0.5, -0.55), (0.5, -0.55))
            g.line((-0.5, -0.47), (-0.5, -0.63))
            g.line((0.5, -0.47), (0.5, -0.63))
    return draw


for _agent, _nome, _marker in (
        ("CO2", "EXTINTOR DE GÁS CARBÔNICO - CO2", "co2"),
        ("AP", "EXTINTOR DE ÁGUA PRESSURIZADA - AP", "ap"),
        ("ESPUMA", "EXTINTOR DE ESPUMA MECÂNICA", "espuma"),
        ("PQS_BC", "EXTINTOR DE PÓ BC", "bc"),
        ("PQS_ABC", "EXTINTOR DE PÓ ABC", "abc"),
        ("PO_D", "EXTINTOR DE PÓ D", "d")):
    _add(f"EXTINTOR_{_agent}", _nome, "EXTINTORES", "PORTÁTEIS", 4, "INC_EXT", "EXTINTOR",
         _ext(_marker, False))
    _add(f"EXTINTOR_{_agent}_SOBRERODAS", _nome, "EXTINTORES", "SOBRERODAS", 4, "INC_EXT",
         "EXTINTOR", _ext(_marker, True))

# 2. Sistema fixo de extinção: hidrantes (p. 5) ---------------------------------------------

def _hidrante(arrows: int) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        dome(g, 0.0, -0.05, 0.5, -0.4)
        xcirc(g, 0.0, -0.1, 0.14)
        if arrows == 1:
            arrow(g, (0.1, 0.0), (0.28, 0.42))
        else:
            arrow(g, (-0.05, 0.0), (-0.2, 0.42))
            arrow(g, (0.05, 0.0), (0.2, 0.42))
    return draw


def _urbano(underground: bool) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        for a, b in ((-0.7, -0.45), (-0.35, -0.1), (0.1, 0.35), (0.45, 0.7)):
            g.line((a, 0.0), (b, 0.0))
        g.line((0.0, -0.12), (0.0, 0.12))
        g.line((-0.1, 0.12), (0.1, 0.12))
        if underground:
            arrow(g, (0.0, -0.45), (0.0, 0.0))
        else:
            arrow(g, (0.0, 0.0), (0.0, 0.45))
            arrow(g, (0.0, 0.2), (-0.4, 0.2))
            arrow(g, (0.0, 0.2), (0.4, 0.2))
    return draw


def _recalque(check: bool, sprinkler: bool) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        g.poly(*ngon(-0.25, 0.0, 0.3, 8, 22.5))
        if sprinkler:
            g.poly((-0.25, 0.2), (-0.05, 0.0), (-0.25, -0.2), (-0.45, 0.0))
            xcirc(g, -0.25, 0.0, 0.07)
        else:
            xcirc(g, -0.25, 0.0, 0.14)
        g.line((0.05, 0.0), (0.25, 0.0))
        if check:
            valve(g, 0.35, 0.0, 0.1)
            arrow(g, (0.45, 0.0), (0.7, 0.0))
        else:
            arrow(g, (0.25, 0.0), (0.7, 0.0))
    return draw


def _bomba(g: Glyph) -> None:
    g.poly(*ngon(0.0, 0.0, 0.42, 10, 90))
    g.line((-0.3, 0.05), (0.0, 0.32), (0.3, 0.05))
    for x in (-0.2, 0.0, 0.2):
        g.arc(x, -0.12, 0.1, 0, 180)


def _reserva(g: Glyph, inner: str = "") -> None:
    g.poly(*rect(-0.5, -0.35, 0.5, 0.25))
    g.line((-0.25, 0.4), (-0.1, 0.25))
    g.line((0.25, 0.4), (0.1, 0.25))
    if inner == "spk":
        g.poly((0.0, 0.15), (0.2, -0.05), (0.0, -0.25), (-0.2, -0.05))
        xcirc(g, 0.0, -0.05, 0.07)
    elif inner == "foam":
        g.disk(0.0, -0.05, 0.1)


_G = "SISTEMA FIXO DE EXTINÇÃO"
_add("HIDRANTE_DUPLO", "HIDRANTE DUPLO", _G, "SISTEMA DE HIDRANTES", 5, "INC_HID", "HIDRANTE",
     _hidrante(2))
_add("HIDRANTE_SIMPLES", "HIDRANTE SIMPLES", _G, "SISTEMA DE HIDRANTES", 5, "INC_HID",
     "HIDRANTE", _hidrante(1))
_add("HIDRANTE_URBANO", "HIDRANTE URBANO", _G, "SISTEMA DE HIDRANTES", 5, "INC_HID",
     "HIDRANTE_URBANO", _urbano(False), 1.0)
_add("HIDRANTE_URBANO_SUBTERRANEO", "HIDRANTE URBANO SUBTERRÂNEO", _G, "SISTEMA DE HIDRANTES",
     5, "INC_HID", "HIDRANTE_URBANO", _urbano(True), 1.0)
_add("BOMBA_INCENDIO", "BOMBA DE INCÊNDIO", _G, "SISTEMA DE HIDRANTES", 5, "INC_HID",
     "BOMBA_INCENDIO", _bomba)
_add("RESERVA_TECNICA_INCENDIO", "RESERVA TÉCNICA DE INCÊNDIO", _G, "SISTEMA DE HIDRANTES", 5,
     "INC_HID", "RESERVA_TECNICA", _reserva)
_add("REGISTRO_RECALQUE", "REGISTRO DE RECALQUE", _G, "SISTEMA DE HIDRANTES", 5, "INC_HID",
     "REGISTRO_RECALQUE", _recalque(False, False), 1.0)
_add("REGISTRO_RECALQUE_RETENCAO", "REGISTRO DE RECALQUE COM VÁLVULA DE RETENÇÃO", _G,
     "SISTEMA DE HIDRANTES", 5, "INC_HID", "REGISTRO_RECALQUE", _recalque(True, False), 1.0)


def _acionador_bomba(g: Glyph) -> None:
    dome(g, 0.0, 0.0, 0.5, -0.3)
    g.poly(*ngon(0.0, 0.05, 0.2, 8, 22.5))
    g.arc(-0.07, 0.0, 0.05, 0, 180)
    g.arc(0.07, 0.0, 0.05, 0, 180)
    g.line((0.0, -0.15), (0.0, -0.45))
    g.circle(0.0, -0.5, 0.05)


_add("ACIONADOR_BOMBA_INCENDIO", "ACIONADOR BOMBA INCÊNDIO", _G, "SISTEMA DE HIDRANTES", 5,
     "INC_HID", "ACIONADOR_BOMBA", _acionador_bomba)


# 3. Sprinklers (p. 5-6) ------------------------------------------------------------------------

def _spk_line(g: Glyph) -> None:
    dashed(g, (-0.75, 0.0), (-0.3, 0.0), 0.1, 0.07)
    dashed(g, (0.3, 0.0), (0.75, 0.0), 0.1, 0.07)


def _spk_cima(g: Glyph) -> None:
    _spk_line(g)
    g.disk(0.0, 0.0, 0.25)


def _spk_pendente(g: Glyph) -> None:
    _spk_line(g)
    g.circle(0.0, 0.0, 0.25)


def _spk_lateral(g: Glyph) -> None:
    dashed(g, (-0.75, 0.25), (0.75, 0.25), 0.1, 0.07)
    g.poly((-0.25, 0.25), (0.25, 0.25), (0.0, -0.25))


def _diamond_x(g: Glyph, cx: float = 0.0, cy: float = 0.0, s: float = 0.22) -> None:
    g.poly((cx, cy + s), (cx + s, cy), (cx, cy - s), (cx - s, cy))
    xcirc(g, cx, cy, s * 0.35)


def _bomba_spk(g: Glyph) -> None:
    g.poly(*ngon(0.0, 0.0, 0.45, 8, 22.5))
    g.poly(*ngon(0.0, 0.0, 0.33, 8, 22.5))
    _diamond_x(g, 0.0, 0.0, 0.25)


def _painel_spk(g: Glyph) -> None:
    g.poly(*rect(-0.6, -0.35, 0.6, 0.35))
    _diamond_x(g)


def _vga(g: Glyph) -> None:
    g.poly(*rect(-0.35, -0.55, 0.35, 0.45))
    g.line((-0.4, 0.5), (0.4, 0.5))
    _diamond_x(g, 0.0, 0.05, 0.2)
    g.line((0.0, -0.17), (0.0, -0.3))


_add("BICO_SPRINKLER_CIMA", "BICO DE SPRINKLER PARA CIMA", _G, "SPRINKLERS", 5, "INC_SPK",
     "SPRINKLER", _spk_cima, 0.6)
_add("BICO_SPRINKLER_PENDENTE", "BICO DE SPRINKLER PENDENTE", _G, "SPRINKLERS", 5, "INC_SPK",
     "SPRINKLER", _spk_pendente, 0.6)
_add("BICO_SPRINKLER_LATERAL", "BICO DE SPRINKLER LATERAL", _G, "SPRINKLERS", 5, "INC_SPK",
     "SPRINKLER", _spk_lateral, 0.6)
_add("REGISTRO_RECALQUE_SPRINKLER", "REGISTRO DE RECALQUE PARA SISTEMA DE SPRINKLERS", _G,
     "SPRINKLERS", 5, "INC_SPK", "REGISTRO_RECALQUE", _recalque(True, True), 1.0)
_add("BOMBA_CHUVEIROS_AUTOMATICOS", "BOMBA PARA SISTEMA DE SPRINKLERS", _G, "SPRINKLERS", 5,
     "INC_SPK", None, _bomba_spk)
_add("RESERVA_TECNICA_SPRINKLER", "RESERVA TÉCNICA PARA SISTEMA DE SPRINKLERS", _G,
     "SPRINKLERS", 5, "INC_SPK", "RESERVA_TECNICA", lambda g: _reserva(g, "spk"))
_add("PAINEL_COMANDO_CHUVEIROS", "PAINEL DE COMANDO DO SISTEMA DE SPRINKLERS", _G,
     "SPRINKLERS", 6, "INC_SPK", None, _painel_spk)
_add("VALVULA_GOVERNO_ALARME_VGA", "VÁLVULA DE GOVERNO E ALARME - VGA", _G, "SPRINKLERS", 6,
     "INC_SPK", None, _vga)


# 4. Gás carbônico e espuma (p. 6) --------------------------------------------------------------

def _bateria(fill: bool) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        for cx in (-0.6, 0.0, 0.6):
            if fill:
                g.fill((cx - 0.28, -0.3), (cx + 0.28, -0.3), (cx, 0.3))
            else:
                g.poly((cx - 0.28, -0.3), (cx + 0.28, -0.3), (cx, 0.3))
                g.line((cx, -0.3), (cx, 0.3))
        g.line((-0.6, -0.3), (0.6, -0.3))
        if not fill:
            g.line((-0.6, -0.2), (0.6, -0.2))
    return draw


def _acionador_co2(g: Glyph) -> None:
    dome(g, 0.0, -0.05, 0.5, -0.4)
    g.fill((-0.08, 0.0), (0.08, 0.0), (0.0, 0.15))
    g.circle(0.0, -0.12, 0.05)
    g.line((0.0, -0.17), (0.0, -0.4))


def _espuma_dome(arrows: str) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        dome(g, 0.0, -0.1, 0.5, -0.4)
        g.disk(0.0, -0.12, 0.13)
        if arrows == "esguicho":
            arrow(g, (0.1, 0.1), (0.3, 0.45))
        if arrows in ("fixa", "movel"):
            arrow(g, (-0.7, -0.45), (0.7, -0.45))
        if arrows == "movel":
            g.line((-0.5, -0.4), (-0.5, -0.5))
            g.line((0.5, -0.4), (0.5, -0.5))
    return draw


def _tanque_espuma(g: Glyph) -> None:
    g.poly(*rect(-0.5, -0.35, 0.5, 0.25))
    g.line((-0.25, 0.4), (-0.1, 0.25))
    g.line((0.25, 0.4), (0.1, 0.25))
    g.disk(0.0, -0.05, 0.1)


def _canhao(portatil: bool) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        if portatil:
            g.fill(*ngon(0.1, -0.15, 0.17, 8, 22.5))
        else:
            xcirc(g, 0.1, -0.15, 0.14)
        arrow(g, (-0.5, -0.15), (-0.1, -0.15))
        arrow(g, (0.15, -0.05), (0.35, 0.4))
        g.line((-0.1, 0.4), (0.4, 0.4))
    return draw


_add("BATERIA_CILINDROS_GAS_CARBONICO", "BATERIA DE CILINDROS DE CO2", _G, "GÁS CARBÔNICO", 6,
     "INC_FIXO", None, _bateria(True), 0.9)
_add("ACIONADOR_SISTEMA_GAS_CARBONICO", "ACIONADOR MANUAL DO SISTEMA DE CO2", _G,
     "GÁS CARBÔNICO", 6, "INC_FIXO", None, _acionador_co2)
_add("BATERIA_HALON", "BATERIA DE HALON", _G, "GÁS CARBÔNICO", 6, "INC_FIXO", None,
     _bateria(False), 0.9)
_add("TANQUE_ATMOSFERICO_ESPUMA", "TANQUE ATMOSFÉRICO DE ESPUMA", _G, "SISTEMA DE ESPUMA", 6,
     "INC_FIXO", None, _tanque_espuma)
_add("ESTACAO_FIXA_EMULSIONAMENTO", "ESTAÇÃO FIXA DE EMULSIONAMENTO", _G, "SISTEMA DE ESPUMA",
     6, "INC_FIXO", None, _espuma_dome("fixa"))
_add("ESTACAO_MOVEL_EMULSIONAMENTO", "ESTAÇÃO MÓVEL DE EMULSIONAMENTO", _G,
     "SISTEMA DE ESPUMA", 6, "INC_FIXO", None, _espuma_dome("movel"))
_add("CANHAO_MONITOR_PORTATIL_ESPUMA", "CANHÃO MONITOR PORTÁTIL SISTEMA DE ESPUMA", _G,
     "SISTEMA DE ESPUMA", 6, "INC_FIXO", None, _canhao(True))
_add("CANHAO_MONITOR_RESFRIAMENTO", "CANHÃO MONITOR SISTEMA DE RESFRIAMENTO", _G,
     "SISTEMA DE ESPUMA", 6, "INC_FIXO", None, _canhao(False))
_add("LIQUIDO_GERADOR_ESPUMA", "LÍQUIDO GERADOR DE ESPUMA", _G, "SISTEMA DE ESPUMA", 6,
     "INC_FIXO", None, _espuma_dome("lge"))
_add("ESGUICHO_LANCADOR_ESPUMA", "ESGUICHO LANÇADOR DE ESPUMA", _G, "SISTEMA DE ESPUMA", 6,
     "INC_FIXO", None, _espuma_dome("esguicho"))

# 5. Iluminação de emergência (p. 7) ----------------------------------------------------------

_I = "SISTEMA DE ILUMINAÇÃO DE EMERGÊNCIA"


def _ilum(g: Glyph) -> None:
    lamp(g, 0.0, 0.0, 1.0)


def _ilum_baliz(g: Glyph) -> None:
    lamp(g, 0.0, 0.1, 0.9)
    g.poly((-0.05, -0.38), (0.15, -0.38), (0.15, -0.3), (0.3, -0.45), (0.15, -0.6), (0.15, -0.52),
           (-0.05, -0.52))


def _ilum_explosao(g: Glyph) -> None:
    lamp(g, 0.0, 0.0, 0.9)
    for a in range(0, 360, 30):
        g.arc(0.0, 0.0, 0.5, a, a + 18)


def _baterias(g: Glyph) -> None:
    g.poly(*rect(-0.5, -0.3, 0.5, 0.3))
    g.line((-0.4, 0.3), (-0.4, 0.38), (-0.3, 0.38), (-0.3, 0.3))
    g.line((0.3, 0.3), (0.3, 0.38), (0.4, 0.38), (0.4, 0.3))
    g.line((-0.4, 0.15), (-0.3, 0.15))
    g.line((-0.35, 0.1), (-0.35, 0.2))
    g.line((0.3, 0.15), (0.4, 0.15))
    lamp(g, 0.0, 0.0, 0.5)


def _central_ilum(g: Glyph) -> None:
    g.poly(*rect(-0.5, -0.3, 0.5, 0.3))
    lamp(g, 0.0, 0.0, 0.5)


def _motogerador(g: Glyph) -> None:
    g.poly(*ngon(0.0, -0.05, 0.4, 10, 90))
    g.poly(*rect(-0.12, 0.35, 0.12, 0.5))
    g.arc(0.0, -0.05, 0.1, 40, 330)


_add("PONTO_ILUMINACAO_EMERGENCIA", "PONTO DE ILUMINAÇÃO DE EMERGÊNCIA", _I, "", 7,
     "ILUMINACAO", "ILUMINACAO_EMERGENCIA", _ilum)
_add("PONTO_ILUMINACAO_EMERGENCIA_BALIZAMENTO",
     "PONTO DE ILUMINAÇÃO DE EMERGÊNCIA TIPO BALIZAMENTO", _I, "", 7, "ILUMINACAO",
     "ILUMINACAO_EMERGENCIA", _ilum_baliz)
_add("PONTO_ILUMINACAO_EMERGENCIA_PROVA_EXPLOSAO",
     "PONTO DE ILUMINAÇÃO DE EMERGÊNCIA À PROVA DE EXPLOSÃO E PÓ", _I, "", 7, "ILUMINACAO",
     "ILUMINACAO_EMERGENCIA", _ilum_explosao)
_add("BATERIAS_ACUMULADORES_EMERGENCIA",
     "BATERIAS E ACUMULADORES DO SISTEMA DE ILUMINAÇÃO DE EMERGÊNCIA", _I, "", 7, "ILUMINACAO",
     None, _baterias)
_add("CENTRAL_SISTEMA_EMERGENCIA_LUZ", "CENTRAL DO SISTEMA DE ILUMINAÇÃO DE EMERGÊNCIA", _I, "",
     7, "ILUMINACAO", None, _central_ilum)
_add("GRUPO_MOTOGERADOR", "GRUPO MOTOGERADOR", _I, "", 7, "ELETRICO", None, _motogerador)

# 6. Vasos e tanques (p. 7-8) ---------------------------------------------------------------

_V = "VASOS E TANQUES"


def _glp(g: Glyph) -> None:
    pts = ngon(0.0, 0.0, 0.5, 6, 90)
    g.poly(*pts)
    for i in range(3):
        g.line(pts[i], pts[i + 3])


def _vaso(g: Glyph) -> None:
    g.poly(*ngon(0.0, 0.0, 0.5, 6, 90))
    g.poly(*ngon(0.0, 0.0, 0.32, 10, 90))


def _tanque(orient: str, dash: str) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        if orient == "h":
            stadium(g, 0.0, 0.0, 1.4, 0.5, 0.14, dash)
        else:
            stadium(g, 0.0, 0.0, 0.5, 1.4, 0.14, dash)
    return draw


_add("CENTRAL_GLP", "CENTRAL DE GLP", _V, "GLP", 7, "VASOS_TANQUES", "CENTRAL_GLP", _glp)
_add("VASO_PRESSAO", "VASO PRESSÃO", _V, "GLP", 7, "VASOS_TANQUES", None, _vaso)
for _id, _nome, _o, _d in (
        ("TANQUE_HORIZONTAL_ENTERRADO", "TANQUE HORIZONTAL ENTERRADO", "h", "tudo"),
        ("TANQUE_HORIZONTAL_SUPERFICIE", "TANQUE HORIZONTAL SUPERFÍCIE", "h", ""),
        ("TANQUE_VERTICAL_ENTERRADO", "TANQUE VERTICAL ENTERRADO", "v", "tudo"),
        ("TANQUE_VERTICAL_SUPERFICIE", "TANQUE VERTICAL SUPERFÍCIE", "v", ""),
        ("TANQUE_HORIZONTAL_SEMIENTERRADO", "TANQUE HORIZONTAL SEMIENTERRADO", "h", "baixo"),
        ("TANQUE_VERTICAL_SEMIENTERRADO", "TANQUE VERTICAL SEMIENTERRADO", "v", "baixo")):
    _add(_id, _nome, _V, "TANQUES", 7 if _id.endswith(("ENTERRADO", "SUPERFICIE"))
         and "SEMI" not in _id else 8, "VASOS_TANQUES", None, _tanque(_o, _d), 0.8)

# 7. Sistema elétrico (p. 8) ----------------------------------------------------------------

_E = "SISTEMA ELÉTRICO"


def _chave(kind: str) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        w = 1.0 if kind == "quadro" else 0.55
        g.poly(*rect(-w / 2, -0.35, w / 2, 0.35))
        bolt(g, -0.1 if kind == "quadro" else 0.0, 0.0, 0.6)
        if kind == "principal":
            g.line((0.28, 0.1), (0.4, 0.1), (0.4, -0.2), (0.28, -0.2))
    return draw


_add("CHAVE_ELETRICA_SECUNDARIA", "CHAVE ELÉTRICA SECUNDÁRIA", _E, "", 8, "ELETRICO", None,
     _chave("secundaria"))
_add("CHAVE_ELETRICA_PRINCIPAL", "CHAVE ELÉTRICA PRINCIPAL", _E, "", 8, "ELETRICO", None,
     _chave("principal"))
_add("QUADRO_DISTRIBUICAO_LUZ", "QUADRO DE DISTRIBUIÇÃO DE LUZ", _E, "", 8, "ELETRICO", None,
     _chave("quadro"), 0.7)

# 8. Sistema de alarme (p. 8) -------------------------------------------------------------------

_A = "SISTEMA DE ALARME"


def _aviso_sonoro(g: Glyph) -> None:
    g.poly(*rect(-0.35, -0.12, -0.1, 0.12))
    g.poly((-0.1, 0.12), (0.2, 0.3), (0.2, -0.3), (-0.1, -0.12))


def _aviso_rays(g: Glyph, label: str) -> None:
    g.circle(0.0, 0.0, 0.25)
    g.text(label, 0.0, 0.0, 0.22)
    for a in (45, 135, 225, 315):
        d = (math.cos(math.radians(a)), math.sin(math.radians(a)))
        g.line((d[0] * 0.33, d[1] * 0.33), (d[0] * 0.45, d[1] * 0.45))


def _aviso_mecanico(g: Glyph) -> None:
    g.circle(0.0, 0.0, 0.25)
    g.line((-0.5, 0.0), (0.5, 0.0))
    g.arc(0.0, 0.0, 0.33, -80, 70)
    arrow(g, (0.07, -0.32), (-0.02, -0.34))


_add("AVISADOR_SONORO_ELETRONICO", "AVISADOR SONORO ELETRÔNICO", _A, "", 8, "INC_ALARME",
     "AVISADOR", _aviso_sonoro)
_add("AVISADOR_AUDIOVISUAL", "AVISADOR AUDIOVISUAL", _A, "", 8, "INC_ALARME", "AVISADOR",
     lambda g: _aviso_rays(g, "AV"))
_add("AVISADOR_SONORO_MECANICO", "AVISADOR SONORO MECÂNICO", _A, "", 8, "INC_ALARME",
     "AVISADOR", _aviso_mecanico)
_add("AVISADOR_VISUAL", "AVISADOR VISUAL", _A, "", 8, "INC_ALARME", "AVISADOR",
     lambda g: _aviso_rays(g, "V"))

# 9. Sistema de detecção (p. 9) -----------------------------------------------------------------

_D = "SISTEMA DE DETECÇÃO"


def _det(kind: str) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        r = 0.3
        if kind == "parede":
            g.line((-0.3, -0.5), (-0.3, 0.5))
            g.circle(0.0, 0.0, r)
            return
        g.circle(0.0, 0.0, r)
        if kind == "termico":
            g.line((-r, r * 0.85), (r, r * 0.85))
            g.line((0.0, r * 0.85), (0.0, -r))
        elif kind == "termovel":
            d = r * math.cos(math.radians(45))
            g.line((-d, -d), (d, d))
            g.line((-d, d), (d, -d))
        elif kind == "fumaca":
            g.fill((0.0, r), (0.0, -r), *[(-r * math.sin(math.radians(a)),
                                          r * math.cos(math.radians(a))) for a in
                                         range(0, 181, 15)][::-1], c=None)
            g.line((0.0, r), (0.0, -r))
        elif kind == "multi":
            g.fill((0.0, r), (0.0, -r), *[(-r * math.sin(math.radians(a)),
                                          r * math.cos(math.radians(a))) for a in
                                         range(0, 181, 15)][::-1])
            g.line((0.0, 0.0), (r * 0.7, r * 0.7))
            g.line((0.0, 0.0), (r * 0.7, -r * 0.7))
        elif kind == "chama":
            g.line((-r * 0.75, 0.0), (0.0, r * 0.75), (0.0, -r * 0.75), (-r * 0.75, 0.0))
            g.line((0.0, r), (0.0, -r))
        elif kind == "entreforro":
            g.line((-r * 0.7, -r * 0.7), (-r * 1.2, -r * 1.2))
            arrow(g, (r * 0.7, r * 0.7), (r * 1.7, r * 1.7))
        elif kind == "entrepiso":
            g.line((-r * 0.7, -r * 0.7), (-r * 1.2, -r * 1.2))
            arrow(g, (r * 1.7, r * 1.7), (r * 0.75, r * 0.75))
        elif kind == "intemperie":
            g.line((-0.5, 0.2), (0.0, 0.5), (0.5, 0.2), (-0.5, 0.2))
    return draw


def _acionador_manual(g: Glyph) -> None:
    g.poly(*rect(-0.4, -0.4, 0.4, 0.4))
    g.poly(*rect(-0.35, -0.35, 0.35, 0.35))
    g.disk(0.0, 0.0, 0.14)


def _central(g: Glyph) -> None:
    g.poly(*rect(-0.8, -0.2, 0.8, 0.2))
    g.line((-0.8, 0.0), (0.8, 0.0))
    for x in (-0.4, 0.0, 0.4):
        g.line((x, -0.2), (x, 0.2))


for _id, _nome, _k in (
        ("DETECTOR_TERMICO", "DETECTOR TÉRMICO", "termico"),
        ("DETECTOR_TERMOVELOCIMETRICO", "DETECTOR TERMOVELOCIMÉTRICO", "termovel"),
        ("DETECTOR_FUMACA", "DETECTOR DE FUMAÇA", "fumaca"),
        ("DETECTOR_MULTISENSOR", "DETECTOR MULTISENSOR", "multi"),
        ("DETECTOR_CHAMA", "DETECTOR DE CHAMA", "chama"),
        ("DETECTOR_ENTREFORRO", "DETECTOR NO ENTREFORRO", "entreforro"),
        ("DETECTOR_ENTREPISO", "DETECTOR NO ENTREPISO", "entrepiso"),
        ("DETECTOR_PAREDE", "DETECTOR NA PAREDE", "parede")):
    _add(_id, _nome, _D, "", 9, "INC_ALARME", "DETECTOR", _det(_k), 0.45)
_add("PROTECAO_CONTRA_INTEMPERIES", "PROTEÇÃO CONTRA INTEMPÉRIES", _D, "", 9, "INC_ALARME",
     None, lambda g: (g.circle(0.0, 0.0, 0.3), _det("intemperie")(g)), 0.45)
_add("ACIONADOR_MANUAL", "ACIONADOR MANUAL", _D, "", 9, "INC_ALARME", "ACIONADOR_MANUAL",
     _acionador_manual, 0.4)
_add("CENTRAL_ALARME_DETECCAO", "CENTRAL", _D, "", 9, "INC_ALARME", "CENTRAL_ALARME",
     _central, 0.7)

# 10. Sistemas passivos (p. 10-11) ---------------------------------------------------------------

_S = "SISTEMAS PASSIVOS"


def _barra(g: Glyph) -> None:
    g.poly((-0.8, 0.25), (0.0, 0.25), (-0.4, -0.25))
    g.poly((0.0, 0.25), (0.8, 0.25), (0.4, -0.25))


def _pcf(minutes: int) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        g.line((-0.9, 0.0), (-0.5, 0.0))
        g.line((0.5, 0.0), (0.9, 0.0))
        g.line((-0.5, 0.0), (-0.5, 0.9))
        g.arc(-0.5, 0.0, 0.9, 0, 90)
        g.text(str(minutes), 0.0, -0.25, 0.25)
    return draw


def _bar(kind: str) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        if kind == "divisoria":
            g.poly(*rect(-1.0, -0.03, 1.0, 0.03))
            return
        pts = rect(-1.0, -0.07, 1.0, 0.07)
        if kind == "corta_fogo":
            g.fill(*pts)
        elif kind == "compartimentacao":
            g.hatch(*pts)
            g.poly(*pts)
        else:
            g.poly(*pts)
    return draw


def _elev(kind: str) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        g.poly(*rect(-0.45, -0.45, 0.45, 0.45))
        if kind == "elevador":
            g.line((-0.45, -0.45), (0.45, 0.45))
            g.line((-0.45, 0.45), (0.45, -0.45))
        elif kind == "emergencia":
            g.fill((-0.45, 0.45), (0.45, 0.45), (0.0, 0.0))
            g.fill((-0.45, -0.45), (0.45, -0.45), (0.0, 0.0))
        elif kind == "montacarga":
            g.line((-0.45, -0.45), (0.45, 0.45))
            g.line((-0.45, 0.45), (0.45, -0.45))
            g.fill((-0.45, -0.45), (0.45, -0.45), (0.0, 0.0))
        else:  # shaft
            g.fill(*rect(0.0, 0.0, 0.45, 0.45))
            g.fill(*rect(-0.45, -0.45, 0.0, 0.0))
    return draw


def _damper(kind: str) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        g.line((-0.35, 0.5), (0.35, 0.5))
        g.line((-0.35, 0.4), (0.35, 0.4))
        g.line((0.0, 0.55), (0.0, 0.1))
        if kind == "fogo":
            g.fill(*ngon(0.0, -0.05, 0.15, 8, 22.5))
        else:
            g.poly(*ngon(0.0, -0.15, 0.25, 8, 22.5))
            bolt(g, 0.0, -0.15, 0.35)
            if kind == "ambos":
                g.disk(0.0, -0.42, 0.04)
    return draw


_add("BARRA_ANTIPANICO", "BARRA ANTIPÂNICO", _S, "", 10, "PASSIVOS", None, _barra, 0.6)
for _m in (60, 90, 120):
    _add(f"PORTA_CORTA_FOGO_P{_m}", f"PORTA CORTA-FOGO P-{_m}", _S, "ABERTURAS PROTEGIDAS", 10,
         "PORTA_CORTA_FOGO", None, _pcf(_m), 0.9, uso="porta")
_add("PAREDE_CORTA_FOGO", "PAREDE CORTA-FOGO", _S, "VEDOS", 10, "PAREDE_CORTA_FOGO", None,
     _bar("corta_fogo"), 1.0, uso="parede")
_add("PAREDE_COMPARTIMENTACAO", "PAREDE DE COMPARTIMENTAÇÃO", _S, "VEDOS", 10,
     "PAREDE_COMPARTIMENTACAO", None, _bar("compartimentacao"), 1.0, uso="parede")
_add("PAREDE_COMUM", "PAREDE COMUM", _S, "VEDOS", 10, "PAREDE", None, _bar("comum"), 1.0,
     uso="parede")
_add("DIVISORIA", "DIVISÓRIA", _S, "VEDOS", 10, "DIVISORIA", None, _bar("divisoria"), 1.0,
     uso="parede")
_add("ELEVADOR", "ELEVADOR", _S, "ELEVADORES", 10, "PASSIVOS", None, _elev("elevador"), 0.8)
_add("ELEVADOR_EMERGENCIA", "ELEVADOR DE EMERGÊNCIA", _S, "ELEVADORES", 10, "PASSIVOS", None,
     _elev("emergencia"), 0.8)
_add("MONTACARGA", "MONTACARGA", _S, "ELEVADORES", 10, "PASSIVOS", None, _elev("montacarga"),
     0.8)
_add("SHAFT_PROTEGIDO", "SHAFT PROTEGIDO", _S, "ELEVADORES", 10, "PASSIVOS", None,
     _elev("shaft"), 0.8)
_add("DAMPER_CORTA_FOGO", "DAMPER CORTA-FOGO", _S, "DAMPERS", 10, "PASSIVOS", None,
     _damper("fogo"))
_add("DAMPER_CORTA_FUMACA", "DAMPER CORTA-FUMAÇA", _S, "DAMPERS", 10, "PASSIVOS", None,
     _damper("fumaca"))
_add("DAMPER_CORTA_FOGO_E_FUMACA", "DAMPER CORTA-FOGO E CORTA-FUMAÇA", _S, "DAMPERS", 11,
     "PASSIVOS", None, _damper("ambos"))

# 11. Controle de fumaça (p. 11) ----------------------------------------------------------------

_F = "CONTROLE DE FUMAÇA"


def _ventilador(g: Glyph) -> None:
    g.poly(*ngon(-0.2, 0.0, 0.32, 10, 90))
    fan(g, -0.2, 0.0, 0.6)
    g.line((-0.2, 0.32), (0.7, 0.32), (0.7, -0.1), (0.1, -0.1))


def _acionador_fumaca(g: Glyph) -> None:
    g.poly(*rect(-0.55, -0.4, 0.55, 0.4))
    fan(g, 0.0, 0.0, 0.7)


def _damper_sobre(g: Glyph) -> None:
    g.line((-0.3, 0.5), (0.3, 0.5))
    g.line((-0.3, 0.4), (0.3, 0.4))
    g.line((0.0, 0.5), (0.0, 0.25))
    g.poly(*ngon(0.0, -0.05, 0.3, 10, 90))
    fan(g, 0.0, -0.05, 0.5)


def _veneziana(kind: str) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        if kind == "filtro":
            g.poly(*rect(-0.12, -0.45, 0.12, 0.45))
            g.hatch(*rect(-0.12, -0.45, 0.0, 0.45))
            arrow(g, (-0.4, 0.0), (0.55, 0.0))
        elif kind == "piso":
            g.poly(*rect(-0.12, -0.4, 0.12, 0.4))
            g.poly(*rect(0.12, -0.4, 0.28, 0.4))
            for y in (-0.3, -0.1, 0.1, 0.3):
                g.line((-0.12, y - 0.1), (0.12, y + 0.1))
            g.poly((-0.5, 0.0), (-0.3, 0.1), (-0.3, -0.1))
            g.line((-0.3, 0.0), (0.6, 0.0))
        elif kind == "teto":
            g.poly(*rect(-0.4, 0.05, 0.4, 0.25))
            for x in (-0.3, -0.1, 0.1, 0.3):
                g.line((x - 0.1, 0.05), (x + 0.1, 0.25))
            g.line((0.0, 0.5), (0.0, -0.2))
            g.poly((-0.07, -0.2), (0.07, -0.2), (0.0, -0.32))
        else:  # grelha
            g.line((0.0, 0.5), (-0.15, 0.4), (0.0, 0.3), (-0.15, 0.2), (0.0, 0.1))
            g.line((0.0, -0.5), (-0.15, -0.4), (0.0, -0.3), (-0.15, -0.2), (0.0, -0.1))
            g.line((0.0, 0.5), (0.0, -0.5))
            arrow(g, (-0.4, 0.0), (0.5, 0.0))
    return draw


def _dimensoes(g: Glyph) -> None:
    g.text("Largura x Altura", 0.0, 0.3, 0.15)
    g.text("(Veneziana)", 0.0, 0.1, 0.15)
    g.line((-0.6, -0.05), (0.6, -0.05))
    g.text("Altura do piso", 0.0, -0.25, 0.15)


_add("VENTILADOR_EXAUSTOR_FUMACA", "VENTILADOR OU EXAUSTOR PARA CONTROLE DE FUMAÇA", _S,
     "CONTROLE DE FUMAÇA", 11, "FUMACA", None, _ventilador, 0.7)
_add("ACIONADOR_EXAUSTAO_VENTILACAO", "ACIONADOR MANUAL (EXAUSTÃO OU VENTILAÇÃO)", _S,
     "CONTROLE DE FUMAÇA", 11, "FUMACA", None, _acionador_fumaca)
_add("DAMPER_SOBREPRESSAO", "DAMPER DE SOBREPRESSÃO", _S, "CONTROLE DE FUMAÇA", 11, "FUMACA",
     None, _damper_sobre)
_add("VENEZIANA_ENTRADA_AR_FILTRO", "VENEZIANA DE ENTRADA DE AR COM FILTRO", _S,
     "CONTROLE DE FUMAÇA", 11, "FUMACA", None, _veneziana("filtro"))
_add("VENEZIANA_ENTRADA_AR_PISO", "VENEZIANA DE ENTRADA DE AR JUNTO AO PISO", _S,
     "CONTROLE DE FUMAÇA", 11, "FUMACA", None, _veneziana("piso"))
_add("VENEZIANA_ENTRADA_AR_TETO", "VENEZIANA DE ENTRADA DE AR JUNTO AO TETO", _S,
     "CONTROLE DE FUMAÇA", 11, "FUMACA", None, _veneziana("teto"))
_add("GRELHA_AJUSTE_BALANCEAMENTO", "GRELHA COM DISPOSITIVO DE AJUSTE E BALANCEAMENTO", _S,
     "CONTROLE DE FUMAÇA", 11, "FUMACA", None, _veneziana("grelha"))
_add("DIMENSOES_VENEZIANA", "DIMENSÕES DA VENEZIANA E ALTURA DO PISO", _S,
     "CONTROLE DE FUMAÇA", 11, "FUMACA", None, _dimensoes, 1.0)

# 12. Rotas de fuga e outros (p. 12) -------------------------------------------------------------


def _rota(final: bool) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        for i in range(4 if final else 3):
            x = -1.0 + i * 0.4
            g.fill(*rect(x, -0.15, x + 0.3, 0.15))
        if final:
            g.fill((0.55, -0.15), (0.75, -0.15), (0.75, -0.3), (1.05, 0.0), (0.75, 0.3),
                   (0.75, 0.15), (0.55, 0.15))
        else:
            g.fill((0.2, -0.2), (0.45, 0.0), (0.2, 0.2), (0.3, 0.0))
            for x in (0.6, 0.95):
                g.fill(*rect(x, -0.15, x + 0.3, 0.15))
    return draw


def _registro(g: Glyph) -> None:
    g.line((-0.6, 0.0), (0.6, 0.0))
    valve(g, 0.0, 0.0, 0.3)


def _tanque_pressao(g: Glyph) -> None:
    stadium(g, 0.0, 0.1, 0.4, 0.9, 0.1)
    g.line((0.0, -0.35), (0.0, -0.6))


def _manometro(g: Glyph) -> None:
    g.poly(*ngon(0.0, 0.15, 0.25, 8, 22.5))
    g.line((0.0, -0.1), (0.0, -0.5))


def _pressostato(g: Glyph) -> None:
    g.poly(*rect(-0.2, 0.0, 0.2, 0.4))
    g.line((0.0, 0.0), (0.0, -0.5))


def _tubo(kind: str) -> Callable[[Glyph], None]:
    def draw(g: Glyph) -> None:
        g.circle(-0.5, -0.3, 0.05)
        g.line((-0.45, -0.28), (0.6, 0.3))
        if kind in ("sobe", "passa"):
            g.line((0.1, 0.0), (0.3, 0.2), (0.35, 0.05))
        if kind in ("desce", "passa"):
            g.line((-0.15, -0.14), (0.05, 0.06), (-0.1, -0.02))
    return draw


def _diametro(g: Glyph) -> None:
    g.circle(0.0, 0.1, 0.25)
    g.line((-0.25, 0.1), (0.25, 0.1))
    g.text("INC", 0.0, 0.18, 0.12)
    g.text("63", 0.0, 0.03, 0.12)
    g.line((-0.1, -0.12), (-0.3, -0.5))


_add("ROTA_DE_FUGA_DIRECAO_FLUXO", "DIREÇÃO DO FLUXO", "ROTAS DE FUGA", "DIRECIONAMENTO", 12,
     "ROTAS", "SINALIZACAO", _rota(False), 1.0)
_add("ROTA_DE_FUGA_FINAL", "SAÍDA FINAL", "ROTAS DE FUGA", "DIRECIONAMENTO", 12, "ROTAS",
     "SAIDA", _rota(True), 1.0)
_add("REGISTRO_VALVULA", "REGISTRO", "OUTROS", "", 12, "TUBULACAO", None, _registro, 0.6)
_add("TANQUE_PRESSAO", "TANQUE DE PRESSÃO", "OUTROS", "", 12, "TUBULACAO", None,
     _tanque_pressao)
_add("MANOMETRO", "MANÔMETRO", "OUTROS", "", 12, "TUBULACAO", None, _manometro)
_add("PRESSOSTATO", "PRESSOSTATO", "OUTROS", "", 12, "TUBULACAO", None, _pressostato)
_add("TUBO_SOBE", "TUBO QUE SOBE", "OUTROS", "", 12, "TUBULACAO", None, _tubo("sobe"), 0.8)
_add("TUBO_DESCE", "TUBO QUE DESCE", "OUTROS", "", 12, "TUBULACAO", None, _tubo("desce"), 0.8)
_add("TUBO_PASSA", "TUBO QUE PASSA", "OUTROS", "", 12, "TUBULACAO", None, _tubo("passa"), 0.8)
_add("DIAMETRO_CANALIZACAO", "REPRESENTAÇÃO DO DIÂMETRO DA CANALIZAÇÃO", "OUTROS", "", 12,
     "TUBULACAO", None, _diametro)

# 13. Placas da NT 2-05 (esquemáticas) -------------------------------------------------------------

_PLACAS: tuple[tuple[str, str], ...] = (
    ("P-1", "Proibido fumar"), ("P-2", "Proibido produzir chama"),
    ("P-3", "Proibido utilizar água para apagar o fogo"),
    ("P-4", "Proibido utilizar elevador em caso de incêndio"),
    ("P-5", "Proibido obstruir este local"),
    ("A-1", "Alerta geral"), ("A-2", "Cuidado, risco de incêndio"),
    ("A-3", "Cuidado, risco de explosão"), ("A-4", "Cuidado, risco de corrosão"),
    ("A-5", "Cuidado, risco de choque elétrico"), ("A-6", "Cuidado, risco de radiação"),
    ("A-7", "Cuidado, risco de exposição a produtos tóxicos"),
    *((f"S-{n}", "Orientação do sentido da saída de emergência") for n in range(1, 8)),
    *((f"S-{n}", "Orientação do sentido da escada de emergência") for n in range(8, 12)),
    ("S-12", "Saída de emergência"),
    ("S-13-D", "Orientação do sentido da saída de emergência (direita)"),
    ("S-13-E", "Orientação do sentido da saída de emergência (esquerda)"),
    ("S-14", "Saída de emergência"),
    ("S-15-D", "Orientação do sentido de saídas de emergência acessíveis (direita)"),
    ("S-15-E", "Orientação do sentido de saídas de emergência acessíveis (esquerda)"),
    ("S-16-D", "Orientação do sentido de saídas de emergência acessíveis (direita)"),
    ("S-16-E", "Orientação do sentido de saídas de emergência acessíveis (esquerda)"),
    ("S-17", "Número do pavimento"),
    ("S-18", "Instrução de abertura de porta por barra antipânico"),
    ("S-19", "Instruções para porta corta-fogo (mantida fechada)"),
    ("S-20", "Instruções para porta corta-fogo (casos da NBR 11742)"),
    ("S-21", "Acesso a um dispositivo para abertura de porta de saída de emergência"),
    ("S-22", "Mecanismo de abertura de porta de saída de emergência"),
    ("S-23", "Elevador de emergência"), ("S-24", "Ponto de encontro"),
    ("E-1", "Alarme sonoro"), ("E-2", "Comando manual de alarme de incêndio"),
    ("E-3", "Comando manual de bomba de incêndio"),
    ("E-4", "Telefone ou interfone de emergência"), ("E-5", "Extintor de incêndio"),
    ("E-6", "Mangotinho"), ("E-7", "Abrigo de mangueira e hidrante"),
    ("E-8", "Hidrante de incêndio"),
    ("E-9", "Conjunto de equipamentos de combate a incêndio"),
    ("E-10", "Válvula de controle do sistema de chuveiros automáticos"),
    ("E-11", "Extintor de incêndio sobre rodas"),
    ("E-12", "Manta para abafamento de chamas em pessoas"),
    ("E-13", "Seta à esquerda, localização de equipamentos de combate a incêndio ou alarme"),
    ("E-14", "Seta à direita, localização de equipamentos de combate a incêndio ou alarme"),
    ("E-15", "Seta diagonal à esquerda, localização de equipamentos de combate a incêndio "
              "ou alarme"),
    ("E-16", "Seta diagonal à direita, localização de equipamentos de combate a incêndio "
              "ou alarme"),
    ("E-17", "Sinalização de solo para equipamentos de combate a incêndio (hidrante e "
              "extintores)"),
)
_PLACA_PAG = {"P": 8, "A": 9, "S": 10, "E": 14}


def _placa(code: str) -> Callable[[Glyph], None]:
    kind = code[0]
    n = int(code.split("-")[1])
    red, yellow, green = 1, 2, 3

    def draw(g: Glyph) -> None:
        if kind == "P":  # circular: faixa e barra diametral vermelhas
            g.circle(0.0, 0.0, 0.5, c=red)
            g.circle(0.0, 0.0, 0.4, c=red)
            d = 0.5 * math.cos(math.radians(45))
            g.line((-d, d), (d, -d), c=red)
            g.text(code, 0.0, 0.0, 0.2)
        elif kind == "A":  # triangular, faixa preta
            g.poly((-0.55, -0.4), (0.55, -0.4), (0.0, 0.55))
            g.poly((-0.45, -0.34), (0.45, -0.34), (0.0, 0.43))
            g.text(code, 0.0, -0.12, 0.2)
        elif kind == "S":  # retangular verde
            g.fill(*rect(-0.5, -0.3, 0.5, 0.3), c=green)
            g.text(code, 0.0, 0.0, 0.22)
        elif code == "E-17":  # solo: 1,00 m com 0,70 m vermelho e borda amarela de 0,15 m
            g.fill(*rect(-0.5, -0.5, 0.5, 0.5), c=yellow)
            g.fill(*rect(-0.35, -0.35, 0.35, 0.35), c=red)
        else:  # equipamentos: quadrada vermelha
            g.fill(*rect(-0.4, -0.4, 0.4, 0.4), c=red)
            g.text(code, 0.0, 0.0, 0.22 if n < 10 else 0.2)
            if code in ("E-13", "E-14", "E-15", "E-16"):
                ang = {"E-13": 180, "E-14": 0, "E-15": 135, "E-16": 45}[code]
                dx, dy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                arrow(g, (-dx * 0.2, -dy * 0.2 + 0.18), (dx * 0.28, dy * 0.28 + 0.18), c=7)
    return draw


def _placa_glyph(code: str) -> Callable[[], Glyph]:
    def build() -> Glyph:
        g = Glyph()
        _placa(code)(g)
        return g

    return build


for _code, _nome in _PLACAS:
    _id = f"PICTO_{_code}"
    _grupo = {"P": "PROIBIÇÃO", "A": "ALERTA", "S": "ORIENTAÇÃO E SALVAMENTO",
              "E": "EQUIPAMENTOS DE COMBATE A INCÊNDIO E ALARME"}[_code[0]]
    CATALOGO[_id] = Entrada(
        _id, f"{_code} - {_nome}", f"PLACAS NT 2-05: {_grupo}", "", P2_05, _PLACA_PAG[_code[0]],
        "SINALIZACAO", "SINALIZACAO", _placa_glyph(_code), 1.0 if _code == "E-17" else 0.4,
        esquematico=True, extra_classes=("SAIDA",) if _code in ("S-12", "S-14") else ())


# --- consulta -----------------------------------------------------------------------------------

_ALIASES: dict[str, str] = {}
for _e in CATALOGO.values():
    _ALIASES[_e.id.upper()] = _e.id
    if _e.id.startswith("PICTO_"):
        _ALIASES[_e.id[6:].upper()] = _e.id


def achar(chave: str) -> Entrada | None:
    """Entrada pelo id (nome do bloco) ou, para placas, pelo código ("E-5")."""
    return CATALOGO.get(_ALIASES.get(chave.strip().upper(), ""))


def listar(grupo: str | None = None, busca: str | None = None,
           placas: bool = True) -> list[Entrada]:
    out = []
    for e in CATALOGO.values():
        if not placas and e.esquematico:
            continue
        if grupo and grupo.casefold() not in f"{e.grupo} {e.subgrupo}".casefold():
            continue
        if busca and busca.casefold() not in f"{e.id} {e.nome}".casefold():
            continue
        out.append(e)
    return out


def grupos() -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in CATALOGO.values():
        counts[e.grupo] = counts.get(e.grupo, 0) + 1
    return counts
