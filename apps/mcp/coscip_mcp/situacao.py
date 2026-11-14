"""Planta de situação (frente F, 13/11/2026).

Desenha, numa região própria do model space e na escala dela (1:500 é o comum nas pranchas
analisadas; 1:250 quando o lote é pequeno), o que as plantas de situação dos projetos de
referência mostram:

- o **lote** em traço grosso, com as medidas de cada lado;
- as **edificações** dentro dele, hachuradas, com nome opcional e setas de caimento do telhado;
- as **ruas**: leito entre dois meios-fios (paralelas ao eixo), esquinas arredondadas, linha
  de interrupção nas pontas e o nome escrito ao longo da rua;
- **distâncias** cotadas (até a esquina mais próxima, recuo, largura da rua) e textos soltos
  ("ALINHAMENTO", "RECUO 5,00");
- a **seta do norte** e o título com a escala.

Tudo o que é medida vem do usuário (lote, ruas, distância à esquina, norte); o motor não
supõe nada. As coordenadas são em metros no sistema da planta: desenhe a situação longe da
planta baixa, como os cortes.
"""

from __future__ import annotations

import math
from typing import Annotated, Any, Literal

from ezdxf.enums import TextEntityAlignment
from pydantic import BaseModel, ConfigDict, Field
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from coscip_mcp import apresentacao

Ponto = Annotated[list[float], Field(min_length=2, max_length=2)]

CAMADAS = ("SITUACAO_LOTE", "SITUACAO_EDIF", "SITUACAO_RUA", "SITUACAO_TEXTO", "SITUACAO_COTA",
           "NORTE")


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EdificacaoSit(_M):
    poligono: list[Ponto] = Field(min_length=3, max_length=200)
    rotulo: str = Field(default="", max_length=40, description="ex. BLOCO A, ÁREA COBERTA")
    caimentos: list[Annotated[list[float], Field(min_length=3, max_length=3)]] = Field(
        default_factory=list, max_length=20,
        description="setas de caimento do telhado: [x, y, ângulo em graus da seta]")


class Rua(_M):
    nome: str = Field(min_length=1, max_length=60)
    eixo: list[Ponto] = Field(min_length=2, max_length=50)
    largura_m: float = Field(gt=2, le=80, description="largura entre os meios-fios (leito)")
    calcada_m: float = Field(default=0.0, ge=0, le=15,
                             description="calçada desenhada além do meio-fio (0 = não desenhar)")


class Distancia(_M):
    a: Ponto
    b: Ponto
    deslocamento_m: float = Field(default=0.0, description="afasta a linha de cota da medida")


class TextoSit(_M):
    texto: str = Field(min_length=1, max_length=60)
    x: float
    y: float
    graus: float = 0.0


class Situacao(_M):
    tipo: Literal["situacao"]
    escala: int = Field(default=500, ge=100, le=2000,
                        description="denominador da impressão da situação (texto e cotas)")
    lote: list[Ponto] = Field(min_length=3, max_length=200)
    edificacoes: list[EdificacaoSit] = Field(default_factory=list, max_length=30)
    ruas: list[Rua] = Field(default_factory=list, max_length=12)
    raio_esquina_m: float = Field(default=4.0, ge=0, le=20)
    distancias: list[Distancia] = Field(default_factory=list, max_length=20)
    textos: list[TextoSit] = Field(default_factory=list, max_length=30)
    cotar_lote: bool = True
    norte_graus: float | None = Field(default=None, description="direção do norte medida a partir "
                                      "do eixo +y, no sentido anti-horário; None = sem seta")
    norte_xy: Ponto | None = Field(default=None, description="posição da seta; sem ela, à direita "
                                   "do lote")
    titulo: str = Field(default="", max_length=60, description="título no model space; vazio "
                        "quando a folha já dá o título da vista")


