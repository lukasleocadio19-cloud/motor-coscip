"""Imagens de página e caminho geométrico das tabelas a partir dos PDFs oficiais (F2.1, F2.2).

Para cada fonte do manifesto com imagem ausente (ou tabela sem caminho geométrico), baixa o PDF
da URL oficial, **confere o SHA-256** contra o ``sha256_pdf`` capturado (recusa se diferente —
o texto da base é daquela edição) e:

- renderiza **só as páginas referenciadas** nos ``.md`` com ``pypdfium2`` (150 dpi), nos
  caminhos exatos que o texto já cita (``media/<nt>/pagina-NN.jpg|png``);
- extrai com ``pdfplumber`` a tabela indicada em cada ``normative/tabelas/<nt>/*.yaml``
  (``indice_geometrico``) e grava o caminho ``geometrica``.

Precisa de rede até o portal do CBMERJ: roda no workflow ``normas-midia.yml`` (GitHub
Actions), não na máquina do usuário.

    python -m tools.normas.render_paginas --imagens --tabelas [--cache pdfs/]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

import yaml

from tools.normas import tabelas
from tools.normas.manifesto import FONTES, MANIFESTO
from tools.normas.vigencia import fetch


class HashMismatch(RuntimeError):
    pass


def get_pdf(fonte: dict[str, Any], cache: Path | None, fetcher=fetch) -> bytes:
    cached = cache / f"{fonte['sha256_pdf']}.pdf" if cache else None
    if cached and cached.is_file():
        data = cached.read_bytes()
    else:
        data = fetcher(fonte["url"])
    digest = hashlib.sha256(data).hexdigest()
    if digest != fonte["sha256_pdf"]:
        raise HashMismatch(f"{fonte['documento']}: SHA-256 do PDF {digest[:12]}… ≠ capturado "
                           f"{fonte['sha256_pdf'][:12]}… (edição mudou? ver vigência)")
    if cached and not cached.is_file():
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(data)
    return data


def missing_pages(fonte: dict[str, Any]) -> dict[int, Path]:
    return {img["pagina"]: FONTES / img["caminho"] for img in fonte["imagens"]
            if img["estado"] == "ausente" and img["pagina"]}


def tables_without_geometry(fonte: dict[str, Any]) -> list[Path]:
    out = []
    for t in fonte["tabelas"]:
        path = t.get("arquivo")
        if path:
            data = tabelas.load(tabelas.ROOT / path)
            if not (data.get("caminhos") or {}).get("geometrica"):
                out.append(tabelas.ROOT / path)
    return out


def run(do_images: bool, do_tables: bool, cache: Path | None, fetcher=fetch,
        only: set[str] | None = None) -> dict[str, list[str]]:
    import pdfplumber

    data = yaml.safe_load(MANIFESTO.read_text(encoding="utf-8"))
    log: dict[str, list[str]] = {"imagens": [], "tabelas": [], "erros": []}
    for fonte in data["fontes"]:
        if only and fonte["documento"] not in only:
            continue
        pages = missing_pages(fonte) if do_images else {}
        tabs = tables_without_geometry(fonte) if do_tables else []
        if not pages and not tabs:
            continue
        try:
            pdf = get_pdf(fonte, cache, fetcher)
        except Exception as exc:  # noqa: BLE001 — registra e segue para a próxima fonte
            log["erros"].append(f"{fonte['documento']}: {exc}")
            continue
        for p in tabelas.render_pages(pdf, pages):
            log["imagens"].append(p.relative_to(FONTES).as_posix())
        for tpath in tabs:
            t = tabelas.load(tpath)
            found = tabelas.extract_geometric(pdf, t["pagina"])
            idx = int(t.get("indice_geometrico", 0))
            if idx >= len(found):
                log["erros"].append(f"{tpath.name}: página {t['pagina']} tem {len(found)} "
                                    "tabela(s) geométricas; conferir indice_geometrico")
                continue
            t["caminhos"]["geometrica"] = {
                "metodo": f"pdfplumber {pdfplumber.__version__}, estratégia por linhas",
                "bbox": found[idx]["bbox"], "linhas": found[idx]["linhas"]}
            tpath.write_bytes(tabelas.dump(t).encode("utf-8"))
            tabelas.refresh(tpath)
            log["tabelas"].append(tpath.name)
    return log


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Imagens e tabelas dos PDFs oficiais (F2)")
    ap.add_argument("--imagens", action="store_true")
    ap.add_argument("--tabelas", action="store_true")
    ap.add_argument("--cache", type=Path)
    ap.add_argument("--documento", action="append", help="só estes (ex.: 'NT 2-01')")
    args = ap.parse_args(argv)
    log = run(args.imagens, args.tabelas, args.cache, only=set(args.documento or []) or None)
    print(f"imagens geradas: {len(log['imagens'])}; tabelas extraídas: {len(log['tabelas'])}")
    for e in log["erros"]:
        print(f"ERRO {e}")
    return 1 if log["erros"] and not (log["imagens"] or log["tabelas"]) else 0


if __name__ == "__main__":
    sys.exit(main())
