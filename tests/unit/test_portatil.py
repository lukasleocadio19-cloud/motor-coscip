"""Pacote portátil do Windows (F0.3): montagem sem baixar nada, com embeddable falso."""

from __future__ import annotations

import zipfile
from pathlib import Path

from tools.package import portatil


def _fake_embed(tmp: Path) -> Path:
    z = tmp / "python-3.12.10-embed-amd64.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("python.exe", b"MZ")
        f.writestr("python312.zip", b"PK")
        f.writestr("python312._pth", "python312.zip\r\n.\r\n#import site\r\n")
    return z


def test_pth_includes_site_packages_app_and_import_site():
    lines = portatil.pth_lines("python312.zip")
    assert lines[0] == "python312.zip"
    assert "Lib\\site-packages" in lines
    assert "..\\app\\packages\\analysis" in lines
    assert "..\\app\\apps\\mcp" in lines
    assert lines[-1] == "import site"  # sem isso site-packages não é lido


def test_build_layout_and_checksum(tmp_path):
    out = tmp_path / "dist"
    out.mkdir()
    zip_path = portatil.build("9.9.9", _fake_embed(tmp_path), out, install_deps=False,
                              require_static=False)
    names = set(zipfile.ZipFile(zip_path).namelist())
    base = "MotorCoscip-9.9.9-win64/"
    for f in ("iniciar.cmd", "mcp.cmd", "verificar.cmd", "LEIA-ME.txt", "python/python.exe",
              "app/apps/mcp/coscip_mcp/server.py", "app/normative/checks/catalogo.yaml",
              "app/normative/fontes/nt-2-01-extintores.md", "app/requirements/runtime.lock"):
        assert base + f in names, f
    assert not any("__pycache__" in n for n in names)
    pth = zipfile.ZipFile(zip_path).read(base + "python/python312._pth").decode()
    assert "import site" in pth.splitlines() and "#import site" not in pth
    digest, fname = (out / "SHA256SUMS").read_text().split()
    assert fname == zip_path.name and digest == portatil.sha256(zip_path)
    cmd = zipfile.ZipFile(zip_path).read(base + "verificar.cmd").decode()
    assert "coscip_mcp --verificar" in cmd and "\r\n" in cmd
