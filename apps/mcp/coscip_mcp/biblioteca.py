"""Biblioteca própria de blocos de arquitetura e equipamentos (frente D2, §9 da arquitetura).

Louças, mobiliário, equipamentos de cozinha, recipientes de GLP, escada e pilar, desenhados em
planta (metros, centro na origem) por este módulo. **Não vem de nenhum arquivo de terceiros.**
Cada bloco é parametrizado por largura e profundidade (os recipientes de GLP, só pelo diâmetro):
o bloco é definido já no tamanho pedido (``MOB_FOGAO_160X90``), sem escala desigual na inserção,
para que círculos continuem círculos.

Camadas: tudo em ``MOBILIARIO`` (o dicionário do motor a trata como não obstáculo), exceto o pilar
(``PILARES``) e a escada (``ESCADA``), que o motor reconhece como estrutura.
O motor não conta estes blocos como equipamento de segurança.
"""

from __future__ import annotations

import difflib
import math
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from coscip_mcp.simbologia import Glyph, arrow, dashed, emit, rect


@dataclass(frozen=True)
class BlocoBib:
    id: str
    nome: str
    grupo: str
    largura_m: float
    profundidade_m: float
    camada: str
    desenho: Callable[[float, float], Glyph]
    so_diametro: bool = False  # recipientes: só a largura (diâmetro) vale


def _ellipse(cx: float, cy: float, rx: float, ry: float, n: int = 28) -> list[tuple[float, float]]:
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n))
            for i in range(n)]


def _caixa(g: Glyph, w: float, d: float, dentro: float = 0.0) -> None:
    g.poly(*rect(-w / 2 + dentro, -d / 2 + dentro, w / 2 - dentro, d / 2 - dentro))


def _vaso(w: float, d: float) -> Glyph:
    g = Glyph()
    tank = min(0.2, d * 0.28)
    g.poly(*rect(-w * 0.45, d / 2 - tank, w * 0.45, d / 2))
    by = (d / 2 - tank - d / 2) / 2
    ry = (d - tank) / 2
    g.poly(*_ellipse(0, by, w / 2 * 0.95, ry * 0.97))
    g.poly(*_ellipse(0, by - 0.01, w / 2 * 0.62, ry * 0.7))
    return g


def _lavatorio(w: float, d: float) -> Glyph:
    g = Glyph()
    _caixa(g, w, d)
    g.poly(*_ellipse(0, -d * 0.04, w * 0.38, d * 0.34))
    g.circle(0, -d * 0.04, min(w, d) * 0.04)
    g.line((-w * 0.08, d * 0.42), (w * 0.08, d * 0.42))
    return g


def _pia(w: float, d: float) -> Glyph:
    g = Glyph()
    _caixa(g, w, d)
    cubas = 2 if w >= 1.0 else 1
    cw = (w - 0.1 * (cubas + 1)) / cubas
    for i in range(cubas):
        x0 = -w / 2 + 0.1 + i * (cw + 0.1)
        g.poly(*rect(x0, -d / 2 + 0.08, x0 + cw, d / 2 - 0.12))
    g.circle(0, d / 2 - 0.04, 0.025)
    return g


def _chuveiro(w: float, d: float) -> Glyph:
    g = Glyph()
    _caixa(g, w, d)
    g.line((-w / 2, -d / 2), (w / 2, d / 2))
    g.circle(0, 0, min(w, d) * 0.08)
    g.circle(w * 0.3, d * 0.3, min(w, d) * 0.05)
    return g


def _mesa(w: float, d: float) -> Glyph:
    g = Glyph()
    _caixa(g, w, d)
    return g


def _cadeira(w: float, d: float) -> Glyph:
    g = Glyph()
    _caixa(g, w, d)
    g.line((-w / 2, d / 2 - 0.05), (w / 2, d / 2 - 0.05))
    return g


def _mesa_4(w: float, d: float) -> Glyph:
    g = _mesa(w, d)
    c = 0.40  # cadeira 0,40 x 0,40, encostada na mesa
    for cx, cy, rot in ((0, d / 2 + c / 2, 0), (0, -d / 2 - c / 2, 180),
                        (-w / 2 - c / 2, 0, 90), (w / 2 + c / 2, 0, 270)):
        a = math.radians(rot)
        cos, sin = math.cos(a), math.sin(a)
        pts = [(cx + x * cos - y * sin, cy + x * sin + y * cos)
               for x, y in rect(-c / 2 + 0.02, -c / 2 + 0.02, c / 2 - 0.02, c / 2 - 0.02)]
        g.poly(*pts)
        # encosto: lado afastado da mesa
        back = [(cx + x * cos - y * sin, cy + x * sin + y * cos)
                for x, y in ((-c / 2 + 0.02, c / 2 - 0.07), (c / 2 - 0.02, c / 2 - 0.07))]
        g.line(*back)
    return g


def _balcao(w: float, d: float) -> Glyph:
    g = Glyph()
    _caixa(g, w, d)
    _caixa(g, w, d, 0.05)
    return g


