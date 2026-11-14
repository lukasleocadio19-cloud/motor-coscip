"""Isométrico da rede de sprinklers (frente E).

Desenha, em perspectiva isométrica (eixos a 30°), a rede calculada por
``coscip_design.rede_sprinklers``: prumada com a VGA na base, tubulação geral, subgeral, ramais,
bicos, diâmetro de cada trecho e as cotas de altura; ao lado, o **quadro de cálculo hidráulico**
(trecho, nós, DN, comprimento, vazão, velocidade e perda de carga) e a pressão na base da prumada.

Tudo vem do cálculo, nada é digitado: o isométrico e o memorial não podem divergir. Os nomes de
nós e trechos (B1, J1, T1, PR) não começam por S, E, A, P ou M seguidos de número, para o leitor do
motor não os confundir com placas de sinalização. Desenhado no model space, na escala da planta.
"""

from __future__ import annotations

import math
from typing import Any

from coscip_design.rede_sprinklers import Rede, Tubo
from ezdxf.enums import TextEntityAlignment
from shapely.geometry import LineString, Point, box
from shapely.geometry.base import BaseGeometry

from coscip_mcp import apresentacao

C30, S30 = math.cos(math.radians(30)), math.sin(math.radians(30))
CAMADAS = ("ISO_TUBO", "ISO_PRUMADA", "ISO_BICO", "ISO_TEXTO", "ISO_COTA", "ISO_QUADRO",
           "ISO_AUX")


def _fmt(v: float, casas: int = 2) -> str:
    return f"{v:.{casas}f}".replace(".", ",")


class _Iso:
    def __init__(self, doc, msp, rede: Rede, x0: float, y0: float, escala: int) -> None:  # noqa: ANN001
        self.doc, self.msp, self.rede, self.escala = doc, msp, rede, escala
        self.f = apresentacao.fator(escala)
        for nome in CAMADAS:
            apresentacao.criar_camada(doc, nome)
        ax, ay = rede.zona.alimentacao
        self.ox, self.oy = ax, ay  # a prumada fica sobre (x0, y0)
        self.x0, self.y0 = x0, y0

    def P(self, p: tuple[float, float, float]) -> tuple[float, float]:
        dx, dy, dz = p[0] - self.ox, p[1] - self.oy, p[2] - self.rede.zona.z_base_m
        return (self.x0 + (dx - dy) * C30, self.y0 + (dx + dy) * S30 + dz)

    def texto(self, s: str, x: float, y: float, mm: float = apresentacao.TEXTO_PEQUENO_MM, *,
              centro: bool = False, camada: str = "ISO_TEXTO") -> None:
        t = self.msp.add_text(s, dxfattribs={"layer": camada, "style": apresentacao.ESTILO_TEXTO,
                                             "height": apresentacao.altura_texto(self.escala, mm)})
        t.set_placement((x, y), align=TextEntityAlignment.MIDDLE_CENTER if centro
                        else TextEntityAlignment.LEFT)

    def linha(self, a: tuple[float, float], b: tuple[float, float], camada: str,
              dash: bool = False) -> None:
        attrs: dict[str, Any] = {"layer": camada}
        if dash:
            attrs["linetype"] = "DASHED"
        self.msp.add_line(a, b, dxfattribs=attrs)


def _tipo_camada(t: Tubo) -> str:
    return "ISO_PRUMADA" if t.tipo in ("prumada", "geral") else "ISO_TUBO"


