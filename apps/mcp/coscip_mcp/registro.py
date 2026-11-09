"""Registra o servidor no Claude Desktop sem estragar a configuração existente.

    python -m coscip_mcp.registro [--config <claude_desktop_config.json>]
        [--env COSCIP_NORMAS_DIR=D:\\normas] [--remover]

O arquivo do Claude Desktop guarda também as preferências do aplicativo. Aqui ele é lido
como JSON, recebe só a entrada ``mcpServers["coscip-plantas"]`` e volta a ser gravado com
o mesmo recuo, sem BOM (o aplicativo não aceita), depois de uma cópia ``.bak`` datada.

Sem ``--config`` o arquivo é procurado: o lugar muda conforme a forma de instalação do
aplicativo (clássica em ``%APPDATA%\\Claude``; pela loja em ``%LOCALAPPDATA%\\Claude-Data\\<id>``
ou dentro do pacote). Registrar no lugar errado não dá erro, só não aparece no Claude.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

NAME = "coscip-plantas"
FILE = "claude_desktop_config.json"


def candidates(env: dict[str, str] | None = None) -> list[Path]:
    """Lugares onde o Claude Desktop guarda a configuração, do mais específico ao clássico."""
    env = os.environ if env is None else env
    out: list[Path] = []
    local, roaming = env.get("LOCALAPPDATA"), env.get("APPDATA")
    if local:
        out += sorted(Path(local).glob(f"Claude-Data/*/{FILE}"))
        out += sorted(Path(local).glob(f"Packages/Claude_*/LocalCache/Roaming/Claude/{FILE}"))
    if roaming:
        out.append(Path(roaming) / "Claude" / FILE)
    return out


def default_config(env: dict[str, str] | None = None) -> Path:
    """O arquivo que existe; se nenhum existir, o da instalação clássica."""
    found = candidates(env)
    if not found:
        raise FileNotFoundError("APPDATA/LOCALAPPDATA não definidos: informe --config")
    return next((p for p in found if p.exists()), found[-1])


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
        # Registrar de novo (atualização) mantém as variáveis já gravadas e soma as novas.
        merged = {**((servers.get(NAME) or {}).get("env") or {}), **(env or {})}
        entry: dict = {"command": python, "args": ["-m", "coscip_mcp"]}
        if merged:
            entry["env"] = merged
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
    ap.add_argument("--config", default="", help="omitido: procura o arquivo do aplicativo")
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--env", action="append", default=[], help="CHAVE=valor")
    ap.add_argument("--remover", action="store_true")
    a = ap.parse_args(argv)
    env = dict(item.split("=", 1) for item in a.env if "=" in item)
    config = Path(a.config) if a.config else default_config()
    out = register(config, a.python, env or None, a.remover)
    if out["backup"]:
        print(f"cópia da configuração anterior: {out['backup']}")
    print(("removido" if a.remover else "registrado") + f" '{NAME}' em {out['config']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
