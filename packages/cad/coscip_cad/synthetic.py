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


TRAPS = ("minsert", "camada", "duplicado", "saida", "aninhado", "explodido", "xref",
         "atributo", "legenda")


def make_trap(path: Path, kind: str) -> Path:
    """Planta 20×10 m com UMA armadilha de reconhecimento (plano de correção, F5.4).

    Paredes no layer PAREDE e um extintor de referência em (2, 2) em todas; o resto depende
    de ``kind`` (ver ``TRAPS``). Os testes afirmam a contagem exata e o motivo de cada
    elemento ignorado.
    """
    if kind not in TRAPS:
        raise ValueError(f"armadilha desconhecida: {kind}")
    doc = ezdxf.new("R2018", setup=True)
    doc.header["$INSUNITS"] = 6
    for name in ("PAREDE", "INC_EXT", "INC_SAIDA", "SINALIZACAO", "TEXTOS", "LEGENDA",
                 "INC_OFF", "INC_CONGELADA", "INC_NAO_PLOTA", "INC_DIVERSOS"):
        doc.layers.add(name)
    ext = doc.blocks.new("EXTINTOR_PQS_ABC")
    ext.add_circle((0, 0), 0.2, dxfattribs={"layer": "INC_EXT"})
    msp = doc.modelspace()
    for a, b in (((0, 0), (20, 0)), ((20, 0), (20, 10)), ((20, 10), (0, 10)), ((0, 10), (0, 0))):
        msp.add_line(a, b, dxfattribs={"layer": "PAREDE"})
    msp.add_blockref("EXTINTOR_PQS_ABC", (2, 2), dxfattribs={"layer": "INC_EXT"})

    if kind == "minsert":  # matriz 3×4 = 12 extintores em uma entidade
        ref = msp.add_blockref("EXTINTOR_PQS_ABC", (5, 3), dxfattribs={"layer": "INC_EXT"})
        ref.grid(size=(3, 4), spacing=(2.0, 3.0))  # linhas × colunas; (dy, dx)
    elif kind == "camada":  # desligada, congelada e não plotável: nada disso é desenho
        doc.layers.get("INC_OFF").off()
        doc.layers.get("INC_CONGELADA").freeze()
        doc.layers.get("INC_NAO_PLOTA").dxf.plot = 0
        for x, layer in ((6, "INC_OFF"), (8, "INC_CONGELADA"), (10, "INC_NAO_PLOTA")):
            msp.add_blockref("EXTINTOR_PQS_ABC", (x, 5), dxfattribs={"layer": layer})
        msp.add_text("SAÍDA", dxfattribs={"layer": "INC_OFF", "height": 0.25}).set_placement(
            (12, 1))
    elif kind == "duplicado":  # cópia no mesmo ponto e a 3 cm: um objeto; a 1 m: outro
        for x, y in ((8, 5), (8, 5), (8.03, 5)):
            msp.add_blockref("EXTINTOR_PQS_ABC", (x, y), dxfattribs={"layer": "INC_EXT"})
        msp.add_blockref("EXTINTOR_PQS_ABC", (9, 5), dxfattribs={"layer": "INC_EXT"})
    elif kind == "saida":  # bloco de saída + texto SAÍDA + placa S-12 na mesma porta
        sai = doc.blocks.new("SAIDA_EMERGENCIA")
        sai.add_line((-0.5, 0), (0.5, 0), dxfattribs={"layer": "INC_SAIDA"})
        s12 = doc.blocks.new("PLACA_S-12")
        s12.add_lwpolyline([(0, 0), (0.3, 0), (0.3, 0.15), (0, 0.15)], close=True,
                           dxfattribs={"layer": "SINALIZACAO"})
        msp.add_blockref("SAIDA_EMERGENCIA", (10, 0.1), dxfattribs={"layer": "INC_SAIDA"})
        msp.add_text("SAÍDA", dxfattribs={"layer": "INC_SAIDA", "height": 0.25}).set_placement(
            (10.2, 0.6))
        msp.add_blockref("PLACA_S-12", (9.7, 0.3), dxfattribs={"layer": "SINALIZACAO"})
    elif kind == "aninhado":  # bloco desconhecido dentro de desconhecido, em camada de incêndio
        sub = doc.blocks.new("SUB_Y")
        sub.add_circle((0, 0), 0.2, dxfattribs={"layer": "INC_DIVERSOS"})
        grp = doc.blocks.new("GRUPO_X")
        grp.add_line((0, 0), (1, 0), dxfattribs={"layer": "TEXTOS"})
        grp.add_blockref("SUB_Y", (0.5, 0.5), dxfattribs={"layer": "INC_DIVERSOS"})
        msp.add_blockref("GRUPO_X", (10, 5), dxfattribs={"layer": "TEXTOS"})
    elif kind == "explodido":  # extintor desenhado com linhas soltas + texto de agente
        msp.add_circle((10, 5), 0.2, dxfattribs={"layer": "INC_EXT"})
        msp.add_text("PQS 6KG", dxfattribs={"layer": "INC_EXT", "height": 0.2}).set_placement(
            (10.3, 5))
    elif kind == "xref":  # conteúdo em arquivo externo: ausente desta planta
        doc.add_xref_def("arquitetura.dwg", "ARQ_XREF")
        msp.add_blockref("ARQ_XREF", (0, 0), dxfattribs={"layer": "TEXTOS"})
    elif kind == "atributo":  # ATTRIB com agente e rótulo "SAÍDA" que é atributo, não texto
        tag = doc.blocks.new("EXTINTOR_TAG")
        tag.add_circle((0, 0), 0.2, dxfattribs={"layer": "INC_EXT"})
        tag.add_attdef("AGENTE", (0.3, 0), dxfattribs={"height": 0.15})
        tag.add_attdef("OBS", (0.3, -0.3), dxfattribs={"height": 0.15})
        ref = msp.add_blockref("EXTINTOR_TAG", (10, 5), dxfattribs={"layer": "INC_EXT"})
        ref.add_auto_attribs({"AGENTE": "CO2 6KG", "OBS": "SAÍDA"})
    elif kind == "legenda":  # quadro de simbologia marcado pelo analista (sem título)
        for i in range(2):
            msp.add_blockref("EXTINTOR_PQS_ABC", (30, 8 - i), dxfattribs={"layer": "LEGENDA"})
    doc.saveas(path)
    return path


