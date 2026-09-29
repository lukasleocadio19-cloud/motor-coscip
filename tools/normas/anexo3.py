"""Anexo III do Decreto 42/2018, Tabelas 5 a 21, como dado do pacote (plano de correção, F4.3).

Gera ``normative/base/sistemas-exigidos-5-21.yaml`` a partir das tabelas conferidas em
``normative/tabelas/decreto-42-2018/`` (leitura visual × camada de texto, estado calculado).
Só entra tabela com estado ``verificada``; a linha de cada medida é a leitura visual.
O pacote confere de novo cada linha contra o texto ingerido (``verify_height_tables``).

    python -m tools.normas.anexo3            # grava
    python -m tools.normas.anexo3 --conferir # sai 1 se desatualizado
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from typing import Any

import yaml

from tools.normas import tabelas

ROOT = tabelas.ROOT
OUT = ROOT / "normative" / "base" / "sistemas-exigidos-5-21.yaml"
FOLDER = tabelas.TABELAS / "decreto-42-2018"
URL = "https://www.cbmerj.rj.gov.br/wp-content/uploads/2024/05/COSCIP_DEC_42-2018_COMPILADO.pdf"

MEASURES = {
    "Extintores": "extinguishers", "Hidrantes e mangotinhos": "hydrants",
    "Chuveiros automáticos": "sprinklers", "Sinalização de segurança": "signage",
    "Iluminação de Emergência": "lighting", "Alarme de Incêndio": "alarm",
    "Detecção de Incêndio": "detection", "Saídas de Emergência": "exits",
    "Plano de emergência": "emergency_plan", "Controle de fumaça": "smoke_control",
    "Hidrante urbano": "urban_hydrant", "Acesso de viatura em edificações": "vehicle_access",
    "Compartimentação Vertical": "vertical_compartmentation",
    "Segurança Estrutural contra Incêndio": "structural_safety",
    "Controle de Materiais de Acabamento": "finishing_materials", "SPDA": "spda",
    "Sistema de espuma": "foam",
    "Pressurização de escada de emergência, elevador de emergência, antecâmaras e áreas de "
    "refúgio": "stair_pressurization",
}


def _measure(label: str) -> tuple[str, str, str | None]:
    """Rótulo com nota colada ("Extintores11", "Chuveiros automáticos 11")."""
    m = re.fullmatch(r"(.*?)\s*(\d{1,2})?", label.strip())
    base, note = m.group(1).strip(), m.group(2)
    if base not in MEASURES:
        raise ValueError(f"medida desconhecida no Anexo III: {label!r}")
    return MEASURES[base], base, note


def build() -> dict[str, Any]:
    tables = []
    for f in sorted(FOLDER.glob("tabela-*.yaml")):
        data = tabelas.load(f)
        if data["estado"] != "verificada":
            continue
        cols = [c for b in data["anexo3"]["blocos"] for c in b["colunas"]]
        measures = []
        for row in data["caminhos"]["visual"]["linhas"]:
            mid, label, note = _measure(row[0])
            if len(row) - 1 != len(cols):
                raise ValueError(f"{f.name}: {label} com {len(row) - 1} células")
            measures.append({"id": mid, "label": label, "label_note": note,
                             "source_label": row[0], "cells": row[1:]})
        tables.append({
            "table": data["anexo3"]["tabela"], "page": data["pagina"], "title": data["titulo"],
            "blocks": data["anexo3"]["blocos"], "measures": measures,
            "verification": {"state": data["estado"],
                             "paths": data["resultado"]["caminhos_comparados"],
                             "file": f"normative/tabelas/decreto-42-2018/{f.name}",
                             "file_sha256": hashlib.sha256(f.read_bytes()).hexdigest()},
        })
    return {
        "schema_version": "requirements-height/1.0",
        "source": {"document": "Decreto 42/2018", "item": "Anexo III, Tabelas 5 a 21",
                   "pdf_sha256": tables and tabelas.load(
                       FOLDER / "tabela-05.yaml")["fonte_pdf_sha256"] or None,
                   "url": URL},
        "note": ("Gerado por tools/normas/anexo3.py das tabelas conferidas (não editar). "
                 "Consulta indicativa, em rascunho: célula com nota (X1, X2…) é condicional e "
                 "traço não é dispensa global."),
        "tables": tables,
    }


def dump(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Anexo III, Tabelas 5 a 21 (F4.3)")
    ap.add_argument("--conferir", action="store_true")
    args = ap.parse_args(argv)
    text = dump(build())
    if args.conferir:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print("ok" if ok else "desatualizado: python -m tools.normas.anexo3")
        return 0 if ok else 1
    OUT.write_bytes(text.encode("utf-8"))
    print(f"ok: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
