"""Tabelas em dois caminhos independentes (plano de correção, F2.2/F2.3)."""

from __future__ import annotations

import hashlib

import pytest

from tools.normas import render_paginas, tabelas


def make_pdf(cells: list[list[str]], x0=72, y0=700, w=120, h=24) -> bytes:
    """PDF mínimo de uma página com uma tabela desenhada por linhas (Helvetica)."""
    ops = ["0.8 w"]
    rows, cols = len(cells), len(cells[0])
    for i in range(rows + 1):
        y = y0 - i * h
        ops.append(f"{x0} {y} m {x0 + cols * w} {y} l S")
    for j in range(cols + 1):
        x = x0 + j * w
        ops.append(f"{x} {y0} m {x} {y0 - rows * h} l S")
    for i, row in enumerate(cells):
        for j, text in enumerate(row):
            ops.append(f"BT /F1 10 Tf {x0 + j * w + 6} {y0 - (i + 1) * h + 8} Td ({text}) Tj ET")
    stream = "\n".join(ops).encode("latin-1")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
            b"/Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % n + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1,
                                                                             xref)
    return bytes(out)


CELLS = [["Risco", "Area (m2)", "Distancia (m)"],
         ["Pequeno", "250", "20"], ["Medio", "150", "15"], ["Grande", "100", "10"]]


def test_compare_cell_rules():
    ok = tabelas.compare_cell("Edificaçoẽ s", "Edificações")
    assert ok["estado"] == "verificada"
    assert tabelas.compare_cell("35,00m", "35,00 m")["estado"] == "verificada"
    assert tabelas.compare_cell("20 m", "25 m") == {"estado": "divergente",
                                                     "motivo": "números diferentes"}
    assert tabelas.compare_cell(None, "x")["estado"] == "pendente_humano"
    assert tabelas.compare_cell("Grupo A", "Grupo B")["estado"] == "divergente"


def test_evaluate_needs_two_paths_and_says_which():
    one = {"caminhos": {"visual": {"linhas": [["a"]]}}}
    assert tabelas.evaluate(one)["estado"] == "pendente_humano"
    two = {"caminhos": {"visual": {"linhas": [["a", "1"]]}, "texto": {"linhas": [["a", "1"]]}}}
    res = tabelas.evaluate(two)
    assert res["estado"] == "verificada" and res["caminhos_comparados"] == ["visual", "texto"]
    assert "falta a extração geométrica" in res["observacao"]
    bad = {"caminhos": {"visual": {"linhas": [["a", "1"]]},
                        "geometrica": {"candidatos": [{"linhas": [["a"]]}]}}}
    assert tabelas.evaluate(bad)["estado"] == "divergente"
    # entre as candidatas da página vale a que concorda; a escolha fica registrada
    two_tables = {"caminhos": {"visual": {"linhas": [["a", "1"]]},
                               "geometrica": {"candidatos": [{"linhas": [["x"]]},
                                                             {"linhas": [["a", None, "1"]]}]}}}
    res = tabelas.evaluate(two_tables)
    assert res["estado"] == "verificada" and res["candidato_geometrico"] == 1
    assert res["caminhos_comparados"] == ["visual", "geometrica"]


def test_synthetic_pdf_render_and_geometric_extraction(tmp_path):
    pdf = make_pdf(CELLS)
    [img] = tabelas.render_pages(pdf, {1: tmp_path / "media" / "pagina-01.jpg"})
    assert img.read_bytes()[:3] == b"\xff\xd8\xff"  # JPEG
    [png] = tabelas.render_pages(pdf, {1: tmp_path / "pagina-01.png"})
    assert png.read_bytes()[:4] == b"\x89PNG"
    [found] = tabelas.extract_geometric(pdf, 1)
    assert found["linhas"] == CELLS
    res = tabelas.compare(CELLS, found["linhas"])
    assert res["estado"] == "verificada" and res["celulas"] == []


def test_pdf_with_other_hash_is_refused():
    fonte = {"documento": "NT 9-99", "url": "https://x/a.pdf", "sha256_pdf": "0" * 64}
    with pytest.raises(render_paginas.HashMismatch):
        render_paginas.get_pdf(fonte, None, fetcher=lambda url: make_pdf(CELLS))
    good = {**fonte, "sha256_pdf": hashlib.sha256(make_pdf(CELLS)).hexdigest()}
    assert render_paginas.get_pdf(good, None, fetcher=lambda url: make_pdf(CELLS))


