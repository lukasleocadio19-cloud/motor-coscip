"""Modelo da edificação e vistas derivadas da planta: cortes e fachadas (frente D5, §9).

A planta que a IA descreve (salas, paredes, portas, janelas, mobiliário) ganha altura por uma
operação ``edificacao`` (pé-direito, laje, platibanda e volumes como dutos e abrigos). Daí saem
vistas **coerentes com a planta**, porque vêm da mesma geometria:

- ``secao``: corte por uma linha da planta. Paredes, lajes e volumes cortados saem hachurados;
  os vãos cortados mostram verga e peitoril; o que está além do plano (móveis, equipamentos,
  extintores, luminárias) sai em traço fino dentro de uma profundidade de vista; cotas de altura e
  em cadeia e marcas de nível.
- ``fachada``: elevação de um dos quatro lados, a partir das arestas externas da edificação:
  paredes, portas e janelas nas posições da planta, platibanda e volumes que passam do telhado.

Limites, para não prometer o que não há: sem remoção de linhas ocultas (o que está atrás de uma
parede cortada pode aparecer); sem telhado inclinado, escadas em corte, estrutura nem
esquadrias detalhadas; a altura é uma só para todos os pavimentos desenhados (um pavimento por
planta); a fachada trata cada aresta externa como plano único (sem recuos de profundidade).
Alturas e peitoris são informados pelo usuário, nunca supostos.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

from ezdxf.enums import TextEntityAlignment
from pydantic import BaseModel, ConfigDict, Field
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.base import BaseGeometry

from coscip_mcp import apresentacao

PISO_M = 0.10  # espessura do piso desenhada abaixo do nível 0,00
Retangulo = Annotated[list[float], Field(min_length=4, max_length=4)]


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Volume(_M):
    """Volume vertical fora do que a planta mostra: duto de exaustão, abrigo, caixa d'água..."""

    nome: str = Field(min_length=1, max_length=40)
    retangulo: Retangulo = Field(description="[x0, y0, x1, y1] na planta, em metros")
    base_m: float = Field(default=0.0, ge=0, le=100)
    topo_m: float = Field(gt=0, le=100)
    tracejado: bool = False  # projeção (ex. coifa): traço tracejado, sem hachura


class Cobertura(_M):
    """Telhado inclinado sobre a laje/forro (medidas do usuário).

    ``uma_agua``: o plano cai para ``caimento`` (o lado mais baixo). ``duas_aguas``: a cumeeira
    corre ao longo do eixo ``cumeeira`` ("x" ou "y") pelo meio da pegada. A inclinação vale em
    toda a cobertura; o beiral avança além das paredes no sentido do caimento."""

    tipo: Literal["uma_agua", "duas_aguas"]
    inclinacao_pct: float = Field(ge=2.0, le=100.0, description="ex. 10 para telha metálica")
    caimento: Literal["norte", "sul", "leste", "oeste"] = "sul"
    cumeeira: Literal["x", "y"] = "x"
    beiral_m: float = Field(default=0.50, ge=0, le=3.0)
    espessura_m: float = Field(default=0.06, gt=0.01, le=0.5)
    telha: str = Field(default="", max_length=60,
                       description="chamada da telha nos cortes, ex. TELHA TRAPEZOIDAL DE AÇO")


class Edificacao(_M):
    """Alturas da edificação, informadas pelo usuário (o motor não as supõe)."""

    tipo: Literal["edificacao"]
    pe_direito_m: float = Field(ge=2.0, le=20.0)
    laje_m: float = Field(default=0.20, gt=0.05, le=1.0)
    platibanda_m: float = Field(default=0.0, ge=0, le=3.0, description="0 = sem platibanda")
    volumes: list[Volume] = Field(default_factory=list, max_length=40)
    cobertura: Cobertura | None = Field(default=None, description="telhado inclinado; sem ela, "
                                        "cobertura plana (laje)")
    forro: str = Field(default="", max_length=40,
                       description="chamada do forro nos cortes, ex. FORRO DE GESSO")


class Secao(_M):
    """Corte pela linha ``a`` -> ``b`` da planta, desenhado com o piso (cota 0,00) em ``x, y``."""

    tipo: Literal["secao"]
    nome: str = Field(min_length=1, max_length=3)
    a: Annotated[list[float], Field(min_length=2, max_length=2)]
    b: Annotated[list[float], Field(min_length=2, max_length=2)]
    sentido: Literal["esquerda", "direita"] = "esquerda"
    x: float
    y: float
    profundidade_m: float = Field(default=4.0, gt=0, le=60,
                                  description="até onde, além do plano, mostrar o que se vê")
    marca_na_planta: bool = True
    figura_humana: bool = Field(default=True, description="silhueta de 1,70 m para dar escala, "
                                "num vão livre do corte")
    classe_parede: str = Field(default="", max_length=6, pattern=r"^(|I|II-A|II-B|III-A|III-B|"
                               r"IV-A|IV-B|V-A|V-B|VI)$",
                               description="classe de reação ao fogo do revestimento das paredes "
                               "(NT 2-20) informada pelo usuário: rótulo PAREDE CLASSE nos vãos")


