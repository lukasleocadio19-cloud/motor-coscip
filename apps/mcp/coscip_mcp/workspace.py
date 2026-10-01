"""Plantas abertas pela IA e as operações das ferramentas do MCP.

Regras que valem aqui como no app:

- a unidade do desenho é **provisória** até uma medida de referência confirmada pelo
  usuário ($INSUNITS errou em 5 de 5 projetos reais); sem ela não há análise;
- coordenadas mostradas à IA estão em metros na escala em uso; os pavimentos são guardados
  em unidades do desenho e continuam válidos quando a escala muda;
- a análise lê a saída estruturada do motor e o Plano de Verificação; nada tem valor
  normativo.
"""

from __future__ import annotations

import math
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import numpy as np
from coscip_findings import consolidate
from coscip_findings.achado import to_achados
from pydantic import BaseModel, ConfigDict, Field

from coscip_analysis import AnalysisInput, parse_dictionary, run
from coscip_analysis.analyze import FIRE_CLASSES
from coscip_analysis.evidence import plant_evidence
from coscip_analysis.plan import Plan, load_plan, sha256_file
from coscip_analysis.symbols import Symbol, mark_legends, recognition_ledger, recognize
from coscip_cad import DxfReader
from coscip_cad.dwg import DwgConversionError, dwg_to_dxf
from coscip_cad.unit_evidence import suggest_unit
from coscip_cbm import FINDING_KIND_LABELS, FindingKind
from coscip_geometry.units import INSUNITS_TO_METERS
from coscip_mcp import norms
from coscip_normative.exit_distances import consult_exit_distance
from coscip_normative.package import load_package
from coscip_normative.requirements import consult_requirements
from coscip_normative.verification import compile_verification_plan, execute_plan

UNIT_TOLERANCE = 0.02  # desvio máximo entre a medida e uma unidade padrão (CAD-02)
# F7.3: duas medidas independentes; a escala de cada uma não pode divergir mais que 0,5 %.
REFERENCE_AGREEMENT = 0.005
REFERENCE_MIN_ANGLE_DEG = 30.0
STANDARD_UNITS = {"m": 1.0, "dm": 0.1, "cm": 0.01, "mm": 0.001, "in": 0.0254, "ft": 0.3048}


class ToolError(ValueError):
    """Erro de uso da ferramenta: a mensagem vai para a IA dizendo como corrigir."""


@lru_cache(maxsize=1)
def dictionary():  # noqa: ANN201
    return parse_dictionary(load_package(norms.PACKAGE_DIR).symbols)


@dataclass
class OpenDrawing:
    id: str
    path: Path
    sha256: str
    dxf_version: str
    insunits: int
    insunits_name: str
    warnings: list[str]
    suggestion: dict[str, Any]
    scale_to_m: float
    scale_source: str
    plan: Plan
    symbols: list[Symbol] = field(default_factory=list)
    unrecognized: list[dict[str, Any]] = field(default_factory=list)
    ledger: dict[str, Any] = field(default_factory=dict)
    overrides: dict[str, str] = field(default_factory=dict)
    floors: list[dict[str, Any]] = field(default_factory=list)  # clip em unidades do desenho
    confirmation: dict[str, Any] | None = None
    last_analysis: dict[str, Any] | None = None
    # Quando o arquivo aberto era DWG: origem da conversão (ADR 0002/0006).
    conversion: dict[str, Any] | None = None

    @property
    def confirmed(self) -> bool:
        return self.confirmation is not None

    def scale_note(self) -> str:
        if self.confirmed:
            return f"escala confirmada: 1 unidade = {self.scale_to_m:g} m"
        return (f"escala PROVISÓRIA ({self.scale_source}): 1 unidade = {self.scale_to_m:g} m. "
                "Medidas indicativas até confirmar_unidade.")


