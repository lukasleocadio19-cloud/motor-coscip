#!/usr/bin/env python3
"""Confere se toda citação do bilhete está localizada no índice de itens das NTs.

    python3 scripts/conferir_citacoes.py bilhete.txt [--json]

Reconhece citações na forma da anatomia do bilhete: ``NT 2-01:2020, item 5.2.5``,
``NT 2-01:2020, Tabela 3``, ``NT 2-08:2019, Anexo C`` e ``Decreto 42/2018, Art. 19``. Para
cada uma confere, no índice ``itens.jsonl`` (``references/`` da skill empacotada ou
``normative/indices`` do repositório): o documento existe, o dispositivo existe nele e o ano
da edição citada é o da edição indexada. ``[A CONFERIR]`` é citação **não localizada**.
Sai com código 1 se alguma citação não conferir (ou se não houver citação nenhuma).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_CITE = re.compile(
    r"\b(?P<doc>NT\s+\d-\d{2}(?:\s+P\d)?|Decreto\s+42/2018)"
    r"(?::(?P<ano>\d{4}))?"
    r"(?:\s*\([^)]*\))?"                       # edição por extenso entre parênteses
    r",\s*(?P<disp>(?:item|itens)\s+\[A CONFERIR\]|\[A CONFERIR\]|"
    r"item\s+\d+(?:\.\d+)*|Tabela\s+[A-Z]?\d{1,2}[A-Z]?|Anexo\s+(?:[IVX]{1,5}|[A-Z])\b|"
    r"Art\.\s*\d{1,3})", re.I)


def index_path() -> Path:
    cands = [HERE.parent / "references" / "itens.jsonl"]
    cands += [up / "normative" / "indices" / "itens.jsonl" for up in HERE.parents]
    for cand in cands:
        if cand.is_file():
            return cand
    raise FileNotFoundError("itens.jsonl não encontrado (references/ ou normative/indices/)")


def load_index() -> dict[str, dict]:
    docs: dict[str, dict] = {}
    for line in index_path().read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        d = docs.setdefault(row["documento"].upper(), {"edicao": row.get("edicao") or "",
                                                       "itens": {}})
        d["itens"].setdefault(row["item"].upper(), row)
    return docs


def _dispositivo(disp: str) -> str | None:
    disp = " ".join(disp.split())
    if "[A CONFERIR]" in disp.upper():
        return None
    m = re.match(r"(?:item|itens)\s+(.+)", disp, re.I)
    if m:
        return m.group(1)
    m = re.match(r"Art\.\s*(\d+)", disp, re.I)
    if m:
        return f"Art. {m.group(1)}"
    m = re.match(r"Anexo\s+(\S+)", disp, re.I)
    if m:
        return f"ANEXO {m.group(1).upper()}"
    return disp


def check(text: str) -> list[dict]:
    docs = load_index()
    out = []
    for m in _CITE.finditer(text):
        doc = " ".join(m.group("doc").split())
        item = _dispositivo(m.group("disp"))
        row = {"citacao": m.group(0), "documento": doc, "dispositivo": item,
               "ano": m.group("ano")}
        entry = docs.get(doc.upper())
        if entry is None:
            row.update(ok=False, problema="documento fora do índice")
        elif item is None:
            row.update(ok=False, problema="[A CONFERIR]: dispositivo não localizado")
        elif item.upper() not in entry["itens"]:
            row.update(ok=False, problema=f"{item} não existe no índice de {doc}")
        elif row["ano"] and row["ano"] not in entry["edicao"]:
            row.update(ok=False, problema=f"edição citada {row['ano']}, indexada "
                                          f"'{entry['edicao']}'")
        else:
            hit = entry["itens"][item.upper()]
            row.update(ok=True, pagina=hit.get("pagina"), edicao=entry["edicao"])
        out.append(row)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bilhete", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rows = check(args.bilhete.read_text(encoding="utf-8"))
    bad = [r for r in rows if not r["ok"]]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        for r in rows:
            mark = "ok " if r["ok"] else "NÃO"
            extra = f"p. {r.get('pagina')}" if r["ok"] else r["problema"]
            print(f"[{mark}] {r['citacao']} — {extra}")
        print(f"{len(rows) - len(bad)}/{len(rows)} citação(ões) localizada(s) no índice")
    return 0 if rows and not bad else 1


if __name__ == "__main__":
    sys.exit(main())