ANALYTIC = ("corredor_l", "pilar", "duas_portas")


def make_analytic(path: Path, kind: str) -> tuple[Path, float, tuple[float, float]]:
    """Planta com a maior distância percorrida conhecida analiticamente (F7).

    Paredes em linha simples (espessura zero: o domínio é exato) no layer PAREDE e UM
    extintor pequeno (círculo de 5 cm). Devolve (arquivo, distância exata, pior ponto).
    """
    import math

    doc = ezdxf.new("R2018", setup=True)
    doc.header["$INSUNITS"] = 6
    for name in ("PAREDE", "INC_EXT"):
        doc.layers.add(name)
    ext = doc.blocks.new("EXTINTOR_PQS_ABC")
    ext.add_circle((0, 0), 0.05, dxfattribs={"layer": "INC_EXT"})
    msp = doc.modelspace()

    def poly(pts: list[tuple[float, float]], close: bool = True) -> None:
        # Cada lado em trechos de até 1 m (LINEs colineares, como sai de muitos desenhos):
        # a detecção de paredes pede um mínimo de segmentos e o grafo ignora os colineares.
        ring = [*pts, pts[0]] if close else pts
        for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False):
            n = max(1, math.ceil(math.dist((x1, y1), (x2, y2))))
            for i in range(n):
                a = (x1 + (x2 - x1) * i / n, y1 + (y2 - y1) * i / n)
                b = (x1 + (x2 - x1) * (i + 1) / n, y1 + (y2 - y1) * (i + 1) / n)
                msp.add_line(a, b, dxfattribs={"layer": "PAREDE"})

    if kind == "corredor_l":
        # L: perna horizontal 20×2 e perna vertical x 18..20 até y 15; extintor em (1, 1)
        poly([(0, 0), (20, 0), (20, 15), (18, 15), (18, 2), (0, 2)])
        src = (1.0, 1.0)
        corner = (18.0, 2.0)
        worst = (20.0, 15.0)
        dist = math.dist(src, corner) + math.dist(corner, worst)
    elif kind == "pilar":
        # sala 10×10, pilar 2×2 no centro; extintor em (0,5; 0,5): o canto (10, 10) fica
        # atrás do pilar e o caminho contorna o canto (4, 6) ou (6, 4)
        poly([(0, 0), (10, 0), (10, 10), (0, 10)])
        poly([(4, 4), (6, 4), (6, 6), (4, 6)])
        src, worst = (0.5, 0.5), (10.0, 10.0)
        dist = math.dist(src, (4.0, 6.0)) + math.dist((4.0, 6.0), worst)
    elif kind == "duas_portas":
        # 20×6 com parede em x = 10 e duas portas de 1 m (y 0,5..1,5 e 4,5..5,5); extintor em
        # (1, 5); o pior ponto é (20, 0), pela porta de baixo (canto (10; 1,5))
        poly([(0, 0), (20, 0), (20, 6), (0, 6)])
        for a, b in (((10, 0), (10, 0.5)), ((10, 1.5), (10, 4.5)), ((10, 5.5), (10, 6))):
            poly([a, b], close=False)
        src, worst = (1.0, 5.0), (20.0, 0.0)
        dist = min(math.dist(src, (10, 1.5)) + math.dist((10, 1.5), worst),
                   math.dist(src, (10, 4.5)) + math.dist((10, 4.5), worst))
    else:
        raise ValueError(f"planta analítica desconhecida: {kind}")
    msp.add_blockref("EXTINTOR_PQS_ABC", src, dxfattribs={"layer": "INC_EXT"})
    doc.saveas(path)
    return path, dist, worst