class Workspace:
    def __init__(self) -> None:
        self.drawings: dict[str, OpenDrawing] = {}

    def get(self, drawing_id: str) -> OpenDrawing:
        try:
            return self.drawings[drawing_id]
        except KeyError:
            raise ToolError(f"planta {drawing_id!r} não está aberta; use abrir_planta") from None

    # --- abrir ---------------------------------------------------------------------------

    def open(self, path: str) -> dict[str, Any]:
        p = Path(path).expanduser()
        if not p.exists():
            raise ToolError(f"arquivo não encontrado: {p}")
        conversion = None
        if p.suffix.lower() == ".dwg":
            try:
                conv = dwg_to_dxf(p, cache_dir())
            except DwgConversionError as exc:
                raise ToolError(str(exc)) from exc
            conversion = conv.as_dict()
            p = Path(conv.dxf_path)
        elif p.suffix.lower() != ".dxf":
            raise ToolError("só .dxf ou .dwg; planta em PDF ou imagem não tem geometria")
        reader = DxfReader()
        doc = reader.open(p)
        inv = reader.inventory(doc)
        sug = suggest_unit(doc)
        if sug.meters_per_unit and sug.strength == "forte":
            scale, source = sug.meters_per_unit, f"cotas do desenho indicam {sug.unit}"
        elif inv.insunits in INSUNITS_TO_METERS:
            scale, source = INSUNITS_TO_METERS[inv.insunits], f"$INSUNITS = {inv.insunits_name}"
        else:
            scale, source = 1.0, "sem indício; supondo metros"
        sha = sha256_file(p)
        # Aberto a partir de DWG: o id segue o DWG, que é o documento de origem.
        ident = conversion["dwg_sha256"][:10] if conversion else sha[:10]
        warnings = list(inv.warnings)
        if conversion:
            warnings += ["Lido de DWG convertido pelo ODA File Converter: handles são do DXF "
                         "derivado, não do DWG original.", conversion["note"]]
        d = OpenDrawing(id=ident, path=p, sha256=sha, dxf_version=inv.dxf_version,
                        insunits=inv.insunits, insunits_name=inv.insunits_name,
                        warnings=warnings, suggestion=sug.as_dict(),
                        scale_to_m=scale, scale_source=source, plan=Plan(scale_to_m=scale),
                        conversion=conversion)
        self._load(d)
        self.drawings[d.id] = d
        return self.overview(d)

    def _load(self, d: OpenDrawing) -> None:
        d.plan = load_plan(d.path, d.scale_to_m)
        self._recognize(d)
        d.last_analysis = None

    def _recognize(self, d: OpenDrawing) -> None:
        book: dict[str, Any] = {}
        d.symbols, d.unrecognized = recognize(d.plan, dictionary(), d.overrides, ledger=book)
        mark_legends(d.symbols, d.plan, dictionary())
        d.ledger = recognition_ledger(d.plan, d.symbols, dictionary(), book)

    def overview(self, d: OpenDrawing) -> dict[str, Any]:
        plan = d.plan
        counts = np.bincount(plan.segment_layer, minlength=len(plan.layers)) \
            if len(plan.segment_layer) else np.zeros(len(plan.layers), dtype=int)
        layers = sorted(({"camada": name, "segmentos": int(counts[i]),
                          "parede_provavel": dictionary().is_obstacle_layer(name)}
                         for i, name in enumerate(plan.layers)),
                        key=lambda r: -r["segmentos"])
        totals: dict[str, dict[str, int]] = {}
        for s in d.symbols:
            row = totals.setdefault(s.cls, {"na_planta": 0, "legenda": 0, "demolir": 0})
            row[{"LEGEND": "legenda", "DEMOLISH": "demolir"}.get(s.excluded or "",
                                                                 "na_planta")] += 1
        return {
            "planta_id": d.id, "arquivo": str(d.path), "sha256": d.sha256,
            "versao_dxf": d.dxf_version,
            **({"convertido_de_dwg": d.conversion} if d.conversion else {}),
            "unidade": {"insunits": d.insunits_name, "sugestao_pelas_cotas": d.suggestion,
                        "escala_m_por_unidade": d.scale_to_m, "origem": d.scale_source,
                        "confirmada": d.confirmed, "nota": d.scale_note()},
            "extensao_m": _extent(plan, robust=False),
            "extensao_principal_m": _extent(plan, robust=True),
            "entidades": plan.entity_count, "segmentos": int(len(plan.segments)),
            "textos": len(plan.texts),
            "camadas": layers[:40], "total_camadas": len(layers),
            "simbolos_por_classe": totals,
            "blocos_nao_reconhecidos": d.unrecognized[:25],
            "balanco_reconhecimento": ledger_brief(d.ledger),
            "pavimentos_definidos": [f["name"] for f in d.floors],
            "avisos": d.warnings,
            "proximo_passo": ("ver_planta para enxergar o desenho; listar_textos e "
                              "listar_simbolos para ler; confirmar_unidade com duas medidas "
                              "conhecidas, não paralelas, antes de analisar."),
        }

    # --- leitura ---------------------------------------------------------------------------

    def texts(self, drawing_id: str, window: list[float] | None, contains: str | None,
              limit: int) -> dict[str, Any]:
        d = self.get(drawing_id)
        rows = [t for t in d.plan.texts if _inside(t.x, t.y, window)
                and (not contains or contains.casefold() in t.text.casefold())]
        rows.sort(key=lambda t: (-round(t.y, 1), t.x))
        return {"nota": d.scale_note(), "total": len(rows), "mostrados": min(len(rows), limit),
                "textos": [{"texto": t.text, "x": round(t.x, 3), "y": round(t.y, 3),
                            "camada": t.layer, "bloco": t.block, "handle": t.handle}
                           for t in rows[:limit]]}

    def symbols(self, drawing_id: str, cls: str | None, window: list[float] | None,
                include_excluded: bool) -> dict[str, Any]:
        d = self.get(drawing_id)
        rows = []
        for n, s in enumerate(d.symbols, start=1):
            if cls and s.cls != cls.upper():
                continue
            if not include_excluded and s.excluded:
                continue
            if not _inside(s.x, s.y, window):
                continue
            rows.append({"n": n, "classe": s.cls, "x": round(s.x, 3), "y": round(s.y, 3),
                         "bloco": s.block, "camada": s.layer, "handle": s.handle,
                         "reconhecido_por": s.stage, "atributos": s.attrs,
                         "excluido": s.excluded})
        return {"nota": d.scale_note(), "total": len(rows), "simbolos": rows[:500],
                "classes_do_dicionario": sorted(dictionary().classes),
                "blocos_nao_reconhecidos": d.unrecognized[:25]}

    def classify_blocks(self, drawing_id: str, mapping: dict[str, str]) -> dict[str, Any]:
        d = self.get(drawing_id)
        known = set(dictionary().classes)
        bad = {b: c for b, c in mapping.items() if c.upper() not in known}
        if bad:
            raise ToolError(f"classes inexistentes: {bad}; use uma de {sorted(known)}")
        d.overrides.update({b: c.upper() for b, c in mapping.items()})
        self._recognize(d)
        d.last_analysis = None
        return {"aplicado": mapping, "todas_as_substituicoes": d.overrides,
                "aviso": "classificação feita pela IA: confirme com o usuário antes de concluir",
                **{k: v for k, v in self.overview(d).items()
                   if k in ("simbolos_por_classe", "blocos_nao_reconhecidos")}}

    def measure(self, drawing_id: str, points: list[list[float]]) -> dict[str, Any]:
        d = self.get(drawing_id)
        if len(points) < 2:
            raise ToolError("informe ao menos dois pontos [x, y]")
        parts = [math.dist(a, b) for a, b in zip(points, points[1:], strict=False)]
        return {"trechos_m": [round(v, 3) for v in parts], "total_m": round(sum(parts), 3),
                "total_unidades_do_desenho": round(sum(parts) / d.scale_to_m, 4),
                "nota": d.scale_note()}

    # --- unidade e pavimentos ---------------------------------------------------------------

    def confirm_unit(self, drawing_id: str, references: list[dict[str, Any]],
                     justification: str) -> dict[str, Any]:
        """Escala por DUAS medidas de referência independentes (F7.3).

        As medidas não podem ser paralelas (ângulo ≥ ``REFERENCE_MIN_ANGLE_DEG``) e a escala
        que cada uma implica não pode divergir mais que ``REFERENCE_AGREEMENT``: uma cota
        errada, ou um desenho com escalas diferentes por eixo, bloqueia a confirmação.
        """
        d = self.get(drawing_id)
        if len(justification.strip()) < 10:
            raise ToolError("justificativa obrigatória: de onde vem a medida (cota, "
                            "informação do usuário) e quem confirmou")
        if len(references) < 2:
            raise ToolError("informe duas medidas de referência independentes (não paralelas),"
                            " ex. uma cota horizontal e uma vertical")
        refs = []
        for i, r in enumerate(references, 1):
            a, b, real_m = r.get("ponto_a"), r.get("ponto_b"), r.get("medida_real_m")
            if not a or not b or real_m is None:
                raise ToolError(f"referência {i}: informe ponto_a, ponto_b e medida_real_m")
            if real_m <= 0:
                raise ToolError(f"referência {i}: a medida real precisa ser positiva")
            drawn = math.dist(a, b)
            if drawn <= 0:
                raise ToolError(f"referência {i}: os dois pontos coincidem")
            refs.append({"a": a, "b": b, "real_m": float(real_m), "drawn": drawn,
                         "implied": d.scale_to_m * real_m / drawn,
                         "dir": ((b[0] - a[0]) / drawn, (b[1] - a[1]) / drawn)})
        best = 0.0
        for i, r in enumerate(refs):
            for q in refs[i + 1:]:
                sin = abs(r["dir"][0] * q["dir"][1] - r["dir"][1] * q["dir"][0])
                best = max(best, math.degrees(math.asin(min(1.0, sin))))
        if best < REFERENCE_MIN_ANGLE_DEG:
            raise ToolError(f"as referências são paralelas (maior ângulo entre elas "
                            f"{best:.1f}°); use medidas em direções diferentes (≥ "
                            f"{REFERENCE_MIN_ANGLE_DEG:g}°), ex. uma horizontal e uma vertical")
        implied = [r["implied"] for r in refs]
        spread = (max(implied) - min(implied)) / min(implied)
        if spread > REFERENCE_AGREEMENT:
            raise ToolError(
                f"as referências discordam entre si ({spread:.2%} > "
                f"{REFERENCE_AGREEMENT:.1%}): implicam 1 unidade = "
                + " / ".join(f"{v:.6g} m" for v in implied)
                + ". Confira os pontos e as medidas; escala diferente por eixo não é aceita.")
        mean = sum(implied) / len(implied)
        unit, meters = min(STANDARD_UNITS.items(), key=lambda kv: abs(kv[1] - mean) / kv[1])
        deviation = abs(meters - mean) / meters
        if deviation > UNIT_TOLERANCE:
            raise ToolError(
                f"as medidas implicam 1 unidade = {mean:.6g} m, que não bate com nenhuma "
                f"unidade padrão (mais perto: {unit}, desvio {deviation:.1%}). Confira os "
                "pontos e as medidas.")
        changed = meters != d.scale_to_m
        old = d.scale_to_m
        d.scale_to_m, d.scale_source = meters, "confirmada por duas medidas de referência"
        d.confirmation = {
            "unidade": unit, "m_por_unidade": meters,
            "referencias": [{"ponto_a_unidades": [v / old for v in r["a"]],
                             "ponto_b_unidades": [v / old for v in r["b"]],
                             "medida_real_m": r["real_m"],
                             "m_por_unidade_implicado": round(r["implied"], 9)}
                            for r in refs],
            "desvio_entre_referencias": round(spread, 5),
            "angulo_entre_referencias_graus": round(best, 1),
            "desvio": round(deviation, 4),
            "insunits_declarado": d.insunits_name, "justificativa": justification}
        if changed:
            self._load(d)
        return {"confirmado": d.confirmation, "escala_mudou": changed,
                "nota": ("coordenadas em metros mudaram de escala: releia com ver_planta"
                         if changed else "a escala provisória estava certa"),
                "pavimentos_mantidos": [f["name"] for f in d.floors]}

    def define_floors(self, drawing_id: str, floors: list[dict[str, Any]]) -> dict[str, Any]:
        d = self.get(drawing_id)
        if not floors:
            raise ToolError("informe ao menos um pavimento")
        out = []
        k = d.scale_to_m
        for f in floors:
            name = str(f.get("nome") or "").strip()
            if not name:
                raise ToolError("todo pavimento precisa de nome")
            if f.get("poligono"):
                pts = f["poligono"]
                if len(pts) < 3:
                    raise ToolError(f"{name}: polígono com menos de 3 pontos")
                clip = {"type": "POLYGON", "points": [[x / k, y / k] for x, y in pts]}
            elif f.get("janela"):
                x0, y0, x1, y1 = f["janela"]
                if not (x1 > x0 and y1 > y0):
                    raise ToolError(f"{name}: janela precisa de x1 > x0 e y1 > y0")
                clip = {"x0": x0 / k, "y0": y0 / k, "x1": x1 / k, "y1": y1 / k}
            else:
                raise ToolError(f"{name}: informe janela [x0,y0,x1,y1] ou poligono")
            out.append({"id": uuid.uuid4().hex, "name": name, "clip": clip})
        names = [f["name"] for f in out]
        if len(names) != len(set(names)):
            raise ToolError("nomes de pavimento repetidos")
        d.floors = out
        d.last_analysis = None
        inside = {f["name"]: sum(1 for s in d.symbols if not s.excluded
                                 and s.cls in FIRE_CLASSES and _in_clip(s.x, s.y, f["clip"], k))
                  for f in out}
        return {"pavimentos": names, "simbolos_de_seguranca_por_pavimento": inside,
                "nota": d.scale_note()}

    # --- análise --------------------------------------------------------------------------

    def analyze(self, drawing_id: str, context: dict[str, Any],
                wall_layers: list[str] | None) -> dict[str, Any]:
        d = self.get(drawing_id)
        if not d.confirmed:
            raise ToolError("unidade não confirmada: peça ao usuário duas medidas conhecidas "
                            "em direções diferentes (cotas horizontal e vertical) e use "
                            "confirmar_unidade antes de analisar")
        ctx_model = AnalysisContext.model_validate(context)
        base = norms.load_base()
        ctx = {k: v for k, v in ctx_model.model_dump().items() if v is not None}
        _derive_risk(ctx, base.table("classification"))
        ctx["requirements_reference"] = consult_requirements(base.table("requirements"), ctx)
        ctx["exit_distance_reference"] = consult_exit_distance(base.table("exit_distances"),
                                                               ctx)
        out = run(AnalysisInput(
            dxf=d.path, scale_to_m=d.scale_to_m, dictionary=dictionary(), rules=[],
            context=ctx, floors=[dict(f) for f in d.floors], symbol_overrides=d.overrides,
            obstacle_layers=wall_layers))
        d.last_analysis = out
        pe = plant_evidence(out, process_id=f"mcp:{d.id}", source_id=d.id)
        plan = compile_verification_plan(base.catalog, pe.context)
        findings = execute_plan(plan, base.catalog, pe.process_evidence,
                                pe.context.all_facts(), floors=pe.floors)
        result = consolidate(findings)
        return _report(d, out, ctx, pe, result, base)


