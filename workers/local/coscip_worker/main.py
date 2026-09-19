"""Entrada do worker: ``python -m coscip_worker.main <manifest.json>``.

Código de saída 0 = result.json gravado; qualquer outro = falha técnica (nunca sucesso).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from coscip_worker.stages import import_dxf


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("uso: coscip-worker <manifest.json>", file=sys.stderr)
        return 2
    manifest_path = Path(args[0]).resolve()
    workdir = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = import_dxf.run(manifest, workdir)
    tmp = workdir / manifest["output_dir"] / "result.json.tmp"
    tmp.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(tmp.with_suffix(""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