def _fogao(w: float, d: float) -> Glyph:
    g = Glyph()
    _caixa(g, w, d)
    cols, rows = 3, 2
    r = min(w / cols, (d - 0.3) / rows) * 0.34
    for i in range(cols):
        for j in range(rows):
            cx = -w / 2 + w * (i + 0.5) / cols
            cy = -d / 2 + 0.2 + (d - 0.3) * (j + 0.5) / rows
            g.circle(cx, cy, r)
            g.circle(cx, cy, r * 0.45)
    g.line((-w / 2 + 0.05, -d / 2 + 0.1), (w / 2 - 0.05, -d / 2 + 0.1))
    return g


def _chapa(w: float, d: float) -> Glyph:
    g = Glyph()
    _caixa(g, w, d)
    _caixa(g, w, d, 0.06)
    g.line((-w / 2 + 0.06, -d / 2 + 0.06), (w / 2 - 0.06, d / 2 - 0.06))
    return g


def _fritadeira(w: float, d: float) -> Glyph:
    g = Glyph()
    _caixa(g, w, d)
    cw = (w - 0.3) / 2
    for i in range(2):
        x0 = -w / 2 + 0.1 + i * (cw + 0.1)
        g.poly(*rect(x0, -d / 2 + 0.12, x0 + cw, d / 2 - 0.12))
    return g


def _forno(w: float, d: float) -> Glyph:
    g = Glyph()
    _caixa(g, w, d)
    _caixa(g, w, d, 0.08)
    g.line((-w / 2 + 0.08, d / 2 - 0.08), (w / 2 - 0.08, -d / 2 + 0.08))
    g.line((-w / 2 + 0.08, -d / 2 + 0.08), (w / 2 - 0.08, d / 2 - 0.08))
    return g


def _coifa(w: float, d: float) -> Glyph:
    """Projeção da coifa: contorno e diagonais tracejados (elemento acima do plano de corte)."""
    g = Glyph()
    x0, y0, x1, y1 = -w / 2, -d / 2, w / 2, d / 2
    for p, q in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)),
                 ((x0, y1), (x0, y0)), ((x0, y0), (x1, y1)), ((x0, y1), (x1, y0))):
        dashed(g, p, q, 0.25, 0.12)
    return g


def _refrigerador(w: float, d: float) -> Glyph:
    g = Glyph()
    _caixa(g, w, d)
    g.line((-w / 2, d / 6), (w / 2, d / 6))
    g.line((-w * 0.38, d / 2 - 0.06), (-w * 0.38, d / 6 + 0.04))
    return g


def _botijao(w: float, _d: float) -> Glyph:
    g = Glyph()
    g.circle(0, 0, w / 2)
    g.circle(0, 0, w / 2 * 0.82)
    g.circle(0, 0, w / 2 * 0.22)
    return g


def _escada(w: float, d: float) -> Glyph:
    """Lance reto: degraus de 0,28 m ao longo da profundidade e seta no sentido de subida."""
    g = Glyph()
    _caixa(g, w, d)
    n = max(2, round(d / 0.28))
    for i in range(1, n):
        y = -d / 2 + d * i / n
        g.line((-w / 2, y), (w / 2, y))
    arrow(g, (0, -d / 2 + 0.2), (0, d / 2 - 0.25), head=min(0.25, w * 0.2))
    return g


def _pilar(w: float, d: float) -> Glyph:
    g = Glyph()
    g.fill(*rect(-w / 2, -d / 2, w / 2, d / 2))
    return g


