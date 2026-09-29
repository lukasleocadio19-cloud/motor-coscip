#!/usr/bin/env python3
"""Rascunho do bilhete a partir da matriz consolidada (ponto de partida, não texto final).

    python3 scripts/rascunho_bilhete.py matriz.json --out bilhete.txt --nota nota.md

Entra no bilhete só o que é exigência: achado **não conforme** e pendência do projeto
(``DOCUMENT_MISSING``, ``DOCUMENT_INCOMPLETE`` ou ``DIVERGENCE`` a compatibilizar) com
providência e sem revisão do analista em aberto. Falta de dado para a análise
(``DATA_MISSING``, ``NOT_VERIFIABLE``), revisão do analista e achado com ``review_status``
``PENDING`` ficam **fora** do bilhete e aparecem na nota de rastreabilidade (interna) com o
motivo: ausência de evidência nunca vira exigência nem conformidade.
Cada item segue a forma canônica de ``references/anatomia-do-bilhete.md``; o critério adotado
é escrito como tal. Depois: revisar a redação, ``conferir_citacoes.py`` e
``contar_bilhete.py``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Medidas na ordem do Anexo III do Decreto; documentação e o resto depois.
ORDEM_TEMA = ["Enquadramento", "Quadro Resumo", "Extintores", "Hidrantes e mangotinhos",
              "Chuveiros automáticos", "Sinalização", "Iluminação de emergência",
              "Alarme de incêndio", "Detecção de incêndio", "Saídas de emergência",
              "Memorial", "Documentação", "Responsabilidade técnica"]
PENDENCIA_DO_PROJETO = {"DOCUMENT_MISSING", "DOCUMENT_INCOMPLETE", "DIVERGENCE"}


def entra_no_bilhete(a: dict[str, Any]) -> tuple[bool, str]:
    if a["compliance_status"] == "NON_COMPLIANT":
        return True, "não conforme"
    if a["compliance_status"] == "UNDETERMINED" and a["tipo"] in PENDENCIA_DO_PROJETO \
            and a.get("saneamento"):
        if a["review_status"] == "PENDING":
            return False, f"pendência do projeto ({a['tipo']}) aguardando o analista"
        return True, "pendência do projeto"
    motivo = {"COMPLIANT": "conforme", "NOT_APPLICABLE": "não aplicável"}.get(
        a["compliance_status"], f"inconclusivo ({a['tipo']}): decidir antes de exigir")
    return False, motivo


def _ano(a: dict[str, Any]) -> str:
    m = re.search(r"(19|20)\d{2}", a["regra"].get("edicao") or "")
    return f":{m.group(0)}" if m else ""


def _dispositivo(item: str) -> str:
    if re.fullmatch(r"\d+(?:\.\d+)*", item):
        return f"item {item}"
    m = re.fullmatch(r"ANEXO\s+(\S+)", item, re.I)
    if m:
        return f"Anexo {m.group(1).upper()}"
    return item


def citacao(a: dict[str, Any]) -> str:
    r = a["regra"]
    return f"{r['documento']}{_ano(a)}, {_dispositivo(r['item'])}"


def _titulo_e_fato(fato: str) -> tuple[str, str]:
    head, sep, rest = fato.partition(". ")
    return (head.rstrip("."), rest.rstrip(".") if sep else "")


def _ordem(a: dict[str, Any]) -> tuple:
    tema = a["tema"]
    pos = ORDEM_TEMA.index(tema) if tema in ORDEM_TEMA else len(ORDEM_TEMA)
    return (pos, tema, a.get("escopo") or "", a["id"])


def item_text(n: int, a: dict[str, Any]) -> str:
    titulo, fato = _titulo_e_fato(a["fato"])
    crit = a.get("criterio_adotado")
    base = f"{titulo} — {citacao(a)}"
    if crit:
        base += f" (critério adotado: {crit['decisao'].rstrip('.')})"
    corpo = f"{fato}." if fato else ""
    pede = a.get("saneamento") or ""
    if pede and not pede.lower().startswith("solicita-se"):
        pede = "Solicita-se " + pede[0].lower() + pede[1:]
    return " ".join(p for p in (f"{n}. {base}:", corpo, pede) if p).strip()


def rascunho(matriz: dict[str, Any], processo: str = "") -> tuple[str, str]:
    achados = sorted(matriz["achados"], key=_ordem)
    itens = []
    nota = ["| Item | Achado da matriz | Citação | Destino |", "| --- | --- | --- | --- |"]
    for a in achados:
        entra, motivo = entra_no_bilhete(a)
        if entra:
            itens.append(item_text(len(itens) + 1, a))
            nota.append(f"| {len(itens)} | {a['id']} | {citacao(a)} | bilhete ({motivo}) |")
        else:
            nota.append(f"| — | {a['id']} | {citacao(a)} | fora do bilhete: {motivo} |")
    cab = [f"Processo {processo}".strip(), ""] if processo else []
    fecho = ["", "A presente análise restringe-se aos elementos apresentados. A reapresentação "
             "será integralmente reanalisada, podendo ser formuladas novas exigências caso as "
             "correções alterem o projeto ou revelem condição não declarada."]
    texto = "\n".join([*cab, *itens, *fecho]) + "\n"
    nota_md = "\n".join(["# Nota de rastreabilidade (interna, não enviar)", "",
                         f"> {matriz.get('aviso', '')}", "", *nota]) + "\n"
    return texto, nota_md


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("matriz", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--nota", type=Path)
    ap.add_argument("--processo", default="")
    args = ap.parse_args(argv)
    matriz = json.loads(args.matriz.read_text(encoding="utf-8"))
    texto, nota = rascunho(matriz, args.processo)
    args.out.write_text(texto, encoding="utf-8")
    if args.nota:
        args.nota.write_text(nota, encoding="utf-8")
    print(f"rascunho: {texto.count(chr(10))} linha(s); revisar a redação, depois "
          "conferir_citacoes.py e contar_bilhete.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
