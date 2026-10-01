"""Limites, notas e integridade posicional do Anexo III."""
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from coscip_api.plant_service import PlantContext
from coscip_normative import parse_markdown
from coscip_normative.requirements import consult_requirements, verify_requirements

BASE = Path(__file__).resolve().parents[2] / "normative" / "base"


@pytest.fixture
def table():
    return yaml.safe_load((BASE / "sistemas-exigidos.yaml").read_text(encoding="utf-8"))


def requirement_sources(table):
    lines = [table["source"]["title"]]
    lines += ["| " + " | ".join(row) + " |" for row in table["header_rows"]]
    lines += ["| " + " | ".join(m["source_row"]) + " |" for m in table["measures"]]
    lines += ["Controle de Materiais de", "Acabamento"]
    lines += ["| " + note + " |" for note in table["notes"]]
    text = ('---\ndocumento: DECRETO-42-2018\nsha256_pdf: '
            + table["source"]["pdf_sha256"] + '\n---\n## Página 26\nANEXO III\n'
            + "\n".join(lines) + "\n## Página 27\nTabela 3 - outra tabela")
    residential = table.get("residential_table")
    if residential:
        text += "\n" + residential["source"]["title"] + "\nou superior a 02 pavimentos\n"
        text += "\n".join("| " + " | ".join(row) + " |" for row in residential["header_rows"])
        text += "\n" + "\n".join("| " + " | ".join(m["source_row"]) + " |"
                                 for m in residential["measures"])
        text += "\nAcesso de viatura em\nedificações\nSegurança Estrutural contra\nIncêndio\n"
        text += "\n".join("| " + note + " |" for note in residential["notes"])
    grouping = table.get("grouping_table")
    if grouping:
        text += "\n## Página 28\n" + grouping["source"]["title"] + "\n"
        text += "\n".join("| " + " | ".join(row) + " |" for row in grouping["header_rows"])
        text += "\n" + "\n".join("| " + " | ".join(m["source_row"]) + " |"
                                 for m in grouping["measures"])
        text += "\nAcesso de viatura em\nedificações\n"
        text += "\n".join("| " + note + " |" for note in grouping["notes"])
    src = parse_markdown(text.encode(), "decreto.md")
    return {src.document: src}


@pytest.fixture
def sources(table):
    return requirement_sources(table)


def verified(table, sources):
    errors = []
    result = verify_requirements(table, sources, errors)
    assert not errors
    return result


def context(**changes):
    return {"occupancy": "D-2", "building_area_m2": 396, "building_floors": 1,
            "single_occupancy": True, **changes}


def test_bank_and_inclusive_limits(table, sources):
    t = verified(table, sources)
    for area, floors in [(396, 1), (900, 2)]:
        result = consult_requirements(t, context(building_area_m2=area, building_floors=floors))
        assert result["status"] == "INDICATIVE"
        assert result["column"] == "A/D/E/G"
        cells = {m["id"]: m["status"] for m in result["measures"]}
        assert {k for k, v in cells.items() if v == "REQUIRED"} == {
            "extinguishers", "signage", "lighting", "exits"}
        assert "hydrants" not in cells and "alarm" not in cells
        assert result["source_sha256"] == sources["Decreto 42/2018"].text_sha256


@pytest.mark.parametrize("changes,status", [
    ({"building_area_m2": 900.01}, "OUT_OF_SCOPE"),
    ({"building_floors": 3}, "OUT_OF_SCOPE"),
    ({"occupancy": "M-2"}, "OUT_OF_SCOPE"),
    ({"occupancy": "L-2"}, "OUT_OF_SCOPE"),
    ({"occupancy": "D-99"}, "OUT_OF_SCOPE"),
    ({"occupancy": "A-1"}, "REVIEW_REQUIRED"),
    ({"occupancy": "A-6"}, "REVIEW_REQUIRED"),
    ({"single_occupancy": False}, "REVIEW_REQUIRED"),
    ({"single_occupancy": None}, "REVIEW_REQUIRED"),
    ({"building_area_m2": None}, "MISSING_DATA"),
    ({"building_floors": None}, "MISSING_DATA"),
])
def test_no_inference_outside_scope(table, sources, changes, status):
    result = consult_requirements(verified(table, sources), context(**changes))
    assert result["status"] == status and not result["measures"]