class Fachada(_M):
    tipo: Literal["fachada"]
    lado: Literal["sul", "norte", "leste", "oeste"]
    x: float
    y: float
    letreiro: str = Field(default="", max_length=40,
                          description="texto da testeira (nome do estabelecimento), se houver")


# --- modelo (preenchido pelo autoria.py) ---------------------------------------------------


@dataclass
class Abertura:
    tipo: str  # porta | janela
    poly: BaseGeometry
    x: float
    y: float
    largura: float
    angulo: float
    base: float  # 0 na porta, peitoril na janela
    altura: float


@dataclass
class Peca:
    nome: str
    poly: BaseGeometry
    base: float
    topo: float
    classe: str  # mobiliario | volume | extintor | luz
    tracejado: bool = False


@dataclass
class Modelo:
    paredes: BaseGeometry  # paredes já com os vãos recortados
    pegada: Polygon  # contorno externo da edificação
    aberturas: list[Abertura] = field(default_factory=list)
    pecas: list[Peca] = field(default_factory=list)
    edif: Edificacao | None = None

    @property
    def h_forro(self) -> float:
        assert self.edif is not None  # noqa: S101
        return self.edif.pe_direito_m

    @property
    def h_laje(self) -> float:
        assert self.edif is not None  # noqa: S101
        return self.edif.pe_direito_m + self.edif.laje_m

    @property
    def h_topo(self) -> float:
        assert self.edif is not None  # noqa: S101
        return self.h_laje + self.edif.platibanda_m


    # --- telhado ------------------------------------------------------------------------------
    def regiao_cobertura(self) -> tuple[float, float, float, float] | None:
        """Retângulo da cobertura em planta (pegada + beiral), ou None sem telhado."""
        if self.edif is None or self.edif.cobertura is None or self.pegada.is_empty:
            return None
        b = self.edif.cobertura.beiral_m
        x0, y0, x1, y1 = self.pegada.bounds
        return (x0 - b, y0 - b, x1 + b, y1 + b)

    def z_telhado(self, x: float, y: float) -> float:
        """Cota da face inferior do telhado no ponto (x, y): o plano passa pela laje (topo das
        paredes) na linha das paredes do lado baixo."""
        assert self.edif is not None and self.edif.cobertura is not None  # noqa: S101
        c = self.edif.cobertura
        s = c.inclinacao_pct / 100.0
        x0, y0, x1, y1 = self.pegada.bounds
        z0 = self.h_laje
        if c.tipo == "uma_agua":
            dist = {"sul": y - y0, "norte": y1 - y, "oeste": x - x0, "leste": x1 - x}[c.caimento]
            return z0 + s * dist
        if c.cumeeira == "x":
            meia, d = (y1 - y0) / 2, abs(y - (y0 + y1) / 2)
        else:
            meia, d = (x1 - x0) / 2, abs(x - (x0 + x1) / 2)
        return z0 + s * (meia - d)

    def z_cumeeira(self) -> float:
        r = self.regiao_cobertura()
        if r is None:
            return self.h_topo
        x0, y0, x1, y1 = self.pegada.bounds
        pts = [(x0, y0), (x1, y0), (x0, y1), (x1, y1), ((x0 + x1) / 2, (y0 + y1) / 2)]
        assert self.edif is not None and self.edif.cobertura is not None  # noqa: S101
        return max(self.z_telhado(*p) for p in pts) + self.edif.cobertura.espessura_m

    def z_maximo(self) -> float:
        return max(self.h_topo, self.z_cumeeira())


def _fmt(v: float) -> str:
    return f"{v:.2f}".replace(".", ",")


# silhueta humana de 1,70 m (metade direita, de cima para baixo; espelhada para fechar)
_SILHUETA_DIR = [(0.06, 1.49), (0.20, 1.44), (0.24, 1.30), (0.26, 0.86), (0.21, 0.86),
                 (0.19, 1.18), (0.17, 0.92), (0.15, 0.0), (0.04, 0.0), (0.02, 0.80), (0.0, 0.82)]
SILHUETA_LARGURA_M = 0.52


def figura_humana(msp, x: float, y: float, camada: str = "VISTA_ESCALA") -> None:  # noqa: ANN001
    """Silhueta humana de 1,70 m com os pés em (x, y): dá a escala do corte (todas as pranchas
    de referência analisadas usam uma)."""
    meia = [(x + px, y + pz) for px, pz in _SILHUETA_DIR]
    outra = [(x - px, y + pz) for px, pz in reversed(_SILHUETA_DIR[:-1])]
    msp.add_lwpolyline(meia + outra, close=True, dxfattribs={"layer": camada})
    msp.add_circle((x, y + 1.60), 0.11, dxfattribs={"layer": camada})


