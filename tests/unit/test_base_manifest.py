"""Manifesto da base normativa (plano de correção, F1.2).

O manifesto é derivado dos ``.md``, das imagens e das tabelas conferidas: este teste recalcula
e compara, então nenhuma mudança na base passa sem ficar registrada nele.
"""

from __future__ import annotations

import hashlib

import yaml

from tools.normas import manifesto

DATA = yaml.safe_load(manifesto.MANIFESTO.read_text(encoding="utf-8"))


def test_manifest_is_up_to_date():
    assert manifesto.MANIFESTO.read_text(encoding="utf-8") == manifesto.dump(manifesto.build()), (
        "manifesto desatualizado: python -m tools.normas.manifesto")


def test_every_source_is_in_manifest_with_matching_hash():
    listed = {f["arquivo"]: f for f in DATA["fontes"]}
    files = manifesto.source_files()
    assert {f.name for f in files} == set(listed)
    assert len(files) == 53  # 52 NTs + Decreto 42/2018
    for f in files:
        entry = listed[f.name]
        assert entry["sha256_md"] == hashlib.sha256(f.read_bytes()).hexdigest(), f.name
        assert entry["sha256_pdf"] and len(entry["sha256_pdf"]) == 64, f.name
        assert entry["url"] and entry["url"].startswith("https://"), f.name


def test_image_state_matches_disk():
    for fonte in DATA["fontes"]:
        for img in fonte["imagens"]:
            path = manifesto.FONTES / img["caminho"]
            if img["estado"] == "presente":
                assert path.is_file(), img["caminho"]
                assert hashlib.sha256(path.read_bytes()).hexdigest() == img["sha256"]
            else:
                assert img["estado"] == "ausente" and not path.exists(), img["caminho"]
                assert img["sha256"] is None


def test_no_orphan_images():
    referenced = {img["caminho"] for f in DATA["fontes"] for img in f["imagens"]}
    on_disk = {p.relative_to(manifesto.FONTES).as_posix()
               for p in (manifesto.FONTES / "media").rglob("*") if p.is_file()}
    assert on_disk <= referenced, sorted(on_disk - referenced)[:10]


def test_summary_counts_are_consistent():
    r = DATA["resumo"]
    assert r["imagens_presentes"] + r["imagens_ausentes"] == r["imagens_referenciadas"] >= 434
    assert sum(r["tabelas_por_estado"].values()) == sum(len(f["tabelas"]) for f in DATA["fontes"])
    # "capa": quadro de cabeçalho da NT na página 1 (número, versão, vigência), não normativo
    allowed = {"bruto", "verificada", "divergente", "pendente_humano", "capa"}
    assert set(r["tabelas_por_estado"]) <= allowed
    assert all(t["pagina"] == 1 for f in DATA["fontes"] for t in f["tabelas"]
               if t["estado"] == "capa")