def test_publish_is_idempotent_and_only_verified():
    md = "## Página 5\n\ntexto\n\n### Tabelas extraídas\n\n| a |\n\n---\n\n## Página 6\n"
    t = {"documento": "NT 9-99", "tabela": "Tabela 3", "titulo": "Teste", "pagina": 5,
         "conferida_em": "2026-09-29", "estado": "verificada",
         "resultado": {"caminhos_comparados": ["visual", "texto"]},
         "caminhos": {"visual": {"linhas": CELLS}}}
    once = tabelas.publish(t, md)
    assert "### Tabela 3 — Teste (conferida)" in once
    assert once.index("(conferida)") < once.index("## Página 6")
    assert tabelas.publish(t, once) == once
    assert tabelas.publish({**t, "estado": "divergente"}, once) == md
    assert tabelas.RAW_MARKED in tabelas.mark_raw(md)


def test_committed_tables_state_is_computed_not_hand_written():
    files = tabelas.table_files()
    for f in files:
        data = tabelas.load(f)
        assert data["schema_version"] == tabelas.SCHEMA, f.name
        res = tabelas.evaluate(data)
        assert data["resultado"] == res and data["estado"] == res["estado"], (
            f"{f.name}: rode python -m tools.normas.tabelas comparar")
        md = (tabelas.FONTES / data["arquivo"]).read_text(encoding="utf-8")
        block = f"### {data['tabela']} — {data['titulo']} (conferida)"
        assert (block in md) == (data["estado"] == "verificada"), (
            f"{f.name}: rode python -m tools.normas.tabelas publicar")


def test_merged_up_marker_is_compared_compact_and_published_full():
    table = {"documento": "NT X", "tabela": "Tabela 9", "titulo": "t", "pagina": 1,
             "conferida_em": "2026-09-29", "resultado": {"caminhos_comparados": ["visual"]},
             "caminhos": {"visual": {"linhas_cabecalho": 1, "linhas": [
                 ["Grupo", "Divisão", "Risco"], ["A", "A-1", "PEQUENO"], ["^", "A-2", "^"]]}}}
    assert tabelas.compact(table["caminhos"]["visual"]["linhas"])[2] == ["A-2"]
    md = tabelas.to_markdown(table)
    assert "| A | A-2 | PEQUENO |" in md


def test_superscript_spacing_and_m2_are_not_content():
    assert tabelas.compare_cell("NE 1", "NE1")["estado"] == "verificada"
    assert tabelas.compare_cell("1.200 MJ/m2", "1.200 MJ/m²")["estado"] == "verificada"
    assert tabelas.compare_cell("PF 4", "PF 5")["estado"] == "divergente"


def test_engine_risk_classification_matches_verified_anexo_b():
    """O enquadramento que o motor usa (NT 1-04, Anexo B) é o da tabela conferida (F2)."""
    import yaml

    base = yaml.safe_load((tabelas.ROOT / "normative" / "base" / "enquadramento.yaml")
                          .read_text("utf-8"))
    verified: dict[str, str] = {}
    for f in sorted((tabelas.TABELAS / "nt-1-04").glob("anexo-b-p*.yaml")):
        data = tabelas.load(f)
        assert data["estado"] == "verificada", f.name
        prev = None
        for row in data["caminhos"]["visual"]["linhas"][1:]:
            prev = prev if row[4] == tabelas.MERGED_UP else row[4]
            verified.setdefault(row[2], prev)
    engine = {d["id"]: d["risk"] for d in base["divisions"]}
    assert engine == verified


def test_forma_geometrica_so_vale_para_a_grade_desenhada():
    table = {"forma": {"faixa": [2, 4], "linhas_cabecalho": 0},
             "forma_geometrica": {"faixa": None},
             "caminhos": {"geometrica": {"candidatos": []}}}
    assert tabelas.forma_of(table)["faixa"] == [2, 4]  # camada de texto
    assert not tabelas.geo_forma(table)["faixa"]  # grade: sem o recorte da camada de texto
    grade = [["Extintores", "X"], ["Hidrantes", "X"], ["Chuveiros", None, "X"]]
    assert tabelas.shape(grade, tabelas.geo_forma(table)) == [
        ["Extintores", "X"], ["Hidrantes", "X"], ["Chuveiros", "X"]]