def cache_dir() -> Path:
    """Onde ficam os DXF derivados de DWG (fora do repositório; apagável)."""
    return Path(os.environ.get("COSCIP_MCP_CACHE")
                or Path(tempfile.gettempdir()) / "coscip-mcp") / "dwg"


class AnalysisContext(BaseModel):
    """Enquadramento informado pelo usuário (o que a planta não traz)."""

    model_config = ConfigDict(extra="forbid")

    occupancy: str | None = Field(default=None, max_length=20)
    risk_class: Literal["PEQUENO", "MEDIO", "GRANDE"] | None = None
    unifamiliar: bool = False
    building_area_m2: float | None = Field(default=None, gt=0)
    building_floors: int | None = Field(default=None, ge=1, le=300)
    building_height_m: float | None = Field(default=None, gt=0)
    single_occupancy: bool | None = None
    grouped_houses_or_lots: int | None = Field(default=None, ge=1)
    requires_hydrants: bool | None = None
    requires_alarm: bool | None = None
    requires_lighting: bool | None = None
    exit_max_distance_m: float | None = Field(default=None, gt=0, le=300)
    exits_confirmed: bool = False
    construction_type: Literal["ALFA", "BETA", "GAMA"] | None = None
    sprinklers_or_detection: bool | None = None
    multiple_exits: bool | None = None
    layout_defined: bool | None = None


