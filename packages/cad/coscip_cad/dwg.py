"""DWG → DXF pelo ODA File Converter (ADR 0006).

O DWG é formato fechado; o motor continua lendo DXF. Este módulo converte uma **cópia** do
DWG com o ODA File Converter instalado no computador e registra a origem (ADR 0002): SHA-256
do DWG e do DXF, ferramenta, versão e tempo. Os handles do DXF derivado não são tratados
como handles do DWG original.

Licença: o ODA File Converter gratuito restringe não membros da ODA a uso **não comercial**.
Produto vendido exige a assinatura da ODA (ou outro conversor licenciado).
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import shutil
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

ODA_ENV = "COSCIP_ODA_PATH"
DXF_VERSION = "R2018"
LICENSE_NOTE = ("ODA File Converter gratuito: uso não comercial para não membros da ODA. "
                "Produto vendido exige assinatura da ODA.")
_SEARCH = (r"C:\Program Files\ODA\ODAFileConverter*\ODAFileConverter.exe",
           r"C:\Program Files (x86)\ODA\ODAFileConverter*\ODAFileConverter.exe")

Runner = Callable[[Path, Path, Path], None]  # (conversor, dwg de entrada, dxf de saída)


class DwgConversionError(RuntimeError):
    pass


@dataclass(frozen=True)
class DwgConversion:
    dwg_path: str
    dwg_sha256: str
    dwg_version: str | None
    dxf_path: str
    dxf_sha256: str
    dxf_version: str
    tool: str
    tool_path: str
    tool_version: str | None
    seconds: float
    cached: bool
    note: str = LICENSE_NOTE

    def as_dict(self) -> dict:
        return asdict(self)


def find_oda() -> Path | None:
    """Conversor configurado em ``COSCIP_ODA_PATH`` ou o mais novo instalado."""
    configured = os.environ.get(ODA_ENV)
    if configured:
        path = Path(configured.strip('"'))
        return path if path.is_file() else None
    found = sorted((Path(p) for pattern in _SEARCH for p in glob.glob(pattern)),
                   key=lambda p: _version_key(p.parent.name))
    return found[-1] if found else None


def _version_key(folder: str) -> tuple[int, ...]:
    digits = folder.replace("ODAFileConverter", "").strip()
    try:
        return tuple(int(x) for x in digits.split("."))
    except ValueError:
        return (0,)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dwg_header_version(path: Path) -> str | None:
    """Versão gravada nos 6 primeiros bytes do DWG (ex.: AC1032 = 2018)."""
    head = path.read_bytes()[:6]
    return head.decode("ascii") if head.startswith(b"AC10") else None


def _oda_runner(tool: Path, dwg: Path, dxf: Path) -> None:
    import ezdxf
    from ezdxf.addons import odafc

    ezdxf.options.set("odafc-addon", "win_exec_path", str(tool))
    try:
        odafc.convert(dwg, dxf, version=DXF_VERSION, audit=True, replace=True)
    except odafc.ODAFCError as exc:
        raise DwgConversionError(f"ODA File Converter falhou: {exc}") from exc


def dwg_to_dxf(dwg: Path, cache_dir: Path, *, tool: Path | None = None,
               runner: Runner | None = None) -> DwgConversion:
    """Converte uma cópia do DWG; reaproveita a conversão anterior do mesmo conteúdo."""
    dwg = Path(dwg)
    if not dwg.is_file():
        raise DwgConversionError(f"arquivo não encontrado: {dwg}")
    version = dwg_header_version(dwg)
    if version is None:
        raise DwgConversionError("o arquivo não tem cabeçalho de DWG (AC10xx)")
    tool = tool or find_oda()
    if tool is None:
        raise DwgConversionError(
            "ODA File Converter não encontrado. Instale-o (opendesign.com → ODA File "
            f"Converter, aceitando a licença) ou informe o executável em {ODA_ENV}. "
            + LICENSE_NOTE)
    sha = _sha256(dwg)
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"{sha[:16]}.dxf"
    meta = cache_dir / f"{sha[:16]}.json"
    if out.exists() and meta.exists():
        data = json.loads(meta.read_text(encoding="utf-8"))
        if data.get("dxf_sha256") == _sha256(out) and data.get("tool_path") == str(tool):
            return DwgConversion(**{**data, "dwg_path": str(dwg), "cached": True})
    t0 = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="coscip_dwg_") as tmp:
        # Nome simples na cópia: o conversor trabalha por pasta e não gosta de acentos.
        copy = Path(tmp) / "entrada" / "origem.dwg"
        copy.parent.mkdir()
        shutil.copyfile(dwg, copy)
        result = Path(tmp) / "saida.dxf"
        (runner or _oda_runner)(tool, copy, result)
        if not result.exists() or result.stat().st_size == 0:
            raise DwgConversionError("o conversor não produziu o DXF")
        shutil.move(result, out)
    conv = DwgConversion(
        dwg_path=str(dwg), dwg_sha256=sha, dwg_version=version, dxf_path=str(out),
        dxf_sha256=_sha256(out), dxf_version=DXF_VERSION, tool="ODA File Converter",
        tool_path=str(tool), tool_version=_tool_version(tool),
        seconds=round(time.monotonic() - t0, 2), cached=False)
    meta.write_text(json.dumps(conv.as_dict(), ensure_ascii=False, indent=1),
                    encoding="utf-8")
    return conv


def _tool_version(tool: Path) -> str | None:
    key = _version_key(tool.parent.name)
    return ".".join(str(v) for v in key) if key != (0,) else None
