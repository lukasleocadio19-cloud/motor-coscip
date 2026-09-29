#!/usr/bin/env python3
"""Gera manifesto técnico inicial sem modificar os arquivos do processo."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pypdf import PdfReader

DWG_VERSOES = {
    b"AC1015": "AutoCAD 2000",
    b"AC1018": "AutoCAD 2004",
    b"AC1021": "AutoCAD 2007",
    b"AC1024": "AutoCAD 2010",
    b"AC1027": "AutoCAD 2013",
    b"AC1032": "AutoCAD 2018",
}


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as stream:
        for bloco in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def pdf_info(caminho: Path) -> dict:
    reader = PdfReader(str(caminho))
    campos = reader.get_fields() or {}
    assinaturas = [
        nome
        for nome, campo in campos.items()
        if str(campo.get("/FT", "")) == "/Sig"
    ]
    return {
        "paginas": len(reader.pages),
        "criptografado": bool(reader.is_encrypted),
        "campos_assinatura_pdf": assinaturas,
    }


def dwg_info(caminho: Path) -> dict:
    assinatura = caminho.read_bytes()[:6]
    return {
        "assinatura": assinatura.decode("ascii", errors="replace"),
        "versao_declarada": DWG_VERSOES.get(assinatura, "desconhecida"),
        "analise_geometrica": "não executada por este inventário",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("diretorio", type=Path)
    parser.add_argument("--saida", type=Path)
    args = parser.parse_args()

    itens = []
    for caminho in sorted(p for p in args.diretorio.iterdir() if p.is_file()):
        item = {
            "arquivo": caminho.name,
            "extensao": caminho.suffix.lower(),
            "tamanho_bytes": caminho.stat().st_size,
            "sha256": sha256(caminho),
        }
        try:
            if caminho.suffix.lower() == ".pdf":
                item.update(pdf_info(caminho))
            elif caminho.suffix.lower() == ".dwg":
                item.update(dwg_info(caminho))
        except Exception as erro:
            item["erro_leitura"] = str(erro)
        itens.append(item)

    texto = json.dumps({"arquivos": itens}, ensure_ascii=False, indent=2)
    if args.saida:
        args.saida.write_text(texto + "\n", encoding="utf-8")
    else:
        print(texto)


if __name__ == "__main__":
    main()
