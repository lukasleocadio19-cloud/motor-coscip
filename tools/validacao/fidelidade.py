"""Validação de fidelidade (plano de correção, F9): métricas contra o gabarito do analista.

O corpus-gabarito fica **fora do repositório** (dados reais nunca entram aqui). Cada
processo é uma pasta com um código anonimizado escolhido pelo usuário:

    <corpus>/P01/gabarito.yaml        # o que o analista de fato exigiu / contou / mediu
    <corpus>/P01/sistema/matriz.json  # consolidar_matriz.py (opcional)
    <corpus>/P01/sistema/bilhete.txt  # bilhete do sistema (opcional)
    <corpus>/P01/sistema/simbolos.json  # listar_simbolos do MCP (opcional)
    <corpus>/P01/sistema/analise.json   # analisar_planta do MCP (opcional)

``gabarito.yaml``::

    processo: P01
    exigencias:            # itens do bilhete efetivamente emitido
      - {documento: NT 2-01, item: "5.2.5", tema: Extintores}
    simbolos:              # rotulados à mão (metros, coordenada da planta confirmada)
      - {classe: EXTINTOR, x: 5.0, y: 3.2}
    medidas:               # distâncias conferidas à mão no CAD
      - {pavimento: Térreo, sistema: extinguisher, valor_m: 12.4, tolerancia_m: 0.1}

O relatório (``docs/validacao/AAAA-MM-DD.md``) só leva números e os códigos anonimizados.
A parte sintética (respostas analíticas do F7 e o processo fictício do F8) roda sem corpus.

    python -m tools.validacao.fidelidade --sintetico --out docs/validacao/2026-09-29.md
    python -m tools.validacao.fidelidade --corpus D:/coscip-gabarito --sintetico --out ...
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import sys
import tempfile
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
SYMBOL_TOL_M = 0.5  # símbolo rotulado e detectado a até 0,5 m = o mesmo objeto
SAFETY_CLASSES = ("EXTINTOR", "HIDRANTE", "ACIONADOR", "SAIDA", "ILUMINACAO", "SINALIZACAO",
                  "DETECTOR", "SPRINKLER")


def _script(rel: str) -> Any:
    path = ROOT / "skills" / rel
    spec = importlib.util.spec_from_file_location(f"_f9_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text))
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).upper().split())


def exigencia_key(documento: str, item: str) -> tuple[str, str]:
    item = re.sub(r"^(ITEM|ITENS)\s+", "", _fold(item))
    return _fold(documento), item


# ------------------------------------------------------------------ exigências e citações

def exigencias_do_sistema(matriz: dict[str, Any]) -> list[dict[str, str]]:
    """O que o sistema levaria ao bilhete (mesma seleção do ``rascunho_bilhete.py``)."""
    rascunho = _script("emitir-bilhete-cbmerj/scripts/rascunho_bilhete.py")
    return [{"id": a["id"], "documento": a["regra"]["documento"], "item": a["regra"]["item"]}
            for a in matriz["achados"] if rascunho.entra_no_bilhete(a)[0]]


def exigencias_metrics(gabarito: list[dict[str, Any]],
                       sistema: list[dict[str, Any]]) -> dict[str, Any]:
    """Casamento por (documento, item), contando repetições (multiconjunto)."""
    want = Counter(exigencia_key(e["documento"], e["item"]) for e in gabarito)
    got = Counter(exigencia_key(e["documento"], e["item"]) for e in sistema)
    hit = want & got
    tp, fn, fp = sum(hit.values()), sum((want - got).values()), sum((got - want).values())
    return {"acertadas": tp, "faltantes": fn, "indevidas": fp,
            "precisao": tp / (tp + fp) if tp + fp else None,
            "revocacao": tp / (tp + fn) if tp + fn else None,
            "faltantes_lista": sorted(" ".join(k) for k in (want - got).elements()),
            "indevidas_lista": sorted(" ".join(k) for k in (got - want).elements())}


def citacoes_metrics(bilhete: str) -> dict[str, Any]:
    rows = _script("emitir-bilhete-cbmerj/scripts/conferir_citacoes.py").check(bilhete)
    ok = sum(r["ok"] for r in rows)
    return {"total": len(rows), "corretas": ok,
            "taxa": ok / len(rows) if rows else None,
            "problemas": [f"{r['citacao']}: {r['problema']}" for r in rows if not r["ok"]]}


# ------------------------------------------------------------------ símbolos

def simbolos_metrics(rotulos: list[dict[str, Any]], detectados: list[dict[str, Any]],
                     tol_m: float = SYMBOL_TOL_M) -> dict[str, Any]:
    """Precisão e revocação por classe; casamento guloso pelo mais próximo, 1 para 1."""
    out: dict[str, Any] = {}
    classes = sorted({r["classe"] for r in rotulos} | {d["classe"] for d in detectados})
    for cls in classes:
        want = [r for r in rotulos if r["classe"] == cls]
        got = [d for d in detectados if d["classe"] == cls]
        pairs = sorted((math.dist((w["x"], w["y"]), (g["x"], g["y"])), i, j)
                       for i, w in enumerate(want) for j, g in enumerate(got))
        used_w: set[int] = set()
        used_g: set[int] = set()
        for d, i, j in pairs:
            if d > tol_m:
                break
            if i not in used_w and j not in used_g:
                used_w.add(i)
                used_g.add(j)
        tp = len(used_w)
        out[cls] = {"rotulados": len(want), "detectados": len(got), "casados": tp,
                    "precisao": tp / len(got) if got else None,
                    "revocacao": tp / len(want) if want else None}
    return out


# ------------------------------------------------------------------ distâncias

def distancias_metrics(manuais: list[dict[str, Any]],
                       analise: dict[str, Any]) -> list[dict[str, Any]]:
    by_floor = {p["pavimento"]: p for p in analise.get("pavimentos", [])}
    out = []
    for m in manuais:
        motor = ((by_floor.get(m["pavimento"]) or {}).get("maior_percurso_m") or {}).get(
            m["sistema"])
        row = {"pavimento": m["pavimento"], "sistema": m["sistema"], "manual_m": m["valor_m"],
               "motor_m": None, "erro_m": None, "incerteza_m": None, "dentro": None}
        if motor and motor.get("valor") is not None:
            err = motor["valor"] - m["valor_m"]
            unc = (motor.get("incerteza") or 0) + (m.get("tolerancia_m") or 0)
            row.update(motor_m=motor["valor"], erro_m=round(err, 3),
                       incerteza_m=motor.get("incerteza"), dentro=abs(err) <= unc)
        out.append(row)
    return out


# ------------------------------------------------------------------ corpus

def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def processo(folder: Path) -> dict[str, Any]:
    gab = yaml.safe_load((folder / "gabarito.yaml").read_text(encoding="utf-8")) or {}
    sis = folder / "sistema"
    out: dict[str, Any] = {"processo": str(gab.get("processo") or folder.name)}
    matriz = _json(sis / "matriz.json")
    if matriz is not None and gab.get("exigencias") is not None:
        out["exigencias"] = exigencias_metrics(gab["exigencias"],
                                               exigencias_do_sistema(matriz))
    if (sis / "bilhete.txt").is_file():
        out["citacoes"] = citacoes_metrics((sis / "bilhete.txt").read_text(encoding="utf-8"))
    simb = _json(sis / "simbolos.json")
    if simb is not None and gab.get("simbolos"):
        out["simbolos"] = simbolos_metrics(gab["simbolos"],
                                           simb.get("simbolos", simb) if isinstance(simb, dict)
                                           else simb)
    analise = _json(sis / "analise.json")
    if analise is not None and gab.get("medidas"):
        out["distancias"] = distancias_metrics(gab["medidas"], analise)
    return out


def corpus(folder: Path) -> list[dict[str, Any]]:
    return [processo(p) for p in sorted(folder.iterdir())
            if p.is_dir() and (p / "gabarito.yaml").is_file()]


# ------------------------------------------------------------------ parte sintética

def sintetico() -> dict[str, Any]:
    """Respostas analíticas do F7 e o processo fictício do F8 (reprodutível, sem corpus)."""
    from coscip_analysis import AnalysisInput, RuleBinding, parse_dictionary, run
    from coscip_cad.synthetic import ANALYTIC, make_analytic
    from coscip_normative.package import load_package

    pkg = load_package(ROOT / "normative" / "base")
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for kind in ANALYTIC:
            path, exact, _ = make_analytic(Path(tmp) / f"{kind}.dxf", kind)
            (region,) = run(AnalysisInput(
                dxf=path, scale_to_m=1.0, dictionary=parse_dictionary(pkg.symbols),
                rules=[RuleBinding(r) for r in pkg.rules],
                context={"risk_class": "PEQUENO", "unifamiliar": False},
                floors=[{"id": "f", "name": "P", "clip": {"x0": -1, "y0": -1, "x1": 25,
                                                           "y1": 20}}]))["regions"]
            cov = region["coverage"]["extinguisher"]
            rows.append({"planta": kind, "exato_m": round(exact, 3),
                         "vetorial_m": cov["max_travel_m"],
                         "erro_m": round(cov["max_travel_m"] - exact, 3),
                         "incerteza_m": cov["uncertainty_m"],
                         "fmm_m": cov["methods"]["fmm"]["value_m"],
                         "grade_m": cov["methods"]["grid"]["value_m"],
                         "grade_incerteza_m": cov["methods"]["grid"]["uncertainty_m"],
                         "consistente": cov["consistent"]})
    return {"distancias_analiticas": rows}


# ------------------------------------------------------------------ relatório

def _pct(v: float | None) -> str:
    return "—" if v is None else f"{100 * v:.1f} %".replace(".", ",")


def _m(v: float | None) -> str:
    return "—" if v is None else f"{v:.3f}".replace(".", ",")


def relatorio(dia: str, processos: list[dict[str, Any]] | None,
              sint: dict[str, Any] | None, estado_catalogo: dict[str, int]) -> str:
    L = [f"# Validação de fidelidade — {dia}", "",
         "Plano de correção, F9. Gerado por `python -m tools.validacao.fidelidade`; não editar "
         "os números à mão. **Nenhum resultado tem valor normativo** e nenhum check ou regra "
         "sai de rascunho sem homologação por responsável técnico (REG-05/06).", "",
         "## Estado de publicação", "",
         "| Estado | Checks e regras |", "| --- | --- |"]
    L += [f"| {k} | {v} |" for k, v in sorted(estado_catalogo.items())]
    L += ["", "## Corpus-gabarito (processos reais anonimizados)", ""]
    if not processos:
        L += ["**Não medido.** O corpus-gabarito (5–10 processos reais com o bilhete emitido "
              "pelo analista, 3 plantas com símbolos rotulados à mão e 10 medidas conferidas "
              "no CAD) depende do usuário e fica fora do repositório. Formato em "
              "`tools/validacao/fidelidade.py`."]
    else:
        L += ["| Processo | Acertadas | Faltantes | Indevidas | Precisão | Revocação | "
              "Citações corretas |", "| --- | --- | --- | --- | --- | --- | --- |"]
        for p in processos:
            e, c = p.get("exigencias") or {}, p.get("citacoes") or {}
            L.append(f"| {p['processo']} | {e.get('acertadas', '—')} | "
                     f"{e.get('faltantes', '—')} | {e.get('indevidas', '—')} | "
                     f"{_pct(e.get('precisao'))} | {_pct(e.get('revocacao'))} | "
                     f"{c.get('corretas', '—')}/{c.get('total', '—')} |")
        simb = [(p["processo"], cls, r) for p in processos
                for cls, r in (p.get("simbolos") or {}).items()]
        if simb:
            L += ["", "### Reconhecimento de símbolos (meta: revocação 100 % nas classes de "
                  "segurança)", "", "| Processo | Classe | Rotulados | Detectados | Precisão | "
                  "Revocação |", "| --- | --- | --- | --- | --- | --- |"]
            L += [f"| {p} | {cls} | {r['rotulados']} | {r['detectados']} | "
                  f"{_pct(r['precisao'])} | {_pct(r['revocacao'])} |" for p, cls, r in simb]
        dist = [(p["processo"], r) for p in processos for r in p.get("distancias") or []]
        if dist:
            L += ["", "### Distâncias conferidas à mão", "",
                  "| Processo | Pavimento | Sistema | Manual (m) | Motor (m) | Erro (m) | "
                  "Incerteza (m) | Dentro |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
            L += [f"| {p} | {r['pavimento']} | {r['sistema']} | {_m(r['manual_m'])} | "
                  f"{_m(r['motor_m'])} | {_m(r['erro_m'])} | {_m(r['incerteza_m'])} | "
                  f"{'sim' if r['dentro'] else 'não' if r['dentro'] is False else '—'} |"
                  for p, r in dist]
    if sint:
        L += ["", "## Referência sintética (reprodutível)", "",
              "Plantas com resposta analítica conhecida (F7). O método vetorial é o principal; "
              "FMM e grade são conferência.", "",
              "| Planta | Exato (m) | Vetorial (m) | Erro (m) | Incerteza (m) | FMM (m) | "
              "Grade (m) | Grade ± (m) | Métodos concordam |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        L += [f"| {r['planta']} | {_m(r['exato_m'])} | {_m(r['vetorial_m'])} | "
              f"{_m(r['erro_m'])} | {_m(r['incerteza_m'])} | {_m(r['fmm_m'])} | "
              f"{_m(r['grade_m'])} | {_m(r['grade_incerteza_m'])} | "
              f"{'sim' if r['consistente'] else 'não'} |" for r in sint["distancias_analiticas"]]
        L += ["", "Processo fictício de ponta a ponta (DXF + memorial, F8): "
              "`tests/integration/test_processo_sintetico_f8.py` (matriz única com motor e "
              "skill; bilhete com todas as citações localizadas no índice)."]
    L += ["", "## Pendências para homologar", "",
          "1. Corpus-gabarito e medidas reais (usuário).",
          "2. Responsável técnico revisa checks e regras; cada homologação registra "
          "responsável, registro (CREA/CAU), data e o relatório de validação que a sustenta "
          "(`homologation` no check/regra; sem ela o carregamento recusa `HOMOLOGATED`/"
          "`PUBLISHED`)."]
    return "\n".join(L) + "\n"


def estado_publicacao() -> dict[str, int]:
    from coscip_normative.package import load_package
    from coscip_normative.verification import load_catalog

    states = Counter(c.publication_state for c in
                     load_catalog(ROOT / "normative" / "checks").checks)
    states.update(r.publication_state for r in load_package(ROOT / "normative" / "base").rules)
    return dict(states)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validação de fidelidade (F9)")
    ap.add_argument("--corpus", type=Path, help="pasta do corpus-gabarito (fora do repo)")
    ap.add_argument("--sintetico", action="store_true")
    ap.add_argument("--data", default=date.today().isoformat())
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    if args.corpus and ROOT in args.corpus.resolve().parents:
        print("o corpus-gabarito fica fora do repositório (dados reais)", file=sys.stderr)
        return 1
    procs = corpus(args.corpus) if args.corpus else None
    text = relatorio(args.data, procs, sintetico() if args.sintetico else None,
                     estado_publicacao())
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"ok: {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