def _derive_risk(ctx: dict[str, Any], table: dict[str, Any] | None) -> None:
    """Risco pela NT 1-04, Anexo B, quando o usuário deu só a ocupação."""
    if ctx.get("risk_class") or not ctx.get("occupancy") or not table:
        return
    row = next((r for r in table.get("divisions", []) if r["id"] == ctx["occupancy"]
                and r.get("verified")), None)
    if row:
        ctx["risk_class"] = table["risk_to_rules"][row["risk"]]
        ctx["risk_basis"] = (f"NT 1-04, Anexo B (p. {row.get('page')}): {row['id']} → "
                             f"{row['risk']}")


def ledger_brief(ledger: dict[str, Any]) -> dict[str, Any]:
    """Balanço de reconhecimento (F5.3) para a IA: completo? o que falta e por quê."""
    if not ledger:
        return {}
    return {
        "completo": ledger["complete"],
        "insercoes": ledger["inserts"], "textos_curtos": ledger["short_texts"],
        "nao_reconhecidos_em_camada_de_seguranca": ledger["unrecognized_in_safety_layers"],
        "blocos_nao_reconhecidos": ledger["unrecognized_blocks"][:15],
        "candidatos_extintor_sem_bloco": ledger["exploded_candidates"][:10],
        "xrefs": ledger["xrefs"], "layouts_com_geometria": ledger["paper_space"],
        "leitura": ("Completo = nenhum bloco não reconhecido em camada de segurança e nenhum "
                    "XREF: só então contagem e distância podem concluir. Bloco de segurança "
                    "não reconhecido: classificar_blocos com confirmação do usuário."),
    }