def _txt(msp, s: str, x: float, y: float, h: float, camada: str, rot: float = 0.0,  # noqa: ANN001
         centro: bool = True) -> None:
    t = msp.add_text(s, dxfattribs={"layer": camada, "height": h, "rotation": rot,
                                     "style": apresentacao.ESTILO_TEXTO})
    t.set_placement((x, y), align=TextEntityAlignment.MIDDLE_CENTER if centro
                    else TextEntityAlignment.LEFT)


def _legivel(graus: float) -> float:
    g = (graus + 180) % 360 - 180
    if g > 90:
        g -= 180
    elif g <= -90:
        g += 180
    return g


def _cota(msp, a: tuple[float, float], b: tuple[float, float], dist: float,  # noqa: ANN001
          escala: int) -> None:
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 360
    if 90 < ang <= 270:  # texto de cabeça para baixo: inverte o sentido e o lado
        a, b, dist = b, a, -dist
    d = msp.add_aligned_dim(p1=a, p2=b, distance=dist,
                            dimstyle=apresentacao.dimstyle_nome(escala),
                            dxfattribs={"layer": "SITUACAO_COTA"})
    d.render()


def _quebra(msp, p: tuple[float, float], q: tuple[float, float], f: float) -> None:  # noqa: ANN001
    """Linha de interrupção entre p e q (passa um pouco além), com o 'raio' no meio."""
    ux, uy = q[0] - p[0], q[1] - p[1]
    n = math.hypot(ux, uy)
    ux, uy = ux / n, uy / n
    nx, ny = -uy, ux
    ext = 0.8 * f
    a = (p[0] - ux * ext, p[1] - uy * ext)
    b = (q[0] + ux * ext, q[1] + uy * ext)
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    z = 0.9 * f
    pts = [a, (mx - ux * z * 0.3, my - uy * z * 0.3),
           (mx - ux * z * 0.1 + nx * z, my - uy * z * 0.1 + ny * z),
           (mx + ux * z * 0.1 - nx * z, my + uy * z * 0.1 - ny * z),
           (mx + ux * z * 0.3, my + uy * z * 0.3), b]
    msp.add_lwpolyline(pts, dxfattribs={"layer": "SITUACAO_RUA"})


def _bloco_norte(doc) -> str:  # noqa: ANN001
    """Bloco NORTE de raio 1 (círculo, seta meio cheia e a letra N), apontando para +y."""
    if "NORTE" in doc.blocks:
        return "NORTE"
    b = doc.blocks.new("NORTE")
    b.add_circle((0, 0), 1.0, dxfattribs={"layer": "0"})
    ponta, esq, dir_ = (0, 1.25), (-0.45, -0.6), (0.45, -0.6)
    h = b.add_hatch(color=0, dxfattribs={"layer": "0"})
    h.set_solid_fill(color=0)
    h.paths.add_polyline_path([ponta, esq, (0, 0)], is_closed=True)
    b.add_lwpolyline([ponta, esq, (0, 0), dir_], close=True, dxfattribs={"layer": "0"})
    t = b.add_text("N", dxfattribs={"layer": "0", "height": 0.65,
                                     "style": apresentacao.ESTILO_TEXTO})
    t.set_placement((0, 2.0), align=TextEntityAlignment.MIDDLE_CENTER)
    return "NORTE"


def _norte(doc, msp, x: float, y: float, graus: float, f: float) -> None:  # noqa: ANN001
    r = 1.4 * f
    msp.add_blockref(_bloco_norte(doc), (x, y), dxfattribs={
        "layer": "NORTE", "xscale": r, "yscale": r, "rotation": graus})


