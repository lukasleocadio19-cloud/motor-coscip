"""Confere as skills empacotadas (plano de correção, F3 — aceite).

Para cada skill (vigentes e de transição), sobre o conteúdo final do zip (``pack.files_for``):

1. todo caminho citado (``references/…``, ``scripts/…``, ``agents/…``, ``assets/…``) em
   SKILL.md e nas referências próprias existe no pacote;
2. toda skill chamada por ``$nome`` existe e é vigente (skill de transição não pode ser chamada
   por uma vigente);
3. toda NT citada (``NT x-yy``) existe no catálogo da base (``normative/fontes``).

Os textos das NTs (``nt-*.md``, Decreto) não são conferidos aqui: as imagens deles estão no
manifesto (F1.2) e as citações, no ``verify_catalog``.

    python -m tools.skills.verificar_links    # sai 1 se houver problema
"""

from __future__ import annotations

import re
import sys
from typing import Any

from tools.skills.pack import config, files_for

_PATH = re.compile(r"(?<![\w/.-])((?:references|scripts|agents|assets)/[\w./-]+\.\w+)")
_SKILL = re.compile(r"\$([a-z][a-z0-9-]+)")
_NT = re.compile(r"\bNTs? ?(\d)-(\d{2})\b")
_SKIP = re.compile(r"^references/(nt-\d-\d{2}.*|decreto-42-2018-coscip-compilado)\.md$|"
                   r"^references/(media/|itens\.jsonl$|banco-de-citacoes\.md$|"
                   r"edicoes-vigentes\.md$)")
# NT citada fora do catálogo de propósito (e por quê): só vale se o texto disser isso
_NT_FORA_PERMITIDO = {"3-08": "minuta de recarga de veículo elétrico, citada como não vigente"}
# nomes de skill válidos fora do catálogo CBMERJ (exemplos de shell/variáveis em scripts)
_NOT_SKILLS = {"env", "root", "args", "python", "path", "home"}


def catalog_nts() -> set[str]:
    from tools.normas.manifesto import source_files

    out = set()
    for f in source_files():
        m = re.match(r"nt-(\d)-(\d{2})", f.name)
        if m:
            out.add(f"{m.group(1)}-{m.group(2)}")
    return out


def check_skill(name: str, files: dict[str, bytes], vigentes: set[str],
                known: set[str], nts: set[str]) -> list[str]:
    problems: list[str] = []
    for rel, data in files.items():
        if _SKIP.match(rel) or not rel.endswith((".md", ".py", ".yaml", ".yml")):
            continue
        text = data.decode("utf-8", errors="replace")
        for m in _PATH.finditer(text):
            target = m.group(1).rstrip(".")
            if target not in files and not target.startswith("references/media/"):
                problems.append(f"{name}/{rel}: cita {target}, que não existe no pacote")
        if rel.endswith(".md"):
            for m in _SKILL.finditer(text):
                s = m.group(1)
                if s in _NOT_SKILLS or s.startswith(("cbmerj-grupo-n", "cbmerj-grupo-x")):
                    continue
                if s not in known:
                    problems.append(f"{name}/{rel}: chama ${s}, skill inexistente")
                elif name in vigentes and s not in vigentes:
                    problems.append(f"{name}/{rel}: skill vigente chama ${s}, que será aposentada")
            for m in _NT.finditer(text):
                nt = f"{m.group(1)}-{m.group(2)}"
                if nt not in nts and nt not in _NT_FORA_PERMITIDO:
                    problems.append(f"{name}/{rel}: cita NT {nt}, fora do catálogo da base")
    return sorted(set(problems))


def run() -> dict[str, Any]:
    cfg = config()
    vigentes = set(cfg["vigentes"])
    known = vigentes | set(cfg["aposentar"])
    nts = catalog_nts()
    report: dict[str, list[str]] = {}
    for name, spec in cfg["vigentes"].items():
        files = files_for(name, spec.get("fontes") or [], spec.get("comuns"))
        report[name] = check_skill(name, files, vigentes, known, nts)
    for name in cfg["aposentar"]:
        try:
            files = files_for(name, [])
        except FileNotFoundError:
            continue
        report[name] = check_skill(name, files, vigentes, known, nts)
    return report


def main() -> int:
    report = run()
    bad = 0
    for name, problems in report.items():
        print(f"{'ok ' if not problems else 'ERR'} {name}")
        for p in problems:
            print(f"    {p}")
        bad += len(problems)
    print(f"{bad} problema(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