def _report(d: OpenDrawing, out: dict[str, Any], ctx: dict[str, Any], pe, result,  # noqa: ANN001
            base: norms.NormBase) -> dict[str, Any]:
    floors = []
    for region in out["regions"]:
        if region.get("kind") != "PLAN":
            continue
        geo = region.get("geometry") or {}
        cov = region.get("coverage") or {}
        floors.append({
            "pavimento": region["name"], "origem": region["source"],
            "confirmado": region["confirmed"],
            "area_util_m2": geo.get("interior_m2"),
            "incerteza_area_m2": geo.get("interior_uncertainty_m2"),
            "paredes": {"detectadas": geo.get("walls_detected"),
                        "modo": geo.get("obstacle_mode")},
            "simbolos": region.get("counts"),
            "maior_percurso_m": {k: {"valor": c["max_travel_m"], "incerteza": c["uncertainty_m"],
                                     "ponto": c["worst_point"],
                                     "area_nao_alcancada_m2": c["unreachable_m2"],
                                     "algoritmo": c.get("algorithm"),
                                     "orcamento_incerteza": c.get("uncertainty_budget"),
                                     "metodos_concordam": c.get("consistent"),
                                     "metodos": c.get("methods")}
                                 for k, c in cov.items() if c.get("max_travel_m") is not None},
            "maior_distancia_direta_saida_m": ({"valor": cov["exit"]["max_direct_m"],
                                                "incerteza": cov["exit"]["direct_uncertainty_m"]}
                                               if cov.get("exit", {}).get("max_direct_m")
                                               is not None else None),
        })
    pending = []
    for g in result.pending_groups:
        items = [f for f in result.findings if f.group_key == g.group_key and f.is_pending]
        measured = [{"onde": f.scope_label or "processo", "valor": f.measured.value,
                     "unidade": f.measured.unit, "exigido": f.measured.required,
                     "incerteza": f.measured.uncertainty_abs,
                     "origem_do_limite": f.measured.required_source}
                    for f in items if f.measured]
        pending.append({"tipo": FINDING_KIND_LABELS[FindingKind(g.kind)], "titulo": g.title,
                        "onde": list(g.scopes) or ["processo"], "explicacao": g.explanation,
                        "providencia": g.required_action, "faltando": list(g.missing),
                        "medidas": measured, "revisao": str(g.review_status),
                        "checks": list(g.finding_ids),
                        "base_normativa": [f"{c['document']} {c['item']}"
                                           for c in g.normative_citations]})
    # Título neutro do check ("Mínimo de dois extintores…"), não o da pendência.
    ok = sorted({base.catalog.get(f.check_id).title
                 + (f" ({f.scope_label})" if f.scope_label else "")
                 for f in result.findings if f.compliance_status.value == "COMPLIANT"})
    return {
        "aviso": "RASCUNHO sem valor normativo: regras e checks não homologados.",
        "escala": d.scale_note(),
        "enquadramento": {
            "ocupacao": ctx.get("occupancy"), "risco": ctx.get("risk_class"),
            "base_do_risco": ctx.get("risk_basis"),
            "anexo_iii": _brief(ctx["requirements_reference"],
                                ("status", "column", "message", "conflicts")),
            "exigencias_da_tabela": [m["label"] for m in
                                     ctx["requirements_reference"].get("measures", [])
                                     if m.get("status") == "REQUIRED"],
            "anexo_c_nt_2_08": _brief(ctx["exit_distance_reference"],
                                      ("status", "limit_m", "by_floor_m", "measure", "missing",
                                       "message")),
            "divergencias_do_analista": list(pe.overrides),
        },
        "pavimentos": floors,
        # GATE-0 da skill (F8): medida do motor só entra na matriz com unidade confirmada e
        # balanço de reconhecimento completo.
        "gate_0": {"unidade_confirmada": d.confirmed,
                   "balanco_completo": out["recognition_ledger"]["complete"],
                   "aberto": bool(d.confirmed and out["recognition_ledger"]["complete"])},
        "balanco_reconhecimento": ledger_brief(out["recognition_ledger"]),
        "regioes_ignoradas": [{"regiao": n, "motivo": r} for n, r in pe.skipped_regions],
        "resumo": result.summary.as_dict(),
        "pendencias": pending,
        "sem_pendencia": ok,
        # F8: os mesmos achados no contrato comum das skills (skills/_comum/achado.schema.json),
        # para entrar na matriz consolidada sem tradução.
        "achados": to_achados(result.findings, pe.evidence),
        "checks_nao_verificados_por_citacao": base.excluded_checks,
        "avisos_do_motor": out.get("warnings", []),
        "simbolos_fora_dos_pavimentos": len(out.get("symbols_outside_regions", [])),
        "duracao_s": out.get("duration_s"),
        "dica": "ver_planta com percurso='extinguisher'|'hydrant'|'manual_call_point'|'exit' "
                "mostra o pior caminho de cada pavimento.",
    }


