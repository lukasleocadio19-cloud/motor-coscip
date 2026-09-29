"""Planta carregada do DXF em metros: inserções, textos, segmentos por camada e contornos.

Lê o DXF com o mesmo leitor da importação (identidade de origem preservada: handle e caminho
de instâncias) e aplica a escala confirmada pelo analista. Os segmentos das curvas são as
poligonais discretizadas do leitor (flecha registrada); servem para obstáculos e mapas,
não para medidas exatas.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from coscip_cad import DxfReader


@dataclass(frozen=True)
class InsertRec:
    handle: str
    path: tuple[str, ...]
    block: str
    layer: str
    x: float  # ponto de inserção
    y: float
    # Centro e tamanho do que o bloco DESENHA (o ponto de base pode estar longe: 21471).
    cx: float | None = None
    cy: float | None = None
    size: float | None = None
    rotation: float = 0.0
    # Atributos visíveis da inserção (etiqueta → valor), ex.: {"AGENTE": "PQS"}.
    attribs: tuple[tuple[str, str], ...] = ()

    @property
    def child_prefix(self) -> tuple[str, ...]:
        """Prefixo do caminho de instâncias dos filhos desta inserção."""
        return (*self.path[:-1], f"block:{self.block}@{self.handle}")


@dataclass(frozen=True)
class TextRec:
    handle: str
    path: tuple[str, ...]
    layer: str
    text: str
    x: float
    y: float
    block: str | None
    # ATTRIB: etiqueta e caminho da inserção dona (o texto é atributo dela, não texto solto).
    tag: str | None = None
    owner_path: tuple[str, ...] | None = None


@dataclass(frozen=True)
class ClosedPolyline:
    handle: str
    layer: str
    points: np.ndarray  # (n, 2) metros


@dataclass
class Plan:
    scale_to_m: float
    inserts: list[InsertRec] = field(default_factory=list)
    texts: list[TextRec] = field(default_factory=list)
    closed: list[ClosedPolyline] = field(default_factory=list)
    segments: np.ndarray = field(default_factory=lambda: np.zeros((0, 4)))
    segment_layer: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.int32))
    # bit 0: dentro de bloco; bit 1: curva (arco, círculo, elipse, spline)
    segment_flags: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.int8))
    layers: list[str] = field(default_factory=list)
    entity_count: int = 0
    invisible_skipped: int = 0
    max_sagitta_m: float = 0.0
    # Balanço (F5): o que o leitor não entregou e por quê; XREFs; conteúdo fora do Model.
    skipped: list = field(default_factory=list)
    xrefs: list[str] = field(default_factory=list)
    paper_space: dict[str, int] = field(default_factory=dict)

    def layer_mask(self, predicate) -> np.ndarray:  # noqa: ANN001
        keep = np.array([bool(predicate(n)) for n in self.layers], dtype=bool)
        if not len(keep):
            return np.zeros(len(self.segment_layer), dtype=bool)
        return keep[self.segment_layer]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_plan(path: Path, scale_to_m: float, max_expanded: int = 2_000_000) -> Plan:
    if not (scale_to_m > 0):
        raise ValueError("escala inválida: a unidade precisa estar confirmada")
    reader = DxfReader(max_expanded=max_expanded)
    doc = reader.open(path)
    plan = Plan(scale_to_m=scale_to_m)
    layer_ids: dict[str, int] = {}
    coords: list[float] = []
    seg_layers: list[int] = []
    seg_flags: list[int] = []
    k = scale_to_m
    raw_inserts: list[tuple] = []
    plan_rot: dict[int, float] = {}
    open_blocks: list[tuple[tuple[str, ...], int, int]] = []  # (prefixo, índice, 1º segmento)
    ranges: dict[int, tuple[int, int]] = {}

    def close_until(path_t: tuple[str, ...]) -> None:
        while open_blocks and path_t[:len(open_blocks[-1][0])] != open_blocks[-1][0]:
            prefix, idx, start = open_blocks.pop()
            ranges[idx] = (start, len(seg_layers))

    by_path: dict[tuple[str, ...], int] = {}
    attribs: dict[int, list[tuple[str, str]]] = {}
    for e in reader.entities(doc):
        plan.entity_count += 1
        path_t = tuple(e.instance_path)
        close_until(path_t)
        if e.entity_type == "INSERT" and e.anchor and e.block_name:
            idx = len(raw_inserts)
            raw_inserts.append((e.handle, path_t, e.block_name, e.layer,
                                e.anchor[0] * k, e.anchor[1] * k))
            by_path[path_t] = idx
            open_blocks.append(((*path_t[:-1], f"block:{e.block_name}@{e.handle}"), idx,
                                len(seg_layers)))
            plan_rot[idx] = e.rotation
        elif e.entity_type in {"TEXT", "MTEXT", "ATTRIB"} and e.text and e.anchor:
            txt = " ".join(e.text.split())
            if txt:
                owner = path_t[:-1] if e.entity_type == "ATTRIB" else None
                if owner is not None and owner in by_path:
                    attribs.setdefault(by_path[owner], []).append((e.tag or "", txt))
                plan.texts.append(TextRec(e.handle, path_t, e.layer, txt,
                                          e.anchor[0] * k, e.anchor[1] * k, e.block_name,
                                          tag=e.tag, owner_path=owner))
        if e.polylines:
            lid = layer_ids.setdefault(e.layer, len(layer_ids))
            plan.max_sagitta_m = max(plan.max_sagitta_m, e.max_sagitta * k)
            flag = (1 if e.block_name else 0) | (2 if e.max_sagitta > 0 else 0)
            for pl in e.polylines:
                for (x1, y1), (x2, y2) in zip(pl, pl[1:], strict=False):
                    coords.extend((x1 * k, y1 * k, x2 * k, y2 * k))
                    seg_layers.append(lid)
                    seg_flags.append(flag)
                if (e.entity_type in {"LWPOLYLINE", "POLYLINE"} and len(pl) >= 4
                        and _is_closed(pl)):
                    plan.closed.append(ClosedPolyline(e.handle, e.layer,
                                                      np.asarray(pl, dtype=float) * k))
    close_until(())
    plan.invisible_skipped = reader.invisible_skipped
    plan.skipped = list(reader.skipped)
    plan.xrefs = [b.name for b in doc.blocks if b.block and b.block.is_xref]
    plan.paper_space = {lay.name: len(lay) for lay in doc.layouts if lay.name != "Model"
                        and len(lay) > 1}
    plan.layers = [n for n, _ in sorted(layer_ids.items(), key=lambda kv: kv[1])]
    plan.segments = (np.asarray(coords, dtype=float).reshape(-1, 4) if coords
                     else np.zeros((0, 4)))
    plan.segment_layer = np.asarray(seg_layers, dtype=np.int32)
    plan.segment_flags = np.asarray(seg_flags, dtype=np.int8)
    for idx, rec in enumerate(raw_inserts):
        lo, hi = ranges.get(idx, (0, 0))
        cx = cy = size = None
        if hi > lo:
            seg = plan.segments[lo:hi]
            xs, ys = seg[:, [0, 2]], seg[:, [1, 3]]
            x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
            cx, cy = float((x0 + x1) / 2), float((y0 + y1) / 2)
            size = float(np.hypot(x1 - x0, y1 - y0))
        plan.inserts.append(InsertRec(*rec, cx=cx, cy=cy, size=size,
                                      rotation=plan_rot.get(idx, 0.0),
                                      attribs=tuple(attribs.get(idx, ()))))
    return plan


def _is_closed(pl) -> bool:  # noqa: ANN001
    (x0, y0), (xn, yn) = pl[0], pl[-1]
    span = max(abs(x0 - xn), abs(y0 - yn))
    size = max(max(p[0] for p in pl) - min(p[0] for p in pl),
               max(p[1] for p in pl) - min(p[1] for p in pl), 1e-12)
    return span <= 1e-6 * size
