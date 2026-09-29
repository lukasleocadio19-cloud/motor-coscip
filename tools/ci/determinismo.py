"""Mesma entrada ⇒ mesma saída da análise, byte a byte, em Windows e Linux (plano, F7.4).

Gera as plantas sintéticas (``make_fire_plan`` e as analíticas do F7) com metadados fixos e
fim de linha ``\\n``, roda o motor e calcula o SHA-256 do JSON canônico da saída (chaves
ordenadas; só ``duration_s`` sai, porque é tempo de relógio). A CI roda nos dois sistemas e
compara os hashes.

    python -m tools.ci.determinismo --out hashes.json
    python -m tools.ci.determinismo --comparar linux.json windows.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
VOLATILE = frozenset({"duration_s"})
FLOORS = {
    "fire_plan": [{"id": "floor-0001", "name": "Térreo",
                   "clip": {"x0": -1, "y0": -1, "x1": 31, "y1": 13}}],
    "analytic": [{"id": "floor-0001", "name": "Pavimento",
                  "clip": {"x0": -1, "y0": -1, "x1": 25, "y1": 20}}],
}


def canonical(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): canonical(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, list | tuple):
        return [canonical(v) for v in obj]
    return obj


def digest(obj: Any) -> str:
    text = json.dumps(canonical(obj), sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fixed_newlines(path: Path) -> Path:
    """No Windows o ezdxf grava em modo texto (CRLF): a entrada precisa ser a mesma."""
    text = path.read_text(encoding="utf-8")
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    return path


def drawings(folder: Path) -> list[tuple[str, Path, str]]:
    import ezdxf

    from coscip_cad.synthetic import ANALYTIC, make_analytic, make_fire_plan

    ezdxf.options.write_fixed_meta_data_for_testing = True
    out = [("fire_plan", _fixed_newlines(make_fire_plan(folder / "fire_plan.dxf")),
            "fire_plan")]
    for kind in ANALYTIC:
        path, _, _ = make_analytic(folder / f"{kind}.dxf", kind)
        out.append((kind, _fixed_newlines(path), "analytic"))
    return out


def analyze(path: Path, floors: list[dict[str, Any]]) -> dict[str, Any]:
    from coscip_analysis import AnalysisInput, RuleBinding, parse_dictionary, run
    from coscip_normative.package import load_package

    pkg = load_package(ROOT / "normative" / "base")
    return run(AnalysisInput(
        dxf=path, scale_to_m=1.0, dictionary=parse_dictionary(pkg.symbols),
        rules=[RuleBinding(r) for r in pkg.rules],
        context={"risk_class": "PEQUENO", "unifamiliar": False, "building_area_m2": 360},
        floors=floors))


def hashes() -> dict[str, dict[str, str]]:
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, path, floors in drawings(Path(tmp)):
            result = analyze(path, FLOORS[floors])
            out[name] = {"dxf_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "analysis_sha256": digest(result)}
    return out


def compare(files: list[Path]) -> int:
    loaded = {f.name: json.loads(f.read_text(encoding="utf-8")) for f in files}
    names = sorted({k for v in loaded.values() for k in v})
    bad = 0
    for name in names:
        seen = {f: (v.get(name) or {}) for f, v in loaded.items()}
        for key in ("dxf_sha256", "analysis_sha256"):
            values = {f: s.get(key) for f, s in seen.items()}
            if len(set(values.values())) != 1:
                bad += 1
                print(f"DIVERGE {name} {key}: {values}")
    print("ok: saídas idênticas" if not bad else f"{bad} divergência(s)")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Determinismo da análise (F7.4)")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--comparar", nargs="+", type=Path)
    args = ap.parse_args(argv)
    if args.comparar:
        return compare(args.comparar)
    result = hashes()
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
