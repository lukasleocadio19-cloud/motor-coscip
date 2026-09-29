"""Análise da planta: símbolos → regiões → geometria → fatos → regras → saída auditável.

Saída ``plant-analysis/1.0`` (JSON): tudo que o relatório mostra vem daqui, com origem
(handle + caminho de instâncias), método e incerteza de cada fato.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from coscip_analysis.dictionary import SymbolDictionary
from coscip_analysis.plan import Plan, load_plan, sha256_file
from coscip_analysis.regions import (
    Region,
    Room,
    auto_regions,
    cluster_texts,
    floor_regions,
    rooms_from_texts,
)
from coscip_analysis.spatial import (
    Grid,
    Walker,
    clip_mask,
    direct_farthest,
    direct_uncertainty,
    interior,
    rasterize,
    travel_uncertainty,
)
from coscip_analysis.svgmap import region_map
from coscip_analysis.symbols import (
    Symbol,
    is_safety_layer,
    mark_legends,
    recognition_ledger,
    recognize,
)
from coscip_rules.dsl import RuleDefinition
from coscip_rules.engine import EvaluationContext, Fact, evaluate

SCHEMA = "plant-analysis/1.0"

# Sistemas com distância percorrida: (chave do fato, classes de origem, rótulo)
SYSTEMS = (
    ("extinguisher", ("EXTINTOR",), "Extintores"),
    ("hydrant", ("HIDRANTE", "MANGOTINHO"), "Hidrantes/mangotinhos"),
    ("manual_call_point", ("ACIONADOR_MANUAL",), "Acionadores manuais"),
    ("exit", ("SAIDA",), "Saídas de emergência"),
)
FIRE_CLASSES = {"EXTINTOR", "HIDRANTE", "MANGOTINHO", "ILUMINACAO_EMERGENCIA", "DETECTOR",
                "ACIONADOR_MANUAL", "AVISADOR", "SPRINKLER", "CENTRAL_ALARME", "SAIDA"}
SIGN_ASSOCIATION_M = 2.5  # placa E-5 "junto" do extintor: associação heurística, não norma
UNREACHABLE_TOLERANCE_M2 = 2.0
# Identidade do cálculo de percurso (§27): muda a versão quando o algoritmo mudar.
TRAVEL_ALGORITHM = "grid_dijkstra_16"
TRAVEL_ALGORITHM_VERSION = "1.0"
# Distância direta (NT 2-08 5.3.3.3, sem leiaute): só para saídas.
DIRECT_ALGORITHM = "grid_euclidean_nearest"
DIRECT_ALGORITHM_VERSION = "1.0"
DIRECT_SYSTEMS = frozenset({"exit"})


@dataclass
class RuleBinding:
    rule: RuleDefinition
    rule_version_id: str | None = None
    citations: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AnalysisInput:
    dxf: Path
    scale_to_m: float
    dictionary: SymbolDictionary
    rules: list[RuleBinding]
    context: dict[str, Any]
    floors: list[dict[str, Any]] = field(default_factory=list)
    symbol_overrides: dict[str, str] = field(default_factory=dict)
    obstacle_layers: list[str] | None = None  # escolha do analista substitui os padrões
    max_expanded: int = 2_000_000
    # Quadros de legenda marcados pelo analista ([x0, y0, x1, y1] em metros): têm prioridade
    # sobre a heurística; símbolo dentro deles nunca protege nada.
    legend_regions: list[list[float]] = field(default_factory=list)


def _fact(value: Any, unc: float | None = 0.0, evidence: tuple[str, ...] = ()) -> Fact:
    return Fact(value=value, uncertainty_abs=unc, evidence_ids=evidence)


def _context_facts(ctx: dict[str, Any]) -> dict[str, Fact]:
    out = {}
    for k, v in ctx.items():
        if v is None or v == "":
            continue
        out[f"context.{k}"] = _fact(v, 0.0)
    return out


def run(inp: AnalysisInput, progress=None) -> dict[str, Any]:  # noqa: ANN001
    t0 = time.monotonic()
    step = progress or (lambda _msg: None)
    step("Lendo o DXF")
    plan = load_plan(inp.dxf, inp.scale_to_m, inp.max_expanded)
    d = inp.dictionary
    step("Reconhecendo símbolos")
    book: dict[str, Any] = {}
    symbols, unrecognized = recognize(plan, d, inp.symbol_overrides, ledger=book)
    legend_marked = 0
    for x0, y0, x1, y1 in inp.legend_regions:
        for s in symbols:
            if s.excluded is None and x0 <= s.x <= x1 and y0 <= s.y <= y1:
                s.excluded = "LEGEND"
                s.attrs["legend_source"] = "analista"
                legend_marked += 1
    legend_marked += mark_legends(symbols, plan, d)
    ledger = recognition_ledger(plan, symbols, d, book)
    blocking = [(i.cx if i.cx is not None else i.x, i.cy if i.cy is not None else i.y)
                for i in book["unrecognized"] if is_safety_layer(d, i.layer)]
    blocking += [(c["x"], c["y"]) for c in ledger["exploded_candidates"]]
    clusters = cluster_texts(plan.texts)

    if inp.obstacle_layers is not None:
        chosen = {n.upper() for n in inp.obstacle_layers}
        obstacle = plan.layer_mask(lambda n: n.upper() in chosen)
        obstacle_source = "analista"
    else:
        obstacle = plan.layer_mask(d.is_obstacle_layer)
        obstacle_source = "padrões do dicionário"
    obstacle_layers = sorted({plan.layers[i] for i in np.unique(plan.segment_layer[obstacle])})

    step("Delimitando regiões")
    if inp.floors:
        regions = floor_regions(inp.floors, inp.scale_to_m)
    else:
        regions = auto_regions(plan, d, clusters)
    rooms = rooms_from_texts(clusters, plan.closed, d)
    ctx_facts = _context_facts(inp.context)

    warnings: list[str] = []
    if plan.invisible_skipped:
        warnings.append(f"{plan.invisible_skipped} entidade(s) invisível(is) de blocos dinâmicos "
                        "ignorada(s) (estados de visibilidade ocultos).")
    if not inp.floors:
        warnings.append("Nenhum pavimento recortado: as regiões foram agrupadas automaticamente "
                        "e os resultados delas exigem revisão humana.")
    if not obstacle_layers:
        warnings.append("Nenhuma camada de parede reconhecida: percursos viram linha reta "
                        "(limite inferior) e ficam em revisão. Indique as camadas de parede.")

    results: list[dict[str, Any]] = []
    regions_out = []
    for i, region in enumerate(regions, start=1):
        step(f"Analisando {region.name} ({i}/{len(regions)})")
        regions_out.append(_analyze_region(region, plan, symbols, rooms, obstacle, d,
                                           inp.rules, ctx_facts, results, blocking))

    assigned = {s["id"] for r in regions_out for s in r["symbols"]}
    outside = [s.as_dict() for s in symbols if s.id not in assigned and s.excluded is None
               and s.cls in FIRE_CLASSES]
    by_status: dict[str, int] = {}
    for r in results:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    return {
        "schema_version": SCHEMA,
        "drawing": {"sha256": sha256_file(inp.dxf), "scale_to_m": inp.scale_to_m,
                    "entity_count": plan.entity_count,
                    "invisible_skipped": plan.invisible_skipped,
                    "text_count": len(plan.texts), "insert_count": len(plan.inserts),
                    "segment_count": int(len(plan.segments)),
                    "max_sagitta_m": plan.max_sagitta_m},
        "dictionary": {"id": d.id, "version": d.version, "sha256": d.sha256},
        "context": inp.context,
        "obstacles": {"source": obstacle_source, "layers": obstacle_layers,
                      "segments": int(obstacle.sum())},
        "symbol_totals": _totals(symbols),
        "legend_symbols": [s.as_dict() for s in symbols if s.excluded == "LEGEND"],
        "legend_marked": legend_marked,
        "symbols_outside_regions": outside,
        "unrecognized_blocks": unrecognized,
        "recognition_ledger": ledger,
        "regions": regions_out,
        "results": results,
        "summary": {"by_status": by_status, "regions": len(regions_out),
                    "plan_regions": sum(1 for r in regions_out if r["kind"] == "PLAN")},
        "warnings": warnings,
        "duration_s": round(time.monotonic() - t0, 2),
    }


def _totals(symbols: list[Symbol]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for s in symbols:
        row = out.setdefault(s.cls, {"protective": 0, "legend": 0, "demolish": 0})
        key = {"LEGEND": "legend", "DEMOLISH": "demolish"}.get(s.excluded or "", "protective")
        row[key] += 1
    return out


def _analyze_region(region: Region, plan: Plan, symbols: list[Symbol], rooms: list[Room],
                    obstacle: np.ndarray, d: SymbolDictionary, rules: list[RuleBinding],
                    ctx_facts: dict[str, Fact], results: list[dict[str, Any]],
                    blocking: list[tuple[float, float]] = ()) -> dict[str, Any]:
    x0, y0, x1, y1 = region.bbox
    inside_sym = [s for s in symbols
                  if x0 <= s.x <= x1 and y0 <= s.y <= y1
                  and region.contains(np.array([s.x]), np.array([s.y]))[0]]
    prot = [s for s in inside_sym if s.excluded is None]
    if region.source == "AUTO":
        region.kind = "PLAN" if any(s.cls in FIRE_CLASSES for s in prot) else "OTHER"
    out: dict[str, Any] = {**region.summary(), "symbols": [s.as_dict() for s in inside_sym]}
    counts: dict[str, int] = {}
    for s in prot:
        counts[s.cls] = counts.get(s.cls, 0) + 1
    out["counts"] = counts
    region_rooms = [r for r in rooms if x0 <= r.x <= x1 and y0 <= r.y <= y1
                    and region.contains(np.array([r.x]), np.array([r.y]))[0]]
    out["rooms"] = [r.as_dict() for r in region_rooms]
    out["area_checks"] = _area_checks(region_rooms)
    if region.kind != "PLAN":
        out["skipped"] = "sem símbolos de segurança contra incêndio (corte, fachada ou detalhe)"
        return out

    # --- geometria --------------------------------------------------------------------
    grid = Grid.around(region.bbox)
    segs = plan.segments
    in_box = _bbox_overlap(segs, region.bbox)
    sel = obstacle & in_box
    walls_detected = int(sel.sum()) >= 20
    obstacle_mode = "WALL_LAYERS"
    if not walls_detected:
        # Provisório: linhas soltas (fora de blocos, sem curvas) de layers que não são de
        # texto/cota/mobiliário. Portas e símbolos costumam ser blocos → ficam de fora.
        loose = ((plan.segment_flags & 3) == 0) & in_box & plan.layer_mask(
            lambda n: not any(p.search(n) for p in d.non_obstacle_layers))
        if int(loose.sum()) >= 20:
            sel, obstacle_mode = loose, "LOOSE_LINES"
        else:
            obstacle_mode = "NONE"
    walls = rasterize(grid, segs[sel])
    clip = clip_mask(grid, region.polygon)
    inner = interior(grid, walls, clip) if obstacle_mode != "NONE" else None
    if inner is None or inner.area_m2 < 10:
        walls_detected, obstacle_mode = False, "NONE"
        free = clip & ~walls
        area_m2 = float(free.sum() * grid.cell_area())
        area_unc = area_m2  # sem paredes a área útil não é conhecida
        method = "sem obstáculos reconhecidos: área do recorte, só indicativa"
    else:
        free = inner.mask
        area_m2, area_unc, method = inner.area_m2, inner.uncertainty_m2, inner.method
        if obstacle_mode == "LOOSE_LINES":
            area_unc = max(area_unc, 0.25 * area_m2)
            method = ("SEM layer de parede: linhas soltas usadas como obstáculo provisório "
                      "(revisão obrigatória); " + method)
    walker = Walker(grid, free)
    out["geometry"] = {"cell_m": grid.h, "walls_detected": walls_detected,
                       "obstacle_mode": obstacle_mode,
                       "obstacle_segments": int(sel.sum()), "interior_m2": round(area_m2, 2),
                       "interior_uncertainty_m2": round(area_unc, 2), "method": method}

    facts: dict[str, Fact] = dict(ctx_facts)
    facts["floor.area_m2"] = _fact(round(area_m2, 3), area_unc)
    facts["floor.count.extinguishers"] = _fact(counts.get("EXTINTOR", 0), 0.0)
    facts["floor.count.lighting"] = _fact(counts.get("ILUMINACAO_EMERGENCIA", 0), 0.0)
    facts["floor.has_hydrants"] = _fact(bool(counts.get("HIDRANTE") or counts.get("MANGOTINHO")))
    facts["floor.has_alarm"] = _fact(bool(counts.get("ACIONADOR_MANUAL")
                                          or counts.get("CENTRAL_ALARME")
                                          or counts.get("AVISADOR")))
    facts["quality.walls_detected"] = _fact(walls_detected)
    # F5.3: bloco não reconhecido em camada de segurança, extintor "explodido" (sem bloco) ou
    # XREF pendente neste pavimento impedem concluir contagem e distância.
    pending = [(x, y) for x, y in blocking if x0 <= x <= x1 and y0 <= y <= y1
               and region.contains(np.array([x]), np.array([y]))[0]]
    facts["quality.recognition.complete"] = _fact(not pending and not plan.xrefs)
    facts["quality.xref_resolved"] = _fact(not plan.xrefs)
    facts["quality.region_confirmed"] = _fact(region.confirmed)
    # Extintor presumido pela placa E-5 + E-17 (sem símbolo): contagem só indicativa.
    facts["quality.extinguisher.not_presumed"] = _fact(
        not any(s.cls == "EXTINTOR" and s.attrs.get("presumed") for s in prot))

    coverage = {}
    fields: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for key, classes, label in SYSTEMS:
        src = [s for s in prot if s.cls in classes]
        cov = _coverage(walker, grid, src, key, label)
        coverage[key] = cov["summary"]
        if cov.get("field") is not None:
            fields[key] = (cov["field"], cov["pred"])
        if cov["summary"]["max_travel_m"] is not None:
            facts[f"floor.{key}.max_travel_m"] = _fact(
                cov["summary"]["max_travel_m"], cov["summary"]["uncertainty_m"],
                tuple(s.id for s in src))
            facts[f"quality.{key}.complete"] = _fact(
                cov["summary"]["unreachable_m2"] <= UNREACHABLE_TOLERANCE_M2)
    out["coverage"] = coverage

    # --- sujeitos ---------------------------------------------------------------------
    subjects: list[tuple[str, str, str, dict[str, Fact]]] = [
        ("FLOOR", region.id, region.name, facts)]
    ext = [s for s in prot if s.cls == "EXTINTOR"]
    signs = [s for s in inside_sym if s.cls == "SINALIZACAO" and s.excluded is None]
    for s in ext:
        near = [g for g in signs if g.attrs.get("code") == "E-5"
                and math.hypot(g.x - s.x, g.y - s.y) <= SIGN_ASSOCIATION_M]
        embedded = [c for c in s.attrs.get("embedded_signs", []) if c == "E-5"]
        n = len(near) + len(embedded)
        s.attrs["e5_signs"] = n
        sf = dict(ctx_facts)
        sf["symbol.class"] = _fact("EXTINTOR")
        sf["symbol.e5_signs"] = _fact(n, 0.0, tuple(g.id for g in near))
        sf["quality.region_confirmed"] = _fact(region.confirmed)
        subjects.append(("SYMBOL", s.id, _symbol_label(s), sf))
    for r in region_rooms:
        if r.kind != "SPECIAL":
            continue
        rf = dict(ctx_facts)
        rf["room.special"] = _fact(True)
        rf["quality.region_confirmed"] = _fact(region.confirmed)
        dist = _nearest_to_room(r, ext)
        if dist is not None:
            rf["room.nearest_extinguisher_m"] = _fact(round(dist[0], 3), dist[1],
                                                      (dist[2],))
        subjects.append(("ROOM", r.id, r.label, rf))

    region_results = []
    for subject_type, sid, slabel, sfacts in subjects:
        for b in rules:
            if b.rule.subject != subject_type:
                continue
            o = evaluate(b.rule, EvaluationContext(sid, sfacts))
            res = {"rule_id": b.rule.id, "rule_version": b.rule.version,
                   "rule_version_id": b.rule_version_id, "title": b.rule.title,
                   "measure": b.rule.measure, "subject_type": subject_type,
                   "measured_fact": b.rule.calculation.measured,
                   "subject_id": sid, "subject_label": slabel, "region_id": region.id,
                   "region_name": region.name, "status": o.status.value,
                   "applicability": o.applicability.value, "reason_code": o.reason_code,
                   "trace": _jsonable(o.trace), "citations": b.citations,
                   "publication_state": b.rule.publication_state}
            results.append(res)
            region_results.append(res)
    out["facts"] = {k: {"value": _jsonable(f.value), "uncertainty": f.uncertainty_abs,
                        "evidence": list(f.evidence_ids)}
                    for k, f in facts.items() if not k.startswith("context.")}
    out["symbols"] = [s.as_dict() for s in inside_sym]
    out["map_svg"] = region_map(region, grid, free, plan, sel, inside_sym, fields,
                                region_results, region_rooms, coverage)
    return out


def _coverage(walker: Walker, grid: Grid, src: list[Symbol], key: str,
              label: str) -> dict[str, Any]:
    summary: dict[str, Any] = {"label": label, "sources": len(src), "max_travel_m": None,
                               "uncertainty_m": None, "worst_point": None,
                               "unreachable_m2": 0.0, "unsnapped": []}
    if not src or walker.n == 0:
        return {"summary": summary}
    if key in DIRECT_SYSTEMS:
        direct = direct_farthest(grid, walker.free, [(s.x, s.y) for s in src])
        if direct is not None:
            summary["max_direct_m"] = round(direct[0], 3)
            summary["direct_uncertainty_m"] = round(direct_uncertainty(grid.h), 3)
            summary["direct_worst_point"] = [round(v, 3) for v in direct[1]]
            summary["direct_algorithm"] = DIRECT_ALGORITHM
            summary["direct_algorithm_version"] = DIRECT_ALGORITHM_VERSION
    cells = []
    for s in src:
        c = walker.snap(s.x, s.y)
        if c is None:
            summary["unsnapped"].append(s.id)
        else:
            cells.append(c)
    if not cells:
        return {"summary": summary}
    field_, pred, _ = walker.distances(cells)
    reach = np.isfinite(field_) & walker.free
    unreachable = walker.free & ~np.isfinite(field_)
    summary["unreachable_m2"] = round(float(unreachable.sum() * grid.cell_area()), 2)
    if reach.any():
        idx = np.unravel_index(np.argmax(np.where(reach, field_, -1)), field_.shape)
        dmax = float(field_[idx])
        summary["max_travel_m"] = round(dmax, 3)
        summary["uncertainty_m"] = round(travel_uncertainty(dmax, grid.h), 3)
        wx, wy = grid.center(int(idx[0]), int(idx[1]))
        summary["worst_point"] = [round(wx, 3), round(wy, 3)]
        path = walker.path_to(pred, int(idx[0]), int(idx[1]))
        stride = max(1, len(path) // 200)
        summary["worst_path"] = [[round(x, 2), round(y, 2)] for x, y in path[::stride]]
        summary["method"] = ("Dijkstra em grade de 16 vizinhos sobre o interior; paredes e "
                             f"esquadrias fixas como obstáculo; célula {grid.h:.2f} m")
        summary["algorithm"] = TRAVEL_ALGORITHM
        summary["algorithm_version"] = TRAVEL_ALGORITHM_VERSION
    return {"summary": summary, "field": field_, "pred": pred}


def _nearest_to_room(room: Room, ext: list[Symbol]) -> tuple[float, float, str] | None:
    if not ext:
        return None
    best = None
    for s in ext:
        if room.polygon is not None:
            from shapely.geometry import Point, Polygon

            poly = Polygon(room.polygon)
            dist = 0.0 if poly.contains(Point(s.x, s.y)) else poly.exterior.distance(
                Point(s.x, s.y))
            unc = 0.3
        else:
            dist, unc = math.hypot(s.x - room.x, s.y - room.y), 3.0
        if best is None or dist < best[0]:
            best = (dist, unc, s.id)
    return best


def _area_checks(rooms: list[Room]) -> list[dict[str, Any]]:
    out = []
    for r in rooms:
        if r.declared_area_m2 is None:
            continue
        row = {"room_id": r.id, "label": r.label, "declared_m2": r.declared_area_m2,
               "computed_m2": None, "difference_m2": None, "status": "SEM_CONTORNO",
               "polygon_handle": r.polygon_handle}
        if r.polygon_area_m2 is not None:
            diff = r.polygon_area_m2 - r.declared_area_m2
            tol = max(0.05, 0.01 * r.declared_area_m2)
            row.update(computed_m2=round(r.polygon_area_m2, 3), difference_m2=round(diff, 3),
                       status="CONFERE" if abs(diff) <= tol else "DIVERGE",
                       tolerance_m2=round(tol, 3))
        out.append(row)
    return out


def _symbol_label(s: Symbol) -> str:
    bits = [s.cls.replace("_", " ").title()]
    if a := s.attrs.get("agent"):
        bits.append(a.replace("_", " "))
    if c := s.attrs.get("capacity"):
        bits.append(c)
    return " · ".join(bits) + f" (handle {s.handle})"


def _bbox_overlap(segs: np.ndarray, bbox: tuple[float, float, float, float]) -> np.ndarray:
    x0, y0, x1, y1 = bbox
    if not len(segs):
        return np.zeros(0, dtype=bool)
    sx0 = np.minimum(segs[:, 0], segs[:, 2])
    sx1 = np.maximum(segs[:, 0], segs[:, 2])
    sy0 = np.minimum(segs[:, 1], segs[:, 3])
    sy1 = np.maximum(segs[:, 1], segs[:, 3])
    return (sx1 >= x0) & (sx0 <= x1) & (sy1 >= y0) & (sy0 <= y1)


def _jsonable(v: Any) -> Any:
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, (np.floating, np.integer)):
        return v.item()
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if hasattr(v, "__str__") and not isinstance(v, (str, int, float, bool, type(None))):
        return str(v)
    return v

