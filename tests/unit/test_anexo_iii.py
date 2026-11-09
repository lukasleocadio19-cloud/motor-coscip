"""Decreto 42/2018, Anexo III, Tabelas 5 a 32 lidas do texto ingerido, e o roteiro das medidas.

As tabelas não são transcritas: o teste confere que a leitura do texto do repositório passa na
conferência estrutural e bate com células lidas à mão no texto em 09/11/2026 (não no PDF).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from coscip_design import anexo_iii

from coscip_mcp import simbologia
from coscip_normative import parse_markdown

FONTES = Path(__file__).resolve().parents[2] / "normative" / "fontes"
DECRETO = FONTES / "decreto-42-2018-coscip-compilado.md"


@pytest.fixture(scope="module")
def sources():
    out = {}
    for f in FONTES.glob("*.md"):
        if f.name == "README.md":
            continue
        text = parse_markdown(f.read_bytes(), f.name)
        out[text.document] = text
    return out


@pytest.fixture(scope="module")
def tabelas(sources):
    return anexo_iii.load(sources)


def medida(t, rotulo):
    return next(m for m in t.medidas if m.rotulo == rotulo)


def test_as_28_tabelas_passam_na_conferencia_estrutural(tabelas):
    assert sorted(tabelas) == list(range(5, 33))
    assert {n: t.problemas for n, t in tabelas.items() if t.problemas} == {}
    todas = [d for t in tabelas.values() for d in sorted(t.divisoes)]
    assert len(todas) == len(set(todas))  # cada divisão em uma única tabela
    assert tabelas[8].divisoes == {"D-1", "D-2", "D-3", "D-4", "D-5"} and tabelas[8].pagina == 32
    assert tabelas[11].divisoes == {"F-3", "F-4", "F-9"}  # divisão quebrada em três linhas
    assert tabelas[28].divisoes == {"M-4", "M-7"}  # título sem espaço, colada à Tabela 27
    padrao = {n for n, t in tabelas.items() if t.padrao}
    assert padrao == set(range(5, 25)) | {27, 30, 32}
    assert all(len(t.colunas) in (6, 12) for n, t in tabelas.items() if n in padrao)


def test_celulas_batem_com_o_texto(tabelas):
    b = tabelas[6]
    assert medida(b, "Chuveiros automáticos").celulas == ["-", "-", "-", "X2", "X", "X"]
    assert medida(b, "Saídas de Emergência").celulas == ["X", "X3", "X3", "X4", "X4, 5",
                                                         "X4, 5, 6"]
    assert b.observacoes[2] == "Exigido apenas para as edificações com 06 pavimentos."
    f = tabelas[10]  # F-1 nas 6 primeiras colunas, F-2 nas 6 últimas
    assert medida(f, "Detecção de Incêndio").celulas == ["X"] * 6 + ["-", "-", "-", "X3", "X", "X"]
    assert [c.divisoes for c in f.colunas] == [("F-1",)] * 6 + [("F-2",)] * 6
    # rótulo quebrado em duas linhas, com as células na linha do meio
    assert medida(tabelas[13], "Segurança Estrutural contra Incêndio").celulas[:6] == ["-"] * 6
    # número de observação colado ao rótulo ("Extintores11")
    assert medida(tabelas[15], "Extintores").observacoes_da_linha == (11,)
    assert "garagens automáticas" in tabelas[15].observacoes[11]
    assert [c.rotulo for c in tabelas[25].colunas][1:] == [
        "Extensão acima de 90 até 500 m", "Extensão acima de 500 até 1000 m",
        "Extensão acima de 1000 até 3000 m", "Extensão acima de 3000 m"]


def test_classe_pela_altura_e_pelo_numero_de_pavimentos():
    assert anexo_iii.classe_de(1, None)[0] == 0 and anexo_iii.classe_de(3, None)[0] == 2
    assert anexo_iii.classe_de(6, 18)[0] == 3 and anexo_iii.classe_de(8, 24)[0] == 4
    assert anexo_iii.classe_de(12, 36)[0] == 5 and anexo_iii.classe_de(5, 32)[0] == 5
    assert anexo_iii.classe_de(8, None)[0] is None  # sem altura não escolhe coluna


def test_consulta_escolhe_a_coluna_e_traz_as_observacoes(tabelas):
    ctx = {"occupancy": "D-2", "building_area_m2": 5000, "building_floors": 8}
    assert anexo_iii.consult(tabelas, ctx)["status"] == "MISSING_DATA"
    r = anexo_iii.consult(tabelas, {**ctx, "building_height_m": 24})
    assert r["status"] == "INDICATIVE" and r["table"] == 8
    assert r["column"].endswith("Acima de 6pav com H ≤ 30m")
    saidas = next(m for m in r["measures"] if m["label"] == "Saídas de Emergência")
    assert saidas["status"] == "CONDITIONAL" and "Enclausurada" in saidas["observacoes"][0]
    assert r["conferencia"].startswith("conferida no PDF oficial: 09/11/2026")
    # até 900 m² e 2 pavimentos vale a Tabela 2; divisão sem tabela não inventa resposta
    assert anexo_iii.consult(tabelas, {**ctx, "building_area_m2": 300,
                                       "building_floors": 1}) is None
    assert anexo_iii.consult(tabelas, {"occupancy": "A-1"}) is None


def test_tabelas_do_grupo_m_por_outro_criterio(tabelas):
    m2 = anexo_iii.consult(tabelas, {"occupancy": "M-2"})
    assert m2["status"] == "CHOOSE_COLUMN" and len(m2["columns"]) == 5
    m5 = anexo_iii.consult(tabelas, {"occupancy": "M-5"})
    assert m5["status"] == "INDICATIVE" and "Silos" in m5["column"]
    assert m2["columns"][0]["column"].startswith("Tanques ou cilindros e processos")
    assert m2["columns"][3]["column"].startswith("Produtos acondicionados")
    m7 = anexo_iii.consult(tabelas, {"occupancy": "M-7"})
    assert m7["status"] == "INDICATIVE" and "pátio de armazenagem" in m7["column"]
    # a observação 5 está no cabeçalho da coluna M-7 e vale para as medidas marcadas nela
    extintores = next(m for m in m7["measures"] if m["label"] == "Extintores")
    assert any(o.startswith("5- Para ocupações subsidiárias") for o in extintores["observacoes"])
    alarme = next(m for m in m7["measures"] if m["label"] == "Alarme de Incêndio")
    assert alarme["status"] == "NOT_MARKED" and alarme["observacoes"] == []


def test_tabela_com_extracao_estragada_nao_e_usada():
    raw = DECRETO.read_bytes().decode("utf-8")
    pos = raw.index("| Saídas de Emergência |", raw.index("| Tabela 8 - Exig"))
    fim = raw.index("\n", pos)
    ruim = raw[:pos] + "| Saídas de Emergência | X | X2 | X2 | X3 | X3, 4 | X3, 4, 99 |" + raw[fim:]
    tabelas = anexo_iii.load({anexo_iii.DOCUMENT: parse_markdown(ruim.encode("utf-8"),
                                                                 DECRETO.name)})
    assert any("99" in p for p in tabelas[8].problemas)
    r = anexo_iii.consult(tabelas, {"occupancy": "D-2", "building_area_m2": 5000,
                                    "building_floors": 3})
    assert r["status"] == "UNVERIFIED" and r["measures"] == []


def test_todas_as_tabelas_estao_conferidas_no_pdf(tabelas):
    """Conferência visual de 09/11/2026 nas páginas 29 a 56 do PDF oficial (mesmo SHA-256)."""
    assert {n for n, t in tabelas.items() if t.conferencia_visual is None} == set()


def test_conferencia_so_vale_para_o_mesmo_pdf_e_a_mesma_leitura(sources, tmp_path):
    sha = sources[anexo_iii.DOCUMENT].pdf_sha256
    lido = anexo_iii.parse_tables(sources[anexo_iii.DOCUMENT])[8].digest()

    def registro(pdf, digest):
        arq = tmp_path / f"{pdf[:6]}-{digest[:6]}.yaml"
        arq.write_text(f"pdf_sha256: {pdf}\nconferidas:\n  8: {{nota: teste, digest: {digest}}}\n",
                       encoding="utf-8")
        return arq

    assert anexo_iii.load(sources, registro(sha, lido))[8].conferencia_visual == "teste"
    assert anexo_iii.load(sources, registro("outro-pdf", lido))[8].conferencia_visual is None
    assert anexo_iii.load(sources, registro(sha, "leitura-antiga"))[8].conferencia_visual is None


def test_texto_alterado_perde_a_conferencia():
    """Trocar uma célula muda o resumo da leitura: a tabela deixa de constar como conferida."""
    raw = DECRETO.read_bytes().decode("utf-8")
    pos = raw.index("| Plano de emergência |", raw.index("| Tabela 6 - Exig"))
    fim = raw.index("\n", pos)
    outro = raw[:pos] + "| Plano de emergência | - | - | - | X | X | X |" + raw[fim:]
    tabelas = anexo_iii.load({anexo_iii.DOCUMENT: parse_markdown(outro.encode("utf-8"),
                                                                 DECRETO.name)})
    assert tabelas[6].valida and tabelas[6].conferencia_visual is None
    assert tabelas[7].conferencia_visual is not None  # as demais continuam conferidas
    r = anexo_iii.consult(tabelas, {"occupancy": "B-1", "building_area_m2": 2000,
                                    "building_floors": 3})
    assert "SEM conferência visual" in r["conferencia"]


def test_roteiro_cobre_todas_as_medidas_e_aponta_para_coisas_que_existem(tabelas, sources):
    rotulos = {m.rotulo for t in tabelas.values() for m in t.medidas}
    assert {r for r in rotulos if anexo_iii.como_tratar(r) is None} == set()
    assert anexo_iii.como_tratar("Extintores")["ferramenta"] == "dimensionar_extintores"
    for row in anexo_iii.roteiro():
        for nt in row.get("nt", []):
            assert nt in sources, (row["rotulo"], nt)
        for sid in row.get("simbolos", []):
            assert simbologia.achar(sid) is not None, (row["rotulo"], sid)
