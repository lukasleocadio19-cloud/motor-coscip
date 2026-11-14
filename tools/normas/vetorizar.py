"""Vetorização de imagens raster (placas e símbolos das NTs) em polígonos com furos.

Sem dependência nova: *marching squares* em numpy sobre um campo suave (0 a 1) ampliado por
interpolação, com encadeamento dos segmentos em anéis fechados, hierarquia anel/furo por
contenção e simplificação de Douglas-Peucker (shapely). Serve à extração dos desenhos oficiais
(NT 1-03, NT 2-05) para ``apps/mcp/coscip_mcp/simbolos_nt.json``.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage
from shapely.geometry import Polygon

Anel = list[tuple[float, float]]
Poligono = tuple[Anel, list[Anel]]  # (exterior, furos)

# segmentos por índice do caso (TL=8, TR=4, BR=2, BL=1); arestas: t=topo r=direita b=base l=esquerda
_CASOS: dict[int, list[tuple[str, str]]] = {
    1: [("l", "b")], 2: [("b", "r")], 3: [("l", "r")], 4: [("t", "r")], 6: [("t", "b")],
    7: [("t", "l")], 8: [("t", "l")], 9: [("t", "b")], 11: [("t", "r")], 12: [("l", "r")],
    13: [("r", "b")], 14: [("l", "b")],
}


def _aresta(chave: tuple[str, int, int], campo: np.ndarray, nivel: float) -> tuple[float, float]:
    tipo, i, j = chave
    if tipo == "h":  # entre (i, j) e (i, j+1)
        a, b = campo[i, j], campo[i, j + 1]
        t = (nivel - a) / (b - a) if b != a else 0.5
        return (j + t, float(i))
    a, b = campo[i, j], campo[i + 1, j]  # "v": entre (i, j) e (i+1, j)
    t = (nivel - a) / (b - a) if b != a else 0.5
    return (float(j), i + t)


def contornos(campo: np.ndarray, nivel: float = 0.5) -> list[Anel]:
    """Anéis fechados (x = coluna, y = linha, em índices do campo) onde o campo cruza ``nivel``.

    O campo é cercado por valores abaixo do nível: formas que tocam a borda fecham nela.
    """
    f = np.pad(campo.astype(float), 1, constant_values=float(min(campo.min(), nivel - 1.0)))
    b = f >= nivel
    idx = (b[:-1, :-1] * 8 + b[:-1, 1:] * 4 + b[1:, 1:] * 2 + b[1:, :-1] * 1).astype(int)
    vizinhos: dict[tuple, list[tuple]] = {}

    def liga(a: tuple, c: tuple) -> None:
        vizinhos.setdefault(a, []).append(c)
        vizinhos.setdefault(c, []).append(a)

    for i, j in zip(*np.nonzero((idx != 0) & (idx != 15)), strict=True):
        i, j = int(i), int(j)
        k = int(idx[i, j])
        chaves = {"t": ("h", i, j), "b": ("h", i + 1, j), "l": ("v", i, j), "r": ("v", i, j + 1)}
        if k in (5, 10):
            centro = (f[i, j] + f[i, j + 1] + f[i + 1, j] + f[i + 1, j + 1]) / 4 >= nivel
            if (k == 5) == centro:
                pares = [("t", "l"), ("b", "r")]
            else:
                pares = [("t", "r"), ("l", "b")]
        else:
            pares = _CASOS[k]
        for p, q in pares:
            liga(chaves[p], chaves[q])

    vistos: set[tuple] = set()
    aneis: list[Anel] = []
    for inicio in vizinhos:
        if inicio in vistos:
            continue
        caminho = [inicio]
        vistos.add(inicio)
        anterior, atual = None, inicio
        while True:
            proximos = [v for v in vizinhos[atual] if v != anterior]
            seguinte = next((v for v in proximos if v not in vistos), None)
            if seguinte is None:
                break
            caminho.append(seguinte)
            vistos.add(seguinte)
            anterior, atual = atual, seguinte
        if len(caminho) >= 3:
            # índices do campo com a moldura de 1 célula descontada
            aneis.append([(x - 1, y - 1) for x, y in (_aresta(c, f, nivel) for c in caminho)])
    return aneis


def poligonos(aneis: list[Anel]) -> list[Poligono]:
    """Agrupa os anéis em polígonos com furos pela profundidade de contenção (par/ímpar)."""
    formas = [Polygon(a).buffer(0) for a in aneis]
    ordem = sorted(range(len(aneis)), key=lambda i: -formas[i].area)
    profundidade = {}
    pai: dict[int, int | None] = {}
    for n, i in enumerate(ordem):
        continentes = [k for k in ordem[:n] if formas[k].contains(formas[i].representative_point())]
        profundidade[i] = len(continentes)
        pai[i] = continentes[-1] if continentes else None
    out: dict[int, tuple[Anel, list[Anel]]] = {}
    for i in ordem:
        if profundidade[i] % 2 == 0:
            out[i] = (aneis[i], [])
    for i in ordem:
        if profundidade[i] % 2 == 1 and pai[i] in out:
            out[pai[i]][1].append(aneis[i])
    return list(out.values())


def simplificar(poligono: Poligono, tolerancia: float) -> Poligono | None:
    """Douglas-Peucker em cada anel; descarta os anéis que colapsam (o exterior descarta tudo)."""
    def uma(a: Anel) -> Anel | None:
        p = Polygon(a).simplify(tolerancia, preserve_topology=True)
        if p.is_empty or p.geom_type != "Polygon" or p.area < tolerancia * tolerancia:
            return None
        return [(float(x), float(y)) for x, y in list(p.exterior.coords)[:-1]]

    ext = uma(poligono[0])
    if ext is None:
        return None
    furos = [f for f in (uma(a) for a in poligono[1]) if f is not None]
    return ext, furos


def vetorizar_campo(campo: np.ndarray, *, nivel: float = 0.5, ampliacao: int = 4,
                    suavizar: float = 0.0, tolerancia_px: float = 0.3) -> list[Poligono]:
    """Polígonos (em pixels da imagem original, y para baixo) da região onde ``campo`` ≥ ``nivel``.

    ``campo`` vai de 0 (fora) a 1 (dentro); é ampliado por interpolação cúbica para que o
    contorno saia em subpixel, como no desenho que originou a imagem.
    """
    c = campo.astype(float)
    if suavizar:
        c = ndimage.gaussian_filter(c, suavizar)
    k = ampliacao
    grande = np.clip(ndimage.zoom(c, k, order=3, grid_mode=True, mode="nearest"), 0.0, 1.0)
    saida: list[Poligono] = []
    for ext, furos in poligonos(contornos(grande, nivel)):
        # índice do campo ampliado -> pixel da imagem original (centro do pixel = +0,5)
        def px(a: Anel) -> Anel:
            return [((x + 0.5) / k, (y + 0.5) / k) for x, y in a]

        s = simplificar((px(ext), [px(f) for f in furos]), tolerancia_px)
        if s:
            saida.append(s)
    return saida
