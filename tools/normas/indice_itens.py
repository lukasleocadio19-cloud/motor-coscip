"""Índice de itens da base normativa (plano de correção, F3.3).

Reaproveita ``coscip_normative.parse_markdown`` (o mesmo índice que confere as citações do
motor) e gera, para cada item, artigo, tabela e anexo de cada fonte: documento, edição, item,
tipo, página e as primeiras palavras. Saídas:

- ``normative/indices/itens.jsonl`` — versionado; lido por ``localizar_item.py`` da skill de
  bilhete e conferido por ``tests/unit/test_indice_itens.py``;
- ``banco-de-citacoes.md`` e ``edicoes-vigentes.md`` — gerados na hora de empacotar a skill
  ``emitir-bilhete-cbmerj`` (``tools/skills/pack.py``).

    python -m tools.normas.indice_itens            # grava o jsonl
    python -m tools.normas.indice_itens --conferir # sai 1 se desatualizado
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from coscip_normative import parse_markdown

ROOT = Path(__file__).resolve().parents[2]
FONTES = ROOT / "normative" / "fontes"
INDICE = ROOT / "normative" / "indices" / "itens.jsonl"
_WORDS = 14
_KIND_ORDER = {"ARTICLE": 0, "SECTION": 1, "NUMBERED": 2, "TABLE": 3, "ANNEX": 4}


def _natural(item: str) -> list[Any]:
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", item)]


def _lead(text: str, item: str) -> str:
    flat = " ".join(text.replace("|", " ").replace("#", " ").split())
    if flat.lower().startswith(item.lower()):
        flat = flat[len(item):].lstrip(" -–—:.")
    words = flat.split()
    return " ".join(words[:_WORDS]) + (" …" if len(words) > _WORDS else "")


def entries() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in sorted(FONTES.glob("*.md")):
        if path.name == "README.md":
            continue
        src = parse_markdown(path.read_bytes(), path.name)
        for item, occurrences in src.items.items():
            # a ocorrência com mais texto é o corpo; as demais costumam ser o sumário
            best = max(occurrences, key=lambda it: (it.end - it.start, -it.start))
            out.append({
                "documento": src.document, "edicao": src.edition, "item": item,
                "tipo": best.kind, "pagina": best.page,
                "ocorrencias": len(occurrences), "arquivo": path.name,
                "inicio": _lead(src.text[best.start:best.end], item),
            })
    out.sort(key=lambda e: (e["documento"], _KIND_ORDER.get(e["tipo"], 9), _natural(e["item"])))
    return out


def jsonl() -> str:
    return "".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in entries())


def banco_md() -> str:
    lines = ["# Banco de citações — gerado da base normativa (não editar)", "",
             "Gerado por `tools/normas/indice_itens.py` a partir de `normative/fontes` (a mesma "
             "base que o motor usa para conferir citações). Cada linha: item, página do PDF e o "
             "início do texto. **Ler o trecho na NT antes de citar**: o índice localiza, não "
             "interpreta. Item ausente daqui não existe na base — marcar `[A CONFERIR]`.", ""]
    current = None
    for e in entries():
        if e["documento"] != current:
            current = e["documento"]
            lines += ["", f"## {current} — {e['edicao']}", "",
                      "| Item | Pág. | Início do texto |", "| --- | --- | --- |"]
        inicio = e["inicio"].replace("|", "/")
        lines.append(f"| {e['item']} | {e['pagina'] or '—'} | {inicio} |")
    return "\n".join(lines) + "\n"


def edicoes_md() -> str:
    import yaml

    from tools.normas.manifesto import MANIFESTO

    data = yaml.safe_load(MANIFESTO.read_text(encoding="utf-8"))
    lines = ["# Edições vigentes na base — gerado do manifesto (não editar)", "",
             "Gerado de `normative/manifests/base.yaml`. É a edição **capturada** em cada data; "
             "se a análise for posterior, confirmar no portal oficial do CBMERJ (o workflow "
             "mensal de vigência abre issue quando um PDF muda).", "",
             "| Documento | Edição | Ato | Captura | Hash do PDF |",
             "| --- | --- | --- | --- | --- |"]
    for f in sorted(data["fontes"], key=lambda f: _natural(f["documento"])):
        lines.append(f"| {f['documento']} | {f['edicao']} | {f['ato'] or '—'} | "
                     f"{f['data_captura']} | `{(f['sha256_pdf'] or '')[:12]}…` |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Índice de itens (F3.3)")
    ap.add_argument("--conferir", action="store_true")
    args = ap.parse_args(argv)
    text = jsonl()
    if args.conferir:
        ok = INDICE.exists() and INDICE.read_text(encoding="utf-8") == text
        print("índice ok" if ok else "índice desatualizado: python -m tools.normas.indice_itens")
        return 0 if ok else 1
    INDICE.parent.mkdir(parents=True, exist_ok=True)
    INDICE.write_bytes(text.encode("utf-8"))
    print(f"ok: {INDICE.relative_to(ROOT)} ({text.count(chr(10))} itens)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
