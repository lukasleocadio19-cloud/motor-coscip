"""Cena visual (VIEW-01): segmentos por camada, relativos a uma origem local.

Formato (scene/1.0):
- ``scene.bin``: Float32 little-endian, 4 valores por segmento (x1, y1, x2, y2),
  agrupados por camada;
- ``scene_ids.bin``: Uint32 little-endian, linha da entidade (em entities.jsonl) de cada segmento;
- manifesto JSON com origem local, enquadramentos, camadas e erro máximo de discretização.

A cena é só visual. Medidas usam os vértices exatos das entidades, nunca estes segmentos.
"""

from __future__ import annotations

import json
from array import array
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from ezdxf.colors import aci2rgb
from ezdxf.document import Drawing

from coscip_cad.dxf_reader import ExtractedEntity

SCENE_SCHEMA = "scene/1.0"


@dataclass
class _Layer:
    coords: array = field(default_factory=lambda: array("d"))
    ids: array = field(default_factory=lambda: array("I"))


def _layer_style(doc: Drawing) -> dict[str, tuple[str, bool]]:
    styles: dict[str, tuple[str, bool]] = {}
    for layer in doc.layers:
        aci = abs(layer.dxf.get("color", 7)) or 7
        r, g, b = aci2rgb(aci) if 0 < aci < 256 else (0, 0, 0)
        # Fundo branco: cores muito claras (ex.: ACI 7 branco, amarelo) ficam escuras.
        if 0.299 * r + 0.587 * g + 0.114 * b > 190:
            r, g, b = int(r * 0.45), int(g * 0.45), int(b * 0.45)
        styles[layer.dxf.name] = (f"#{r:02x}{g:02x}{b:02x}", layer.is_off() or layer.is_frozen())
    return styles


class SceneBuilder:
    def __init__(self, doc: Drawing) -> None:
        self._styles = _layer_style(doc)
        self._layers: dict[str, _Layer] = {}
        self.max_sagitta = 0.0
        self.entity_count = 0

    def add(self, row: int, e: ExtractedEntity) -> None:
        if not e.polylines:
            return
        self.entity_count += 1
        self.max_sagitta = max(self.max_sagitta, e.max_sagitta)
        layer = self._layers.setdefault(e.layer, _Layer())
        for pl in e.polylines:
            for (x1, y1), (x2, y2) in zip(pl, pl[1:], strict=False):
                layer.coords.extend((x1, y1, x2, y2))
                layer.ids.append(row)

    def write(self, out_dir: Path) -> dict:
        names = sorted(self._layers)
        allc = np.concatenate(
            [np.frombuffer(self._layers[n].coords, dtype=np.float64) for n in names]
        ) if names else np.zeros(0)
        pts = allc.reshape(-1, 2) if allc.size else np.zeros((0, 2))
        if len(pts):
            full = [float(pts[:, 0].min()), float(pts[:, 1].min()),
                    float(pts[:, 0].max()), float(pts[:, 1].max())]
            # Enquadramento robusto: parte de 1–99 % e expande 50 % da largura para cada lado,
            # limitado ao desenho. Exclui objetos a quilômetros (visto no 21778) sem cortar
            # a planta quando ela fica num dos lados (visto no 21471).
            lo = np.percentile(pts, 1, axis=0)
            hi = np.percentile(pts, 99, axis=0)
            span = np.maximum(hi - lo, 1e-9)
            lo = np.maximum(lo - 0.5 * span, [full[0], full[1]])
            hi = np.minimum(hi + 0.5 * span, [full[2], full[3]])
            fit = [float(lo[0]), float(lo[1]), float(hi[0]), float(hi[1])]
            origin = [round((fit[0] + fit[2]) / 2, 3), round((fit[1] + fit[3]) / 2, 3)]
        else:
            full = fit = [0.0, 0.0, 0.0, 0.0]
            origin = [0.0, 0.0]

        layers, offset = [], 0
        with open(out_dir / "scene.bin", "wb") as fb, open(out_dir / "scene_ids.bin", "wb") as fi:
            for n in names:
                lay = self._layers[n]
                rel = np.frombuffer(lay.coords, dtype=np.float64).reshape(-1, 2) - origin
                fb.write(rel.astype("<f4").tobytes())
                fi.write(np.frombuffer(lay.ids, dtype=np.uint32).astype("<u4").tobytes())
                count = len(lay.ids)
                color, off = self._styles.get(n, ("#333333", False))
                layers.append({"name": n, "color": color, "dxf_off": off,
                               "offset": offset, "count": count})
                offset += count

        manifest = {
            "scene_schema_version": SCENE_SCHEMA,
            "units": "drawing",  # unidade do desenho; conversão só após confirmação
            "local_origin": origin,
            "bbox": full,
            "fit_bbox": fit,
            "segment_count": offset,
            "entity_count": self.entity_count,
            "curve_rel_sagitta": 1e-3,
            "max_sagitta": self.max_sagitta,
            "layers": layers,
        }
        (out_dir / "scene.json").write_text(json.dumps(manifest), encoding="utf-8")
        return manifest