ROTULO_CLASSE_MM = 1.8


def rotulo_classe_dims(escala: int) -> tuple[float, float]:
    """Largura e altura (m) da moldura do rótulo de classe de material."""
    h = apresentacao.altura_texto(escala, ROTULO_CLASSE_MM)
    return 8.2 * h, 3.0 * h


def rotulo_classe(msp, x: float, y: float, elemento: str, classe: str, escala: int,  # noqa: ANN001
                  camada: str = "ROTULO_CLASSE") -> tuple[float, float, float, float]:
    """Rótulo de controle de materiais de acabamento (NT 2-20) como nas pranchas analisadas:
    moldura com ``ELEMENTO`` / ``CLASSE`` e a classe logo abaixo. Centro da moldura em (x, y).
    Devolve a caixa ocupada (x0, y0, x1, y1), classe incluída."""
    h = apresentacao.altura_texto(escala, ROTULO_CLASSE_MM)
    w, hb = rotulo_classe_dims(escala)
    msp.add_lwpolyline([(x - w / 2, y - hb / 2), (x + w / 2, y - hb / 2), (x + w / 2, y + hb / 2),
                        (x - w / 2, y + hb / 2)], close=True, dxfattribs={"layer": camada})
    for s, dy in ((elemento.upper(), 0.65 * h), ("CLASSE", -0.65 * h), (classe, -2.3 * h)):
        t = msp.add_text(s, dxfattribs={"layer": camada, "height": h,
                                         "style": apresentacao.ESTILO_AMBIENTE})
        t.set_placement((x, y + dy), align=TextEntityAlignment.MIDDLE_CENTER)
    return (x - w / 2, y - 2.9 * h, x + w / 2, y + hb / 2)


class _Desenho:
    """Escreve no model space em coordenadas locais (u para a direita, z para cima) a partir de
    ``(x, y)``, na escala de impressão da planta."""

    def __init__(self, doc, msp, x: float, y: float, escala: int) -> None:  # noqa: ANN001
        self.doc, self.msp, self.x, self.y, self.escala = doc, msp, x, y, escala
        self.f = apresentacao.fator(escala)
        for nome in ("VISTA_CORTE", "VISTA_CONTORNO", "VISTA_AUX", "VISTA_ESQ", "VISTA_COTA",
                     "VISTA_TEXTO", "VISTA_INCENDIO", "VISTA_ILUM", "VISTA_PORTA",
                     "VISTA_COBERTURA", "VISTA_ESCALA", "ROTULO_CLASSE"):
            apresentacao.criar_camada(doc, nome)

    def P(self, u: float, z: float) -> tuple[float, float]:
        return (self.x + u, self.y + z)

    def linha(self, u0: float, z0: float, u1: float, z1: float, camada: str = "VISTA_CONTORNO",
              dash: bool = False) -> None:
        attrs: dict[str, Any] = {"layer": camada}
        if dash:
            attrs["linetype"] = "DASHED"
        self.msp.add_line(self.P(u0, z0), self.P(u1, z1), dxfattribs=attrs)

    def caixa(self, u0: float, z0: float, u1: float, z1: float, camada: str = "VISTA_CONTORNO",
              hachura: bool = False, dash: bool = False) -> None:
        pts = [self.P(u0, z0), self.P(u1, z0), self.P(u1, z1), self.P(u0, z1)]
        attrs: dict[str, Any] = {"layer": camada}
        if dash:
            attrs["linetype"] = "DASHED"
        self.msp.add_lwpolyline(pts, close=True, dxfattribs=attrs)
        if hachura:
            h = self.msp.add_hatch(color=7, dxfattribs={"layer": "VISTA_CORTE"})
            h.set_pattern_fill("ANSI31", color=7, scale=0.05 * self.f)
            h.paths.add_polyline_path(pts, is_closed=True)

    def poli(self, pts: list[tuple[float, float]], camada: str = "VISTA_COBERTURA",
             fechar: bool = False) -> None:
        self.msp.add_lwpolyline([self.P(u, z) for u, z in pts], close=fechar,
                                dxfattribs={"layer": camada})

    def texto(self, s: str, u: float, z: float, mm: float = apresentacao.TEXTO_MM, *,
              centro: bool = False, rot: float = 0.0, camada: str = "VISTA_TEXTO") -> None:
        t = self.msp.add_text(s, dxfattribs={"layer": camada, "rotation": rot,
                                             "height": apresentacao.altura_texto(self.escala, mm),
                                             "style": apresentacao.ESTILO_TEXTO})
        t.set_placement(self.P(u, z), align=TextEntityAlignment.MIDDLE_CENTER if centro
                        else TextEntityAlignment.LEFT)

    def cota_h(self, u0: float, u1: float, z: float, deslocamento: float) -> None:
        d = self.msp.add_linear_dim(
            base=self.P((u0 + u1) / 2, z + deslocamento), p1=self.P(u0, z), p2=self.P(u1, z),
            angle=0, dimstyle=apresentacao.dimstyle_nome(self.escala),
            dxfattribs={"layer": "VISTA_COTA"})
        d.render()

    def cota_v(self, u: float, z0: float, z1: float, deslocamento: float) -> None:
        d = self.msp.add_linear_dim(
            base=self.P(u - deslocamento, (z0 + z1) / 2), p1=self.P(u, z0), p2=self.P(u, z1),
            angle=90, dimstyle=apresentacao.dimstyle_nome(self.escala),
            dxfattribs={"layer": "VISTA_COTA"})
        d.render()

    def nivel(self, u: float, z: float, rotulo: str, dz_texto: float = 0.0) -> None:
        """Marca de nível; ``dz_texto`` (em múltiplos de ``f``) afasta o texto de outro vizinho."""
        self.linha(u, z, u + 0.5 * self.f, z, "VISTA_AUX")
        self.texto(rotulo, u + 0.6 * self.f, z + dz_texto * self.f, apresentacao.TEXTO_PEQUENO_MM)


