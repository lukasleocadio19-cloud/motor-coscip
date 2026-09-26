"""Registra o servidor no Claude Desktop sem estragar a configuração existente.

    python -m coscip_mcp.registro --config "%APPDATA%\\Claude\\claude_desktop_config.json"
        [--env COSCIP_NORMAS_DIR=D:\\normas] [--remover]

O arquivo do Claude Desktop guarda também as preferências do aplicativo. Aqui ele é lido
como JSON, recebe só a entrada ``mcpServers["coscip-plantas"]`` e volta a ser gravado com
o mesmo recuo, sem BOM (o aplicativo não aceita), depois de uma cópia ``.bak`` datada.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

NAME = "coscip-plantas"


def register(config: Path, python: str, env: dict[str, str] | None = None,
             remove: bool = False) -> dict:
    data: dict = {}
    backup = None
    if config.exists():
        text = config.read_text(encoding="utf-8-sig")
        if text.strip():
            data = json.loads(text)  # JSON inválido: para aqui, sem sobrescrever nada
        backup = config.with_name(f"{config.name}.{datetime.now():%Y%m%d-%H%M%S}.bak")
        shutil.copy2(config, backup)
    servers = data.setdefault("mcpServers", {})
    if remove:
        servers.pop(NAME, None)
    else:
        entry: dict = {"command": python, "args": ["-m", "coscip_mcp"]}
        if env:
            entry["env"] = env
        servers[NAME] = entry
    config.parent.mkdir(parents=True, exist_ok=True)
    tmp = config.with_name(config.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(tmp.read_text(encoding="utf-8"))  # confere antes de trocar
    tmp.replace(config)
    return {"config": str(config), "backup": str(backup) if backup else None,
            "entrada": servers.get(NAME), "removido": remove}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m coscip_mcp.registro")
    ap.add_argument("--config", required=True)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--env", action="append", default=[], help="CHAVE=valor")
    ap.add_argument("--remover", action="store_true")
    a = ap.parse_args(argv)
    env = dict(item.split("=", 1) for item in a.env if "=" in item)
    out = register(Path(a.config), a.python, env or None, a.remover)
    if out["backup"]:
        print(f"cópia da configuração anterior: {out['backup']}")
    print(("removido" if a.remover else "registrado") + f" '{NAME}' em {out['config']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
