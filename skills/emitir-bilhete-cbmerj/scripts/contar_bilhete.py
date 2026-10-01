#!/usr/bin/env python3
"""Conta caracteres e bytes UTF-8 do bilhete, no total e por item.

    python3 scripts/contar_bilhete.py bilhete.txt --limite 8000 [--json]

Caracteres e bytes divergem (acentos ocupam 2 bytes em UTF-8). Sem saber como o sistema conta,
dimensionar pelo maior dos dois. Item = linha que começa com "N." (ou "N -"); o texto antes do
primeiro item conta como cabeçalho e o que vem depois do último item faz parte dele.
Sai com código 1 quando o maior dos dois passa do limite.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_ITEM = re.compile(r"^\s*(\d{1,3})\s*[.)-]\s+", re.M)


def medir(texto: str) -> dict:
    texto = texto.replace("\r\n", "\n")
    starts = [(m.start(), m.group(1)) for m in _ITEM.finditer(texto)]
    partes = []
    if not starts or starts[0][0] > 0:
        partes.append(("cabeçalho", texto[: starts[0][0] if starts else len(texto)]))
    for i, (pos, num) in enumerate(starts):
        fim = starts[i + 1][0] if i + 1 < len(starts) else len(texto)
        partes.append((f"item {num}", texto[pos:fim]))
    itens = [{"parte": nome, "caracteres": len(t), "bytes_utf8": len(t.encode("utf-8"))}
             for nome, t in partes if t.strip()]
    return {"caracteres": len(texto), "bytes_utf8": len(texto.encode("utf-8")),
            "itens": itens,
            "mais_longos": sorted(itens, key=lambda i: -i["caracteres"])[:5]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("arquivo", type=Path)
    ap.add_argument("--limite", type=int, default=8000)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    r = medir(args.arquivo.read_text(encoding="utf-8"))
    maior = max(r["caracteres"], r["bytes_utf8"])
    r["limite"] = args.limite
    r["cabe"] = maior <= args.limite
    r["folga"] = args.limite - maior
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(f"caracteres: {r['caracteres']}  bytes UTF-8: {r['bytes_utf8']}  "
              f"limite: {args.limite}  {'CABE' if r['cabe'] else 'NÃO CABE'} "
              f"(folga {r['folga']} pelo maior dos dois)")
        for i in r["itens"]:
            print(f"  {i['parte']:>10}: {i['caracteres']:5d} car. / {i['bytes_utf8']:5d} bytes")
        print("mais longos: " + ", ".join(f"{i['parte']} ({i['caracteres']})"
                                          for i in r["mais_longos"]))
    return 0 if r["cabe"] else 1


if __name__ == "__main__":
    sys.exit(main())