def test_notes_and_unlisted_are_not_unconditional(table, sources):
    t = verified(table, sources)
    f6 = consult_requirements(t, context(occupancy="F-6"))
    assert {m["id"] for m in f6["measures"] if m["status"] == "CONDITIONAL"} == {
        "emergency_plan", "smoke_control"}
    assert "200 pessoas" in f6["notes"][0] and "sem janelas" in f6["notes"][0]
    m3 = consult_requirements(t, context(occupancy="M-3"))
    assert all(m["status"] == "CONDITIONAL" for m in m3["measures"][:4])
    l1 = consult_requirements(t, context(occupancy="L-1"))
    assert next(m for m in l1["measures"] if m["id"] == "lighting")["status"] == "NOT_MARKED"


@pytest.mark.parametrize("kind", ["cell", "columns", "label", "page", "hash", "note", "shape"])
def test_import_rejects_corrupted_table(table, sources, kind):
    bad = deepcopy(table)
    if kind == "cell":
        bad["measures"][2]["source_row"][1] = "-"
        bad["measures"][2]["cells"][0] = "-"
    elif kind == "columns":
        bad["columns"][5], bad["columns"][6] = bad["columns"][6], bad["columns"][5]
    elif kind == "label":
        bad["measures"][2]["source_row"] = bad["measures"][4]["source_row"]
        bad["measures"][2]["cells"] = bad["measures"][4]["cells"]
    elif kind == "page":
        bad["source"]["page"] = 27
    elif kind == "hash":
        bad["source"]["pdf_sha256"] = "different"
    elif kind == "note":
        bad["notes"] = ["Obrigatório para 100 pessoas."]
    else:
        bad["measures"].pop()
    errors = []
    assert not verify_requirements(bad, sources, errors)["verified"]
    assert errors


@pytest.mark.parametrize("values", [
    {"building_area_m2": -1}, {"building_area_m2": float("nan")},
    {"building_area_m2": float("inf")}, {"building_floors": 1.5},
    {"building_floors": True}, {"building_floors": 0},
])
def test_context_rejects_invalid_building_dimensions(values):
    with pytest.raises(ValidationError):
        PlantContext(**values)


def test_old_package_remains_usable_without_reference():
    assert consult_requirements(None, context())["status"] == "UNAVAILABLE"


@pytest.mark.parametrize("division,floors,height,band", [
    ("A-2", 1, 3, 0), ("A-2", 2, 6, 1), ("A-2", 3, 9, 2),
    ("A-2", 4, 12, 3), ("A-2", 5, 15, 3), ("A-2", 6, 18, 4),
    ("A-2", 10, 30, 4), ("A-2", 10, 30.01, 5),
    ("A-3", 1, 3, 6), ("A-3", 2, 6, 7), ("A-3", 3, 9, 8),
    ("A-3", 4, 12, 9), ("A-3", 6, 18, 9), ("A-3", 7, 21, 10),
    ("A-3", 10, 30, 10), ("A-3", 10, 31, 11),
])
def test_residential_bands(table, sources, division, floors, height, band):
    t = verified(table, sources)
    result = consult_requirements(t, context(occupancy=division, building_area_m2=1000,
                                            building_floors=floors, building_height_m=height))
    assert result["status"] == "INDICATIVE"
    assert result["source"]["page"] == 27
    assert result["column"] == table["residential_table"]["columns"][band]["id"]
    assert len(result["measures"]) == 13
    cells = {m["id"]: m["cell"] for m in result["measures"]}
    assert cells["sprinklers"] == ("X" if height > 30 else "-")
    if floors == 3:
        assert cells["hydrants"] == ("X2" if division == "A-2" else "X1")
    if division == "A-3" and 4 <= floors <= 6:
        assert cells["detection"] == "X"


def test_residential_requires_height_and_keeps_low_building_in_table2(table, sources):
    t = verified(table, sources)
    assert consult_requirements(t, context(occupancy="A-2", building_floors=4))[
        "status"] == "MISSING_DATA"
    result = consult_requirements(t, context(occupancy="A-2", building_area_m2=900,
                                            building_floors=2))
    assert result["source"]["page"] == 26
    result = consult_requirements(t, context(occupancy="A-2", building_area_m2=900,
                                            building_floors=3, building_height_m=9))
    assert result["source"]["page"] == 27
    assert next(m for m in result["measures"] if m["id"] == "hydrants")[
        "status"] == "CONDITIONAL"