_B = BlocoBib
BIBLIOTECA: dict[str, BlocoBib] = {b.id: b for b in (
    _B("VASO_SANITARIO", "Vaso sanitário com caixa acoplada", "LOUÇAS", 0.40, 0.70,
       "MOBILIARIO", _vaso),
    _B("LAVATORIO", "Lavatório", "LOUÇAS", 0.50, 0.40, "MOBILIARIO", _lavatorio),
    _B("PIA", "Pia (uma cuba até 1,0 m; duas acima)", "LOUÇAS", 1.20, 0.55, "MOBILIARIO", _pia),
    _B("CHUVEIRO", "Box de chuveiro", "LOUÇAS", 0.90, 0.90, "MOBILIARIO", _chuveiro),
    _B("MESA", "Mesa", "MOBILIÁRIO", 0.90, 0.90, "MOBILIARIO", _mesa),
    _B("CADEIRA", "Cadeira", "MOBILIÁRIO", 0.45, 0.45, "MOBILIARIO", _cadeira),
    _B("MESA_4_LUGARES", "Mesa com quatro cadeiras (largura e profundidade são da mesa)",
       "MOBILIÁRIO", 0.90, 0.90, "MOBILIARIO", _mesa_4),
    _B("BALCAO", "Balcão ou bancada", "MOBILIÁRIO", 2.00, 0.60, "MOBILIARIO", _balcao),
    _B("REFRIGERADOR", "Refrigerador ou câmara", "EQUIPAMENTOS DE COZINHA", 0.80, 0.70,
       "MOBILIARIO", _refrigerador),
    _B("FOGAO", "Fogão industrial de seis bocas (GLP)", "EQUIPAMENTOS DE COZINHA", 1.60, 0.90,
       "MOBILIARIO", _fogao),
    _B("CHAPA", "Chapa de grelhados (GLP)", "EQUIPAMENTOS DE COZINHA", 1.20, 0.90,
       "MOBILIARIO", _chapa),
    _B("FRITADEIRA", "Fritadeira de duas cubas (GLP)", "EQUIPAMENTOS DE COZINHA", 1.10, 0.90,
       "MOBILIARIO", _fritadeira),
    _B("FORNO", "Forno combinado (GLP)", "EQUIPAMENTOS DE COZINHA", 1.10, 0.90,
       "MOBILIARIO", _forno),
    _B("COIFA", "Projeção da coifa (tracejada)", "EQUIPAMENTOS DE COZINHA", 5.00, 1.20,
       "MOBILIARIO", _coifa),
    _B("BOTIJAO_P45", "Recipiente de GLP P-45 (diâmetro 0,38 m)", "GLP", 0.38, 0.38,
       "MOBILIARIO", _botijao, so_diametro=True),
    _B("BOTIJAO_P190", "Recipiente de GLP P-190 (diâmetro 0,60 m)", "GLP", 0.60, 0.60,
       "MOBILIARIO", _botijao, so_diametro=True),
    _B("ESCADA", "Lance de escada (setas no sentido de subida)", "ESTRUTURA", 1.20, 3.00,
       "ESCADA", _escada),
    _B("PILAR", "Pilar", "ESTRUTURA", 0.30, 0.30, "PILARES", _pilar),
)}


def achar(chave: str) -> BlocoBib | None:
    """Bloco pelo id; aceita minúsculas, espaços e acentos ("fogão" acha FOGAO)."""
    k = unicodedata.normalize("NFKD", chave).encode("ascii", "ignore").decode()
    return BIBLIOTECA.get(k.strip().upper().replace(" ", "_"))


def parecidos(chave: str) -> list[str]:
    return difflib.get_close_matches(chave.upper(), list(BIBLIOTECA), n=4, cutoff=0.5)


def tamanho(bloco: BlocoBib, largura_m: float | None, profundidade_m: float | None
            ) -> tuple[float, float]:
    w = largura_m or bloco.largura_m
    d = w if bloco.so_diametro else (profundidade_m or bloco.profundidade_m)
    return round(w, 3), round(d, 3)


def nome_do_bloco(bloco: BlocoBib, w: float, d: float) -> str:
    return f"MOB_{bloco.id}_{round(w * 100)}X{round(d * 100)}"


def inserir(doc, msp, bloco: BlocoBib, x: float, y: float, rotacao: float,  # noqa: ANN001
            largura_m: float | None, profundidade_m: float | None, camada: str) -> str:
    """Define o bloco (uma vez por tamanho) e o insere; devolve o nome do bloco."""
    w, d = tamanho(bloco, largura_m, profundidade_m)
    nome = nome_do_bloco(bloco, w, d)
    if nome not in doc.blocks:
        emit(doc.blocks.new(nome), bloco.desenho(w, d))
    msp.add_blockref(nome, (x, y), dxfattribs={"layer": camada, "rotation": rotacao})
    return nome


# Alturas para as vistas (cortes e fachadas): (base, topo) em metros; ``None`` no topo = até o
# forro. São medidas usuais de projeto, uma PREMISSA do desenho (o usuário não informou): o
# resumo das vistas avisa e o responsável técnico confere.
ALTURAS: dict[str, tuple[float, float | None]] = {
    "VASO_SANITARIO": (0.0, 0.80), "LAVATORIO": (0.0, 0.85), "PIA": (0.0, 0.90),
    "CHUVEIRO": (0.0, 0.05), "MESA": (0.0, 0.75), "CADEIRA": (0.0, 0.90),
    "MESA_4_LUGARES": (0.0, 0.90), "BALCAO": (0.0, 0.90), "REFRIGERADOR": (0.0, 2.00),
    "FOGAO": (0.0, 0.90), "CHAPA": (0.0, 0.90), "FRITADEIRA": (0.0, 0.90), "FORNO": (0.0, 0.90),
    "COIFA": (2.00, 2.60), "BOTIJAO_P45": (0.0, 1.25), "BOTIJAO_P190": (0.0, 1.30),
    "ESCADA": (0.0, None), "PILAR": (0.0, None),
}


def faixa_de_altura(bloco: BlocoBib, forro_m: float) -> tuple[float, float]:
    """(base, topo) do bloco nas vistas, em metros."""
    base, topo = ALTURAS.get(bloco.id, (0.0, 0.90))
    return base, forro_m if topo is None else topo


__all__ = ["ALTURAS", "BIBLIOTECA", "BlocoBib", "achar", "faixa_de_altura", "inserir",
           "nome_do_bloco", "parecidos", "tamanho"]
