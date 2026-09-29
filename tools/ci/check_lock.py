"""Confere que os locks em ``requirements/`` correspondem ao ``pyproject.toml`` (F0.2).

Recompila com o mesmo comando do cabeçalho de cada lock, partindo do lock atual (as versões
travadas são preferência, então lançamento novo no PyPI não acusa nada), e compara as linhas
sem o cabeçalho. Diferença = alguém mudou dependência sem regenerar o lock:

    uv pip compile pyproject.toml --universal --python-version 3.12 --generate-hashes \\
        -o requirements/runtime.lock
    uv pip compile pyproject.toml --extra dev ... -o requirements/dev.lock
"""

from __future__ import annotations

import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _body(text: str) -> list[str]:
    return [line for line in text.splitlines() if not line.startswith("#")]


def main() -> int:
    bad = 0
    for lock in sorted((ROOT / "requirements").glob("*.lock")):
        header = lock.read_text(encoding="utf-8").splitlines()[1]
        args = shlex.split(header.lstrip("#").strip())
        out = Path(tempfile.mkdtemp()) / lock.name
        args[args.index("-o") + 1] = str(out)
        # o lock atual vira preferência: só muda se o pyproject pedir outra versão
        out.write_bytes(lock.read_bytes())
        subprocess.run([sys.executable, "-m", *args, "-q"], cwd=ROOT, check=True)
        if _body(out.read_text(encoding="utf-8")) != _body(lock.read_text(encoding="utf-8")):
            print(f"DESATUALIZADO: {lock.relative_to(ROOT)} (regenerar com: {header[1:].strip()})")
            bad += 1
        else:
            print(f"ok: {lock.relative_to(ROOT)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