def test_residential_changed_cell_rejects_whole_package(table, sources):
    table["residential_table"]["measures"][1]["cells"][0] = "-"
    errors = []
    assert not verify_requirements(table, sources, errors)["verified"]
    assert any("Tabela 3" in error for error in errors)


@pytest.mark.parametrize("division,count,cell", [
    ("A-4", 1, "-"), ("A-4", 6, "-"), ("A-4", 7, "X"), ("A-5", None, "X"),
])
def test_grouping_table_is_partial_and_independent_of_area(table, sources, division, count, cell):
    result = consult_requirements(verified(table, sources), context(
        occupancy=division, building_area_m2=None, building_floors=None,
        grouped_houses_or_lots=count))
    assert result["status"] == "INDICATIVE" and result["source"]["page"] == 28
    assert len(result["measures"]) == 2 and result["measures"][0]["cell"] == cell
    assert "parcial" in result["message"] and "cada edificação" in result["message"]
    assert "Tabela 3" in result["notes"][0]


def test_grouping_missing_count_is_not_a_small_group(table, sources):
    result = consult_requirements(verified(table, sources), context(occupancy="A-4"))
    assert result["status"] == "MISSING_DATA" and result["measures"] == []


def test_real_but_truncated_note_is_rejected(table, sources):
    table["notes"] = ["Exigido somente para lotação superior a 200 pessoas."]
    errors = []
    assert not verify_requirements(table, sources, errors)["verified"]
    assert errors


@pytest.mark.parametrize("field", ["requirements", "classification", "symbols"])
def test_package_rejects_references_outside_its_directory(tmp_path, field):
    from coscip_normative.package import PackageError, load_package

    package = tmp_path / "base"
    shutil.copytree(BASE, package)
    manifest_path = package / "pacote.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest[field] = "../external.yaml"
    (tmp_path / "external.yaml").write_text("schema_version: pretend", encoding="utf-8")
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    with pytest.raises(PackageError, match="fora do pacote"):
        load_package(package)


def test_malformed_requirements_reports_failure_without_crashing():
    from coscip_normative.package import load_package, verify_package

    package = load_package(BASE)
    package.requirements = {"wrong": "shape"}
    result = verify_package(package, {})
    assert not result["verified"]
    assert any("estrutura inválida" in failure for failure in result["failures"])



def test_conflict_is_reported_without_overwriting_analyst_choice(table, sources):
    t = verified(table, sources)
    ctx = context(requires_lighting=False, requires_hydrants=False)
    result = consult_requirements(t, ctx)
    assert len(result["conflicts"]) == 1 and "Iluminação" in result["conflicts"][0]
    assert ctx["requires_lighting"] is False
    result = consult_requirements(t, context(occupancy="A-2", building_floors=4,
                                            building_height_m=12, requires_hydrants=False))
    assert len(result["conflicts"]) == 1 and "Hidrantes" in result["conflicts"][0]
    result = consult_requirements(t, context(occupancy="A-2", building_floors=3,
                                            building_height_m=9, requires_hydrants=False))
    assert result["conflicts"] == []  # X2 depende da condição de área da nota.


def test_conferred_table_heading_does_not_cut_the_annex():
    # o bloco conferido publicado ("### Anexo A — ... (conferida)") repete o nome do anexo;
    # o anexo verdadeiro continua até o próximo anexo, com as páginas seguintes
    from coscip_normative import verify_citation

    md = ("---\ndocumento: NT 1-03\n---\n## Página 4\n\n### ANEXO A - SIMBOLOGIA\n\n"
          "| EXTINTOR |\n\n"
          "<!-- tabela-conferida: Anexo A p4 -->\n### Anexo A — Simbologia (conferida)\n\n"
          "| EXTINTOR |\n<!-- /tabela-conferida: Anexo A p4 -->\n\n---\n\n## Página 5\n\n"
          "| HIDRANTE SIMPLES |\n\n1.1 Item numerado\n")
    src = parse_markdown(md.encode("utf-8"), "nt-1-03.md")
    assert len(src.items["Anexo A"]) == 1
    check = verify_citation({src.document: src}, "NT 1-03", "Anexo A",
                            ("EXTINTOR", "HIDRANTE SIMPLES"))
    assert check.verified, check.problem