def _intervalos(geom: BaseGeometry, linha: LineString) -> list[tuple[float, float]]:
    """Trechos ``(u0, u1)`` de ``linha`` que ficam dentro de ``geom``."""
    inter = linha.intersection(geom)
    if inter.is_empty:
        return []
    partes = getattr(inter, "geoms", [inter])
    out = []
    for p in partes:
        if p.geom_type != "LineString" or p.length < 1e-6:
            continue
        us = sorted(linha.project(Point(c)) for c in p.coords)
        out.append((us[0], us[-1]))
    return sorted(out)


def _projetar(poly: BaseGeometry, linha: LineString) -> tuple[float, float]:
    us = [linha.project(Point(c)) for c in poly.exterior.coords]
    return min(us), max(us)


def secao(doc, msp, m: Modelo, op: Secao, escala: int) -> dict[str, Any]:  # noqa: ANN001
    """Desenha o corte e devolve um resumo (trechos cortados, alturas)."""
    if m.edif is None:
        raise ValueError("secao exige a operação edificacao (pé-direito)")
    a, b = tuple(op.a), tuple(op.b)
    L = LineString([a, b])
    if L.length < 1e-6:
        raise ValueError("secao: os dois pontos são iguais")
    ux, uy = (b[0] - a[0]) / L.length, (b[1] - a[1]) / L.length
    side = 1.0 if op.sentido == "esquerda" else -1.0
    nx, ny = -uy * side, ux * side  # direção de observação
    d = _Desenho(doc, msp, op.x, op.y, escala)
    f = d.f

    def lado_visto(poly: BaseGeometry) -> float:  # profundidade além do plano (>0: à frente)
        c = poly.centroid
        return (c.x - a[0]) * nx + (c.y - a[1]) * ny

    tem_telhado = m.regiao_cobertura() is not None

    def topo_externo(meio: Point) -> float:
        """Parede externa sobe até a platibanda ou, com telhado, até a face do telhado."""
        return max(m.h_topo, m.z_telhado(meio.x, meio.y)) if tem_telhado else m.h_topo

    cortados = 0
    # --- paredes cortadas -----------------------------------------------------------------
    for u0, u1 in _intervalos(m.paredes, L):
        meio = L.interpolate((u0 + u1) / 2)
        topo = topo_externo(meio) if meio.distance(m.pegada.exterior) < 0.35 else m.h_forro
        d.caixa(u0, 0, u1, topo, "VISTA_CORTE", hachura=True)
        cortados += 1
    # --- vãos: verga e peitoril (a parede cortada tem o buraco em toda a altura) ----------
    for ab in m.aberturas:
        for u0, u1 in _intervalos(ab.poly, L):
            meio = L.interpolate((u0 + u1) / 2)
            topo = topo_externo(meio) if meio.distance(m.pegada.exterior) < 0.35 else m.h_forro
            if ab.base > 0.01:
                d.caixa(u0, 0, u1, ab.base, "VISTA_CORTE", hachura=True)
            if ab.base + ab.altura < topo - 0.01:
                d.caixa(u0, ab.base + ab.altura, u1, topo, "VISTA_CORTE", hachura=True)
            if ab.tipo == "janela":
                d.caixa(u0, ab.base, u1, ab.base + ab.altura, "VISTA_ESQ")
            else:
                d.caixa(u0 + 0.03, 0, u1 - 0.03, ab.altura, "VISTA_PORTA")
    # --- piso e laje -----------------------------------------------------------------------
    for u0, u1 in _intervalos(m.pegada, L):
        d.caixa(u0, -PISO_M, u1, 0, "VISTA_CORTE", hachura=True)
        d.caixa(u0, m.h_forro, u1, m.h_laje, "VISTA_CORTE", hachura=True)
    # --- peças: cortadas (hachura) ou além do plano (traço fino) ---------------------------
    for p in m.pecas:
        cortes = _intervalos(p.poly, L)
        if cortes:
            for u0, u1 in cortes:
                d.caixa(u0, p.base, u1, p.topo, "VISTA_CORTE" if not p.tracejado
                        else "VISTA_AUX", hachura=not p.tracejado, dash=p.tracejado)
            continue
        prof = lado_visto(p.poly)
        if not (0 < prof <= op.profundidade_m):
            continue
        u0, u1 = _projetar(p.poly, L)
        if u1 < 0 or u0 > L.length:
            continue
        if p.classe == "extintor":
            d.caixa(u0, 0.95, u1, 1.5, "VISTA_INCENDIO")
        elif p.classe == "luz":
            d.caixa(u0, m.h_forro - 0.25, u1, m.h_forro - 0.12, "VISTA_ILUM")
        else:
            d.caixa(u0, p.base, u1, p.topo, "VISTA_AUX", dash=p.tracejado)
    pu = _intervalos(m.pegada, L)
    u_ini = pu[0][0] if pu else 0.0
    u_fim = pu[-1][1] if pu else L.length
    # --- telhado cortado -------------------------------------------------------------------
    z_max = m.h_topo
    chamada_telha = None
    if tem_telhado:
        assert m.edif.cobertura is not None  # noqa: S101
        c = m.edif.cobertura
        rx0, ry0, rx1, ry1 = m.regiao_cobertura()  # type: ignore[misc]
        regiao = Polygon([(rx0, ry0), (rx1, ry0), (rx1, ry1), (rx0, ry1)])
        for ua, ub in _intervalos(regiao, L):
            us = [ua, ub]
            if c.tipo == "duas_aguas":  # vértice onde a linha cruza a cumeeira
                xm, ym = (m.pegada.bounds[0] + m.pegada.bounds[2]) / 2, \
                    (m.pegada.bounds[1] + m.pegada.bounds[3]) / 2
                ridge = LineString([(xm, ry0 - 1), (xm, ry1 + 1)]) if c.cumeeira == "y" \
                    else LineString([(rx0 - 1, ym), (rx1 + 1, ym)])
                cruz = L.intersection(ridge)
                if not cruz.is_empty and cruz.geom_type == "Point":
                    uc = L.project(cruz)
                    if ua < uc < ub:
                        us.append(uc)
            us.sort()
            baixo = [(u, m.z_telhado(*L.interpolate(u).coords[0])) for u in us]
            cima = [(u, z + c.espessura_m) for u, z in baixo]
            d.poli(baixo + list(reversed(cima)), "VISTA_COBERTURA", fechar=True)
            z_max = max(z_max, max(z for _, z in cima))
            if c.telha and chamada_telha is None:
                uq = ua + 0.62 * (ub - ua)
                chamada_telha = (uq, m.z_telhado(*L.interpolate(uq).coords[0]) + c.espessura_m)
    # chamadas de material (telha e forro), em traço fino
    if chamada_telha is not None and m.edif.cobertura is not None:
        uq, zq = chamada_telha
        zt = z_max + 0.45 * f
        d.linha(uq, zq, uq + 0.35 * f, zt, "VISTA_AUX")
        d.linha(uq + 0.35 * f, zt, uq + 0.55 * f, zt, "VISTA_AUX")
        d.texto(m.edif.cobertura.telha.upper(), uq + 0.6 * f, zt, apresentacao.TEXTO_PEQUENO_MM)
        z_max = max(z_max, zt + 0.25 * f)
    vaos = _vaos_internos(_intervalos(m.paredes, L), u_ini, u_fim)
    if m.edif.forro and vaos:
        v0, v1 = max(vaos, key=lambda v: v[1] - v[0])
        d.texto(m.edif.forro.upper(), (v0 + v1) / 2, m.h_forro - 0.45 * f,
                apresentacao.TEXTO_PEQUENO_MM, centro=True)
    # --- rótulos de classe (NT 2-20) e figura humana, nos vãos livres -------------------------
    ocupado: list[tuple[float, float]] = []  # faixas de u ocupadas até 2 m de altura
    for p in m.pecas:
        if _intervalos(p.poly, L) or 0 < lado_visto(p.poly) <= op.profundidade_m:
            pu0, pu1 = _projetar(p.poly, L)
            ocupado.append((pu0, pu1))
    for ab in m.aberturas:
        for au0, au1 in _intervalos(ab.poly, L):
            ocupado.append((au0, au1))
    rotulos = 0
    if op.classe_parede:
        w_r, h_r = rotulo_classe_dims(escala)
        for v0, v1 in sorted(vaos, key=lambda v: v[0] - v[1])[:4]:
            if v1 - v0 < w_r + 0.4:
                continue
            uc = v0 + 0.15 + w_r / 2
            rotulo_classe(msp, *d.P(uc, 1.55), "PAREDE", op.classe_parede, escala)
            ocupado.append((uc - w_r / 2 - 0.1, uc + w_r / 2 + 0.1))
            rotulos += 1
    humano = None
    if op.figura_humana and vaos:
        for v0, v1 in sorted(vaos, key=lambda v: v[0] - v[1]):
            u_h = _vaga(v0 + 0.4, v1 - 0.4, SILHUETA_LARGURA_M / 2 + 0.1, ocupado)
            if u_h is not None and m.h_forro >= 1.9:
                figura_humana(msp, *d.P(u_h, 0.0))
                humano = round(u_h, 2)
                break
    # --- cotas, níveis e título --------------------------------------------------------------
    d.cota_v(u_ini, 0, m.h_forro, 0.8 * f)
    d.cota_v(u_ini, 0, m.h_topo, 1.4 * f)
    cortes_par = sorted(_intervalos(m.paredes, L))
    marcas = [u_ini] + [u for iv in cortes_par for u in iv if u_ini < u < u_fim] + [u_fim]
    marcas = sorted({round(u, 3) for u in marcas})
    for u0, u1 in zip(marcas, marcas[1:], strict=False):
        if u1 - u0 > 0.06:
            d.cota_h(u0, u1, 0, -0.7 * f)
    d.cota_h(u_ini, u_fim, 0, -1.4 * f)
    for z, rot, dz in ((0.0, "+0,00", 0.0), (m.h_forro, f"+{_fmt(m.h_forro)} (forro)", -0.2),
                       (m.h_laje, f"+{_fmt(m.h_laje)} (laje)", 0.1)):
        d.nivel(u_fim + 0.2 * f, z, rot, dz)
    if m.edif.platibanda_m > 0:
        d.nivel(u_fim + 0.2 * f, m.h_topo, f"+{_fmt(m.h_topo)} (platibanda)")
    if tem_telhado and m.z_cumeeira() > m.h_topo + 0.05:
        d.nivel(u_fim + 0.2 * f, m.z_cumeeira(), f"+{_fmt(m.z_cumeeira())} (cumeeira)", 0.1)
    d.linha(u_ini - 1.5 * f, 0, u_fim + 1.5 * f, 0, "VISTA_CONTORNO")
    d.texto(f"CORTE {op.nome.upper()}-{op.nome.upper()}", u_ini, z_max + 1.2 * f,
            apresentacao.TEXTO_TITULO_MM)
    d.texto(f"ESCALA 1:{escala}", u_ini, z_max + 0.55 * f, apresentacao.TEXTO_MM)
    out: dict[str, Any] = {"nome": op.nome.upper(), "trechos_de_parede_cortados": cortados,
                           "pe_direito_m": m.edif.pe_direito_m,
                           "altura_total_m": round(m.z_maximo(), 3),
                           "extensao_m": round(u_fim - u_ini, 3)}
    if tem_telhado:
        out["cumeeira_m"] = round(m.z_cumeeira(), 3)
    if op.classe_parede:
        out["rotulos_de_classe"] = rotulos
    if op.figura_humana:
        out["figura_humana"] = humano is not None
    return out


