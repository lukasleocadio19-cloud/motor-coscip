"""Regiões de análise e leitura dos textos da planta (ambientes e áreas declaradas).

Região = pavimento recortado pelo analista (confirmado) ou, na falta dele, um agrupamento
automático das paredes do Model (várias plantas lado a lado são comuns: corpus 19/09).
Região automática é SUGESTÃO: os resultados dela ficam em revisão humana.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import ndimage

from coscip_analysis.dictionary import SymbolDictionary
from coscip_analysis.plan import ClosedPolyline, Plan, TextRec
from coscip_analysis.spatial import points_in_polygon

_AREA = re.compile(r"(?<![\d,.])(\d{1,6}(?:[.,]\d{1,3})?)\s*m\s*[²2](?![0-9])", re.I)
_UPPER_WORD = re.compile(r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{3,}")
MAX_CLUSTER_SEGMENT_M = 15.0


@dataclass
class Region:
    id: str
    name: str
    source: str  # FLOOR | AUTO
    confirmed: bool
    polygon: np.ndarray  # (n, 2) metros
    floor_id: str | None = None
    kind: str = "PLAN"  # PLAN | OTHER
    notes: list[str] = field(default_factory=list)

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        p = self.polygon
        return (float(p[:, 0].min()), float(p[:, 1].min()),
                float(p[:, 0].max()), float(p[:, 1].max()))

    def contains(self, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
        return points_in_polygon(np.asarray(xs, float), np.asarray(ys, float), self.polygon)

    def summary(self) -> dict[str, Any]:
        x0, y0, x1, y1 = self.bbox
        return {"id": self.id, "name": self.name, "source": self.source,
                "confirmed": self.confirmed, "floor_id": self.floor_id, "kind": self.kind,
                "bbox_m": [round(v, 3) for v in (x0, y0, x1, y1)], "notes": self.notes,
                "polygon_m": [[round(float(x), 3), round(float(y), 3)] for x, y in self.polygon]}


def floor_regions(floors: list[dict[str, Any]], scale: float) -> list[Region]:
    out = []
    for f in floors:
        clip = f["clip"]
        if clip.get("type") == "POLYGON":
            pts = np.asarray(clip["points"], dtype=float) * scale
        else:
            x0, y0, x1, y1 = (clip[k] * scale for k in ("x0", "y0", "x1", "y1"))
            pts = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
        out.append(Region(f"floor-{f['id'][:8]}", f["name"], "FLOOR", True, pts,
                          floor_id=f["id"]))
    return out


def auto_regions(plan: Plan, d: SymbolDictionary, clusters: list[TextCluster],
                 cell: float = 2.0) -> list[Region]:
    """Agrupa a geometria do Model em desenhos separados (componentes conexos).

    Usa todas as linhas com até ``MAX_CLUSTER_SEGMENT_M``: molduras de prancha e limites de
    terreno (linhas longas) não emendam plantas vizinhas. Plantas vindas de PDF (layers
    ``PDF_*``) também viram região, mesmo sem layer de parede.
    """
    segs = plan.segments
    if not len(segs):
        return []
    length = np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1])
    segs = segs[length <= MAX_CLUSTER_SEGMENT_M]
    if not len(segs):
        return []
    pts = np.vstack([segs[:, :2], segs[:, 2:], (segs[:, :2] + segs[:, 2:]) / 2])
    lo = np.percentile(pts, 0.2, axis=0) - 5
    hi = np.percentile(pts, 99.8, axis=0) + 5
    span = hi - lo
    cell = max(cell, math.sqrt(float(span[0] * span[1]) / 3_000_000))
    nx, ny = int(span[0] // cell) + 1, int(span[1] // cell) + 1
    occ = np.zeros((ny, nx), dtype=bool)
    ok = np.all((pts >= lo) & (pts <= hi), axis=1)
    cols = ((pts[ok, 0] - lo[0]) // cell).astype(int)
    rows = ((pts[ok, 1] - lo[1]) // cell).astype(int)
    occ[rows, cols] = True
    grown = ndimage.binary_dilation(occ, iterations=2)
    lab, _ = ndimage.label(grown, structure=np.ones((3, 3)))
    regions: list[Region] = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        if sl is None:
            continue
        count = int((occ[sl] & (lab[sl] == i)).sum())
        y0, y1 = lo[1] + sl[0].start * cell, lo[1] + sl[0].stop * cell
        x0, x1 = lo[0] + sl[1].start * cell, lo[0] + sl[1].stop * cell
        if (x1 - x0) * (y1 - y0) < 30 or count < 15:
            continue
        poly = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=float)
        regions.append(Region("", "", "AUTO", False, poly))
    regions.sort(key=lambda r: (-round(r.bbox[3] / 50), r.bbox[0]))
    for k, r in enumerate(regions, start=1):
        r.id = f"auto-{k}"
        r.name = _region_title(r, clusters, d) or f"Região automática {k}"
    return regions


def _region_title(r: Region, clusters: list[TextCluster], d: SymbolDictionary) -> str | None:
    x0, y0, x1, y1 = r.bbox
    w, h = x1 - x0, y1 - y0
    best = None
    for c in clusters:
        # Título costuma ficar logo abaixo ou dentro do desenho.
        if not (x0 - 0.1 * w <= c.x <= x1 + 0.1 * w and y0 - 0.25 * h - 6 <= c.y <= y1):
            continue
        if any(p.search(c.text) for p in d.region_titles) and len(c.text) <= 60:
            letters = [ch for ch in c.text if ch.isalpha()]
            upper = sum(ch.isupper() for ch in letters) >= 0.8 * max(1, len(letters))
            score = (("PLANTA" in c.text.upper()) * 2 + upper, -abs(c.y - y0))
            if best is None or score > best[0]:
                best = (score, c.text)
    return best[1] if best else None


# --- textos -----------------------------------------------------------------
@dataclass
class TextCluster:
    text: str
    x: float
    y: float
    handles: list[str]
    layers: list[str]


def cluster_texts(texts: list[TextRec], radius: float = 1.0) -> list[TextCluster]:
    """Junta linhas de um mesmo rótulo (ex.: "CASA DE" + "BOMBAS"; "QUARTO 01" + "7,80 m²")."""
    n = len(texts)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    cells: dict[tuple[int, int], list[int]] = {}
    for i, t in enumerate(texts):
        if len(t.text) > 80:
            continue
        cells.setdefault((math.floor(t.x / radius), math.floor(t.y / radius)), []).append(i)
    for (cx, cy), members in cells.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in cells.get((cx + dx, cy + dy), ()):
                    for i in members:
                        if i < j and math.hypot(texts[i].x - texts[j].x,
                                                texts[i].y - texts[j].y) <= radius:
                            parent[find(i)] = find(j)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        if len(texts[i].text) <= 80:
            groups.setdefault(find(i), []).append(i)
    out = []
    for members in groups.values():
        members.sort(key=lambda i: (-round(texts[i].y, 1), texts[i].x))
        if len(members) > 6:  # bloco de notas/tabela: mantém linhas separadas
            out.extend(TextCluster(texts[i].text, texts[i].x, texts[i].y, [texts[i].handle],
                                   [texts[i].layer]) for i in members)
            continue
        out.append(TextCluster(
            " ".join(texts[i].text for i in members),
            float(np.mean([texts[i].x for i in members])),
            float(np.mean([texts[i].y for i in members])),
            [texts[i].handle for i in members], sorted({texts[i].layer for i in members})))
    return out


@dataclass
class Room:
    id: str
    label: str
    x: float
    y: float
    kind: str  # SPECIAL | DECLARED_AREA
    declared_area_m2: float | None = None
    polygon: np.ndarray | None = None
    polygon_handle: str | None = None
    polygon_area_m2: float | None = None
    handles: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "label": self.label, "x": round(self.x, 3),
                "y": round(self.y, 3), "kind": self.kind,
                "declared_area_m2": self.declared_area_m2,
                "polygon_handle": self.polygon_handle,
                "polygon_area_m2": (round(self.polygon_area_m2, 4)
                                    if self.polygon_area_m2 is not None else None),
                "text_handles": self.handles}


def _poly_area(p: np.ndarray) -> float:
    x, y = p[:, 0], p[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2)


def _containing_polygon(x: float, y: float, closed: list[ClosedPolyline],
                        max_area: float = 3000.0) -> tuple[ClosedPolyline, float] | None:
    best = None
    for cp in closed:
        p = cp.points
        if not (p[:, 0].min() <= x <= p[:, 0].max() and p[:, 1].min() <= y <= p[:, 1].max()):
            continue
        a = _poly_area(p)
        if a < 1.0 or a > max_area:
            continue
        if points_in_polygon(np.array([x]), np.array([y]), p)[0] and (best is None or a < best[1]):
            best = (cp, a)
    return best


def rooms_from_texts(clusters: list[TextCluster], closed: list[ClosedPolyline],
                     d: SymbolDictionary) -> list[Room]:
    rooms: list[Room] = []
    for k, c in enumerate(clusters):
        special = any(p.search(c.text) for p in d.special_rooms)
        m = _AREA.search(c.text)
        if not special and not m:
            continue
        area = float(m.group(1).replace(".", "").replace(",", ".")
                     if ("," in m.group(1)) else m.group(1)) if m else None
        label = _AREA.sub("", c.text).replace("A=", "").replace("ÁREA", "").strip(" :=-")
        if not special and not _UPPER_WORD.search(label.upper()):
            continue  # número de área sem nome de ambiente (quadro de áreas, cota)
        room = Room(f"room-{k}", label or c.text, c.x, c.y,
                    "SPECIAL" if special else "DECLARED_AREA", area, handles=c.handles)
        hit = _containing_polygon(c.x, c.y, closed)
        if hit:
            room.polygon, room.polygon_area_m2 = hit[0].points, hit[1]
            room.polygon_handle = hit[0].handle
        rooms.append(room)
    return rooms
