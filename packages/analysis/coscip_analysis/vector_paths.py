"""Distância percorrida vetorial (plano de correção, F7.1) e conferência por Fast Marching (F7.2).

Método principal — exato a menos de uma tolerância declarada:

- paredes do DXF como obstáculos vetoriais: cada segmento vira um retângulo de meia-largura
  ``wall_m`` (linha de desenho não tem espessura); portas abertas são os vãos entre elas;
- **grafo de visibilidade** (Shapely + SciPy): nós = vértices convexos dos obstáculos,
  afastados ``clear_m``, mais as origens (símbolos); aresta = segmento livre. O menor caminho
  euclidiano entre dois pontos é exato (sem erro de discretização);
- **pior ponto** do pavimento por *branch and bound*: a distância geodésica é 1-Lipschitz, então
  numa célula quadrada livre de obstáculos ``d(q) ≤ d(centro) + meia diagonal``. Células cujo
  limite superior não passa do melhor valor já achado são descartadas; as demais são divididas
  até a meia diagonal ≤ ``tol_m``. O erro de amostragem declarado é o limite superior que
  sobrou menos o valor achado (≤ ``tol_m``).

Conferência independente: Fast Marching (``scikit-fmm``, eikonal) numa grade fina sobre o
mesmo interior. Se o vetorial e o FMM divergirem mais que a soma das incertezas, a geometria
não é consistente e nada conclui (``quality.geometry.consistent = false``).
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import shapely
import shapely.ops
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from shapely.geometry import Point, Polygon, box
from shapely.geometry.polygon import orient

from coscip_analysis.spatial import Grid, interior, rasterize

VECTOR_ALGORITHM = "visibility_graph_bnb"
VECTOR_ALGORITHM_VERSION = "1.0"
FMM_ALGORITHM = "scikit_fmm_eikonal"
FMM_ALGORITHM_VERSION = "1.0"
WALL_M = 0.01  # meia-largura de uma linha de parede tratada como obstáculo
CLEAR_M = 0.005  # folga dos nós em relação ao obstáculo
TOL_M = 0.05  # erro máximo de amostragem do pior ponto
MAX_NODES = 2500  # acima disso o vetorial não roda (complexidade): fica o método de grade
MAX_EVALS = 60_000


@dataclass
class VectorDomain:
    """Obstáculos, nós do grafo e o teste de "ponto dentro do pavimento"."""

    obstacles: Any  # shapely (preparada)
    nodes: np.ndarray  # (n, 2)
    region: Polygon
    grid: Grid
    inner: np.ndarray  # interior em grade (h)
    wall_m: float
    clear_m: float
    skipped: str | None = None


@dataclass
class VectorResult:
    value: float
    point: tuple[float, float]
    sampling_error: float
    bends: int
    path: list[tuple[float, float]]
    evaluations: int
    nodes: int
    snap_m: float
    unreachable: bool = False
    notes: list[str] = field(default_factory=list)
    source: int = 0  # índice da origem a que o pior ponto chega


def build_domain(segs: np.ndarray, region: Polygon, grid: Grid, inner: np.ndarray,
                 wall_m: float = WALL_M, clear_m: float = CLEAR_M) -> VectorDomain:
    lines = shapely.linestrings(segs.reshape(-1, 2, 2)) if len(segs) else []
    core = shapely.union_all(shapely.buffer(lines, wall_m, cap_style="square",
                                            join_style="mitre")) if len(segs) else Polygon()
    core = core.intersection(region.buffer(1.0))
    shapely.prepare(core)
    nodes = _convex_nodes(core, clear_m, region)
    dom = VectorDomain(core, nodes, region, grid, inner, wall_m, clear_m)
    if len(nodes) > MAX_NODES:
        dom.skipped = f"{len(nodes)} nós no grafo de visibilidade (limite {MAX_NODES})"
    return dom


def _convex_nodes(core: Any, clear_m: float, region: Polygon) -> np.ndarray:
    if core.is_empty:
        return np.zeros((0, 2))
    grown = core.buffer(clear_m, join_style="mitre", mitre_limit=10.0)
    polys = list(grown.geoms) if hasattr(grown, "geoms") else [grown]
    out = []
    for poly in polys:
        if poly.geom_type != "Polygon":
            continue
        poly = orient(poly, 1.0)  # material do obstáculo sempre à esquerda do percurso
        for ring in (poly.exterior, *poly.interiors):
            pts = np.asarray(ring.coords)[:-1]
            if len(pts) < 3:
                continue
            prev, nxt = np.roll(pts, 1, axis=0), np.roll(pts, -1, axis=0)  # vizinhos no anel
            a, b = pts - prev, nxt - pts
            cross = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
            out.append(pts[cross > 1e-12])  # vértice convexo do obstáculo: onde o caminho dobra
    if not out:
        return np.zeros((0, 2))
    nodes = np.unique(np.round(np.concatenate(out), 9), axis=0)
    keep = shapely.contains_xy(region.buffer(0.5), nodes[:, 0], nodes[:, 1])
    return nodes[keep]


def _visible(dom: VectorDomain, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Segmentos a[i]→b[i] que não tocam obstáculo (vetorizado)."""
    if dom.obstacles.is_empty or not len(a):
        return np.ones(len(a), dtype=bool)
    segs = shapely.linestrings(np.stack([a, b], axis=1))
    same = np.all(np.isclose(a, b), axis=1)
    out = ~shapely.intersects(dom.obstacles, segs)
    out[same] = ~shapely.intersects_xy(dom.obstacles, a[same, 0], a[same, 1]) if same.any() \
        else out[same]
    return out


