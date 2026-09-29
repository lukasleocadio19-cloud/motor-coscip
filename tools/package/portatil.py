"""Monta o pacote portátil do Windows (plano de correção, F0.3; ADR 0007).

Roda no Windows com Python 3.12 (o mesmo ABI do Python embeddable). Não baixa nada: recebe o
zip do Python embeddable já conferido pelo workflow ``release.yml``.

    python tools/package/portatil.py --versao 0.2.0 --python-embed python-3.12.10-embed-amd64.zip
        --saida dist

Resultado: ``dist/MotorCoscip-<versão>-win64.zip`` e ``dist/SHA256SUMS``. Dentro do zip:

    MotorCoscip-<versão>-win64/
      python/            Python embeddable + dependências do requirements/runtime.lock
      app/               código, normative/ e interface já compilada
      iniciar.cmd        aplicativo local no navegador
      mcp.cmd            servidor MCP (stdio) para o Claude
      verificar.cmd      autoteste (python -m coscip_mcp --verificar)

Tudo roda da pasta descompactada, sem administrador e sem instalar Python.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# o que vai para app/ (código, dados normativos e a interface compilada)
APP_ITEMS = ("apps/api", "apps/mcp", "workers", "packages", "normative", "alembic.ini",
             "pyproject.toml", "README.md", "requirements", "scripts/mcp", "docs/runbooks")
SKIP_DIRS = {"__pycache__", "node_modules", "src", ".pytest_cache", "fixtures-out"}
SKIP_SUFFIXES = {".pyc", ".tsx", ".ts"}

CMD = {
    "iniciar.cmd": '@echo off\r\nsetlocal\r\nset "PYTHONUTF8=1"\r\n'
                   '"%~dp0python\\python.exe" -m coscip_api.launcher %*\r\n',
    "mcp.cmd": '@echo off\r\nsetlocal\r\nset "PYTHONUTF8=1"\r\n'
               '"%~dp0python\\python.exe" -m coscip_mcp %*\r\n',
    "verificar.cmd": '@echo off\r\nsetlocal\r\nset "PYTHONUTF8=1"\r\n'
                     'set "PYTHONIOENCODING=utf-8"\r\n'
                     '"%~dp0python\\python.exe" -m coscip_mcp --verificar\r\n'
                     'if errorlevel 1 (echo. & echo AUTOTESTE FALHOU & pause & exit /b 1)\r\n'
                     'echo. & echo Autoteste ok. & pause\r\n',
}


def package_roots() -> list[str]:
    """Pastas de pacotes Python, lidas do pyproject (mesma lista do setuptools)."""
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return list(data["tool"]["setuptools"]["packages"]["find"]["where"])


def pth_lines(stdlib_zip: str) -> list[str]:
    """Conteúdo do ``python312._pth``: stdlib, site-packages, código do app, ``import site``."""
    lines = [stdlib_zip, ".", "Lib\\site-packages"]
    lines += ["..\\app\\" + p.replace("/", "\\") for p in package_roots()]
    lines.append("import site")
    return lines


def _copy_tree(src: Path, dst: Path) -> None:
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src)
        if any(part in SKIP_DIRS for part in rel.parts) or path.suffix in SKIP_SUFFIXES:
            continue
        if path.is_file():
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(version: str, embed_zip: Path, out_dir: Path, *, install_deps: bool = True,
          require_static: bool = True) -> Path:
    name = f"MotorCoscip-{version}-win64"
    stage = out_dir / name
    if stage.exists():
        shutil.rmtree(stage)
    py = stage / "python"
    py.mkdir(parents=True)
    with zipfile.ZipFile(embed_zip) as z:
        z.extractall(py)
    pth = sorted(py.glob("python3*._pth"))
    if len(pth) != 1:
        raise SystemExit(f"esperado um python3*._pth no embeddable; achei {len(pth)}")
    stdlib = sorted(p.name for p in py.glob("python3*.zip"))
    if not stdlib:
        raise SystemExit("stdlib (python3*.zip) ausente no embeddable")
    pth[0].write_bytes(("\r\n".join(pth_lines(stdlib[0])) + "\r\n").encode("ascii"))

    static = ROOT / "apps" / "api" / "coscip_api" / "static" / "index.html"
    if require_static and not static.exists():
        raise SystemExit("interface não compilada: rode 'npm ci && npm run build' antes")
    app = stage / "app"
    for item in APP_ITEMS:
        _copy_tree(ROOT / item, app / item)

    if install_deps:
        site = py / "Lib" / "site-packages"
        site.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", "--require-hashes",
                        "--only-binary=:all:", "--target", str(site),
                        "-r", str(ROOT / "requirements" / "runtime.lock")], check=True)

    for fname, body in CMD.items():
        (stage / fname).write_bytes(body.encode("ascii"))
    (stage / "LEIA-ME.txt").write_bytes((
        f"Motor CAD/COSCIP {version} - pacote portatil (Windows 64 bits)\r\n\r\n"
        "Nao precisa instalar Python. Descompacte a pasta inteira e use:\r\n"
        "  verificar.cmd  autoteste\r\n"
        "  iniciar.cmd    aplicativo no navegador\r\n"
        "  mcp.cmd        servidor MCP para o Claude (ver docs\\runbooks\\instalar-mcp.md;\r\n"
        "                 scripts\\mcp\\instalar.ps1 -Portatil <esta pasta>)\r\n\r\n"
        "Nenhum resultado tem valor normativo ate a homologacao das regras e dos checks.\r\n"
    ).encode("ascii"))

    zip_path = out_dir / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                z.write(path, Path(name) / path.relative_to(stage))
    (out_dir / "SHA256SUMS").write_text(f"{sha256(zip_path)}  {zip_path.name}\n",
                                        encoding="ascii", newline="\n")
    return zip_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--versao", required=True)
    ap.add_argument("--python-embed", required=True, type=Path)
    ap.add_argument("--saida", default=Path("dist"), type=Path)
    ap.add_argument("--sem-dependencias", action="store_true", help="só para teste")
    args = ap.parse_args(argv)
    args.saida.mkdir(parents=True, exist_ok=True)
    zip_path = build(args.versao, args.python_embed, args.saida,
                     install_deps=not args.sem_dependencias)
    print(f"ok: {zip_path} ({zip_path.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