def _vaos_internos(paredes: list[tuple[float, float]], u_ini: float,
                   u_fim: float) -> list[tuple[float, float]]:
    """Trechos livres entre paredes cortadas consecutivas (o interior dos ambientes)."""
    bordas = sorted(paredes)
    out = []
    for (_, a1), (b0, _) in zip(bordas, bordas[1:], strict=False):
        if b0 - a1 > 0.3 and a1 >= u_ini - 1e-6 and b0 <= u_fim + 1e-6:
            out.append((a1, b0))
    return out


def _vaga(u0: float, u1: float, meia: float,
          ocupado: list[tuple[float, float]]) -> float | None:
    """Primeira posição em [u0, u1] cuja faixa ±meia não toca nada ocupado (passo de 10 cm),
    começando do meio para os lados."""
    if u1 - u0 < 2 * meia:
        return None
    meio = (u0 + u1) / 2
    passos = int((u1 - u0) / 0.1) + 1
    for i in range(passos):
        for s in (1, -1):
            u = meio + s * i * 0.05
            if not (u0 + meia <= u <= u1 - meia):
                continue
            if all(u + meia <= a or u - meia >= b for a, b in ocupado):
                return u
    return None


_NORMAL = {"sul": (0.0, -1.0), "norte": (0.0, 1.0), "leste": (1.0, 0.0), "oeste": (-1.0, 0.0)}
# eixo u (para a direita de quem olha de fora para a edificação)
_EIXO_U = {"sul": (1.0, 0.0), "norte": (-1.0, 0.0), "leste": (0.0, 1.0), "oeste": (0.0, -1.0)}


