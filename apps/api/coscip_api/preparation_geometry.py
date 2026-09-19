"""Geometria de recortes e contornos; nunca utiliza buffers visuais."""
from __future__ import annotations

from shapely.geometry import LineString, Point, Polygon, box


def clip_geometry(clip: dict):
    if clip.get('type') == 'POLYGON':
        return Polygon(clip['points'])
    return box(clip['x0'], clip['y0'], clip['x1'], clip['y1'])


def entity_footprint(ent: dict):
    pts = [p[:2] for p in ent.get('points', [])]
    if not pts:
        return None
    return Point(pts[0]) if len(pts) == 1 else LineString(pts)
