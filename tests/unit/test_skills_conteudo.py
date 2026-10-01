"""Conteúdo das skills (plano de correção, F3): links, scripts e contrato de achado."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from coscip_cbm import enums
from tools.skills import pack, verificar_links

SK = pack.SKILLS


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_cited_path_skill_and_nt_exists():
    report = verificar_links.run()
    assert {k: v for k, v in report.items() if v} == {}


def test_bilhete_skill_has_all_cited_files():
    files = pack.files_for("emitir-bilhete-cbmerj", [], ["achado.schema.json"])
    for rel in ("references/anatomia-do-bilhete.md", "references/edicoes-vigentes.md",
                "references/banco-de-citacoes.md", "references/protocolo-de-reducao.md",
                "scripts/localizar_item.py", "scripts/contar_bilhete.py"):
        assert rel in files, rel


def test_achado_schema_uses_engine_enums():
    schema = json.loads((SK / "_comum" / "achado.schema.json").read_text(encoding="utf-8"))
    props = schema["properties"]
    pairs = {"compliance_status": enums.ComplianceStatus, "evidence_status": enums.EvidenceStatus,
             "review_status": enums.ReviewStatus, "severidade": enums.Severity,
             "tipo": enums.FindingKind}
    for field, enum in pairs.items():
        assert props[field]["enum"] == [m.value for m in enum], field
    fonte = props["evidencias"]["items"]["properties"]["fonte_tipo"]["enum"]
    assert fonte == [m.value for m in enums.EvidenceSourceType]
    # conforme exige evidência suficiente e item localizado
    rule = schema["allOf"][0]
    assert rule["then"]["properties"]["evidence_status"] == {"const": "SUFFICIENT"}


def test_contar_bilhete_counts_chars_bytes_and_items(tmp_path):
    mod = _load(SK / "emitir-bilhete-cbmerj" / "scripts" / "contar_bilhete.py")
    txt = "Processo X\n1. Extintores — NT 2-01:2020, item 5.2.5: falta.\n2. Saídas: ok.\n"
    r = mod.medir(txt)
    assert r["caracteres"] == len(txt) and r["bytes_utf8"] == len(txt.encode())
    assert r["bytes_utf8"] > r["caracteres"]  # "—" ocupa 3 bytes
    assert [i["parte"] for i in r["itens"]] == ["cabeçalho", "item 1", "item 2"]
    f = tmp_path / "b.txt"
    f.write_text("1. " + "á" * 10, encoding="utf-8")
    assert mod.main([str(f), "--limite", "15"]) == 1  # 13 caracteres, mas 23 bytes


def test_localizar_item_finds_item_and_page():
    mod = _load(SK / "emitir-bilhete-cbmerj" / "scripts" / "localizar_item.py")
    hits = mod.search_text("unica unidade extintora", "2-01", 5)
    assert hits and hits[0]["item"] == "5.2.4" and hits[0]["pagina"] == 4


def test_inventario_percorre_subpastas_e_remete_dwg_ao_mcp(tmp_path):
    mod = _load(SK / "analisar-processo-cbmerj" / "scripts" / "inventariar_dossie.py")
    (tmp_path / "projeto" / "pranchas").mkdir(parents=True)
    (tmp_path / "projeto" / "pranchas" / "planta.dwg").write_bytes(b"AC1032" + b"\0" * 10)
    (tmp_path / "art.txt").write_text("x")
    (tmp_path / ".oculto").write_text("x")
    itens = {i["arquivo"]: i for i in mod.inventariar(tmp_path)}
    assert set(itens) == {"art.txt", "projeto/pranchas/planta.dwg"}
    dwg = itens["projeto/pranchas/planta.dwg"]
    assert dwg["versao_declarada"] == "AutoCAD 2018"
    assert "abrir_planta" in dwg["analise_geometrica"]


def test_old_skills_fixed():
    le = (SK / "transicao" / "analise-le-completa-pdf" / "SKILL.md").read_text(encoding="utf-8")
    assert "| Heliponto | NT 3-07 |" in le and "| Paiol / Explosivos | NT 4-04 |" in le
    assert "NT 4-03 | Armazenagem" not in le
    assert "15m para risco pequeno" not in le and "20 m no risco pequeno" in le
    assert "APROVADO" not in le and "8.000L" not in le and "2A:20BC para risco" not in le
    ev = (SK / "transicao" / "analise-eventos-completa-pdf" / "SKILL.md").read_text(
        encoding="utf-8")
    assert "NT 5-03" in ev and "APROVADO" not in ev and "2 a 3 pessoas" not in ev
    ca = (SK / "transicao" / "analise-ca-completa-pdf" / "SKILL.md").read_text(encoding="utf-8")
    assert "APTO PARA EMISSÃO" not in ca
