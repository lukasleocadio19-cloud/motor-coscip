"""Autoteste da instalação: ``python -m coscip_mcp --verificar``.

Confere, sem abrir nenhuma planta real: versão do Python, dependências, uma planta sintética
lida de ponta a ponta, os textos das NTs encontrados e conferidos, e o conversor de DWG.
Sai com código 0 quando o essencial funciona (as NTs e o ODA são avisos, não falhas).
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path


def run() -> int:
    ok = True

    def line(status: str, what: str, detail: str = "") -> None:
        print(f"[{status:^5}] {what}" + (f" — {detail}" if detail else ""))

    v = sys.version_info
    good = (v.major, v.minor) == (3, 12)
    ok &= good
    line("ok" if good else "FALHA", f"Python {v.major}.{v.minor}.{v.micro}",
         "" if good else "o motor exige Python 3.12")

    try:
        import ezdxf  # noqa: F401
        import numpy  # noqa: F401
        import shapely  # noqa: F401

        from coscip_mcp.render import render
        from coscip_mcp.server import Server
        line("ok", "dependências do motor")
    except ImportError as exc:
        line("FALHA", "dependências do motor", str(exc))
        return 1

    from coscip_cad.synthetic import make_fire_plan

    srv = Server()
    with tempfile.TemporaryDirectory() as tmp:
        t0 = time.monotonic()
        dxf = make_fire_plan(Path(tmp) / "autoteste.dxf")
        opened = srv.ws.open(str(dxf))
        png, _ = render(srv.ws.get(opened["planta_id"]))
        ext = opened["simbolos_por_classe"].get("EXTINTOR", {}).get("na_planta", 0)
        good = ext == 2 and png.startswith(b"\x89PNG")
        ok &= good
        line("ok" if good else "FALHA", "planta sintética lida e desenhada",
             f"{ext} extintores, imagem {len(png) // 1024} KB, {time.monotonic() - t0:.1f} s")

    from coscip_mcp import norms

    files = norms.source_files()
    if not files:
        line("aviso", "textos das NTs não encontrados",
             "defina COSCIP_NORMAS_DIR com a pasta dos .md; sem eles a análise não cita a "
             "norma e os checks ficam fora do plano (ler e ver a planta funcionam)")
    else:
        base = norms.load_base()
        line("ok", f"textos das NTs: {len(base.sources)} documentos",
             f"{len(base.catalog.checks)} checks no plano, "
             f"{len(base.excluded_checks)} fora por citação não conferida")

    from coscip_cad.dwg import find_oda

    oda = find_oda()
    line("ok" if oda else "aviso", "ODA File Converter (abrir .dwg)",
         str(oda) if oda else "não instalado: só .dxf; instale pelo site opendesign.com")
    print("Instalação OK." if ok else "Instalação com FALHA: veja as linhas acima.")
    return 0 if ok else 1
