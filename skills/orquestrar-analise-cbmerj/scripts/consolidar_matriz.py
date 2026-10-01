#!/usr/bin/env python3
"""Consolida achados de várias fontes (motor e skills) numa matriz única, sem tradução.

    python3 scripts/consolidar_matriz.py motor.json le.json --out matriz.json --md matriz.md

Cada arquivo é uma lista de achados no contrato ``achado.schema.json`` (ou um objeto com a
chave ``achados``, como a saída de ``analisar_planta`` e de ``v2-findings --out``). Regras:

- todo achado é validado contra o esquema (``jsonschema`` se houver; senão uma conferência
  mínima dos campos, enums e da regra "conforme exige evidência suficiente e item
  localizado"); achado inválido **impede** a matriz;
- os achados entram **como vieram**: nenhum status é recalculado, fundido ou traduzido;
- achados equivalentes (mesmo check e escopo; ou mesmo documento, item e escopo) formam um
  grupo que preserva todos os ids e origens; status diferentes dentro do grupo marcam o grupo
  como ``divergente`` (vai para o analista, nunca é resolvido em silêncio);
- mesmo ``id`` com conteúdo diferente é erro.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
MATRIZ_SCHEMA = "matriz-achados/1.0"
ORDEM_TIPO = ["NON_COMPLIANT", "DIVERGENCE", "DOCUMENT_MISSING", "DOCUMENT_INCOMPLETE",
              "DATA_MISSING", "NOT_VERIFIABLE", "ANALYST_REVIEW", "NO_PENDING_ISSUE"]
ORDEM_SEVERIDADE = ["CRITICAL", "MAJOR", "MINOR", "INFORMATIONAL"]
RESULTADO = {"COMPLIANT": "conforme", "NON_COMPLIANT": "não conforme",
             "NOT_APPLICABLE": "não aplicável", "UNDETERMINED": "pendente"}


class MatrizError(ValueError):
    pass


def schema_path() -> Path:
    for cand in (HERE.parent / "references" / "achado.schema.json",
                 HERE.parent.parent / "_comum" / "achado.schema.json"):
        if cand.is_file():
            return cand
    raise MatrizError("achado.schema.json não encontrado (references/ ou skills/_comum/)")


def load_schema() -> dict[str, Any]:
    return json.loads(schema_path().read_text(encoding="utf-8"))


def _minimal_errors(a: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errs = [f"falta {k}" for k in schema["required"] if k not in a]
    props = schema["properties"]
    errs += [f"campo desconhecido {k}" for k in a if k not in props]
    for k, spec in props.items():
        if k in a and "enum" in spec and a[k] not in spec["enum"]:
            errs.append(f"{k}={a[k]!r} fora de {spec['enum']}")
    regra = a.get("regra") or {}
    if not isinstance(regra, dict) or not regra.get("documento") or not regra.get("item"):
        errs.append("regra exige documento e item")
    if a.get("compliance_status") == "COMPLIANT" and (
            a.get("evidence_status") != "SUFFICIENT" or regra.get("item") == "[A CONFERIR]"):
        errs.append("conforme exige evidência suficiente e item localizado")
    return errs


def validate(a: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    try:
        import jsonschema
    except ImportError:
        return _minimal_errors(a, schema)
    validator = jsonschema.Draft202012Validator(schema)
    return [f"{'/'.join(map(str, e.path)) or '(raiz)'}: {e.message}"
            for e in validator.iter_errors(a)]


def read_achados(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("achados")
    if not isinstance(data, list):
        raise MatrizError(f"{path.name}: esperado uma lista de achados ou a chave 'achados'")
    return data


def _group_key(a: dict[str, Any]) -> tuple[str, ...]:
    escopo = a.get("escopo") or ""
    if a.get("check_id"):
        return ("check", a["check_id"], escopo)
    r = a["regra"]
    return ("regra", r["documento"], r["item"], escopo)


def consolidate(sources: list[tuple[str, list[dict[str, Any]]]]) -> dict[str, Any]:
    schema = load_schema()
    by_id: dict[str, dict[str, Any]] = {}
    origin: dict[str, list[str]] = {}
    errors = []
    for name, achados in sources:
        for a in achados:
            problems = validate(a, schema)
            if problems:
                errors.append(f"{name}: {a.get('id', '?')}: " + "; ".join(problems))
                continue
            if a["id"] in by_id and by_id[a["id"]] != a:
                errors.append(f"{name}: id {a['id']} repetido com conteúdo diferente")
                continue
            by_id.setdefault(a["id"], a)
            origin.setdefault(a["id"], []).append(name)
    if errors:
        raise MatrizError("achados fora do contrato:\n- " + "\n- ".join(errors))

    def order(a: dict[str, Any]) -> tuple:
        return (ORDEM_TIPO.index(a["tipo"]), ORDEM_SEVERIDADE.index(a["severidade"]),
                a["tema"], a.get("escopo") or "", a["id"])

    achados = sorted(by_id.values(), key=order)
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for a in achados:
        groups.setdefault(_group_key(a), []).append(a)
    grupos = []
    for key, items in groups.items():
        if len(items) < 2:
            continue
        status = sorted({a["compliance_status"] for a in items})
        grupos.append({"chave": list(key), "ids": [a["id"] for a in items],
                       "origens": sorted({a["origem"] for a in items}),
                       "compliance_status": status, "divergente": len(status) > 1})
    resumo: dict[str, int] = {}
    for a in achados:
        resumo[a["compliance_status"]] = resumo.get(a["compliance_status"], 0) + 1
    return {
        "schema_version": MATRIZ_SCHEMA,
        "aviso": "RASCUNHO sem valor normativo até a homologação das regras e dos checks.",
        "fontes": [{"arquivo": n, "achados": len(a)} for n, a in sources],
        "achados": achados,
        "grupos": grupos,
        "bloqueios": [a["id"] for a in achados
                      if a.get("bloqueante") or (a["review_status"] == "PENDING"
                                                 and a["compliance_status"] == "UNDETERMINED")],
        "resumo": dict(sorted(resumo.items())),
        "arquivos_por_achado": {k: v for k, v in sorted(origin.items())},
    }


def _regra_txt(r: dict[str, Any]) -> str:
    ed = f" ({r['edicao']})" if r.get("edicao") else ""
    return f"{r['documento']}{ed}, {r['item']}"


def _cell(text: Any) -> str:
    return str(text if text is not None else "").replace("|", "/").replace("\n", " ")


def to_markdown(m: dict[str, Any]) -> str:
    lines = ["# Matriz consolidada de achados", "", f"> {m['aviso']}", "",
             "Resumo: " + ", ".join(f"{RESULTADO.get(k, k)} = {v}"
                                     for k, v in m["resumo"].items()), "",
             "| ID | Tema | Escopo | Fato | Regra | Evidência | Resultado | Severidade | "
             "Origem | Saneamento |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for a in m["achados"]:
        ev = "; ".join(f"{e['fonte_tipo']} {e.get('documento', '')} {e.get('localizador', '')}"
                       .strip() for e in a.get("evidencias", []))
        crit = a.get("criterio_adotado")
        regra = _regra_txt(a["regra"]) + (f" — critério adotado: {crit['decisao']}"
                                          if crit else "")
        res = f"{RESULTADO[a['compliance_status']]} ({a['evidence_status']}, " \
              f"{a['review_status']})"
        lines.append("| " + " | ".join(_cell(v) for v in (
            a["id"], a["tema"], a.get("escopo"), a["fato"], regra, ev, res, a["severidade"],
            a["origem"], a.get("saneamento"))) + " |")
    if m["grupos"]:
        lines += ["", "## Achados equivalentes (fontes preservadas)", ""]
        for g in m["grupos"]:
            flag = " **divergente: decidir**" if g["divergente"] else ""
            lines.append(f"- {', '.join(g['ids'])} ({', '.join(g['origens'])}){flag}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("arquivos", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--md", type=Path)
    args = ap.parse_args(argv)
    try:
        matriz = consolidate([(p.name, read_achados(p)) for p in args.arquivos])
    except MatrizError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    args.out.write_text(json.dumps(matriz, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    if args.md:
        args.md.write_text(to_markdown(matriz), encoding="utf-8")
    print(f"matriz: {len(matriz['achados'])} achado(s), {len(matriz['grupos'])} grupo(s) "
          f"equivalente(s), {len(matriz['bloqueios'])} bloqueio(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
