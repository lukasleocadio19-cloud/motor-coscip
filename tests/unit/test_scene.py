"""Cena (VIEW-01): formato binário, camadas, curvas e enquadramento robusto."""

from __future__ import annotations

import json
import struct

import ezdxf

from coscip_cad import DxfReader
from coscip_cad.scene import SceneBuilder


def _build(tmp_path, draw):
    doc = ezdxf.new("R2018")
    msp = doc.modelspace()
    draw(msp)
    path = tmp_path / "s.dxf"
    doc.saveas(path)
    r = DxfReader()
    d = r.open(path)
    sb = SceneBuilder(d)
    for row, e in enumerate(r.entities(d)):
        sb.add(row, e)
    return sb.write(tmp_path), tmp_path


def test_binary_layout_matches_manifest(tmp_path):
    def draw(msp):
        msp.add_line((0, 0), (10, 0), dxfattribs={"layer": "A"})
        msp.add_lwpolyline([(0, 0), (0, 5), (5, 5)], dxfattribs={"layer": "B"})
        msp.add_circle((3, 3), 1, dxfattribs={"layer": "B"})

    m, out = _build(tmp_path, draw)
    seg = (out / "scene.bin").read_bytes()
    ids = (out / "scene_ids.bin").read_bytes()
    assert len(seg) == m["segment_count"] * 16 and len(ids) == m["segment_count"] * 4
    assert json.loads((out / "scene.json").read_text())["layers"] == m["layers"]
    a = next(x for x in m["layers"] if x["name"] == "A")
    x1, y1, x2, y2 = struct.unpack_from("<4f", seg, a["offset"] * 16)
    ox, oy = m["local_origin"]
    assert (round(x1 + ox, 5), round(y1 + oy, 5), round(x2 + ox, 5), round(y2 + oy, 5)) == \
        (0, 0, 10, 0)
    # Círculo discretizado: flecha registrada ≤ 0,1 % do tamanho (diâmetro 2).
    assert 0 < m["max_sagitta"] <= 2e-3


def test_fit_keeps_side_content_and_drops_far_outlier(tmp_path):
    def draw(msp):
        for i in range(200):  # planta principal densa
            msp.add_line((i * 0.1, 0), (i * 0.1, 10))
        for i in range(30):  # prancha lateral, ainda perto
            msp.add_line((40 + i * 0.1, 0), (40 + i * 0.1, 5))
        msp.add_line((4000, 4000), (4001, 4001))  # objeto isolado a ~4 km

    m, _ = _build(tmp_path, draw)
    x0, y0, x1, y1 = m["fit_bbox"]
    assert x0 <= 0 and x1 >= 43 and x1 < 1000
    assert m["bbox"][2] >= 4000
