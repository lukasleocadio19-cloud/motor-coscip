"""Imagem da planta para a IA: geometria, grade com coordenadas em metros e símbolos numerados.

A IA não lê bem uma planta "no olho". Esta imagem foi feita para ser lida com precisão:
a grade traz as coordenadas nas margens, cada símbolo reconhecido tem o número usado em
``listar_simbolos`` e a legenda de cores vai junto em texto.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from coscip_mcp.png import Canvas
from coscip_mcp.workspace import OpenDrawing, ToolError, _extent, dictionary

MARGIN_L, MARGIN_B, MARGIN_T, MARGIN_R = 70, 34, 12, 12
WALL = (35, 35, 35)
OTHER = (165, 165, 165)
GRID = (205, 222, 240)
FLOOR = (0, 90, 210)
PATH = (230, 0, 0)
TEXT_DOT = (240, 140, 0)
CLASS_COLORS = {
    "EXTINTOR": (220, 30, 30), "HIDRANTE": (20, 90, 220), "MANGOTINHO": (20, 90, 220),
    "ACIONADOR_MANUAL": (150, 40, 190), "AVISADOR": (150, 40, 190),
    "CENTRAL_ALARME": (150, 40, 190), "DETECTOR": (150, 40, 190),
    "ILUMINACAO_EMERGENCIA": (240, 150, 0), "SAIDA": (0, 160, 60),
    "SINALIZACAO": (0, 150, 150), "SPRINKLER": (0, 170, 220),
}
OTHER_CLASS = (140, 90, 40)
EXCLUDED = (190, 190, 190)
SYSTEM_KEYS = ("extinguisher", "hydrant", "manual_call_point", "exit")


def _nice_step(span: float, target: int = 10) -> float:
    raw = span / max(target, 1)
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    for m in (1, 2, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def _fmt(v: float, step: float) -> str:
    decimals = 0 if step >= 1 else min(3, max(1, -math.floor(math.log10(step))))
    return f"{v:.{decimals}f}"


def render(d: OpenDrawing, window: list[float] | None = None, layers: list[str] | None = None,
           width: int = 1400, show_texts: bool = False, show_symbols: bool = True,
           path_system: str | None = None) -> tuple[bytes, dict[str, Any]]:
    plan = d.plan
    win = window or _extent(plan, robust=True)
    if not win:
        raise ToolError("desenho sem geometria no Model")
    x0, y0, x1, y1 = win
    if not (x1 > x0 and y1 > y0):
        raise ToolError("janela precisa de x1 > x0 e y1 > y0")
    pad = 0.02 * max(x1 - x0, y1 - y0)
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    width = int(min(max(width, 400), 2400))
    plot_w = width - MARGIN_L - MARGIN_R
    ppm = plot_w / (x1 - x0)  # pixels por metro
    plot_h = int(round((y1 - y0) * ppm))
    if plot_h > 2400 - MARGIN_T - MARGIN_B:
        plot_h = 2400 - MARGIN_T - MARGIN_B
        ppm = plot_h / (y1 - y0)
        plot_w = int(round((x1 - x0) * ppm))
        width = plot_w + MARGIN_L + MARGIN_R
    height = plot_h + MARGIN_T + MARGIN_B
    canvas = Canvas(width, height)

    def px(x: np.ndarray | float) -> np.ndarray | float:
        return MARGIN_L + (np.asarray(x) - x0) * ppm

    def py(y: np.ndarray | float) -> np.ndarray | float:
        return MARGIN_T + (y1 - np.asarray(y)) * ppm

    # grade e rótulos das coordenadas
    step = _nice_step(max(x1 - x0, y1 - y0))
    gx = np.arange(math.ceil(x0 / step) * step, x1, step)
    gy = np.arange(math.ceil(y0 / step) * step, y1, step)
    for v in gx:
        canvas.rect(int(px(v)), MARGIN_T, int(px(v)) + 1, MARGIN_T + plot_h, GRID)
    for v in gy:
        canvas.rect(MARGIN_L, int(py(v)), MARGIN_L + plot_w, int(py(v)) + 1, GRID)

    # geometria
    segs = plan.segments
    shown = 0
    if len(segs):
        keep = ((np.maximum(segs[:, 0], segs[:, 2]) >= x0)
                & (np.minimum(segs[:, 0], segs[:, 2]) <= x1)
                & (np.maximum(segs[:, 1], segs[:, 3]) >= y0)
                & (np.minimum(segs[:, 1], segs[:, 3]) <= y1))
        if layers:
            wanted = {n.upper() for n in layers}
            keep &= plan.layer_mask(lambda n: n.upper() in wanted)
            wall = np.ones(len(segs), dtype=bool)
        else:
            wall = plan.layer_mask(dictionary().is_obstacle_layer)
        for mask, color in ((keep & ~wall, OTHER), (keep & wall, WALL)):
            s = segs[mask]
            shown += len(s)
            canvas.lines(px(s[:, 0]), py(s[:, 1]), px(s[:, 2]), py(s[:, 3]), color)

    # pavimentos definidos
    k = d.scale_to_m
    for i, f in enumerate(d.floors, start=1):
        clip = f["clip"]
        pts = ([(x * k, y * k) for x, y in clip["points"]] if clip.get("type") == "POLYGON"
               else [(clip["x0"] * k, clip["y0"] * k), (clip["x1"] * k, clip["y0"] * k),
                     (clip["x1"] * k, clip["y1"] * k), (clip["x0"] * k, clip["y1"] * k)])
        ring = [*pts, pts[0]]
        for off in (0, 1):
            a, b = np.array(ring[:-1]), np.array(ring[1:])
            canvas.lines(px(a[:, 0]) + off, py(a[:, 1]) + off, px(b[:, 0]) + off,
                         py(b[:, 1]) + off, FLOOR)
        canvas.text(int(px(pts[0][0])) + 4, int(py(pts[-1][1])) + 4, f"P{i}", FLOOR)

    if show_texts:
        for t in plan.texts:
            if x0 <= t.x <= x1 and y0 <= t.y <= y1:
                canvas.disc(px(t.x), py(t.y), 2, TEXT_DOT)

    paths = []
    if path_system:
        if path_system not in SYSTEM_KEYS:
            raise ToolError(f"percurso deve ser um de {SYSTEM_KEYS}")
        if not d.last_analysis:
            raise ToolError("rode analisar_planta antes de pedir o percurso")
        for region in d.last_analysis["regions"]:
            cov = (region.get("coverage") or {}).get(path_system) or {}
            if cov.get("worst_path"):
                p = np.array(cov["worst_path"])
                for off in (0, 1):
                    canvas.lines(px(p[:-1, 0]) + off, py(p[:-1, 1]), px(p[1:, 0]) + off,
                                 py(p[1:, 1]), PATH)
                wx, wy = cov["worst_point"]
                canvas.disc(px(wx), py(wy), 5, PATH)
                paths.append({"pavimento": region["name"], "maior_percurso_m": cov["max_travel_m"],
                              "incerteza_m": cov["uncertainty_m"], "ponto_mais_distante": [wx, wy]})

    listed = []
    if show_symbols:
        for n, s in enumerate(d.symbols, start=1):
            if not (x0 <= s.x <= x1 and y0 <= s.y <= y1):
                continue
            color = EXCLUDED if s.excluded else CLASS_COLORS.get(s.cls, OTHER_CLASS)
            canvas.disc(px(s.x), py(s.y), 3 if s.excluded else 5, color)
            listed.append({"n": n, "classe": s.cls, "x": round(s.x, 2), "y": round(s.y, 2),
                           **({"excluido": s.excluded} if s.excluded else {})})
        if len(listed) <= 300:
            for row in listed:
                canvas.text(int(px(row["x"])) + 7, int(py(row["y"])) - 5, str(row["n"]),
                            CLASS_COLORS.get(row["classe"], OTHER_CLASS), scale=2)

    # margens por último, para os rótulos ficarem legíveis
    canvas.rect(0, 0, MARGIN_L - 2, height, (255, 255, 255))
    canvas.rect(0, MARGIN_T + plot_h + 2, width, height, (255, 255, 255))
    for v in gx:
        label = _fmt(v, step)
        canvas.text(int(px(v)) - 4 * len(label), MARGIN_T + plot_h + 8, label, (40, 60, 90))
    for v in gy:
        label = _fmt(v, step)
        canvas.text(max(2, MARGIN_L - 6 - 8 * len(label)), int(py(v)) - 5, label, (40, 60, 90))

    caption = {
        "janela_m": [round(v, 3) for v in (x0, y0, x1, y1)],
        "imagem_px": [width, height], "pixels_por_metro": round(ppm, 3),
        "grade_m": step, "escala": d.scale_note(),
        "leitura": ("x cresce para a direita, y para cima; rótulos da grade nas margens "
                    "inferior (x) e esquerda (y), em metros"),
        "cores": {"preto": "camadas de parede prováveis", "cinza": "demais camadas",
                  "azul grosso": "pavimentos definidos (P1, P2…)",
                  "vermelho": "extintor", "azul": "hidrante/mangotinho",
                  "roxo": "alarme/detecção", "laranja": "iluminação de emergência",
                  "verde": "saída", "verde-azulado": "sinalização",
                  "cinza claro": "símbolo excluído (legenda/demolir)",
                  **({"pontos laranja": "textos (ver listar_textos)"} if show_texts else {}),
                  **({"linha vermelha": "pior percurso da última análise"} if paths else {})},
        "segmentos_desenhados": shown,
        "simbolos_na_vista": listed[:120],
        "simbolos_na_vista_total": len(listed),
        **({"percursos": paths} if paths else {}),
    }
    return canvas.png(), caption
