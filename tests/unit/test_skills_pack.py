"""Skills geradas do repositório (plano de correção, F1.1, F3.3) e vigência (F1.3)."""

from __future__ import annotations

import hashlib
import json
import zipfile

from tools.normas import indice_itens, vigencia
from tools.skills import pack


def test_no_nt_text_duplicated_inside_skills():
    # a cópia única dos textos é normative/fontes
    dup = [p for p in pack.SKILLS.rglob("*.md")
           if p.name.startswith("nt-") or p.name == "decreto-42-2018-coscip-compilado.md"]
    assert dup == []
    assert not (pack.SKILLS / "cbmerj-grupo-5-legado-nao-usar").exists()
    assert not list(pack.SKILLS.rglob("media"))


def test_group_zip_carries_its_nts_and_images(tmp_path):
    files = pack.files_for("cbmerj-grupo-1-generalidades", ["nt-1-*.md"])
    assert "SKILL.md" in files
    assert "references/nt-1-04-classificacao-de-risco.md" in files
    assert files["references/nt-1-04-classificacao-de-risco.md"] == (
        pack.FONTES / "nt-1-04-classificacao-de-risco.md").read_bytes()
    assert any(k.startswith("references/media/nt-1-04/") for k in files)
    assert not any(k.startswith("references/nt-2-") for k in files)


def test_pack_is_deterministic(tmp_path):
    a = pack.pack(dest=tmp_path / "a")
    b = pack.pack(dest=tmp_path / "b")
    assert [p.name for p in a] == [p.name for p in b]
    for x, y in zip(a, b, strict=True):
        assert hashlib.sha256(x.read_bytes()).digest() == hashlib.sha256(y.read_bytes()).digest()
    names = zipfile.ZipFile(tmp_path / "a" / "orquestrar-analise-cbmerj.zip").namelist()
    assert "orquestrar-analise-cbmerj/SKILL.md" in names
    assert "orquestrar-analise-cbmerj/references/decreto-42-2018-coscip-compilado.md" in names
    bilhete = zipfile.ZipFile(tmp_path / "a" / "emitir-bilhete-cbmerj.zip").namelist()
    for ref in ("edicoes-vigentes.md", "banco-de-citacoes.md", "itens.jsonl"):
        assert f"emitir-bilhete-cbmerj/references/{ref}" in bilhete


def test_item_index_is_up_to_date_and_has_known_items():
    assert indice_itens.INDICE.read_text(encoding="utf-8") == indice_itens.jsonl(), (
        "índice desatualizado: python -m tools.normas.indice_itens")
    text = indice_itens.INDICE.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in text.splitlines()]
    key = {(r["documento"], r["item"]): r for r in rows}
    assert key[("NT 2-01", "5.2.4")]["pagina"] == 4
    assert key[("NT 2-01", "Tabela 3")]["tipo"] == "TABLE"
    assert ("Decreto 42/2018", "Anexo III") in key


def test_vigencia_reports_without_touching_base():
    fontes = [{"documento": "NT 9-99", "arquivo": "x.md", "url": "https://x/a.pdf",
               "sha256_pdf": hashlib.sha256(b"pdf").hexdigest(), "data_captura": "2026-07-23"},
              {"documento": "NT 9-98", "arquivo": "y.md", "url": "https://x/b.pdf",
               "sha256_pdf": "0" * 64, "data_captura": "2026-07-23"},
              {"documento": "NT 9-97", "arquivo": "z.md", "url": "https://x/c.pdf",
               "sha256_pdf": "0" * 64, "data_captura": "2026-07-23"}]

    def fake(url):
        if url.endswith("c.pdf"):
            raise OSError("sem rede")
        return b"pdf"

    rows = {r["documento"]: r for r in vigencia.check(fontes, fetcher=fake)}
    assert rows["NT 9-99"]["estado"] == "IGUAL"
    assert rows["NT 9-98"]["estado"] == "MUDOU"
    assert rows["NT 9-97"]["estado"] == "INDISPONIVEL"  # rede ruim não conclui nada
    body = vigencia.issue_body(rows["NT 9-98"])
    assert "0" * 64 in body and "Nada foi alterado automaticamente" in body
