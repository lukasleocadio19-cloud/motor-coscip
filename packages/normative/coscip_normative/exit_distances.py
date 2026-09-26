"""NT 2-08, Anexo C: distância máxima a percorrer até a saída, como dado conferível.

A tabela sai do texto ingerido (página 22), não de digitação solta: cada linha é conferida
com ``verify_table_row`` e cada limite precisa estar escrito numa célula daquela linha.

A consulta só devolve um limite quando TODOS os dados que o decidem são conhecidos. Ela
nunca aplica as observações que aumentam o limite (lado seguro). Sem leiaute definido vale o
item 5.3.3.3 (decisão do analista registrada na tabela): limite reduzido em 30% e medida em
linha reta.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from coscip_normative.sources import (
    NormativeText,
    fold,
    normalize_document_id,
    verify_citation,
    verify_table_row,
)

SCHEMA = "exit-distances/1.0"
COLUMNS = ("UNPROTECTED_SINGLE", "UNPROTECTED_MULTIPLE", "PROTECTED_SINGLE",
           "PROTECTED_MULTIPLE")
CONSTRUCTION_TYPES = ("ALFA", "BETA", "GAMA")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _Source(_Strict):
    document: str
    item: str
    page: int
    title: str


class _Column(_Strict):
    id: Literal[COLUMNS]
    label: str


class _Row(_Strict):
    id: str
    construction: Literal[CONSTRUCTION_TYPES]
    groups: Literal["ANY"] | tuple[str, ...]
    floor: Literal["ANY", "DISCHARGE", "OTHER"]
    limits_m: tuple[float, float, float, float]
    verify: tuple[str, ...] = Field(min_length=2)
    merged_from: str | None = None


class _Note(_Strict):
    id: str
    effect: Literal["INCREASES", "REDUCES", "REFERRAL", "CONDITION"]
    quote: tuple[str, ...] = Field(min_length=1)
    text: str
    divisions: tuple[str, ...] = ()


class _Basis(_Strict):
    document: str
    item: str
    quote: tuple[str, ...] = Field(min_length=1)


class _LayoutReduction(_Strict):
    """Regra para projeto sem leiaute definido (NT 2-08 5.3.3.3)."""

    factor: float = Field(gt=0, lt=1)
    measure: Literal["DIRECT"]
    basis: _Basis
    decision: str


class _Table(_Strict):
    schema_version: Literal[SCHEMA]
    source: _Source
    columns: tuple[_Column, ...]
    construction_types: dict[str, str]
    rows: tuple[_Row, ...]
    layout_reduction: _LayoutReduction | None = None
    notes: tuple[_Note, ...] = ()


def _cell(value: float) -> str:
    """Como o limite aparece na célula (sem espaço: o texto convertido às vezes cola)."""
    return f"{value:.2f}".replace(".", ",") + "m"


def verify_exit_distances(table: dict[str, Any], sources: dict[str, NormativeText],
                          failures: list[str]) -> dict[str, Any]:
    """Confere estrutura, cada linha na mesma linha da tabela e cada observação citada."""
    try:
        parsed = _Table.model_validate(table)
    except ValidationError as exc:
        failures.append(f"Anexo C: estrutura inválida: {exc}")
        return {"verified": False}
    errors: list[str] = []
    src = parsed.source
    if [c.id for c in parsed.columns] != list(COLUMNS):
        errors.append("colunas fora da ordem conferida")
    ids = [r.id for r in parsed.rows]
    if len(ids) != len(set(ids)):
        errors.append("linhas duplicadas")
    rows_out = []
    for row in parsed.rows:
        check = verify_table_row(sources, src.document, src.item, row.verify)
        cells = {fold(c).replace(" ", "") for c in row.verify}
        unwritten = [v for v in row.limits_m if fold(_cell(v)) not in cells]
        if not check.verified:
            errors.append(f"linha {row.id}: {check.problem}")
        elif check.page != src.page:
            errors.append(f"linha {row.id}: encontrada na página {check.page}, não {src.page}")
        if unwritten:
            errors.append(f"linha {row.id}: limite sem célula conferida: {unwritten}")
        if row.merged_from and row.merged_from not in ids:
            errors.append(f"linha {row.id}: merged_from desconhecido")
        rows_out.append({"id": row.id, "verified": check.verified and not unwritten,
                         "page": check.page, "excerpt": check.excerpt})
    for note in parsed.notes:
        check = verify_citation(sources, src.document, src.item, note.quote)
        if not check.verified:
            errors.append(f"observação {note.id}: {check.problem} {check.missing_terms}")
    if (red := parsed.layout_reduction) is not None:
        check = verify_citation(sources, red.basis.document, red.basis.item, red.basis.quote)
        if not check.verified:
            errors.append(f"redução sem leiaute: {check.problem} {check.missing_terms}")
        # "reduzidas em 30%" ⇒ fica 70%. O fator precisa bater com o texto citado.
        if not any("em 30%" in q for q in red.basis.quote) or abs(red.factor - 0.7) > 1e-9:
            errors.append("redução sem leiaute: fator não corresponde a 'reduzidas em 30%'")
    failures.extend(f"Anexo C: {e}" for e in errors)
    text = sources.get(normalize_document_id(src.document))
    # A tabela conferida vai inteira para o manifesto do pacote; a consulta lê dela.
    return {**table, "verified": not errors, "row_checks": rows_out,
            "source_text_sha256": text.text_sha256 if text else None}


def _group_of(occupancy: str) -> str:
    return occupancy.split("-")[0].strip().upper()


def _matches(row: dict[str, Any], occupancy: str) -> bool:
    groups = row["groups"]
    if groups == "ANY":
        return True
    occupancy = occupancy.strip().upper()
    # Subdivisões explícitas (G-3) valem sozinhas; letra sozinha (C) vale para o grupo.
    return occupancy in groups or (_group_of(occupancy) in groups
                                   and not any(g.startswith(_group_of(occupancy) + "-")
                                               for g in groups))


def consult_exit_distance(table: dict[str, Any] | None,
                          context: dict[str, Any]) -> dict[str, Any]:
    """Limite do Anexo C para o enquadramento informado, ou por que não há limite.

    Entradas (do formulário): ``occupancy``, ``construction_type`` (ALFA/BETA/GAMA),
    ``sprinklers_or_detection``, ``multiple_exits``, ``layout_defined`` e, para γ,
    ``building_floors`` (térrea ⇒ o único pavimento é o de descarga).
    """
    out: dict[str, Any] = {"status": "UNAVAILABLE", "limit_m": None, "missing": [],
                           "notes": [], "message": "Pacote sem Anexo C verificado."}
    if not table or not table.get("verified"):
        return out
    source = table["source"]
    out.update(source=source, message="")
    occupancy = context.get("occupancy")
    wanted = {"occupancy": occupancy, "construction_type": context.get("construction_type"),
              "sprinklers_or_detection": context.get("sprinklers_or_detection"),
              "multiple_exits": context.get("multiple_exits"),
              "layout_defined": context.get("layout_defined")}
    missing = [k for k, v in wanted.items() if v is None or v == ""]
    notes = [n for n in table.get("notes", [])
             if not n.get("divisions") or (occupancy and occupancy in n["divisions"])]
    out["notes"] = [{"id": n["id"], "effect": n["effect"], "text": n["text"]} for n in notes]
    if missing:
        return {**out, "status": "MISSING_DATA", "missing": missing,
                "message": "Informe os dados que decidem a linha e a coluna do Anexo C."}
    if any(n["effect"] == "REFERRAL" for n in notes):
        return {**out, "status": "OUT_OF_SCOPE",
                "message": "A ocupação remete a outra NT (observações do Anexo C)."}
    reduction = table.get("layout_reduction")
    if wanted["layout_defined"] is not True and not reduction:
        return {**out, "status": "REVIEW_REQUIRED",
                "message": "Sem leiaute definido e sem regra de redução no pacote: o analista "
                           "informa o limite."}
    rows = [r for r in table["rows"] if r["construction"] == wanted["construction_type"]
            and _matches(r, occupancy)]
    if not rows:
        return {**out, "status": "OUT_OF_SCOPE",
                "message": f"{occupancy} não aparece nas linhas {wanted['construction_type']}."}
    result = _lookup(table, rows, wanted, context, out)
    if wanted["layout_defined"] is True or result["status"] not in {"FOUND",
                                                                    "DEPENDS_ON_FLOOR"}:
        return {**result, "measure": "TRAVEL"}
    return _reduced(result, reduction)


def _reduced(result: dict[str, Any], reduction: dict[str, Any]) -> dict[str, Any]:
    """Item 5.3.3.3: sem leiaute, limite × fator e distância medida em linha reta."""
    factor = reduction["factor"]
    basis = reduction["basis"]
    out = {**result, "measure": "DIRECT",
           "reduction": {"factor": factor, "document": basis["document"],
                         "item": basis["item"], "decision": reduction["decision"]}}
    if result["status"] == "FOUND":
        out["base_limit_m"] = result["limit_m"]
        out["limit_m"] = round(result["limit_m"] * factor, 2)
    else:
        out["base_by_floor_m"] = result["by_floor_m"]
        out["by_floor_m"] = {k: round(v * factor, 2) for k, v in result["by_floor_m"].items()}
    out["message"] = (f"Sem leiaute definido: limite reduzido em 30% e distância medida em "
                      f"linha reta ({basis['document']} {basis['item']}). " + result["message"])
    return out


def _lookup(table: dict[str, Any], rows: list[dict[str, Any]], wanted: dict[str, Any],
            context: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    source = table["source"]
    column = COLUMNS.index(("PROTECTED" if wanted["sprinklers_or_detection"] else "UNPROTECTED")
                           + ("_MULTIPLE" if wanted["multiple_exits"] else "_SINGLE"))
    by_floor = {r["floor"]: r for r in rows}
    if "ANY" in by_floor:
        row = by_floor["ANY"]
    elif context.get("building_floors") == 1:
        row = by_floor["DISCHARGE"]  # térrea: o único pavimento é o de descarga
    else:
        values = {f: r["limits_m"][column] for f, r in by_floor.items()}
        if len(set(values.values())) == 1:
            row = next(iter(by_floor.values()))
        else:
            return {**out, "status": "DEPENDS_ON_FLOOR", "by_floor_m": values,
                    "rows": {f: r["id"] for f, r in by_floor.items()},
                    "column": COLUMNS[column], "page": source["page"],
                    "message": ("O limite muda entre o piso de descarga e os demais "
                                f"({values.get('DISCHARGE')} m / {values.get('OTHER')} m). "
                                "A análise conclui quando a medida atende o menor ou "
                                "ultrapassa o maior; entre os dois, fica em aberto.")}
    return {**out, "status": "FOUND", "limit_m": row["limits_m"][column], "row": row["id"],
            "column": COLUMNS[column], "page": source["page"],
            "message": "Consulta em rascunho; conferir as observações do Anexo C."}
