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
import base64
import difflib
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zlib
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


def canonical_text(obj: Any) -> str:
    return json.dumps(canonical(obj), sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical_text(obj).encode("utf-8")).hexdigest()


def _pack(data: bytes) -> str:
    return base64.b64encode(zlib.compress(data, 9)).decode("ascii")


def _unpack(text: str) -> list[str]:
    return zlib.decompress(base64.b64decode(text)).decode("utf-8").splitlines()


def _fixed_newlines(path: Path) -> Path:
    """No Windows o ezdxf grava em modo texto (CRLF): a entrada precisa ser a mesma."""
    text = path.read_text(encoding="utf-8")
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    return path


KINDS = ("fire_plan", "corredor_l", "pilar", "duas_portas")


def generate(folder: Path) -> None:
    """Grava as plantas sintéticas. Só é chamada com ``PYTHONHASHSEED=0``: o ezdxf ordena a
    seção OBJECTS pela ordem de um conjunto de strings, então a ENTRADA dependeria da semente
    de hash do processo. A análise, essa sim, roda com semente aleatória e tem de dar o mesmo
    resultado."""
    import ezdxf

    from coscip_cad.synthetic import ANALYTIC, make_analytic, make_fire_plan

    ezdxf.options.write_fixed_meta_data_for_testing = True
    _fixed_newlines(make_fire_plan(folder / "fire_plan.dxf"))
    for kind in ANALYTIC:
        _fixed_newlines(make_analytic(folder / f"{kind}.dxf", kind)[0])


def drawings(folder: Path) -> list[tuple[str, Path, str]]:
    env = {**os.environ, "PYTHONHASHSEED": "0",
           "PYTHONPATH": os.pathsep.join([str(ROOT), os.environ.get("PYTHONPATH", "")])}
    subprocess.run([sys.executable, "-m", "tools.ci.determinismo", "--gerar", str(folder)],
                   check=True, env=env, cwd=ROOT)
    return [(k, folder / f"{k}.dxf", "fire_plan" if k == "fire_plan" else "analytic")
            for k in KINDS]


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
            # o conteúdo vai junto (comprimido) para a CI mostrar ONDE diverge
            out[name] = {"dxf_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "analysis_sha256": digest(result),
                         "dxf_gz": _pack(path.read_bytes()),
                         "analysis_gz": _pack(json.dumps(canonical(result), sort_keys=True,
                                                         ensure_ascii=False, indent=0,
                                                         allow_nan=False).encode("utf-8"))}
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
                blob = key.replace("_sha256", "_gz")
                texts = [(f, _unpack(s[blob])) for f, s in seen.items() if s.get(blob)]
                if len(texts) >= 2:
                    (fa, a), (fb, b) = texts[:2]
                    diff = list(difflib.unified_diff(a, b, fa, fb, n=2, lineterm=""))
                    print("\n".join(diff[:60]))
    print("ok: saídas idênticas" if not bad else f"{bad} divergência(s)")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Determinismo da análise (F7.4)")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--comparar", nargs="+", type=Path)
    ap.add_argument("--gerar", type=Path, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if args.gerar:
        generate(args.gerar)
        return 0
    if args.comparar:
        return compare(args.comparar)
    result = hashes()
    if args.out:
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    print(json.dumps({k: {h: v[h] for h in ("dxf_sha256", "analysis_sha256")}
                      for k, v in result.items()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
