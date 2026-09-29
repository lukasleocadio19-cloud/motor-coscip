"""Integração skills ↔ motor (plano de correção, F8).

Aceite: processo sintético completo (DXF + memorial fictício) analisado pelo MCP, com os
achados do motor e os da skill numa **matriz única** (contrato comum, sem tradução) e um
bilhete cujas citações estão **todas** localizadas no índice de itens.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import jsonschema
import pytest
from coscip_findings import Finding, MeasuredResult
from coscip_findings.achado import to_achado

from coscip_cad.synthetic import make_fire_plan
from coscip_cbm import (
    ComplianceStatus,
    EvidenceStatus,
    FindingKind,
    ReviewStatus,
    Severity,
)
from coscip_mcp.server import Server

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "processo-sintetico"
SCHEMA = json.loads((ROOT / "skills" / "_comum" / "achado.schema.json").read_text("utf-8"))


def _script(rel: str):
    path = ROOT / "skills" / rel
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = mod
    spec.loader.exec_module(mod)
    return mod


matriz_mod = _script("orquestrar-analise-cbmerj/scripts/consolidar_matriz.py")
rascunho_mod = _script("emitir-bilhete-cbmerj/scripts/rascunho_bilhete.py")
citacoes_mod = _script("emitir-bilhete-cbmerj/scripts/conferir_citacoes.py")
contar_mod = _script("emitir-bilhete-cbmerj/scripts/contar_bilhete.py")


def call(srv: Server, name: str, **args):
    reply = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": name, "arguments": args}})
    result = reply["result"]
    text = result["content"][0]["text"]
    return result.get("isError", False), (json.loads(text) if not result.get("isError")
                                          else text)


@pytest.fixture(scope="module")
def processo(tmp_path_factory):
    """O fluxo que a skill segue com o MCP (uso-do-mcp-coscip-plantas.md), na base real."""
    mp = pytest.MonkeyPatch()
    mp.setenv("COSCIP_NORMAS_DIR", str(ROOT / "normative" / "fontes"))
    tmp = tmp_path_factory.mktemp("processo")
    dxf = make_fire_plan(tmp / "proc.dxf", scale=1000)
    srv = Server()
    erro, geral = call(srv, "abrir_planta", caminho=str(dxf))
    assert not erro, geral
    pid = geral["planta_id"]

    def ref(a, b, m):
        return {"ponto_a": a, "ponto_b": b, "medida_real_m": m}

    erro, conf = call(srv, "confirmar_unidade", planta_id=pid,
                      referencias=[ref([0, 0], [14000, 0], 14.0),
                                   ref([0, 0], [0, 12000], 12.0)],
                      justificativa="cotas das paredes do processo fictício")
    assert not erro, conf
    erro, _ = call(srv, "definir_pavimentos", planta_id=pid,
                   pavimentos=[{"nome": "Térreo", "janela": [-1, -1, 31, 13]}])
    assert not erro
    erro, rel = call(srv, "analisar_planta", planta_id=pid, contexto={
        "occupancy": "D-2", "risk_class": "GRANDE", "building_area_m2": 360,
        "building_floors": 1, "exits_confirmed": True, "layout_defined": True,
        "requires_alarm": True})
    assert not erro, rel
    skill = json.loads((FIXTURE / "achados-skill.json").read_text("utf-8"))
    (tmp / "motor.json").write_text(json.dumps({"achados": rel["achados"]}), "utf-8")
    (tmp / "le.json").write_text(json.dumps(skill), "utf-8")
    yield {"tmp": tmp, "rel": rel, "skill": skill["achados"]}
    mp.undo()


def test_gate_0_aberto_e_achados_do_motor_no_contrato(processo):
    rel = processo["rel"]
    assert rel["gate_0"] == {"unidade_confirmada": True, "balanco_completo": True,
                             "aberto": True}
    assert rel["achados"]
    for a in rel["achados"]:
        jsonschema.validate(a, SCHEMA)
        assert a["origem"] == "motor"
    dist = next(a for a in rel["achados"] if a["check_id"] == "EXT-CAD-003-GRANDE")
    assert dist["compliance_status"] == "NON_COMPLIANT"
    assert dist["medida"]["limite"] == 10 and dist["medida"]["valor"] > 10
    assert dist["medida"]["algoritmo"] == "visibility_graph_bnb"
    assert dist["evidencias"][0]["fonte_tipo"] == "CAD"
    minimo = next(a for a in rel["achados"] if a["check_id"] == "EXT-CAD-002")
    assert minimo["criterio_adotado"]["decidido_por"] == "analista"


def test_citacoes_da_skill_conferem_no_texto(processo):
    """Citação que não confere impede o achado: o trecho está literalmente na fonte."""
    fonte = (ROOT / "normative" / "fontes" / "nt-1-01-parte-1-regularizacao.md").read_text(
        "utf-8")
    for a in processo["skill"]:
        jsonschema.validate(a, SCHEMA)
        assert a["regra"]["citacao"] in fonte, a["id"]


@pytest.fixture(scope="module")
def matriz(processo):
    tmp = processo["tmp"]
    assert matriz_mod.main([str(tmp / "motor.json"), str(tmp / "le.json"),
                            "--out", str(tmp / "matriz.json"),
                            "--md", str(tmp / "matriz.md")]) == 0
    return json.loads((tmp / "matriz.json").read_text("utf-8"))


def test_matriz_unica_sem_traducao(processo, matriz):
    tmp = processo["tmp"]
    origem = {a["origem"] for a in matriz["achados"]}
    assert origem == {"motor", "skill"}
    entrada = {a["id"]: a for a in [*processo["rel"]["achados"], *processo["skill"]]}
    assert len(matriz["achados"]) == len(entrada)
    for a in matriz["achados"]:
        assert a == entrada[a["id"]]  # entra como veio: nenhum status recalculado
    assert "LE-DOC-ART" in matriz["bloqueios"]
    md = (tmp / "matriz.md").read_text("utf-8")
    assert "| EXT-CAD-003-GRANDE@" in md and "RASCUNHO" in md


def test_bilhete_com_citacoes_todas_no_indice(processo, matriz):
    tmp = processo["tmp"]
    assert rascunho_mod.main([str(tmp / "matriz.json"), "--out", str(tmp / "bilhete.txt"),
                              "--nota", str(tmp / "nota.md"),
                              "--processo", "SINT-0001/2026 (fictício)"]) == 0
    bilhete = (tmp / "bilhete.txt").read_text("utf-8")
    assert "NT 2-01:2020, Tabela 3" in bilhete  # distância acima do limite, pelo motor
    assert "NT 1-01 P1:2019, item 5.3.7" in bilhete  # ART ausente, pela skill
    # inconclusivo e divergência não viram exigência; vão para a nota interna
    assert "HID-" not in bilhete and "3 extintores" not in bilhete
    nota = (tmp / "nota.md").read_text("utf-8")
    assert "LE-MEM-EXT" in nota and "fora do bilhete" in nota
    rows = citacoes_mod.check(bilhete)
    assert rows and all(r["ok"] for r in rows), [r for r in rows if not r["ok"]]
    assert citacoes_mod.main([str(tmp / "bilhete.txt")]) == 0
    assert contar_mod.medir(bilhete)["bytes_utf8"] < 8000


# ------------------------------------------------------------------ peças isoladas

def _finding(**kw) -> Finding:
    base = dict(check_id="X-1", check_version=1, system="EXTINTORES", scope_id="f1",
                scope_label="Térreo", compliance_status=ComplianceStatus.COMPLIANT,
                evidence_status=EvidenceStatus.SUFFICIENT,
                review_status=ReviewStatus.NOT_REQUIRED, severity=Severity.MAJOR,
                kind=FindingKind.NO_PENDING_ISSUE, reason_code="SATISFIED", title="Título",
                normative_citations=({"document": "NT 2-01", "edition": "2ª edição - 2020",
                                      "item": "5.2.5", "page": None,
                                      "quote": ["duas unidades"]},))
    return Finding(**{**base, **kw})


def test_to_achado_copia_os_tres_status_e_a_medida():
    f = _finding(compliance_status=ComplianceStatus.NON_COMPLIANT,
                 kind=FindingKind.NON_COMPLIANT, reason_code="ABOVE_MAXIMUM",
                 required_action="Reposicionar.",
                 measured=MeasuredResult(value=12.3, unit="m", required=10.0,
                                         uncertainty_abs=0.2, algorithm="v"))
    a = to_achado(f)
    jsonschema.validate(a, SCHEMA)
    assert (a["compliance_status"], a["evidence_status"], a["review_status"]) == (
        "NON_COMPLIANT", "SUFFICIENT", "NOT_REQUIRED")
    assert a["medida"] == {"valor": 12.3, "unidade": "m", "limite": 10.0, "incerteza": 0.2,
                           "algoritmo": "v"}
    assert a["regra"]["citacao"] == "duas unidades" and a["saneamento"] == "Reposicionar."
    assert "Pavimento Térreo: medido 12,3 m (± 0,2 m); limite 10 m" in a["fato"]
    assert "v" not in a["fato"].split(":")[-1]  # algoritmo fica em medida, não no texto


def test_conforme_sem_citacao_localizada_e_recusado():
    with pytest.raises(ValueError, match="conforme sem citação"):
        to_achado(_finding(normative_citations=()))
    bad = {**to_achado(_finding()), "regra": {"documento": "NT 2-01", "item": "[A CONFERIR]"}}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)
    assert matriz_mod._minimal_errors(bad, SCHEMA)


def test_matriz_marca_divergencia_e_recusa_id_repetido(tmp_path):
    a = to_achado(_finding())
    b = {**a, "id": "LE-1", "origem": "skill", "check_id": "X-1",
         "compliance_status": "UNDETERMINED", "evidence_status": "PARTIAL",
         "tipo": "DATA_MISSING"}
    m = matriz_mod.consolidate([("motor", [a]), ("skill", [b])])
    (g,) = m["grupos"]
    assert g["divergente"] and set(g["ids"]) == {a["id"], "LE-1"}
    with pytest.raises(matriz_mod.MatrizError, match="repetido"):
        matriz_mod.consolidate([("x", [a]), ("y", [{**a, "fato": "outro."}])])


def test_conferir_citacoes_recusa_a_conferir_edicao_e_item_inexistente():
    rows = citacoes_mod.check("1. X — NT 2-07:2019, item [A CONFERIR]: fato.\n"
                              "2. Y — NT 2-01:2019, item 5.2.5: edição errada.\n"
                              "3. Z — NT 2-01:2020, item 99.9: item inexistente.\n"
                              "4. W — Decreto 42/2018, Art. 1: ok.")
    assert [r["ok"] for r in rows] == [False, False, False, True]
    assert "não localizado" in rows[0]["problema"] and "edição" in rows[1]["problema"]