def _seta_caimento(msp, x: float, y: float, graus: float, f: float) -> None:  # noqa: ANN001
    a = math.radians(graus)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    c, w, hd = 1.2 * f, 0.22 * f, 0.5 * f
    p0 = (x - ux * c / 2, y - uy * c / 2)
    p1 = (x + ux * (c / 2 - hd), y + uy * (c / 2 - hd))
    ponta = (x + ux * c / 2, y + uy * c / 2)
    pts = [(p0[0] + nx * w, p0[1] + ny * w), (p1[0] + nx * w, p1[1] + ny * w),
           (p1[0] + nx * 2 * w, p1[1] + ny * 2 * w), ponta,
           (p1[0] - nx * 2 * w, p1[1] - ny * 2 * w), (p1[0] - nx * w, p1[1] - ny * w),
           (p0[0] - nx * w, p0[1] - ny * w)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "SITUACAO_EDIF"})


def desenhar(doc, msp, op: Situacao) -> dict[str, Any]:  # noqa: ANN001
    for c in CAMADAS:
        apresentacao.criar_camada(doc, c)
    esc = op.escala
    apresentacao._estilo_cota(doc, esc)  # noqa: SLF001
    f = apresentacao.fator(esc)  # 5,0 em 1:500
    h = apresentacao.altura_texto(esc)
    lote = Polygon(op.lote)
    if not lote.is_valid or lote.area <= 0:
        raise ValueError("situacao: o polígono do lote é inválido ou não tem área")

    # --- ruas: união das faixas, com esquinas arredondadas ----------------------------------
    faixas, pontas = [], []
    for rua in op.ruas:
        eixo = LineString(rua.eixo)
        faixas.append(eixo.buffer(rua.largura_m / 2, cap_style="flat", join_style="mitre"))
        for i0, i1 in ((0, 1), (-1, -2)):
            (x0, y0), (x1, y1) = rua.eixo[i0], rua.eixo[i1]
            ux, uy = x1 - x0, y1 - y0
            n = math.hypot(ux, uy)
            nx, ny = -uy / n, ux / n
            meia = rua.largura_m / 2 + rua.calcada_m
            pontas.append(((x0 + nx * meia, y0 + ny * meia), (x0 - nx * meia, y0 - ny * meia)))
    if faixas:
        leito = unary_union(faixas)
        if op.raio_esquina_m > 0:  # arredonda os cantos côncavos (meio-fio na esquina)
            leito = leito.buffer(op.raio_esquina_m).buffer(-op.raio_esquina_m)
        bordas = [g.exterior for g in getattr(leito, "geoms", [leito])]
        bordas += [i for g in getattr(leito, "geoms", [leito]) for i in g.interiors]
        cortes = unary_union([LineString(p).buffer(0.05) for p in pontas])
        for anel in bordas:
            resto = LineString(anel.coords).difference(cortes)
            for parte in getattr(resto, "geoms", [resto]):
                if parte.length > 0.1:
                    msp.add_lwpolyline(list(parte.coords), dxfattribs={"layer": "SITUACAO_RUA"})
        for rua in op.ruas:
            if rua.calcada_m > 0:
                calc = LineString(rua.eixo).buffer(rua.largura_m / 2 + rua.calcada_m,
                                                   cap_style="flat", join_style="mitre")
                anel = LineString(calc.exterior.coords).difference(cortes).difference(
                    leito.buffer(rua.calcada_m * 0.5))
                for parte in getattr(anel, "geoms", [anel]):
                    if parte.length > 0.1:
                        msp.add_lwpolyline(list(parte.coords),
                                           dxfattribs={"layer": "SITUACAO_RUA"})
        for p, q in pontas:
            _quebra(msp, p, q, f)
        for rua in op.ruas:  # nome no meio do trecho mais longo do eixo
            segs = list(zip(rua.eixo, rua.eixo[1:], strict=False))
            (ax, ay), (bx, by) = max(segs, key=lambda s: math.dist(s[0], s[1]))
            ang = _legivel(math.degrees(math.atan2(by - ay, bx - ax)))
            _txt(msp, rua.nome.upper(), (ax + bx) / 2, (ay + by) / 2,
                 apresentacao.altura_texto(esc, 3.5), "SITUACAO_TEXTO", rot=ang)

    # --- lote e edificações ----------------------------------------------------------------
    msp.add_lwpolyline(list(lote.exterior.coords), close=True,
                       dxfattribs={"layer": "SITUACAO_LOTE"})
    area_edif = 0.0
    for ed in op.edificacoes:
        pg = Polygon(ed.poligono)
        if not pg.is_valid or pg.area <= 0:
            raise ValueError(f"situacao: edificação {ed.rotulo or '(sem nome)'} inválida")
        if not lote.buffer(0.05).contains(pg):
            raise ValueError(f"situacao: a edificação {ed.rotulo or '(sem nome)'} sai do lote")
        area_edif += pg.area
        pts = list(pg.exterior.coords)
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "SITUACAO_EDIF"})
        hatch = msp.add_hatch(color=8, dxfattribs={"layer": "SITUACAO_EDIF"})
        hatch.set_pattern_fill("ANSI31", color=8, scale=0.06 * f)
        hatch.paths.add_polyline_path(pts[:-1], is_closed=True)
        for x, y, g in ed.caimentos:
            _seta_caimento(msp, x, y, g, f)
        if ed.rotulo:
            c = pg.representative_point()
            _txt(msp, ed.rotulo.upper(), c.x, c.y, h, "SITUACAO_TEXTO")

    if op.cotar_lote:
        coords = list(lote.exterior.coords)
        fora = -1.2 * f if lote.exterior.is_ccw else 1.2 * f  # a cota fica do lado de fora
        for p, q in zip(coords, coords[1:], strict=False):
            if math.dist(p, q) < 0.5:
                continue
            ex, ey = q[0] - p[0], q[1] - p[1]
            n = math.hypot(ex, ey)
            mx, my = (p[0] + q[0]) / 2 - ey / n * fora, (p[1] + q[1]) / 2 + ex / n * fora
            lado = fora
            if faixas and leito.buffer(0.5 * f).contains(Point(mx, my)):
                lado = -fora  # lado voltado para a rua: cota por dentro do lote
            _cota(msp, p, q, lado, esc)
    for dist in op.distancias:
        _cota(msp, tuple(dist.a), tuple(dist.b), dist.deslocamento_m, esc)
    for t in op.textos:
        _txt(msp, t.texto.upper(), t.x, t.y, apresentacao.altura_texto(esc, 2.0),
             "SITUACAO_TEXTO", rot=t.graus)

    x0, y0, x1, y1 = lote.bounds
    if op.norte_graus is not None:
        nx_, ny_ = op.norte_xy or (x1 + 6.0 * f, y1 - 3.0 * f)
        _norte(doc, msp, nx_, ny_, op.norte_graus, f)

    # título: abaixo de tudo o que foi desenhado (lote e ruas)
    base_y, cx = y0, x0
    if faixas:
        base_y = min(base_y, leito.bounds[1])
        cx = min(cx, leito.bounds[0])
    if op.titulo:
        _txt(msp, op.titulo.upper(), cx, base_y - 4.0 * f, apresentacao.altura_texto(
            esc, apresentacao.TEXTO_TITULO_MM), "SITUACAO_TEXTO", centro=False)
        _txt(msp, f"ESCALA 1:{esc}", cx, base_y - 5.2 * f, h, "SITUACAO_TEXTO", centro=False)
    return {"escala": f"1:{esc}", "area_do_lote_m2": round(lote.area, 2),
            "area_projecao_edificacoes_m2": round(area_edif, 2),
            "taxa_de_ocupacao": round(area_edif / lote.area, 3), "ruas": len(op.ruas),
            "norte": op.norte_graus is not None,
            "premissas": ["lote, ruas, larguras, distâncias e norte como informados pelo "
                          "usuário; o desenho não confere com levantamento ou RGI"]}


__all__ = ["Situacao", "desenhar"]
