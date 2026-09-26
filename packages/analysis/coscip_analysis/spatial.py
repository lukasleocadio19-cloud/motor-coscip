"""Grade de ocupação, interior da edificação e distância percorrida com obstáculos.

Método (registrado em cada fato):
- paredes/esquadrias fixas rasterizadas em células de ``h`` metros (amostragem a h/3);
- interior = células não alcançáveis a partir da borda depois de fechar vãos de até
  2 × ``close_m`` (portas externas); a faixa externa reaberta por reconstrução morfológica;
- bolsões finos (miolo de parede dupla) e menores que ``min_room_m2`` são descartados;
- distância percorrida = Dijkstra multi-origem numa grade de 16 vizinhos sem cortar quinas.
  O erro de direção da grade de 16 vizinhos é ≤ 2,7 %; a incerteza declarada soma 3 % da
  distância, 2 células e a incerteza de posição do símbolo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

GRID_REL_ERROR = 0.03
SYMBOL_POSITION_M = 0.30
MAX_CELLS = 1_500_000


@dataclass
class Grid:
    x0: float
    y0: float
    h: float
    nx: int
    ny: int

    @classmethod
    def around(cls, bbox: tuple[float, float, float, float], h: float | None = None,
               pad: float = 2.0) -> Grid:
        x0, y0, x1, y1 = bbox
        x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
        area = max((x1 - x0) * (y1 - y0), 1.0)
        if h is None:
            h = min(1.0, max(0.2, math.sqrt(area / 400_000)))
        nx, ny = int(math.ceil((x1 - x0) / h)) + 1, int(math.ceil((y1 - y0) / h)) + 1
        while nx * ny > MAX_CELLS:
            h *= 1.25
            nx, ny = int(math.ceil((x1 - x0) / h)) + 1, int(math.ceil((y1 - y0) / h)) + 1
        return cls(x0, y0, h, nx, ny)

    def cell(self, x: float, y: float) -> tuple[int, int]:
        return int((y - self.y0) // self.h), int((x - self.x0) // self.h)

    def center(self, r: int, c: int) -> tuple[float, float]:
        return self.x0 + (c + 0.5) * self.h, self.y0 + (r + 0.5) * self.h

    def inside(self, r: int, c: int) -> bool:
        return 0 <= r < self.ny and 0 <= c < self.nx

    def cell_area(self) -> float:
        return self.h * self.h


def rasterize(grid: Grid, segs: np.ndarray) -> np.ndarray:
    """Marca as células atravessadas por segmentos (x1, y1, x2, y2) em metros."""
    mask = np.zeros((grid.ny, grid.nx), dtype=bool)
    if not len(segs):
        return mask
    length = np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1])
    steps = np.maximum(1, np.ceil(length / (grid.h / 3.0)).astype(np.int64))
    total = int(steps.sum() + len(steps))
    # Amostragem vetorizada, em blocos para limitar memória.
    idx = np.repeat(np.arange(len(segs)), steps + 1)
    starts = np.repeat(np.cumsum(steps + 1) - (steps + 1), steps + 1)
    t = (np.arange(total) - starts) / np.repeat(steps, steps + 1)
    s = segs[idx]
    xs = s[:, 0] + t * (s[:, 2] - s[:, 0])
    ys = s[:, 1] + t * (s[:, 3] - s[:, 1])
    cols = ((xs - grid.x0) // grid.h).astype(np.int64)
    rows = ((ys - grid.y0) // grid.h).astype(np.int64)
    ok = (rows >= 0) & (rows < grid.ny) & (cols >= 0) & (cols < grid.nx)
    mask[rows[ok], cols[ok]] = True
    return mask


def _disk(r: int) -> np.ndarray:
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


@dataclass
class Interior:
    mask: np.ndarray
    area_m2: float
    uncertainty_m2: float
    dropped_pockets: int
    method: str


def interior(grid: Grid, walls: np.ndarray, clip: np.ndarray | None = None,
             close_m: float = 1.5, min_room_m2: float = 2.0) -> Interior:
    r = max(1, int(round(close_m / grid.h)))
    closed = ndimage.binary_dilation(walls, structure=_disk(r))
    border = np.zeros_like(walls)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    free_closed = ~closed
    lab, _ = ndimage.label(free_closed)
    outside_ids = np.unique(lab[border & free_closed])
    ext0 = np.isin(lab, outside_ids[outside_ids > 0])
    zone = ndimage.binary_dilation(ext0, structure=_disk(r + 1))
    # Reconstrução: exterior cresce pelo espaço livre real, mas só na faixa ``zone``.
    ext = ndimage.binary_propagation(ext0, mask=(~walls) & (zone | ext0))
    inner = ~walls & ~ext
    if clip is not None:
        inner &= clip
    lab4, n = ndimage.label(inner)
    dropped = 0
    if n:
        sizes = ndimage.sum(inner, lab4, index=np.arange(1, n + 1)) * grid.cell_area()
        depth = ndimage.distance_transform_edt(inner) * grid.h
        maxdepth = ndimage.maximum(depth, lab4, index=np.arange(1, n + 1))
        bad = np.where((sizes < min_room_m2) | (maxdepth <= 0.35))[0] + 1
        dropped = len(bad)
        if dropped:
            inner &= ~np.isin(lab4, bad)
    cells = int(inner.sum())
    perim = int((inner & ~ndimage.binary_erosion(inner)).sum())
    return Interior(
        inner, cells * grid.cell_area(), perim * grid.h * grid.h,
        dropped,
        f"grade {grid.h:.2f} m; vãos até {2 * r * grid.h:.1f} m fechados para achar o exterior; "
        f"bolsões < {min_room_m2} m² ou com largura ≤ 0,7 m descartados",
    )


# 16 vizinhos (metade, grafo não dirigido): deslocamento e células que não podem estar
# bloqueadas no caminho (evita cortar quina de parede).
_OFFSETS = (
    ((0, 1), ()), ((1, 0), ()),
    ((1, 1), ((0, 1), (1, 0))), ((1, -1), ((0, -1), (1, 0))),
    ((1, 2), ((0, 1), (1, 1))), ((2, 1), ((1, 0), (1, 1))),
    ((2, -1), ((1, 0), (1, -1))), ((1, -2), ((0, -1), (1, -1))),
)


def _shift(a: np.ndarray, dr: int, dc: int) -> np.ndarray:
    """out[r, c] = a[r + dr, c + dc] (False fora da grade)."""
    out = np.zeros_like(a)
    ny, nx = a.shape
    rs, re_ = max(0, -dr), min(ny, ny - dr)
    cs, ce = max(0, -dc), min(nx, nx - dc)
    if rs < re_ and cs < ce:
        out[rs:re_, cs:ce] = a[rs + dr:re_ + dr, cs + dc:ce + dc]
    return out


class Walker:
    """Grafo de caminhada sobre as células livres; reutilizado por todos os sistemas."""

    def __init__(self, grid: Grid, free: np.ndarray) -> None:
        self.grid, self.free = grid, free
        ids = -np.ones(free.shape, dtype=np.int64)
        ids[free] = np.arange(int(free.sum()))
        self.ids = ids
        rows, cols, w = [], [], []
        for (dr, dc), via in _OFFSETS:
            ok = free & _shift(free, dr, dc)
            for vr, vc in via:
                ok &= _shift(free, vr, vc)
            a = ids[ok]
            b = _shift(ids, dr, dc)[ok]
            rows.append(a)
            cols.append(b)
            w.append(np.full(len(a), grid.h * math.hypot(dr, dc)))
        n = int(free.sum())
        r = np.concatenate(rows) if rows else np.zeros(0, dtype=np.int64)
        c = np.concatenate(cols) if cols else np.zeros(0, dtype=np.int64)
        self.graph = coo_matrix((np.concatenate(w) if w else np.zeros(0), (r, c)),
                                shape=(n, n)).tocsr()
        self.n = n

    def snap(self, x: float, y: float, max_m: float = 1.0) -> tuple[int, int] | None:
        """Célula livre mais próxima do ponto (símbolo desenhado sobre a parede)."""
        g = self.grid
        r0, c0 = g.cell(x, y)
        k = int(math.ceil(max_m / g.h))
        best, best_d = None, None
        for r in range(r0 - k, r0 + k + 1):
            for c in range(c0 - k, c0 + k + 1):
                if g.inside(r, c) and self.free[r, c]:
                    cx, cy = g.center(r, c)
                    d = math.hypot(cx - x, cy - y)
                    if d <= max_m and (best_d is None or d < best_d):
                        best, best_d = (r, c), d
        return best

    def distances(self, cells: list[tuple[int, int]]) -> tuple[np.ndarray, np.ndarray,
                                                               np.ndarray]:
        """Distância (m) de cada célula livre à origem mais próxima; inf se inalcançável."""
        field = np.full(self.free.shape, np.inf)
        pred_grid = -np.ones(self.free.shape, dtype=np.int64)
        src_grid = -np.ones(self.free.shape, dtype=np.int64)
        nodes = sorted({int(self.ids[r, c]) for r, c in cells if self.ids[r, c] >= 0})
        if not nodes or self.n == 0:
            return field, pred_grid, src_grid
        dist, pred, src = dijkstra(self.graph, directed=False, indices=nodes, min_only=True,
                                   return_predecessors=True)
        field[self.free] = dist
        pred_grid[self.free] = pred
        src_grid[self.free] = src
        return field, pred_grid, src_grid

    def path_to(self, pred_grid: np.ndarray, r: int, c: int) -> list[tuple[float, float]]:
        node = int(self.ids[r, c])
        flat_pred = pred_grid[self.free]
        coords = np.argwhere(self.free)
        out = []
        guard = 0
        while node >= 0 and guard < 200_000:
            rr, cc = coords[node]
            out.append(self.grid.center(int(rr), int(cc)))
            node = int(flat_pred[node])
            guard += 1
        return out


def points_in_polygon(xs: np.ndarray, ys: np.ndarray, poly: np.ndarray) -> np.ndarray:
    """Teste par-ímpar vetorizado."""
    inside = np.zeros(xs.shape, dtype=bool)
    px, py = poly[:, 0], poly[:, 1]
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi, xj, yj = px[i], py[i], px[j], py[j]
        cond = (yi > ys) != (yj > ys)
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = (xj - xi) * (ys - yi) / (yj - yi) + xi
        inside ^= cond & (xs < xint)
        j = i
    return inside


def clip_mask(grid: Grid, poly: np.ndarray) -> np.ndarray:
    cy, cx = np.mgrid[0:grid.ny, 0:grid.nx]
    xs = grid.x0 + (cx + 0.5) * grid.h
    ys = grid.y0 + (cy + 0.5) * grid.h
    return points_in_polygon(xs, ys, poly)


def travel_uncertainty(d: float, h: float) -> float:
    return GRID_REL_ERROR * d + 2 * h + SYMBOL_POSITION_M


def direct_farthest(grid: Grid, free: np.ndarray,
                    points: list[tuple[float, float]]) -> tuple[float, tuple[float, float]] | None:
    """Maior distância em LINHA RETA de uma célula livre até o ponto mais próximo.

    É a medida do item 5.3.3.3 da NT 2-08 (projeto sem leiaute): distância direta, sem
    contornar paredes. Devolve a distância e o centro da célula mais desfavorável.
    """
    rows, cols = np.nonzero(free)
    if not len(rows) or not points:
        return None
    xs = grid.x0 + (cols + 0.5) * grid.h
    ys = grid.y0 + (rows + 0.5) * grid.h
    best = np.full(len(xs), np.inf)
    for px, py in points:
        best = np.minimum(best, np.hypot(xs - px, ys - py))
    i = int(np.argmax(best))
    return float(best[i]), (float(xs[i]), float(ys[i]))


def direct_uncertainty(h: float) -> float:
    """Meia diagonal da célula (ponto dentro dela) mais a posição do símbolo."""
    return math.sqrt(2) / 2 * h + SYMBOL_POSITION_M
