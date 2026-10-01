#!/usr/bin/env python3
"""Localiza o item de NT que contém um trecho, com edição e página do PDF.

    python3 scripts/localizar_item.py "distancia maxima a ser percorrida" --nt 2-01
    python3 scripts/localizar_item.py --item 5.2.4 --nt 2-01

Fontes, nesta ordem:
1. texto integral das NTs, se disponível: ``COSCIP_NORMAS_DIR``, as skills de grupo
   instaladas ao lado desta (``../cbmerj-grupo-*/references/nt-*.md``) ou
   ``normative/fontes`` do repositório;
2. o índice ``references/itens.jsonl`` desta skill (gerado da mesma base; só o início de cada
   item).

A busca ignora acentos e maiúsculas e exige todos os termos na mesma linha. O item devolvido é
o item numerado imediatamente anterior ao trecho: **ler o trecho antes de citar** — o item
acima da linha nem sempre é o que fundamenta a exigência. Nada encontrado ⇒ citar
``[A CONFERIR]``, nunca deduzir.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
_PAGE = re.compile(r"^##\s+P[áa]gina\s+(\d+)\s*$", re.M)
_ITEM = re.compile(r"^(?:#{1,6}\s*)?(\d+(?:\.\d+){1,5})\.?\s+\S|"
                   r"(Tabela\s+[A-Z]?\d{1,2}[A-Z]?)\s*[-–—]|"
                   r"^(?:#{1,6}\s*)?(ANEXO\s+(?:[IVX]{1,5}|[A-Z]))\b|"
                   r"\b(Art\.\s*\d{1,3})\s*[ºo°]?\s*[-–—]", re.M | re.I)


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.replace("|", " ").lower().split())


def nt_files() -> list[Path]:
    dirs: list[Path] = []
    if os.environ.get("COSCIP_NORMAS_DIR"):
        dirs += [Path(d) for d in os.environ["COSCIP_NORMAS_DIR"].split(os.pathsep) if d]
    dirs += sorted(HERE.parent.parent.glob("cbmerj-grupo-[1-5]-*/references"))
    dirs += sorted(HERE.parent.parent.glob("orquestrar-analise-cbmerj/references"))
    for up in HERE.parents:
        if (up / "normative" / "fontes").is_dir():
            dirs.append(up / "normative" / "fontes")
            break
    files, seen = [], set()
    for d in dirs:
        if "legado" in str(d):
            continue
        for f in sorted(d.glob("*.md")):
            if (f.name.startswith("nt-") or f.name.startswith("decreto-")) and f.name not in seen:
                seen.add(f.name)
                files.append(f)
    return files


def front_matter(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if text.startswith("---"):
        for line in text[3: text.find("\n---", 3)].splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                out[k.strip()] = v.strip().strip('"')
    return out


def _last(pattern_iter, pos: int):
    found = None
    for m in pattern_iter:
        if m.start() > pos:
            break
        found = m
    return found


def search_text(query: str, nt: str | None, limit: int) -> list[dict]:
    terms = [fold(t) for t in query.split() if len(t) > 2]
    hits = []
    for f in nt_files():
        if nt and f"nt-{nt}" not in f.name:
            continue
        text = f.read_text(encoding="utf-8")
        meta = front_matter(text)
        pages = list(_PAGE.finditer(text))
        items = list(_ITEM.finditer(text))
        for line in re.finditer(r"[^\n]+", text):
            if all(t in fold(line.group(0)) for t in terms):
                page = _last(pages, line.start())
                item = _last(items, line.start())
                ident = next((g for g in item.groups() if g), None) if item else None
                hits.append({"documento": meta.get("documento") or f.stem,
                             "edicao": meta.get("edicao"), "arquivo": f.name,
                             "item": " ".join(ident.split()) if ident else None,
                             "pagina": int(page.group(1)) if page else None,
                             "trecho": line.group(0).strip()[:300], "fonte": "texto integral"})
                if len(hits) >= limit:
                    return hits
    return hits


def search_index(query: str | None, item: str | None, nt: str | None, limit: int) -> list[dict]:
    index = HERE.parent / "references" / "itens.jsonl"
    if not index.exists():
        return []
    terms = [fold(t) for t in (query or "").split() if len(t) > 2]
    want_doc = f"NT {nt}" if nt else None
    out = []
    for line in index.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if want_doc and not row["documento"].startswith(want_doc):
            continue
        if item and row["item"].lower() != item.lower():
            continue
        if terms and not all(t in fold(row["inicio"]) for t in terms):
            continue
        out.append({**row, "trecho": row["inicio"], "fonte": "índice itens.jsonl"})
        if len(out) >= limit:
            break
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("consulta", nargs="?", default="")
    ap.add_argument("--nt", help="ex.: 2-01")
    ap.add_argument("--item", help="ex.: 5.2.4 (confere que o item existe e dá a página)")
    ap.add_argument("--limite", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not args.consulta and not args.item:
        ap.error("informe o trecho ou --item")
    hits = [] if args.item else search_text(args.consulta, args.nt, args.limite)
    if not hits:
        hits = search_index(args.consulta, args.item, args.nt, args.limite)
    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=1))
    elif not hits:
        print("nada encontrado: citar [A CONFERIR] e registrar na nota de rastreabilidade")
    else:
        for h in hits:
            print(f"{h['documento']} ({h.get('edicao') or 'edição?'}), item {h.get('item') or '?'},"
                  f" p. {h.get('pagina') or '?'} [{h['fonte']}]\n    {h['trecho']}")
    return 0 if hits else 1


if __name__ == "__main__":
    sys.exit(main())