def _brief(d: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {k: d.get(k) for k in keys if d.get(k) not in (None, [], "")}


def _inside(x: float, y: float, window: list[float] | None) -> bool:
    if not window:
        return True
    x0, y0, x1, y1 = window
    return x0 <= x <= x1 and y0 <= y <= y1


def _in_clip(x: float, y: float, clip: dict[str, Any], k: float) -> bool:
    if clip.get("type") == "POLYGON":
        from shapely.geometry import Point, Polygon

        return Polygon([(px * k, py * k) for px, py in clip["points"]]).covers(Point(x, y))
    return clip["x0"] * k <= x <= clip["x1"] * k and clip["y0"] * k <= y <= clip["y1"] * k


def _extent(plan: Plan, robust: bool) -> list[float] | None:
    xs = [plan.segments[:, 0], plan.segments[:, 2]] if len(plan.segments) else []
    ys = [plan.segments[:, 1], plan.segments[:, 3]] if len(plan.segments) else []
    if plan.texts:
        xs.append(np.array([t.x for t in plan.texts]))
        ys.append(np.array([t.y for t in plan.texts]))
    if not xs:
        return None
    x, y = np.concatenate(xs), np.concatenate(ys)
    if robust and len(x) > 50:  # ignora o 0,5 % mais afastado (carimbo, lixo longe)
        lo, hi = 0.5, 99.5
        return [round(float(v), 3) for v in (np.percentile(x, lo), np.percentile(y, lo),
                                             np.percentile(x, hi), np.percentile(y, hi))]
    return [round(float(v), 3) for v in (x.min(), y.min(), x.max(), y.max())]

