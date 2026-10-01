"""Fase 3 da arquitetura v2: resultado do motor CAD → ``Evidence`` (§26, §27).

Lê a saída estruturada ``plant-analysis/1.0`` — símbolos com handle e camada, cobertura
de percurso com incerteza e fatos de qualidade por pavimento — e nunca o texto do
relatório nem o veredito das regras antigas. Cada pavimento analisado vira um
``FloorScope`` com suas próprias evidências; os checks de escopo ``FLOOR`` rodam sobre ele.

Regras que o adaptador segue:

- todo símbolo vira uma evidência localizada (handle, camada, pavimento);
- classe procurada e não encontrada vira ``ExtractionGap`` (§54), nunca "não existe";
- extintor presumido pela placa continua evidência, marcado pela porta de qualidade;
- medida de percurso leva valor, incerteza, algoritmo, versão e hash do desenho (§27);
- os fatos ``quality.*`` do pavimento seguem como estão: o executor decide com eles.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from coscip_evidence import Evidence, EvidenceLocator, EvidenceSet, ExtractionGap

from coscip_analysis.analyze import SCHEMA, SYSTEMS, TRAVEL_ALGORITHM, TRAVEL_ALGORITHM_VERSION
from coscip_cbm import EvidenceSourceType
from coscip_normative.verification import FloorScope, ProcessContext, effective_requirement

# Classe do dicionário de símbolos → campo da evidência (vocabulário dos checks).
SYMBOL_FIELDS = {
    "EXTINTOR": "extinguisher",
    "HIDRANTE": "hydrant",
    "MANGOTINHO": "hydrant",  # ponto de hidrante ou mangotinho (NT 2-02)
    "ILUMINACAO_EMERGENCIA": "emergency_light",
    "DETECTOR": "detector",
    "ACIONADOR_MANUAL": "manual_call_point",
    "AVISADOR": "alarm_sounder",
    "SPRINKLER": "sprinkler",
    "CENTRAL_ALARME": "alarm_panel",
    "SAIDA": "exit",
}
SYMBOL_METHOD = "CAD_SYMBOL"
UNKNOWN_AGENT = "DESCONHECIDO"
GEOMETRY_METHOD = "CAD_GEOMETRY"


class PlantEvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class PlantEvidence:
    """O que a análise da planta entrega ao Plano de Verificação."""

    context: ProcessContext
    floors: tuple[FloorScope, ...]
    # Evidência do processo inteiro: como cada exigência de sistema foi determinada.
    process_evidence: EvidenceSet
    drawing_sha256: str
    # Regiões ignoradas (corte, fachada, detalhe) com o motivo, para o relatório.
    skipped_regions: tuple[tuple[str, str], ...] = ()

    @property
    def evidence(self) -> tuple[Evidence, ...]:
        return (*self.process_evidence, *(e for f in self.floors for e in f.evidence))

    @property
    def overrides(self) -> tuple[str, ...]:
        """Onde o analista contrariou a tabela (§30: nunca em silêncio): sistema com X
        declarado não exigido, ou limite até a saída diferente do Anexo C."""
        facts = self.context.facts
        out = [system for system, *_ in REQUIREMENTS
               if facts.get(f"context.normative_requirement_{system}") is True
               and facts.get(f"context.human_override_{system}") is False]
        table = facts.get(f"context.normative_{EXIT_LIMIT}")
        declared = facts.get(f"context.human_override_{EXIT_LIMIT}")
        allowed = table if isinstance(table, list | tuple) else [table]
        if table is not None and declared is not None and all(
                float(declared) != float(v) for v in allowed):
            out.append(EXIT_LIMIT)
        return tuple(out)


# Sistema → (campo do formulário, id da medida no Anexo III, campo da evidência).
REQUIREMENTS = (
    ("hydrants", "requires_hydrants", "hydrants", "hydrant_requirement"),
    ("alarm", "requires_alarm", "alarm", "alarm_requirement"),
    ("lighting", "requires_lighting", "lighting", "lighting_requirement"),
)
EXIT_LIMIT = "exit_max_distance_m"


def process_context(analysis: dict[str, Any], process_id: str) -> ProcessContext:
    """Enquadramento informado no formulário da análise, como fatos ``context.*``.

    Só valores simples viram fato. Para cada sistema, a exigência normativa (célula X do
    Anexo III), a declaração do analista e a exigência efetiva convivem (§30); traço ou
    célula condicional na tabela **não** é dispensa: fica desconhecido.
    """
    ctx = analysis.get("context") or {}
    facts: dict[str, Any] = {f"context.{k}": v for k, v in ctx.items()
                             if isinstance(v, str | int | float | bool) and v != ""}
    marked = _required_measures(ctx.get("requirements_reference"))
    for system, form_field, measure, _field in REQUIREMENTS:
        req = effective_requirement(True if measure in marked else None, ctx.get(form_field))
        for key, value in req.items():
            if value is not None:
                facts[f"context.{key}_{system}"] = value
    facts.update(_exit_limit(ctx))
    return ProcessContext(process_id=process_id, occupancy=ctx.get("occupancy") or None,
                          risk_class=ctx.get("risk_class") or None, facts=facts)


def _exit_limit(ctx: dict[str, Any]) -> dict[str, Any]:
    """Limite até a saída: Anexo C consultado, valor do analista e o efetivo, lado a lado.

    O limite efetivo leva junto a origem (``..._source``), que o achado mostra.
    """
    ref = ctx.get("exit_distance_reference")
    status = ref.get("status") if isinstance(ref, dict) else None
    table: Any = None
    if status == "FOUND":
        table = ref.get("limit_m")
    elif status == "DEPENDS_ON_FLOOR":
        # Piso de descarga ainda não identificado: os dois limites seguem juntos e o
        # executor só conclui o que vale para ambos.
        table = sorted(set((ref.get("by_floor_m") or {}).values())) or None
    declared = ctx.get(EXIT_LIMIT)
    out: dict[str, Any] = {}
    for key, value in effective_requirement(table, declared).items():
        if value is None:
            continue
        name = key.replace("_requirement", "")
        out[f"context.{name}_{EXIT_LIMIT}"] = value
    if declared is not None:
        out[f"context.effective_{EXIT_LIMIT}_source"] = "informado pelo analista"
    elif status == "FOUND":
        out[f"context.effective_{EXIT_LIMIT}_source"] = (
            f"{ref['source']['document']}, {ref['source']['item']}, linha {ref['row']}, "
            f"coluna {ref['column']} (p. {ref['page']})")
    elif table is not None:
        floors = ref.get("by_floor_m") or {}
        out[f"context.effective_{EXIT_LIMIT}_source"] = (
            f"{ref['source']['document']}, {ref['source']['item']}, coluna {ref['column']} "
            f"(p. {ref['page']}): {floors.get('DISCHARGE')} m no piso de descarga, "
            f"{floors.get('OTHER')} m nos demais — piso de descarga não identificado")
    if declared is None and table is not None and (red := ref.get("reduction")):
        base = ref.get("base_limit_m")
        if base is None:  # por piso: "40/35" (descarga/demais)
            by = ref.get("base_by_floor_m") or {}
            base = f"{by.get('DISCHARGE')}/{by.get('OTHER')}"
        out[f"context.effective_{EXIT_LIMIT}_source"] += (
            f"; sem leiaute: reduzido em 30% ({red['document']} {red['item']}, tabela: "
            f"{base} m), distância em linha reta")
    return out


def _required_measures(reference: Any) -> dict[str, dict[str, Any]]:
    """Medidas com X incondicional na consulta ao Anexo III gravada na análise."""
    if not isinstance(reference, dict) or reference.get("status") != "INDICATIVE":
        return {}
    return {m["id"]: m for m in reference.get("measures", [])
            if m.get("status") == "REQUIRED"}


def requirement_evidence(analysis: dict[str, Any], process_id: str) -> list[Evidence]:
    """Como cada exigência foi determinada: pela tabela, pelo analista ou pelos dois.

    A consulta ao Anexo III aponta a coluna da tabela (localizador); a declaração do
    analista é fato humano e dispensa localizador. Com as duas, o consenso aparece.
    """
    ctx = analysis.get("context") or {}
    reference = ctx.get("requirements_reference") or {}
    marked = _required_measures(reference)
    source = reference.get("source") if isinstance(reference, dict) else None
    source_id = (" ".join(str(source.get(k, "")) for k in ("document", "item")).strip()
                 if isinstance(source, dict) else str(source or "Anexo III"))
    out = []
    for _system, form_field, measure, field in REQUIREMENTS:
        if measure in marked:
            out.append(Evidence(
                id=f"table:{field}", process_id=process_id,
                source_type=EvidenceSourceType.NORMATIVE_TABLE, source_id=source_id,
                source_version=1, source_hash=reference.get("source_sha256") or "",
                locator=EvidenceLocator(
                    table_row=f"{reference.get('column')} / {marked[measure]['label']}"),
                field=field, raw_value=marked[measure].get("cell"), normalized_value=True,
                extraction_method="TABLE_LOOKUP", algorithm="consult_requirements"))
        declared = ctx.get(form_field)
        if isinstance(declared, bool):
            out.append(Evidence(
                id=f"human:{field}", process_id=process_id,
                source_type=EvidenceSourceType.HUMAN, source_id="formulário da análise",
                source_version=1, source_hash=_context_hash(ctx), field=field,
                raw_value=declared, normalized_value=declared, extraction_method="MANUAL"))
    return out


def _context_hash(ctx: dict[str, Any]) -> str:
    canonical = json.dumps(ctx, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def plant_evidence(analysis: dict[str, Any], *, process_id: str, source_id: str | None = None,
                   source_version: int = 1) -> PlantEvidence:
    """Converte uma análise da planta em evidências por pavimento."""
    if analysis.get("schema_version") != SCHEMA:
        raise PlantEvidenceError(
            f"saída de análise não suportada: {analysis.get('schema_version')!r}")
    drawing = analysis.get("drawing") or {}
    sha = drawing.get("sha256")
    if not sha:
        raise PlantEvidenceError("análise sem o hash do desenho: evidência sem origem")
    source = source_id or sha[:16]
    dictionary = analysis.get("dictionary") or {}
    floors = []
    skipped = []
    for region in analysis.get("regions", []):
        if region.get("kind") != "PLAN":
            skipped.append((region.get("name", region["id"]), region.get("skipped", "")))
            continue
        floors.append(_floor(region, process_id=process_id, source=source,
                             version=source_version, sha=sha, dictionary=dictionary))
    return PlantEvidence(context=process_context(analysis, process_id), floors=tuple(floors),
                         process_evidence=EvidenceSet.build(
                             process_id, requirement_evidence(analysis, process_id)),
                         drawing_sha256=sha, skipped_regions=tuple(skipped))


def _floor(region: dict[str, Any], *, process_id: str, source: str, version: int, sha: str,
           dictionary: dict[str, Any]) -> FloorScope:
    floor_id = region["id"]
    items: list[Evidence] = []
    gaps: list[ExtractionGap] = []

    def base(**kw: Any) -> Evidence:
        return Evidence(process_id=process_id, source_type=EvidenceSourceType.CAD,
                        source_id=source, source_version=version, source_hash=sha, **kw)

    found: set[str] = set()
    for sym in region.get("symbols", []):
        field = SYMBOL_FIELDS.get(sym.get("class", ""))
        if field is None or sym.get("excluded") is not None:
            continue
        found.add(field)
        presumed = bool((sym.get("attrs") or {}).get("presumed"))
        items.append(base(
            id=f"cad:{floor_id}:{field}:{sym['id']}",
            locator=EvidenceLocator(entity_handle=sym.get("handle") or None,
                                    layer=sym.get("layer") or None, floor_id=floor_id,
                                    object_key=sym.get("object_key")),
            field=field, raw_value=sym.get("block") or sym.get("evidence") or sym["class"],
            normalized_value=True, extraction_method=SYMBOL_METHOD,
            extraction_schema=f"symbols:{dictionary.get('id', '')}",
            algorithm=f"symbol:{sym.get('stage') or 'block_name'}",
            algorithm_version=str(dictionary.get("version", "")) or None,
            quality_gate=("quality.extinguisher.not_presumed" if presumed else None)))
        if field == "extinguisher":
            # Agente do extintor (atributo do bloco ou texto junto): composição da NT 2-01
            # 5.2.5. Não identificado fica explícito, nunca omitido.
            attrs = sym.get("attrs") or {}
            agent = attrs.get("agent") or UNKNOWN_AGENT
            items.append(base(
                id=f"cad:{floor_id}:extinguisher_agent:{sym['id']}",
                locator=EvidenceLocator(entity_handle=sym.get("handle") or None,
                                        layer=sym.get("layer") or None, floor_id=floor_id,
                                        object_key=sym.get("object_key")),
                field="extinguisher_agent",
                raw_value=attrs.get("agent_text") or sym.get("block") or sym["class"],
                normalized_value=agent, extraction_method=SYMBOL_METHOD,
                extraction_schema=f"symbols:{dictionary.get('id', '')}",
                algorithm="symbol:agent", quality_gate=(
                    "quality.extinguisher.not_presumed" if presumed else None)))
    for field in SYMBOL_FIELDS.values():
        if field not in found:
            gaps.append(ExtractionGap(process_id=process_id, source_id=source,
                                      source_version=version, field=field,
                                      extraction_method=SYMBOL_METHOD))

    geometry = region.get("geometry") or {}
    walls_gate = None if geometry.get("walls_detected") else "quality.walls_detected"
    if (area := geometry.get("interior_m2")) is not None:
        items.append(base(
            id=f"cad:{floor_id}:floor_area_m2",
            locator=EvidenceLocator(floor_id=floor_id,
                                    bbox=_bbox(region.get("bbox_m"))),
            field="floor_area_m2", raw_value=f"{area} m²", normalized_value=area, unit="m²",
            uncertainty_abs=geometry.get("interior_uncertainty_m2"),
            extraction_method=GEOMETRY_METHOD, algorithm="grid_interior",
            quality_gate=walls_gate))

    for key, _classes, _label in SYSTEMS:
        cov = (region.get("coverage") or {}).get(key) or {}
        if (direct := cov.get("max_direct_m")) is not None:
            unc = cov.get("direct_uncertainty_m")
            items.append(base(
                id=f"cad:{floor_id}:{key}_direct_distance_m",
                locator=EvidenceLocator(floor_id=floor_id,
                                        bbox=_point(cov.get("direct_worst_point"))),
                field=f"{key}_direct_distance_m", raw_value=f"{direct} ± {unc} m",
                normalized_value=direct, unit="m", uncertainty_abs=unc,
                extraction_method=GEOMETRY_METHOD, algorithm=cov.get("direct_algorithm"),
                algorithm_version=cov.get("direct_algorithm_version")))
        value = cov.get("max_travel_m")
        if value is None:
            continue
        unc = cov.get("uncertainty_m")
        items.append(base(
            id=f"cad:{floor_id}:{key}_walk_distance_m",
            locator=EvidenceLocator(floor_id=floor_id, bbox=_point(cov.get("worst_point"))),
            field=f"{key}_walk_distance_m", raw_value=f"{value} ± {unc} m",
            normalized_value=value, unit="m", uncertainty_abs=unc,
            extraction_method=GEOMETRY_METHOD,
            algorithm=cov.get("algorithm", TRAVEL_ALGORITHM),
            algorithm_version=cov.get("algorithm_version", TRAVEL_ALGORITHM_VERSION),
            uncertainty_budget=cov.get("uncertainty_budget"),
            quality_gate=walls_gate))

    facts = {name: fact.get("value") for name, fact in (region.get("facts") or {}).items()
             if name.startswith(("quality.", "floor."))}
    return FloorScope(id=floor_id, label=region.get("name") or floor_id,
                      evidence=EvidenceSet.build(process_id, items, gaps), facts=facts)


def _bbox(values: Any) -> tuple[float, float, float, float] | None:
    if not values or len(values) != 4:
        return None
    return tuple(float(v) for v in values)  # type: ignore[return-value]


def _point(values: Any) -> tuple[float, float, float, float] | None:
    if not values or len(values) != 2:
        return None
    x, y = (float(v) for v in values)
    return (x, y, x, y)
