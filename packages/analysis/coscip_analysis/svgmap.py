"""Mapa SVG de uma região para o relatório (evidência visual, não medida).

Camadas: interior detectado, área além do limite de percurso de extintor, área sem acesso,
paredes, demais linhas (contexto), pior percurso e símbolos reconhecidos.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from coscip_analysis.plan import Plan
from coscip_analysis.spatial import Grid

MAX_CONTEXT_SEGMENTS = 25_000
MAX_WALL_SEGMENTS = 60_000

CLASS_STYLE = {
    "EXTINTOR": ("#c62828", "E"), "HIDRANTE": ("#1565c0", "H"), "MANGOTINHO": ("#1565c0", "M"),
    "ACIONADOR_MANUAL": ("#6a1b9a", "A"), "AVISADOR": ("#6a1b9a", "V"),
    "CENTRAL_ALARME": ("#6a1b9a", "C"), "DETECTOR": ("#00838f", "D"),
    "ILUMINACAO_EMERGENCIA": ("#f9a825", "L"), "SAIDA": ("#2e7d32", "S"),
    "SINALIZACAO": ("#2e7d32", "P"), "SPRINKLER": ("#0277bd", "K"),
    "BOMBA_INCENDIO": ("#1565c0", "B"), "REGISTRO_RECALQUE": ("#1565c0", "R"),
}


def _runs(mask: np.ndarray, grid: Grid, y_top: float, cls: str) -> list[str]:
    out = []
    ny, _ = mask.shape
    h = grid.h
    for r in range(ny):
        row = mask[r]
        if not row.any():
            continue
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
        y = y_top - (grid.y0 + (r + 1) * h)
        for s, e in zip(starts, ends, strict=True):
            out.append(f'<rect class="{cls}" x="{grid.x0 + s * h:.2f}" y="{y:.2f}" '
                       f'width="{(e - s) * h:.2f}" height="{h:.2f}"/>')
    return out


def _segments_path(segs: np.ndarray, y_top: float) -> str:
    return "".join(f"M{a:.2f} {y_top - b:.2f}L{c:.2f} {y_top - e:.2f}"
                   for a, b, c, e in segs)


def region_map(region, grid: Grid, free: np.ndarray, plan: Plan, walls_sel: np.ndarray,  # noqa: ANN001
               symbols: list, fields: dict[str, tuple[np.ndarray, np.ndarray]],
               results: list[dict[str, Any]], rooms: list,
               coverage: dict[str, Any]) -> str:
    x0, y0, x1, y1 = region.bbox
    pad = 1.0
    y_top = y1  # SVG cresce para baixo: y_svg = y_top - y
    w, h = x1 - x0 + 2 * pad, y1 - y0 + 2 * pad
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0 - pad:.2f} {-pad:.2f} '
             f'{w:.2f} {h:.2f}" class="plan-map" role="img" '
             f'aria-label="Mapa da análise: {_esc(region.name)}">',
             "<style>.in{fill:#e6f2f0}.far{fill:#e53935;fill-opacity:.45}"
             ".nr{fill:#fb8c00;fill-opacity:.55}.wall{stroke:#263238;fill:none}"
             ".ctx{stroke:#b0bec5;fill:none}.path{stroke:#b71c1c;fill:none;"
             "stroke-dasharray:4 3}.sym text{font:bold 0.45px sans-serif;fill:#fff;"
             "text-anchor:middle;dominant-baseline:central}.lbl{font:0.6px sans-serif;"
             "fill:#37474f}</style>"]
    parts.append('<g aria-hidden="true">' + "".join(_runs(free, grid, y_top, "in")) + "</g>")

    limit = next((float(r["trace"]["required"]) for r in results
                  if r.get("measured_fact") == "floor.extinguisher.max_travel_m"
                  and r.get("trace", {}).get("required")), None)
    if "extinguisher" in fields:
        dist, _ = fields["extinguisher"]
        if limit is not None:
            far = free & np.isfinite(dist) & (dist > limit)
            parts.append("<g>" + "".join(_runs(far, grid, y_top, "far")) + "</g>")
        nr = free & ~np.isfinite(dist)
        parts.append("<g>" + "".join(_runs(nr, grid, y_top, "nr")) + "</g>")

    sel_idx = np.where(walls_sel)[0][:MAX_WALL_SEGMENTS]
    ctx_mask = ~walls_sel & _overlap(plan.segments, (x0, y0, x1, y1))
    ctx_idx = np.where(ctx_mask)[0]
    if len(ctx_idx) > MAX_CONTEXT_SEGMENTS:
        ctx_idx = ctx_idx[:: int(np.ceil(len(ctx_idx) / MAX_CONTEXT_SEGMENTS))]
    parts.append(f'<path class="ctx" vector-effect="non-scaling-stroke" stroke-width="0.6" '
                 f'd="{_segments_path(plan.segments[ctx_idx], y_top)}"/>')
    parts.append(f'<path class="wall" vector-effect="non-scaling-stroke" stroke-width="1.2" '
                 f'd="{_segments_path(plan.segments[sel_idx], y_top)}"/>')

    path = (coverage.get("extinguisher") or {}).get("worst_path") or []
    if path:
        pts = " ".join(f"{x:.2f},{y_top - y:.2f}" for x, y in path)
        wx, wy = path[0]
        parts.append(f'<polyline class="path" vector-effect="non-scaling-stroke" '
                     f'stroke-width="1.5" points="{pts}"/><g stroke="#b71c1c" '
                     f'stroke-width="0.12"><line x1="{wx - .4:.2f}" y1="{y_top - wy - .4:.2f}" '
                     f'x2="{wx + .4:.2f}" y2="{y_top - wy + .4:.2f}"/><line x1="{wx - .4:.2f}" '
                     f'y1="{y_top - wy + .4:.2f}" x2="{wx + .4:.2f}" y2="{y_top - wy - .4:.2f}"/>'
                     "</g>")
    for r in rooms:
        parts.append(f'<text class="lbl" x="{r.x:.2f}" y="{y_top - r.y:.2f}">'
                     f'{_esc(r.label[:40])}</text>')
    parts.append('<g class="sym">')
    for s in symbols:
        color, letter = CLASS_STYLE.get(s.cls, ("#455a64", "?"))
        cx, cy = s.x, y_top - s.y
        if s.excluded:
            parts.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="0.3" fill="none" '
                         f'stroke="#90a4ae" stroke-width="0.06"><title>{_esc(s.cls)} '
                         f'({_esc(s.excluded)})</title></circle>')
            continue
        parts.append(f'<g><circle cx="{cx:.2f}" cy="{cy:.2f}" r="0.35" fill="{color}"/>'
                     f'<text x="{cx:.2f}" y="{cy:.2f}">{letter}</text>'
                     f'<title>{_esc(s.cls)} · handle {_esc(s.handle)}</title></g>')
    parts.append("</g></svg>")
    return "".join(parts)


def _overlap(segs: np.ndarray, bbox: tuple[float, float, float, float]) -> np.ndarray:
    x0, y0, x1, y1 = bbox
    if not len(segs):
        return np.zeros(0, dtype=bool)
    return ((np.maximum(segs[:, 0], segs[:, 2]) >= x0) & (np.minimum(segs[:, 0], segs[:, 2]) <= x1)
            & (np.maximum(segs[:, 1], segs[:, 3]) >= y0)
            & (np.minimum(segs[:, 1], segs[:, 3]) <= y1))


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))
