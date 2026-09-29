"""Consulta indicativa do Anexo III; nunca transforma ausência de linha em dispensa."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from coscip_normative.sources import NormativeText, fold


class _Source(BaseModel):
    document: str
    item: str
    page: int = Field(gt=0)
    title: str
    pdf_sha256: str
    url: str
    visual_check: str


class _Column(BaseModel):
    id: str
    divisions: list[str]


class _Measure(BaseModel):
    id: str
    label: str
    source_row: list[str] = Field(min_length=4, max_length=13)
    cells: list[str] = Field(min_length=3, max_length=12)
    label_quotes: list[str] = Field(min_length=1)


class _Table(BaseModel):
    model_config = ConfigDict(strict=True)
    schema_version: str = Field(pattern=r"^requirements/1\.0$")
    source: _Source
    columns: list[_Column] = Field(min_length=3, max_length=12)
    header_rows: list[list[str]] = Field(min_length=5, max_length=11)
    measures: list[_Measure] = Field(min_length=2, max_length=13)
    notes: list[str] = Field(min_length=1)


# Correspondência posicional conferida nos cabeçalhos mesclados do PDF p. 26.
_COLUMN_DIVISIONS = [
    {f"{g}-{n}" for g, count in [("A", 6), ("D", 5), ("E", 3), ("G", 6)]
     for n in range(1, count + 1)},
    {"B-1", "B-2"}, {f"C-{n}" for n in range(1, 5)},
    {f"F-{n}" for n in [1, 2, 3, 4, 7, 8, 10]}, {"F-5", "F-11"}, {"F-6"}, {"F-9"},
    {"H-1", "H-4"}, {"H-2", "H-3"},
    {"I-1", "I-2", "I-3", "J-1", "J-2", "J-3", "J-4", "M-3"}, {"L-1"},
]
_MEASURE_LABELS = {
    "extinguishers": "Extintores", "signage": "Sinalização de segurança",
    "lighting": "Iluminação de Emergência", "exits": "Saídas de Emergência",
    "emergency_plan": "Plano de emergência",
    "finishing_materials": "Controle de Materiais de Acabamento",
    "smoke_control": "Controle de fumaça",
}


_RESIDENTIAL_LABELS = {
    "extinguishers": "Extintores", "hydrants": "Hidrantes e mangotinhos",
    "sprinklers": "Chuveiros automáticos", "signage": "Sinalização de segurança",
    "lighting": "Iluminação de Emergência", "alarm": "Alarme de Incêndio",
    "detection": "Detecção de Incêndio", "exits": "Saídas de Emergência",
    "urban_hydrant": "Hidrante urbano", "vehicle_access": "Acesso de viatura em edificações",
    "vertical_compartmentation": "Compartimentação Vertical",
    "structural_safety": "Segurança Estrutural contra Incêndio",
    "finishing_materials": "Controle de Materiais de Acabamento",
}
_RESIDENTIAL_COLUMNS = [{"A-2"}] * 6 + [{"A-3"}] * 6


def verify_requirements(table: dict, sources: dict[str, NormativeText],
                        failures: list[str], *, residential: bool = False,
                        grouping: bool = False) -> dict:
    try:
        _Table.model_validate(table)
    except ValueError as exc:
        failures.append(f"Anexo III: estrutura inválida: {exc}")
        return {"verified": False}
    number = 4 if grouping else 3 if residential else 2
    expected_columns = _RESIDENTIAL_COLUMNS if residential else _COLUMN_DIVISIONS
    expected_labels = _RESIDENTIAL_LABELS if residential else _MEASURE_LABELS
    if grouping:
        expected_columns = [{"A-4"}, {"A-4"}, {"A-5"}]
        expected_labels = {"urban_hydrant": "Hidrante urbano",
                           "vehicle_access": "Acesso de viatura em edificações"}
    width = len(expected_columns)
    source = table["source"]
    src = sources.get(source["document"])
    errors = []
    if (source["document"] != "Decreto 42/2018" or source["page"] != 24 + number
            or source["item"] != f"Anexo III, Tabela {number}"):
        errors.append("identificação da tabela não corresponde ao mapeamento conferido")
    page = ""
    if src:
        match = re.search(rf"^## Página {source['page']}\s*$([\s\S]*?)(?=^## Página |\Z)",
                          src.text, re.M)
        page = match.group(1) if match else ""
    if not src or src.pdf_sha256 != source["pdf_sha256"]:
        errors.append("PDF diferente do conferido visualmente ou fonte ausente")
    if (fold(source["title"]) not in fold(page)
            or any(fold(q) not in fold(page) for q in table.get("scope_quotes", []))):
        errors.append("título/escopo da tabela ausente na página indicada")
    raw = page.split("<!-- tabela-conferida:")[0]  # a tabela conferida publicada não é fonte
    rows = [[fold(c) for c in line.strip().strip("|").split("|")]
            for line in raw.splitlines() if line.strip().startswith("|")]
    columns = table["columns"]
    if [set(c["divisions"]) for c in columns] != expected_columns:
        errors.append("divisões não correspondem à ordem das colunas conferidas no PDF")
    if len(columns) != width or len({c['id'] for c in columns}) != width:
        errors.append(f"a Tabela {number} precisa conter {width} colunas distintas")
    divisions = [d for c in columns for d in c["divisions"]]
    if not (residential or grouping) and len(divisions) != len(set(divisions)):
        errors.append("divisão repetida em colunas distintas")
    if len(table["header_rows"]) != (8 if grouping else 11 if residential else 10):
        errors.append("cabeçalhos incompletos")
    for header in table["header_rows"]:
        if [fold(c) for c in header] not in rows:
            errors.append("cabeçalho não confere célula a célula")
    measures = table["measures"]
    if {m["id"]: m["label"] for m in measures} != expected_labels:
        errors.append(f"medidas e rótulos não correspondem à Tabela {number}")
    if len({m['id'] for m in measures}) != len(measures):
        errors.append("medida duplicada")
    for measure in measures:
        split_labels = ({"vehicle_access", "structural_safety"} if residential
                        else {"finishing_materials"})
        if grouping:
            split_labels = {"vehicle_access"}
        label_cell = "" if measure["id"] in split_labels else measure["label"]
        if measure["source_row"][0] != label_cell:
            errors.append(f"rótulo ligado à linha errada: {measure['id']}")
        expected = [fold(c) for c in measure["source_row"]]
        if len(expected) != width + 1 or expected not in rows:
            errors.append(f"linha completa não confere: {measure['label']}")
        if measure["cells"] != measure["source_row"][1:]:
            errors.append(f"valores divergentes da transcrição: {measure['label']}")
        for quote in measure.get("label_quotes", []):
            if fold(quote) not in fold(page):
                errors.append(f"rótulo ausente: {quote}")
    note_start = next((i for i, row in enumerate(rows)
                       if row[0].startswith(fold("OBSERVAÇÕES ESPECÍFICAS:"))), None)
    source_notes = (" ".join(row[0] for row in rows[note_start:] if row[0])
                    if note_start is not None else "")
    if not source_notes or fold(" ".join(table["notes"])) != source_notes:
        errors.append("observações ausentes, incompletas ou divergentes da fonte")
    failures.extend(f"Anexo III / Tabela {number}: {e}" for e in errors)
    checked = {**table, "verified": not errors,
               "source_sha256": src.text_sha256 if src else None}
    if not (residential or grouping) and table.get("residential_table") is not None:
        checked["residential_table"] = verify_requirements(
            table["residential_table"], sources, failures, residential=True)
        checked["verified"] &= checked["residential_table"]["verified"]
    if not (residential or grouping) and table.get("grouping_table") is not None:
        checked["grouping_table"] = verify_requirements(
            table["grouping_table"], sources, failures, grouping=True)
        checked["verified"] &= checked["grouping_table"]["verified"]
    return checked


_VALUE = re.compile(r"^(X.*|-+|—)$")


def _page_rows(src: NormativeText | None, page: int) -> list[list[str]]:
    """Linhas de tabela da página (camada de texto), com os rótulos que a extração quebrou em
    três linhas (rótulo / valores / rótulo) juntados de volta; só as células não vazias."""
    if src is None:
        return []
    match = re.search(rf"^## Página {page}\s*$([\s\S]*?)(?=^## Página |\Z)", src.text, re.M)
    body = (match.group(1) if match else "").split("<!-- tabela-conferida:")[0]
    rows = [[c.strip() for c in line.strip().strip("|").split("|") if c.strip()]
            for line in body.splitlines() if line.strip().startswith("|")]
    rows = [r for r in rows if r and not re.fullmatch(r"[\s:-]+", "".join(r))]
    out, i = [], 0
    while i < len(rows):
        if (i + 2 < len(rows) and len(rows[i]) == 1 and not _VALUE.match(rows[i][0])
                and all(_VALUE.match(c) for c in rows[i + 1]) and len(rows[i + 2]) == 1
                and not _VALUE.match(rows[i + 2][0])):
            out.append([f"{rows[i][0]} {rows[i + 2][0]}", *rows[i + 1]])
            i += 3
            continue
        out.append(rows[i])
        i += 1
    return out


def _fold_cell(cell: str) -> str:
    text = fold(cell)
    text = re.sub(r"\s*,\s*", ",", text)
    return re.sub(r"\bx\s+(?=\d)", "x", text)


HEIGHT_BANDS = ("Térrea", "2pav", "3pav", "4, 5 e 6pav", "Acima de 6pav com H ≤ 30m", "H > 30m")


def verify_height_tables(data: dict, sources: dict[str, NormativeText],
                         failures: list[str]) -> dict:
    """Confere as Tabelas 5–21 contra o texto ingerido: título na página, cada linha de medida
    (rótulo + todas as células) igual a uma linha da tabela da página, colunas no padrão."""
    src = sources.get(data.get("source", {}).get("document", ""))
    errors: list[str] = []
    if not src or src.pdf_sha256 != data["source"].get("pdf_sha256"):
        errors.append("Anexo III 5–21: PDF diferente do conferido ou fonte ausente")
    tables_out = []
    seen_divisions: set[str] = set()
    for t in data.get("tables") or []:
        errs = []
        page_rows = [[_fold_cell(c) for c in r] for r in _page_rows(src, t["page"])]
        page_text = " ".join(" ".join(r) for r in page_rows)
        if (_fold_cell(f"Tabela {t['table']}") not in page_text
                or _fold_cell(t["title"][:60]) not in page_text):
            errs.append("título ausente na página")
        if t.get("verification", {}).get("state") != "verificada":
            errs.append("tabela não verificada em dois caminhos")
        width = 0
        for block in t["blocks"]:
            if tuple(block["colunas"]) != HEIGHT_BANDS:
                errs.append("colunas fora do padrão de pavimentos/altura")
            dup = seen_divisions & set(block["divisoes"])
            if dup:
                errs.append(f"divisão em mais de uma tabela: {sorted(dup)}")
            seen_divisions |= set(block["divisoes"])
            width += len(block["colunas"])
        for m in t["measures"]:
            row = [_fold_cell(c) for c in [m["source_label"], *m["cells"]]]
            if len(m["cells"]) != width:
                errs.append(f"{m['label']}: {len(m['cells'])} células, esperado {width}")
            elif row not in page_rows:
                errs.append(f"linha não confere com o texto: {m['label']}")
        failures.extend(f"Anexo III / Tabela {t['table']}: {e}" for e in errs)
        errors.extend(errs)
        tables_out.append({**t, "verified": not errs})
    failures.extend(e for e in errors if e.startswith("Anexo III 5–21"))
    return {"source": data.get("source"), "tables": tables_out,
            "verified": not errors and bool(tables_out),
            "source_sha256": src.text_sha256 if src else None}


def _height_band(floors: int, height: float) -> int:
    """Coluna das Tabelas 5–21: Térrea, 2pav, 3pav, 4–6pav, >6pav com H ≤ 30 m, H > 30 m."""
    if height > 30:
        return 5
    if floors <= 3:
        return max(floors, 1) - 1
    return 3 if floors <= 6 else 4


def _consult_height(height: dict | None, context: dict) -> dict:
    out = {"status": "UNAVAILABLE", "measures": [], "notes": [], "source": None,
           "message": "Pacote sem as Tabelas 5–21 do Anexo III verificadas."}
    if height is None:  # pacote sem as tabelas: fora do que esta consulta cobre
        return {**out, "status": "OUT_OF_SCOPE",
                "message": "Consultar tabelas específicas: ATC acima de 900 m² "
                           "ou mais de 2 pavimentos."}
    if not height.get("verified"):
        return out
    occ = context["occupancy"]
    found = [(t, bi, b) for t in height["tables"] for bi, b in enumerate(t["blocks"])
             if occ in b["divisoes"]]
    if not found:
        return {**out, "status": "OUT_OF_SCOPE",
                "message": "Divisão sem coluna nas Tabelas 5–21; consultar a NT específica."}
    table, bi, block = found[0]
    out.update(source={"document": "Decreto 42/2018", "item": f"Anexo III, Tabela {table['table']}",
                       "page": table["page"], "title": table["title"]},
               source_sha256=height.get("source_sha256"),
               notes=[f"Observações da Tabela {table['table']} na página {table['page']}."])
    h = context.get("building_height_m")
    if h is None:
        return {**out, "status": "MISSING_DATA",
                "message": f"Informe a altura da edificação para escolher a coluna da "
                           f"Tabela {table['table']}."}
    band = _height_band(int(context["building_floors"]), float(h))
    offset = sum(len(b["colunas"]) for b in table["blocks"][:bi])
    measures = []
    for m in table["measures"]:
        cell = m["cells"][offset + band]
        status = ("NOT_MARKED" if cell == "-" else
                  "REQUIRED" if cell == "X" and not m.get("label_note") else "CONDITIONAL")
        measures.append({"id": m["id"], "label": m["label"], "cell": cell, "status": status})
    fields = {"lighting": "requires_lighting", "hydrants": "requires_hydrants",
              "alarm": "requires_alarm"}
    conflicts = [f"{m['label']}: consta X na tabela, mas foi informado como não exigido. "
                 "Conferir a justificativa no processo."
                 for m in measures if m["status"] == "REQUIRED" and m["id"] in fields
                 and context.get(fields[m["id"]]) is False]
    return {**out, "status": "INDICATIVE",
            "column": f"{'/'.join(block['divisoes'])} / {block['colunas'][band]}",
            "conflicts": conflicts, "measures": measures,
            "message": "Consulta em rascunho; conferir as observações da tabela e os riscos "
                       "específicos. Traço não é dispensa global; X com nota é condicional."}


def consult_requirements(table: dict | None, context: dict[str, Any]) -> dict:
    """Área e pavimentos são da edificação, nunca do recorte ou da área útil em grade."""
    out = {"status": "MISSING_DATA", "message": "Informe ocupação, ATC e pavimentos da edificação.",
           "measures": [], "notes": [], "source": None}
    if not table or not table.get("verified"):
        return {**out, "status": "UNAVAILABLE", "message": "Pacote sem Anexo III verificado."}
    out.update(source=table["source"], notes=table["notes"],
               source_sha256=table["source_sha256"])
    occ = context.get("occupancy")
    area, floors = context.get("building_area_m2"), context.get("building_floors")
    if occ in {"A-4", "A-5"}:
        if context.get("unifamiliar") or context.get("single_occupancy") is not True:
            return {**out, "status": "REVIEW_REQUIRED",
                    "message": "Confirme o enquadramento do agrupamento e a ocupação única."}
        return _consult_grouping(table.get("grouping_table"), context)
    if not occ or area is None or floors is None:
        return out
    if (context.get("unifamiliar") or occ in {"A-1", "A-6"}
            or context.get("single_occupancy") is not True):
        return {**out, "status": "REVIEW_REQUIRED",
                "message": "Conferir isenções, agrupamentos ou ocupações múltiplas com o analista."}
    if area > 900 or floors > 2:
        if occ in {"A-2", "A-3"}:
            return _consult_residential(table.get("residential_table"), context)
        return _consult_height(table.get("height_tables"), context)
    column = next((i for i, c in enumerate(table["columns"]) if occ in c["divisions"]), None)
    if column is None:
        return {**out, "status": "OUT_OF_SCOPE",
                "message": "Divisão sem coluna na Tabela 2; consultar tabela e NT específicas."}
    return _column_result(table, column, out, context)


def _column_result(table: dict, column: int, out: dict, context: dict) -> dict:
    measures = []
    for m in table["measures"]:
        cell = m["cells"][column]
        status = ("NOT_MARKED" if cell == "-" else
                  "REQUIRED" if cell == "X" else "CONDITIONAL")
        measures.append({"id": m["id"], "label": m["label"], "cell": cell, "status": status})
    fields = {"lighting": "requires_lighting", "hydrants": "requires_hydrants",
              "alarm": "requires_alarm"}
    conflicts = [f"{m['label']}: consta X na tabela, mas foi informado como não exigido. "
                 "Conferir a justificativa no processo."
                 for m in measures if m["status"] == "REQUIRED" and m["id"] in fields
                 and context.get(fields[m["id"]]) is False]
    return {**out, "status": "INDICATIVE", "column": table["columns"][column]["id"],
            "conflicts": conflicts,
            "message": "Consulta em rascunho; conferir notas e riscos específicos. "
                       "Traço não é dispensa global.",
            "measures": measures}


def _consult_residential(table: dict | None, context: dict) -> dict:
    out = {"status": "UNAVAILABLE", "message": "Pacote sem Tabela 3 verificada.",
           "measures": [], "notes": [], "source": None}
    if not table or not table.get("verified"):
        return out
    out.update(source=table["source"], notes=table["notes"],
               source_sha256=table["source_sha256"])
    height = context.get("building_height_m")
    if height is None:
        return {**out, "status": "MISSING_DATA",
                "message": "Informe a altura da edificação para selecionar a coluna da Tabela 3."}
    floors = context["building_floors"]
    a2 = context["occupancy"] == "A-2"
    if height > 30:
        band = 5
    elif floors <= 3:
        band = floors - 1
    elif floors <= (5 if a2 else 6):
        band = 3
    else:
        band = 4
    return _column_result(table, band + (0 if a2 else 6), out, context)



def _consult_grouping(table: dict | None, context: dict) -> dict:
    out = {"status": "UNAVAILABLE", "message": "Pacote sem Tabela 4 verificada.",
           "measures": [], "notes": [], "source": None}
    if not table or not table.get("verified"):
        return out
    out.update(source=table["source"], notes=table["notes"],
               source_sha256=table["source_sha256"])
    count = context.get("grouped_houses_or_lots")
    if context["occupancy"] == "A-4" and count is None:
        return {**out, "status": "MISSING_DATA",
                "message": "Informe a quantidade de casas ou lotes do agrupamento A-4."}
    column = 2 if context["occupancy"] == "A-5" else (0 if count <= 6 else 1)
    result = _column_result(table, column, out, context)
    result["message"] = ("Consulta parcial do agrupamento, em rascunho. Conferir separadamente "
                         "cada edificação conforme as notas da Tabela 4; não é dispensa global.")
    return result
