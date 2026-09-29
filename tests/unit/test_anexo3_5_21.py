"""Anexo III do Decreto 42/2018, Tabelas 5 a 21 (plano de correção, F4.3)."""

from __future__ import annotations

import copy

import pytest

from coscip_mcp import norms
from coscip_normative.requirements import consult_requirements, verify_height_tables
from tools.normas import anexo3


@pytest.fixture(scope="module")
def base():
    return norms.load_base()


def ctx(occ, floors, height=None, area=2000):
    out = {"occupancy": occ, "building_area_m2": area, "building_floors": floors,
           "single_occupancy": True}
    if height is not None:
        out["building_height_m"] = height
    return out


def cells(res):
    return {m["id"]: (m["cell"], m["status"]) for m in res["measures"]}


def test_generated_file_is_up_to_date_and_all_17_tables_verified(base):
    assert anexo3.OUT.read_text(encoding="utf-8") == anexo3.dump(anexo3.build())
    height = base.package_report["requirements"]["height_tables"]
    assert height["verified"] and [t["table"] for t in height["tables"]] == list(range(5, 22))
    divisions = {d for t in height["tables"] for b in t["blocks"] for d in b["divisoes"]}
    expected = {"A-6", "B-1", "B-2", *(f"C-{i}" for i in range(1, 5)),
                *(f"D-{i}" for i in range(1, 6)), "E-1", "E-2", "E-3",
                *(f"F-{i}" for i in range(1, 12)), *(f"G-{i}" for i in range(1, 7)),
                *(f"H-{i}" for i in range(1, 5)), "I-1", "I-2", "I-3"}
    assert divisions == expected


@pytest.mark.parametrize(("occ", "floors", "height", "column", "expect"), [
    ("D-2", 5, 14, "4, 5 e 6pav", {"sprinklers": ("-", "NOT_MARKED"),
                                   "exits": ("X3", "CONDITIONAL")}),
    ("D-2", 12, 40, "H > 30m", {"sprinklers": ("X", "REQUIRED"),
                                "emergency_plan": ("X6", "CONDITIONAL")}),
    ("F-4", 8, 25, "Acima de 6pav com H ≤ 30m", {"sprinklers": ("X13", "CONDITIONAL"),
                                                "spda": ("-", "NOT_MARKED")}),
    ("F-9", 1, 6, "Térrea", {"spda": ("X9", "CONDITIONAL")}),  # bloco F-3/F-9
    ("G-1", 2, 7, "2pav", {"extinguishers": ("X", "CONDITIONAL")}),  # rótulo com nota 11
    ("H-3", 3, 10, "3pav", {"stair_pressurization": ("X", "REQUIRED")}),
    ("G-5", 1, 12, "Térrea", {"foam": ("X8", "CONDITIONAL")}),
])
def test_consult_picks_table_block_and_band(base, occ, floors, height, column, expect):
    res = consult_requirements(base.table("requirements"), ctx(occ, floors, height))
    assert res["status"] == "INDICATIVE" and res["column"].endswith(column), res
    got = cells(res)
    for mid, value in expect.items():
        assert got[mid] == value, (mid, got[mid])


def test_consult_needs_height_and_never_turns_absence_into_waiver(base):
    res = consult_requirements(base.table("requirements"), ctx("H-3", 3))
    assert res["status"] == "MISSING_DATA" and "Tabela 19" in res["message"]
    res = consult_requirements(base.table("requirements"), ctx("J-2", 1, 5))
    assert res["status"] == "OUT_OF_SCOPE" and res["measures"] == []
    # até 900 m² e 2 pavimentos continua a Tabela 2
    small = consult_requirements(base.table("requirements"), ctx("D-2", 2, 7, area=500))
    assert small["source"]["item"] == "Anexo III, Tabela 2"


def test_tampered_cell_is_refused(base):
    data = copy.deepcopy(base.package.requirements_height)
    data["tables"][3]["measures"][2]["cells"][0] = "X"  # Tabela 8, chuveiros, térrea: "-"
    failures: list[str] = []
    out = verify_height_tables(data, base.sources, failures)
    assert not out["verified"]
    assert any("Tabela 8" in f and "Chuveiros" in f for f in failures)
