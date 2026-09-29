#!/usr/bin/env python3
"""Gera manifesto técnico inicial sem modificar os arquivos do processo.

Percorre o diretório **e todas as subpastas** (processos chegam organizados em pastas por ato
ou por disciplina). Para cada arquivo: caminho relativo, tamanho e SHA-256; PDF: páginas,
criptografia e campos de assinatura (se ``pypdf`` estiver instalado); DWG/DXF: só a
identificação do formato — a **leitura real da planta** (camadas, símbolos, medidas) é feita
pelo MCP ``coscip-plantas`` (``abrir_planta``), nunca por este inventário.

    python3 scripts/inventariar_dossie.py <pasta-do-processo> [--saida manifesto.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

DWG_VERSOES = {
    b"AC1015": "AutoCAD 2000",
    b"AC1018": "AutoCAD 2004",
    b"AC1021": "AutoCAD 2007",
    b"AC1024": "AutoCAD 2010",
    b"AC1027": "AutoCAD 2013",
    b"AC1032": "AutoCAD 2018",
}
LEITURA_PLANTA = ("não executada por este inventário: abrir no MCP coscip-plantas "
                  "(abrir_planta → confirmar_unidade → definir_pavimentos → analisar_planta)")


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as stream:
        for bloco in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def pdf_info(caminho: Path) -> dict:
    try:
        from pypdf import PdfReader
    except ImportError:
        return {"pdf": "pypdf não instalado: páginas e assinaturas não conferidas"}
    reader = PdfReader(str(caminho))
    campos = reader.get_fields() or {}
    assinaturas = [nome for nome, campo in campos.items() if str(campo.get("/FT", "")) == "/Sig"]
    return {
        "paginas": len(reader.pages),
        "criptografado": bool(reader.is_encrypted),
        "campos_assinatura_pdf": assinaturas,
    }


def dwg_info(caminho: Path) -> dict:
    with caminho.open("rb") as stream:
        assinatura = stream.read(6)
    return {
        "assinatura": assinatura.decode("ascii", errors="replace"),
        "versao_declarada": DWG_VERSOES.get(assinatura, "desconhecida"),
        "analise_geometrica": LEITURA_PLANTA,
    }


def dxf_info(_caminho: Path) -> dict:
    return {"analise_geometrica": LEITURA_PLANTA}


def inventariar(diretorio: Path) -> list[dict]:
    itens = []
    arquivos = sorted(p for p in diretorio.rglob("*")
                      if p.is_file() and not any(part.startswith(".")
                                                 for part in p.relative_to(diretorio).parts))
    for caminho in arquivos:
        ext = caminho.suffix.lower()
        item = {
            "arquivo": caminho.relative_to(diretorio).as_posix(),
            "pasta": caminho.parent.relative_to(diretorio).as_posix(),
            "extensao": ext,
            "tamanho_bytes": caminho.stat().st_size,
            "sha256": sha256(caminho),
        }
        try:
            if ext == ".pdf":
                item.update(pdf_info(caminho))
            elif ext == ".dwg":
                item.update(dwg_info(caminho))
            elif ext == ".dxf":
                item.update(dxf_info(caminho))
        except Exception as erro:  # noqa: BLE001 — registra e segue
            item["erro_leitura"] = str(erro)
        itens.append(item)
    return itens


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("diretorio", type=Path)
    parser.add_argument("--saida", type=Path)
    args = parser.parse_args()
    texto = json.dumps({"arquivos": inventariar(args.diretorio)}, ensure_ascii=False, indent=2)
    if args.saida:
        args.saida.write_text(texto + "\n", encoding="utf-8")
    else:
        print(texto)


if __name__ == "__main__":
    main()