def desenhar(doc, msp, rede: Rede, x0: float, y0: float, escala: int,  # noqa: ANN001
             titulo: str = "ISOMÉTRICO DA REDE DE SPRINKLERS",
             quadro: bool = True) -> dict[str, Any]:
    """Desenha o isométrico com a prumada em (x0, y0) e devolve o resumo do que foi desenhado."""
    if not rede.tubos:
        raise ValueError("isometrico: a zona não tem rede calculada (sem bicos)")
    d = _Iso(doc, msp, rede, x0, y0, escala)
    f = d.f
    tx = apresentacao.altura_texto(escala, apresentacao.TEXTO_PEQUENO_MM)

    # --- geometria que os rótulos não podem cobrir ------------------------------------------------
    ocupado: list[BaseGeometry] = []
    base = d.P((rede.zona.alimentacao[0], rede.zona.alimentacao[1], rede.zona.z_base_m))
    topo = d.P((rede.zona.alimentacao[0], rede.zona.alimentacao[1], rede.zona.z_ramal_m))
    xc = base[0] - 0.9 * f
    for t in rede.tubos:
        ocupado.append(LineString([d.P(t.p0), d.P(t.p1)]).buffer(0.04 * f))
    r_bico = 0.12 * f
    for bc in rede.bicos:
        u, v = d.P((bc.x, bc.y, bc.z))
        ocupado.append(Point(u, v - r_bico).buffer(r_bico * 1.1).union(
            LineString([(u, v), (u, v - 0.05 * f)]).buffer(0.03 * f)))
    ocupado.append(Point(base).buffer(0.3 * f))
    ocupado.append(LineString([(xc, base[1]), (xc, topo[1])]).buffer(0.1 * f))

    def rotular(s_: str, candidatos: list[tuple[float, float]], camada: str = "ISO_TEXTO") -> bool:
        """Escreve ``s_`` no primeiro candidato (centro do texto) que não cubra nada; se nenhum
        servir, não escreve (a informação continua no quadro de cálculo)."""
        w = 0.85 * tx * len(s_) + 0.5 * tx
        for cx, cy in candidatos:
            caixa = box(cx - w / 2, cy - tx * 0.95, cx + w / 2, cy + tx * 0.95)
            if not any(caixa.intersects(o) for o in ocupado):
                d.texto(s_, cx, cy, centro=True, camada=camada)
                ocupado.append(caixa)
                return True
        return False

    # --- tubos e diâmetros (rótulo no trecho de ramal que muda de DN e nos demais, se couber) ---
    ultimo_dn: dict[str, int] = {}
    for t in rede.tubos:
        a_, b_ = d.P(t.p0), d.P(t.p1)
        d.linha(a_, b_, _tipo_camada(t))
        rotulado = t.tipo != "ramal" or ultimo_dn.get(t.de) != t.dn
        ultimo_dn[t.para] = t.dn
        comp = math.dist(a_, b_)
        if not rotulado or comp <= 10 * tx:  # trecho curto: só no quadro
            continue
        mx, my = (a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2
        cand = []
        for fr in (0.0, 0.18, -0.18):  # ao longo do trecho
            px, py = mx + (b_[0] - a_[0]) * fr, my + (b_[1] - a_[1]) * fr
            for dist in (1.0, 1.7, 2.6):
                cand += [(px, py + dist * tx), (px, py - dist * tx),
                         (px + (1.5 + dist) * tx, py), (px - (1.5 + dist) * tx, py)]
        rotular(f"DN{t.dn}", cand)
    # --- bicos: pendente (círculo com haste), número e círculo duplo se opera ------------------
    for bc in rede.bicos:
        u, v = d.P((bc.x, bc.y, bc.z))
        d.msp.add_circle((u, v - r_bico), r_bico, dxfattribs={"layer": "ISO_BICO"})
        d.linha((u, v), (u, v - 0.05 * f), "ISO_BICO")
        if bc.opera:
            d.msp.add_circle((u, v - r_bico), 0.65 * r_bico, dxfattribs={"layer": "ISO_BICO"})
        rotular(bc.id, [(u + 0.5 * f, v - 0.5 * f), (u - 0.5 * f, v - 0.5 * f),
                        (u + 0.5 * f, v + 0.4 * f), (u - 0.5 * f, v + 0.4 * f),
                        (u, v - 0.9 * f)], "ISO_BICO")
    # --- VGA na base da prumada e cota de altura -----------------------------------------
    d.msp.add_circle(base, 0.22 * f, dxfattribs={"layer": "ISO_PRUMADA"})
    d.linha((base[0] - 0.16 * f, base[1] - 0.16 * f), (base[0] + 0.16 * f, base[1] + 0.16 * f),
            "ISO_PRUMADA")
    d.linha((base[0] - 0.16 * f, base[1] + 0.16 * f), (base[0] + 0.16 * f, base[1] - 0.16 * f),
            "ISO_PRUMADA")
    rotular("VGA", [(base[0], base[1] - 0.7 * f), (base[0] + 0.9 * f, base[1] - 0.4 * f),
                    (base[0] + 0.9 * f, base[1] + 0.5 * f)])
    d.linha((xc, base[1]), (xc, topo[1]), "ISO_COTA")
    for yy in (base[1], topo[1]):
        d.linha((xc - 0.12 * f, yy), (xc + 0.12 * f, yy), "ISO_COTA")
    rotular(_fmt(rede.zona.z_ramal_m - rede.zona.z_base_m),
            [(xc - 0.75 * f, (base[1] + topo[1]) / 2), (xc - 0.75 * f, base[1] + 0.8 * f)],
            "ISO_COTA")

    # título, eixos e legenda
    exts = [d.P(t.p0) for t in rede.tubos] + [d.P(t.p1) for t in rede.tubos]
    xs, ys = [p[0] for p in exts], [p[1] for p in exts]
    top = max(ys) + 2.2 * f
    d.texto(titulo, min(xs), top, apresentacao.TEXTO_TITULO_MM)
    d.texto(f"{rede.zona.nome} - ESCALA 1:{escala}", min(xs), top - 0.9 * f, apresentacao.TEXTO_MM)
    ex, ey = max(xs) + 1.5 * f, top - 0.2 * f
    for ang, rot in ((30, "+X"), (150, "+Y")):
        e = (ex + math.cos(math.radians(ang)) * 1.2 * f, ey + math.sin(math.radians(ang)) * 1.2 * f)
        d.linha((ex, ey), e, "ISO_AUX")
        d.texto(rot, e[0] + 0.2 * f, e[1], camada="ISO_AUX")
    d.linha((ex, ey), (ex, ey + 1.2 * f), "ISO_AUX")
    d.texto("+Z", ex + 0.2 * f, ey + 1.2 * f, camada="ISO_AUX")
    d.texto("Bico em operação: círculo duplo", min(xs), min(ys) - 1.3 * f, camada="ISO_AUX")

    out: dict[str, Any] = {"tubos": len(rede.tubos), "bicos": len(rede.bicos),
                           "largura_m": round(max(xs) - min(xs), 2),
                           "altura_m": round(max(ys) - min(ys), 2)}
    if quadro:
        largura_titulo = len(titulo) * 0.85 * apresentacao.altura_texto(
            escala, apresentacao.TEXTO_TITULO_MM)
        # o quadro não pode ficar sob o título, que pode ser mais largo que o desenho
        out["quadro"] = _quadro(d, rede, max(max(xs) + 5 * f, min(xs) + largura_titulo + 2 * f),
                                top)
    return out


def _quadro(d: _Iso, rede: Rede, x: float, y: float) -> dict[str, Any]:
    """Quadro de cálculo hidráulico (texto em colunas fixas, com linhas de grade)."""
    f, esc = d.f, d.escala
    h = apresentacao.altura_texto(esc, apresentacao.TEXTO_PEQUENO_MM)
    pitch = 2.0 * h
    colunas = [("TRECHO", 0.0), ("DE", 2.6), ("PARA", 4.6), ("TIPO", 6.8), ("DN", 9.8),
               ("L (m)", 11.4), ("Q (L/min)", 14.0), ("v (m/s)", 17.6), ("perda (bar)", 20.6)]
    esc_x = f * 1.0
    d.texto("QUADRO DE CÁLCULO HIDRÁULICO", x, y, apresentacao.TEXTO_MM, camada="ISO_QUADRO")
    y -= 2.2 * pitch
    for nome, dx in colunas:
        d.texto(nome, x + dx * esc_x, y, camada="ISO_QUADRO")
    d.linha((x, y - 0.5 * pitch), (x + 24.5 * esc_x, y - 0.5 * pitch), "ISO_QUADRO")
    y -= pitch
    linhas = 0
    for t in rede.tubos:
        y -= pitch
        vals = [t.id, t.de, t.para, t.tipo, f"{t.dn}" if t.dn else "-",
                _fmt(t.comprimento_m), _fmt(t.vazao_lpm, 1), _fmt(t.velocidade_ms),
                _fmt(t.perda_bar, 3)]
        for (_, dx), v in zip(colunas, vals, strict=True):
            d.texto(v, x + dx * esc_x, y, camada="ISO_QUADRO")
        linhas += 1
    r = rede.resumo
    y -= 0.5 * pitch
    d.linha((x, y), (x + 24.5 * esc_x, y), "ISO_QUADRO")
    rodape = [
        f"Bicos: {r['bicos']} em {r['ramais']} ramais; em operação: {r['bicos_em_operacao']} "
        f"({_fmt(r['area_de_operacao_m2'])} m²)",
        f"Vazão do bico remoto: {_fmt(r['vazao_do_bico_remoto_lpm'])} L/min a "
        f"{_fmt(r['pressao_do_bico_remoto_bar'], 3)} bar",
        f"Vazão total: {_fmt(r['vazao_total_lpm'], 1)} L/min",
        f"Pressão na base da prumada: {_fmt(r['pressao_na_base_da_prumada_bar'], 3)} bar "
        f"({_fmt(r['pressao_na_base_da_prumada_mca'])} mca)",
        "Hazen-Williams, conexões e VGA por premissa (ver memorial)",
    ]
    for linha in rodape:
        y -= pitch
        d.texto(linha, x, y, camada="ISO_QUADRO")
    return {"linhas": linhas, "x": round(x, 2), "y_final": round(y, 2)}