def fachada(doc, msp, m: Modelo, op: Fachada, escala: int) -> dict[str, Any]:  # noqa: ANN001
    if m.edif is None:
        raise ValueError("fachada exige a operação edificacao (pé-direito)")
    d = _Desenho(doc, msp, op.x, op.y, escala)
    f = d.f
    nx, ny = _NORMAL[op.lado]
    vx, vy = _EIXO_U[op.lado]

    def u_de(x: float, y: float) -> float:
        return x * vx + y * vy

    coords = list(m.pegada.exterior.coords)
    arestas = []
    for p, q in zip(coords, coords[1:], strict=False):
        ex, ey = q[0] - p[0], q[1] - p[1]
        comp = math.hypot(ex, ey)
        if comp < 1e-6:
            continue
        # normal para fora: a pegada tem orientação arbitrária, então testa pelo meio da aresta
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        n1 = (ey / comp, -ex / comp)
        fora = n1 if not m.pegada.contains(Point(mx + n1[0] * 0.05, my + n1[1] * 0.05)) \
            else (-n1[0], -n1[1])
        if fora[0] * nx + fora[1] * ny > 0.7:
            arestas.append((p, q))
    if not arestas:
        raise ValueError(f"fachada {op.lado}: a edificação não tem parede externa desse lado")
    u_min = min(min(u_de(*p), u_de(*q)) for p, q in arestas)
    u_max = max(max(u_de(*p), u_de(*q)) for p, q in arestas)

    def U(x: float, y: float) -> float:
        return u_de(x, y) - u_min

    for p, q in arestas:
        u0, u1 = sorted((U(*p), U(*q)))
        d.caixa(u0, 0, u1, m.h_topo, "VISTA_CONTORNO")
    d.linha(0, m.h_laje, u_max - u_min, m.h_laje, "VISTA_AUX", dash=True)
    nab = 0
    topo_vaos = 0.0
    for ab in m.aberturas:
        # a abertura pertence a esta fachada se encosta numa aresta externa desse lado
        for p, q in arestas:
            if LineString([p, q]).distance(Point(ab.x, ab.y)) < 0.45:
                u = U(ab.x, ab.y)
                u0, u1 = u - ab.largura / 2, u + ab.largura / 2
                if ab.tipo == "janela":
                    d.caixa(u0, ab.base, u1, ab.base + ab.altura, "VISTA_ESQ")
                    d.linha((u0 + u1) / 2, ab.base, (u0 + u1) / 2, ab.base + ab.altura,
                            "VISTA_ESQ")
                    _reflexos(d, u0, u1, ab.base, ab.altura)
                    topo_vaos = max(topo_vaos, ab.base + ab.altura)
                else:
                    topo_vaos = max(topo_vaos, ab.altura)
                    d.caixa(u0, 0, u1, ab.altura, "VISTA_PORTA")
                d.texto(f"{round(ab.largura * 100)}x{round(ab.altura * 100)}"
                        + (f"/{round(ab.base * 100)}" if ab.tipo == "janela" else ""),
                        u, ab.base + ab.altura + 0.25 * f, apresentacao.TEXTO_PEQUENO_MM,
                        centro=True)
                nab += 1
                break
    # volumes: o que passa do telhado e o que está encostado fora da edificação
    for p in m.pecas:
        if p.classe != "volume":
            continue
        u0, u1 = _faixa_u(p.poly, vx, vy, u_min)
        dentro = m.pegada.buffer(0.01).contains(p.poly)
        if dentro:
            if p.topo > m.h_topo:  # só a parte que aparece acima da platibanda
                d.caixa(u0, m.h_topo, u1, p.topo, "VISTA_CONTORNO")
        else:
            lado = (p.poly.centroid.x - m.pegada.centroid.x) * nx \
                + (p.poly.centroid.y - m.pegada.centroid.y) * ny
            d.caixa(u0, p.base, u1, p.topo, "VISTA_CONTORNO" if lado > 0 else "VISTA_AUX",
                    hachura=lado > 0 and not p.tracejado, dash=p.tracejado)
        d.texto(p.nome, (u0 + u1) / 2, p.topo + 0.3 * f, apresentacao.TEXTO_PEQUENO_MM,
                centro=True)
    # telhado visto: silhueta (o mais alto em cada posição) e beiral da frente
    z_max = m.h_topo
    z_beiral = m.h_topo  # o letreiro fica abaixo do beiral da frente
    reg = m.regiao_cobertura()
    if reg is not None:
        assert m.edif.cobertura is not None  # noqa: S101
        esp = m.edif.cobertura.espessura_m
        rx0, ry0, rx1, ry1 = reg
        cantos = [(rx0, ry0), (rx1, ry0), (rx1, ry1), (rx0, ry1)]
        us_r = [u_de(x, y) - u_min for x, y in cantos]
        prof = [x * nx + y * ny for x, y in cantos]  # maior = mais perto de quem olha
        ua, ub = min(us_r), max(us_r)
        pa, pb = min(prof), max(prof)

        def ponto(u: float, p: float) -> tuple[float, float]:
            uu = u + u_min  # volta ao sistema da planta: u ao longo de v, p ao longo de n
            return (uu * vx + p * nx, uu * vy + p * ny)

        n_u = 48
        topo, frente = [], []
        for i in range(n_u + 1):
            u = ua + (ub - ua) * i / n_u
            zs = [m.z_telhado(*ponto(u, pa + (pb - pa) * j / 12)) for j in range(13)]
            topo.append((u, max(zs) + esp))
            frente.append((u, m.z_telhado(*ponto(u, pb))))
        d.poli(topo, "VISTA_COBERTURA")
        d.poli([(ua, frente[0][1]), *frente, (ub, frente[-1][1])], "VISTA_COBERTURA")
        d.linha(ua, frente[0][1], ua, topo[0][1], "VISTA_COBERTURA")
        d.linha(ub, frente[-1][1], ub, topo[-1][1], "VISTA_COBERTURA")
        # face do telhado vista: nervuras da telha em traço fino
        passo = 0.30 * f
        u = ua + passo
        while u < ub - passo / 2:
            i = round((u - ua) / (ub - ua) * n_u)
            if topo[i][1] - frente[i][1] > esp + 0.08:
                d.linha(u, frente[i][1], u, topo[i][1] - esp, "VISTA_AUX")
            u += passo
        z_max = max(z_max, max(z for _, z in topo))
        z_beiral = min(z_beiral, min(z for _, z in frente))
    letreiro = None
    if op.letreiro:
        # acima das etiquetas dos vãos (0,25 f acima do vão, 1,8 mm de altura)
        faixa0, faixa1 = topo_vaos + 0.55 * f, z_beiral - 0.15
        if faixa1 - faixa0 >= 0.30:
            mm = min(8.0, (faixa1 - faixa0) * 1000 / escala * 0.55)
            d.texto(op.letreiro.upper(), (u_max - u_min) / 2, (faixa0 + faixa1) / 2, mm,
                    centro=True)
            letreiro = "desenhado"
        else:
            letreiro = "sem espaço entre os vãos e o topo da fachada"
    d.linha(-1.2 * f, 0, u_max - u_min + 1.2 * f, 0, "VISTA_CONTORNO")
    niveis = [(0.0, "+0,00"), (m.h_topo, f"+{_fmt(m.h_topo)}")]
    if z_max > m.h_topo + 0.05:
        niveis.append((z_max, f"+{_fmt(z_max)}"))
    for z, rot in niveis:
        d.nivel(u_max - u_min + 0.3 * f, z, rot)
    d.cota_h(0, u_max - u_min, 0, -0.9 * f)
    d.texto(f"FACHADA {op.lado.upper()}", 0, z_max + 1.2 * f, apresentacao.TEXTO_TITULO_MM)
    d.texto(f"ESCALA 1:{escala}", 0, z_max + 0.55 * f, apresentacao.TEXTO_MM)
    out = {"lado": op.lado, "largura_m": round(u_max - u_min, 3), "aberturas": nab,
           "altura_total_m": round(z_max, 3)}
    if letreiro:
        out["letreiro"] = letreiro
    return out


def _reflexos(d: _Desenho, u0: float, u1: float, base: float, altura: float) -> None:
    """Dois traços a 45° em cada folha da janela: a convenção de vidro das fachadas."""
    meio = (u0 + u1) / 2
    for a, b in ((u0, meio), (meio, u1)):
        w = b - a
        if w < 0.25 or altura < 0.4:
            continue
        t = min(0.22, w * 0.3, altura * 0.25)
        for k in (0.35, 0.55):
            uc, zc = a + w * k, base + altura * (1 - k)
            d.linha(uc - t / 2, zc - t / 2, uc + t / 2, zc + t / 2, "VISTA_ESQ")


def _faixa_u(poly: BaseGeometry, vx: float, vy: float, u_min: float) -> tuple[float, float]:
    us = [x * vx + y * vy - u_min for x, y in poly.exterior.coords]
    return min(us), max(us)


__all__ = ["Abertura", "Edificacao", "Fachada", "Modelo", "Peca", "Secao", "Volume", "fachada",
           "secao"]