def _free(dom: VectorDomain, pts: np.ndarray) -> np.ndarray:
    """Ponto no pavimento: dentro do recorte, fora de obstáculo e no interior — a célula de
    grade dele é interior, ou ele enxerga o centro de uma célula interior vizinha (faixa junto
    à parede que a grade não cobre)."""
    if not len(pts):
        return np.zeros(0, dtype=bool)
    g = dom.grid
    ok = shapely.contains_xy(dom.region, pts[:, 0], pts[:, 1])
    if not dom.obstacles.is_empty:
        ok &= ~shapely.intersects_xy(dom.obstacles, pts[:, 0], pts[:, 1])
    r = ((pts[:, 1] - g.y0) // g.h).astype(int)
    c = ((pts[:, 0] - g.x0) // g.h).astype(int)
    inside = (r >= 0) & (r < g.ny) & (c >= 0) & (c < g.nx)
    cell_in = np.zeros(len(pts), dtype=bool)
    cell_in[inside] = dom.inner[r[inside], c[inside]]
    result = ok & cell_in
    todo = np.nonzero(ok & ~cell_in & inside)[0]
    for i in todo:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr, cc = r[i] + dr, c[i] + dc
                if 0 <= rr < g.ny and 0 <= cc < g.nx and dom.inner[rr, cc]:
                    center = np.array([g.center(rr, cc)])
                    if _visible(dom, pts[i:i + 1], center)[0]:
                        result[i] = True
                        break
            if result[i]:
                break
    return result


def _snap_source(dom: VectorDomain, p: tuple[float, float]) -> tuple[np.ndarray, float]:
    """Símbolo desenhado sobre a parede: vai para o ponto livre mais próximo (registrado)."""
    pt = np.array([p])
    if dom.obstacles.is_empty or not shapely.intersects_xy(dom.obstacles, p[0], p[1]):
        return pt[0], 0.0
    grown = dom.obstacles.buffer(dom.clear_m * 2, join_style="mitre")
    near = shapely.ops.nearest_points(grown.boundary, Point(p))[0]
    q = np.array([near.x, near.y])
    return q, float(np.hypot(*(q - pt[0])))


class Geodesic:
    """Distância geodésica às origens: Dijkstra no grafo de visibilidade."""

    def __init__(self, dom: VectorDomain, sources: list[tuple[float, float]]) -> None:
        self.dom = dom
        snapped = [_snap_source(dom, s) for s in sources]
        self.sources = np.array([s for s, _ in snapped]) if snapped else np.zeros((0, 2))
        self.snap_m = max((d for _, d in snapped), default=0.0)
        self.pts = np.concatenate([self.sources, dom.nodes]) if len(dom.nodes) else self.sources
        n = len(self.pts)
        ii, jj = np.triu_indices(n, k=1)
        vis = np.zeros(len(ii), dtype=bool)
        for lo in range(0, len(ii), 200_000):
            sl = slice(lo, lo + 200_000)
            vis[sl] = _visible(dom, self.pts[ii[sl]], self.pts[jj[sl]])
        a, b = ii[vis], jj[vis]
        w = np.hypot(*(self.pts[a] - self.pts[b]).T)
        graph = coo_matrix((w, (a, b)), shape=(n, n)).tocsr()
        k = len(self.sources)
        if k:
            dist, pred, _src = dijkstra(graph, directed=False, indices=list(range(k)),
                                  min_only=True, return_predecessors=True)
        else:
            dist, pred = np.full(n, np.inf), -np.ones(n, dtype=int)
        self.D, self.pred = dist, pred

    def at(self, q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Distância em cada ponto de ``q`` e o nó por onde ele chega (-1 = inalcançável)."""
        n = len(self.pts)
        out = np.full(len(q), np.inf)
        via = -np.ones(len(q), dtype=int)
        finite = np.isfinite(self.D)
        if not finite.any():
            return out, via
        idx = np.nonzero(finite)[0]
        P = self.pts[idx]
        for lo in range(0, len(q), max(1, 200_000 // max(1, len(idx)))):
            chunk = q[lo:lo + max(1, 200_000 // max(1, len(idx)))]
            A = np.repeat(chunk, len(idx), axis=0)
            B = np.tile(P, (len(chunk), 1))
            vis = _visible(self.dom, A, B).reshape(len(chunk), len(idx))
            cost = self.D[idx][None, :] + np.hypot(chunk[:, None, 0] - P[None, :, 0],
                                                   chunk[:, None, 1] - P[None, :, 1])
            cost = np.where(vis, cost, np.inf)
            best = np.argmin(cost, axis=1)
            out[lo:lo + len(chunk)] = cost[np.arange(len(chunk)), best]
            via[lo:lo + len(chunk)] = np.where(np.isfinite(out[lo:lo + len(chunk)]),
                                               idx[best], -1)
        del n
        return out, via

    def path(self, q: tuple[float, float], via: int) -> list[tuple[float, float]]:
        out = [q]
        node, guard = via, 0
        while node >= 0 and guard < 10_000:
            out.append((float(self.pts[node][0]), float(self.pts[node][1])))
            if node < len(self.sources):
                break
            node = int(self.pred[node])
            guard += 1
        return out


def worst_point(dom: VectorDomain, sources: list[tuple[float, float]],
                tol_m: float = TOL_M, start_m: float = 1.0) -> VectorResult | None:
    """Maior distância geodésica do pavimento até a origem mais próxima (branch and bound).

    Célula livre de obstáculo: ``d ≤ d(centro) + meia diagonal`` (1-Lipschitz). Célula que
    toca parede é amostrada em 9 pontos e o limite usa a diagonal inteira; sem ponto livre,
    herda o limite da célula-mãe. Tudo é dividido até a meia diagonal ≤ ``tol_m``. O que a
    amostragem não enxerga atrás de uma parede dentro de uma célula mínima é conferido pelo
    método independente (FMM): divergência entre os dois bloqueia a conclusão."""
    if dom.skipped or not sources:
        return None
    geo = Geodesic(dom, sources)
    x0, y0, x1, y1 = dom.region.bounds
    size = max(start_m, dom.grid.h)
    heap: list[tuple[float, float, float, float, bool]] = []  # (-limite, x, y, lado, parede)
    state = {"best": -math.inf, "pt": None, "via": -1, "evals": 0, "unreach": False}
    leaf_ub = -math.inf
    offsets9 = np.array([(dx, dy) for dx in (-0.5, 0, 0.5) for dy in (-0.5, 0, 0.5)])

    def push_cells(cells: list[tuple[float, float, float]], parent_ub: float) -> None:
        if not cells:
            return
        arr = np.array(cells)
        blocked = _cells_blocked(dom, arr)
        samples, owner = [], []
        for i, (cx, cy, side) in enumerate(cells):
            pts = [(cx, cy)] if not blocked[i] else [
                (cx + ox * side * 0.999, cy + oy * side * 0.999) for ox, oy in offsets9]
            samples += pts
            owner += [i] * len(pts)
        samples_a, owner_a = np.array(samples), np.array(owner)
        free = _free(dom, samples_a)
        dist = np.full(len(samples_a), np.nan)
        via = -np.ones(len(samples_a), dtype=int)
        if free.any():
            d, v = geo.at(samples_a[free])
            dist[free], via[free] = d, v
        state["evals"] += int(free.sum())
        for i, (cx, cy, side) in enumerate(cells):
            mine = owner_a == i
            ds = dist[mine]
            if np.isinf(ds).any():
                state["unreach"] = True
            ok = np.isfinite(ds)
            half = side * math.sqrt(2) / 2
            if ok.any():
                k = int(np.argmax(np.where(ok, ds, -np.inf)))
                dmax = float(ds[k])
                if dmax > state["best"]:
                    idx = np.nonzero(mine)[0][k]
                    state.update(best=dmax, pt=(float(samples_a[idx][0]),
                                                float(samples_a[idx][1])), via=int(via[idx]))
                ub = dmax + (2 * half if blocked[i] else half)
            elif blocked[i] and math.isfinite(parent_ub) and \
                    dom.region.intersects(box(cx - side / 2, cy - side / 2,
                                              cx + side / 2, cy + side / 2)):
                ub = parent_ub  # sem amostra livre: vale o limite da mãe
            else:
                continue
            heapq.heappush(heap, (-ub, cx, cy, side, bool(blocked[i])))

    nx, ny = max(1, math.ceil((x1 - x0) / size)), max(1, math.ceil((y1 - y0) / size))
    push_cells([(x0 + (i + 0.5) * size, y0 + (j + 0.5) * size, size)
                for i in range(nx) for j in range(ny)], math.inf)
    while heap and state["evals"] < MAX_EVALS:
        neg_ub, cx, cy, side, near_wall = heapq.heappop(heap)
        ub = -neg_ub
        if ub <= state["best"] + 1e-12:
            heapq.heappush(heap, (neg_ub, cx, cy, side, near_wall))
            break  # nenhuma célula restante pode superar o melhor valor
        # junto à parede o limite usa a diagonal inteira: a folha é menor para o mesmo erro
        if side * math.sqrt(2) / 2 * (2 if near_wall else 1) <= tol_m:
            leaf_ub = max(leaf_ub, ub)
            continue
        q = side / 4
        push_cells([(cx + dx * q, cy + dy * q, side / 2) for dx in (-1, 1) for dy in (-1, 1)],
                   ub)
    if state["pt"] is None:
        return None
    best = state["best"]
    remaining = max([leaf_ub, *(-u for u, *_ in heap)], default=best)
    sampling = max(0.0, remaining - best)
    path = geo.path(state["pt"], state["via"])
    end = path[-1]
    src_idx = int(np.argmin(np.hypot(geo.sources[:, 0] - end[0], geo.sources[:, 1] - end[1])))
    return VectorResult(value=best, point=state["pt"], sampling_error=sampling, source=src_idx,
                        bends=max(0, len(path) - 2), path=path, evaluations=state["evals"],
                        nodes=len(dom.nodes), snap_m=geo.snap_m, unreachable=state["unreach"],
                        notes=([] if state["evals"] < MAX_EVALS
                               else ["limite de avaliações atingido"]))


def _cells_blocked(dom: VectorDomain, arr: np.ndarray) -> np.ndarray:
    if dom.obstacles.is_empty:
        return np.zeros(len(arr), dtype=bool)
    half = arr[:, 2] / 2
    boxes = shapely.box(arr[:, 0] - half, arr[:, 1] - half, arr[:, 0] + half, arr[:, 1] + half)
    return shapely.intersects(dom.obstacles, boxes)


# ------------------------------------------------------------------------ Fast Marching

@dataclass
class FmmResult:
    value: float
    point: tuple[float, float]
    h: float
    uncertainty: float


@dataclass
class FmmGrid:
    """Grade fina e interior do FMM, montados uma vez por pavimento."""

    grid: Grid
    free: np.ndarray


def fmm_grid(segs: np.ndarray, region: Polygon, h: float = 0.05,
             max_cells: int = 1_000_000) -> FmmGrid | None:
    grid = Grid.around(region.bounds, h=h, pad=2.5)  # > fechamento de 1,5 m do interior
    while grid.nx * grid.ny > max_cells:
        grid = Grid.around(region.bounds, h=grid.h * 1.5, pad=2.5)
    walls = rasterize(grid, segs)
    cy, cx = np.mgrid[0:grid.ny, 0:grid.nx]
    xs, ys = grid.x0 + (cx + 0.5) * grid.h, grid.y0 + (cy + 0.5) * grid.h
    clip = shapely.contains_xy(region, xs, ys)
    free = interior(grid, walls, clip).mask
    return FmmGrid(grid, free) if free.any() else None


def fmm_worst(fg: FmmGrid | None, sources: list[tuple[float, float]]) -> FmmResult | None:
    """Segundo método: eikonal por Fast Marching na grade fina, mesmo interior."""
    import skfmm

    if fg is None or not sources:
        return None
    grid, free = fg.grid, fg.free
    phi = np.ones(free.shape)
    for sx, sy in sources:
        r, c = grid.cell(sx, sy)
        rr, cc = _nearest_free(free, r, c)
        if rr is not None:
            phi[rr, cc] = -1.0
    if (phi > 0).all():
        return None
    d = skfmm.distance(np.ma.MaskedArray(phi, ~free), dx=grid.h)
    field_ = np.where(free, np.ma.filled(d, np.nan) + grid.h / 2, np.nan)
    if not np.isfinite(field_).any():
        return None
    i = int(np.nanargmax(field_))
    r, c = divmod(i, grid.nx)
    value = float(field_.flat[i])
    unc = 3 * grid.h + 0.02 * value  # 1ª/2ª ordem, contorno em escada e origem na célula
    return FmmResult(value, grid.center(r, c), grid.h, unc)


def _nearest_free(free: np.ndarray, r: int, c: int, k: int = 40) -> tuple[int | None, int]:
    ny, nx = free.shape
    for rad in range(k):
        for dr in range(-rad, rad + 1):
            for dc in range(-rad, rad + 1):
                rr, cc = r + dr, c + dc
                if max(abs(dr), abs(dc)) == rad and 0 <= rr < ny and 0 <= cc < nx \
                        and free[rr, cc]:
                    return rr, cc
    return None, 0


def region_polygon(poly: np.ndarray) -> Polygon:
    p = Polygon(poly)
    return p if p.is_valid else p.buffer(0)


def uncertainty_budget(result: VectorResult, *, symbol_half_size_m: float,
                       scale_rel: float, wall_m: float = WALL_M,
                       clear_m: float = CLEAR_M) -> dict[str, dict[str, Any]]:
    """Orçamento de incerteza (F7.3): cada parcela com a origem; total = soma (conservador)."""
    budget = {
        "metodo": {"m": 0.0, "origem": "grafo de visibilidade: menor caminho euclidiano exato"},
        "amostragem": {"m": round(result.sampling_error, 4),
                       "origem": "branch and bound (1-Lipschitz): limite superior restante "
                                 "menos o pior valor achado"},
        "posicao_do_simbolo": {"m": round(symbol_half_size_m + result.snap_m, 4),
                               "origem": "metade do tamanho do símbolo"
                                         + (" + deslocamento para fora da parede"
                                            if result.snap_m else "")},
        "unidade_escala": {"m": round(scale_rel * result.value, 4),
                           "origem": ("unidade padrão confirmada: escala exata" if not scale_rel
                                      else f"{scale_rel:.2%} da distância")},
        "modelagem_de_parede": {"m": round(2 * (wall_m + clear_m) * max(1, result.bends), 4),
                                "origem": f"linhas de parede com meia-largura {wall_m} m e "
                                          f"folga {clear_m} m, por dobra do caminho"},
    }
    # Total arredondado PARA CIMA ao milímetro: o valor declarado nunca é menor que a soma.
    total = math.ceil(round(sum(v["m"] for v in budget.values()), 6) * 1000) / 1000
    budget["total"] = {"m": total, "origem": "soma, arredondada para cima ao milímetro"}
    return budget


__all__ = ["VECTOR_ALGORITHM", "VECTOR_ALGORITHM_VERSION", "FMM_ALGORITHM", "VectorDomain",
           "VectorResult", "FmmResult", "build_domain", "worst_point", "fmm_worst",
           "uncertainty_budget", "region_polygon", "box"]
