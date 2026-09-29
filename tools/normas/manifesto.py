"""Manifesto da base normativa (plano de correção, F1.2).

Gera ``normative/manifests/base.yaml`` a partir de ``normative/fontes``: para cada fonte, o
documento, a edição, o ato de aprovação, a URL oficial, o SHA-256 do PDF (front matter) e do
Markdown, a data de captura, as páginas, cada imagem de página referenciada (presente ou
ausente, com hash) e o estado de conferência de cada tabela (``normative/tabelas``).

O manifesto é **derivado**: nunca se edita à mão. ``tests/unit/test_base_manifest.py`` recalcula
e compara; qualquer mudança nos ``.md``, nas imagens ou nas tabelas exige regenerar:

    python -m tools.normas.manifesto            # grava
    python -m tools.normas.manifesto --conferir # só confere (sai com 1 se desatualizado)
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from coscip_normative import parse_markdown

ROOT = Path(__file__).resolve().parents[2]
FONTES = ROOT / "normative" / "fontes"
TABELAS = ROOT / "normative" / "tabelas"
MANIFESTO = ROOT / "normative" / "manifests" / "base.yaml"
SCHEMA = "base-manifest/1.0"

_IMG = re.compile(r"!\[[^\]]*\]\((media/[^)\s]+)\)")
_PAGE = re.compile(r"^## Página (\d+)\s*$", re.M)
_ATO = re.compile(r"Aprovad[ao] pel[ao] ((?:Portaria|Resolução)[^(\n]*?)\s*(?:\(|$)", re.M)
_RAW_TABLES = re.compile(r"^### Tabelas extraídas\b.*$", re.M)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_files(folder: Path = FONTES) -> list[Path]:
    return sorted(f for f in folder.glob("*.md") if f.name != "README.md")


def _page_of(text: str, pos: int) -> int | None:
    found = None
    for m in _PAGE.finditer(text, 0, pos):
        found = int(m.group(1))
    return found


def media_refs(text: str) -> list[tuple[str, int | None]]:
    """Imagens referenciadas no texto, na ordem, com a página do marcador anterior."""
    seen: dict[str, int | None] = {}
    for m in _IMG.finditer(text):
        seen.setdefault(m.group(1), _page_of(text, m.start()))
    return list(seen.items())


def table_states(arquivo: str) -> dict[int, list[dict[str, Any]]]:
    """Estado das tabelas conferidas da fonte ``arquivo`` (campo ``arquivo`` de cada
    ``normative/tabelas/*/*.yaml``), por página. A pasta não precisa ter o nome da mídia."""
    out: dict[int, list[dict[str, Any]]] = {}
    for f in sorted(TABELAS.glob("*/*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        if data.get("arquivo") != arquivo:
            continue
        page = int(data.get("pagina") or 0)
        out.setdefault(page, []).append({
            "tabela": str(data.get("tabela") or f.stem),
            "arquivo": f"normative/tabelas/{f.parent.name}/{f.name}",
            "estado": str(data.get("estado") or "pendente_humano"),
        })
    return out


def _is_cover(text: str, page: int) -> bool:
    """Tabela extraída da página 1 que é o cabeçalho da NT ("NOTA TÉCNICA / CBMERJ / Versão")."""
    if page != 1:
        return False
    from tools.normas.tabelas import raw_table

    try:
        cells = " ".join(c for row in raw_table(text, 1, 1) for c in row).upper()
    except ValueError:
        return False
    return "NOTA" in cells and "CBMERJ" in cells and ("VERSÃO" in cells or "VIGÊNCIA" in cells)


def media_slug(refs: list[tuple[str, int | None]], filename: str) -> str:
    """Pasta de mídia da fonte (``nt-2-01``); sem imagem, derivada do nome do arquivo."""
    if refs:
        return refs[0][0].split("/")[1]
    m = re.match(r"(nt-\d-\d{2}(?:-parte-\d)?)", filename)
    return m.group(1) if m else Path(filename).stem


def entry(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    src = parse_markdown(raw, path.name)
    text = raw.decode("utf-8")
    ato = _ATO.search(text)
    refs = media_refs(text)
    slug = media_slug(refs, path.name)
    images = []
    for rel, page in refs:
        img = FONTES / rel
        present = img.is_file()
        images.append({"caminho": rel, "pagina": page,
                       "estado": "presente" if present else "ausente",
                       "sha256": sha256_bytes(img.read_bytes()) if present else None})
    conferred = table_states(path.name)
    raw_pages = sorted({p for m in _RAW_TABLES.finditer(text)
                        if (p := _page_of(text, m.start())) is not None})
    tables = []
    for page in sorted(set(raw_pages) | set(conferred)):
        states = conferred.get(page)
        if states:
            tables += [{"pagina": page, **s} for s in states]
        elif _is_cover(text, page):
            # quadro de capa da NT (número, versão, vigência): não é tabela normativa
            tables.append({"pagina": page, "estado": "capa"})
        else:
            tables.append({"pagina": page, "estado": "bruto"})
    pages = src.meta.get("paginas_pdf")
    return {
        "arquivo": path.name,
        "documento": src.document,
        "titulo": src.title,
        "edicao": src.edition,
        "ato": " ".join(ato.group(1).split()).rstrip(".") if ato else None,
        "url": src.official_url,
        "sha256_pdf": src.pdf_sha256,
        "sha256_md": sha256_bytes(raw),
        "data_captura": src.captured_at,
        "paginas": int(pages) if pages and str(pages).isdigit() else None,
        "midia": slug,
        "imagens": images,
        "tabelas": tables,
    }


def build(folder: Path = FONTES) -> dict[str, Any]:
    fontes = [entry(f) for f in source_files(folder)]
    imgs = [i for f in fontes for i in f["imagens"]]
    tabs = [t for f in fontes for t in f["tabelas"]]
    states: dict[str, int] = {}
    for t in tabs:
        states[t["estado"]] = states.get(t["estado"], 0) + 1
    return {
        "schema_version": SCHEMA,
        "gerado_por": "tools/normas/manifesto.py (não editar à mão)",
        "resumo": {
            "fontes": len(fontes),
            "imagens_referenciadas": len(imgs),
            "imagens_presentes": sum(i["estado"] == "presente" for i in imgs),
            "imagens_ausentes": sum(i["estado"] == "ausente" for i in imgs),
            "tabelas_por_estado": dict(sorted(states.items())),
        },
        "fontes": fontes,
    }


def dump(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Manifesto da base normativa (F1.2)")
    ap.add_argument("--conferir", action="store_true", help="não grava; sai 1 se desatualizado")
    args = ap.parse_args(argv)
    text = dump(build())
    if args.conferir:
        current = MANIFESTO.read_text(encoding="utf-8") if MANIFESTO.exists() else ""
        if current != text:
            print("manifesto desatualizado: rode python -m tools.normas.manifesto")
            return 1
        print("manifesto ok")
        return 0
    MANIFESTO.write_bytes(text.encode("utf-8"))
    print(f"ok: {MANIFESTO.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
