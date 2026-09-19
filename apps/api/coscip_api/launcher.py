"""Launcher: verifica ambiente, escolhe porta livre em 127.0.0.1 e abre o navegador.

- Um único serviço ativo por instalação (lock de instalação).
- Token de sessão de uso único vai no fragmento da URL (não chega a logs do servidor);
  a interface o troca por cookie e limpa o histórico.
- Fechar a aba não encerra nem conclui jobs; use ``--stop`` ou Ctrl+C.
"""

from __future__ import annotations

import argparse
import os
import secrets
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

from coscip_api.config import Settings


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class InstallLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.fd: int | None = None

    def __enter__(self) -> InstallLock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            pid = self.path.read_text(encoding="utf-8").strip() or "?"
            if pid.isdigit() and not _pid_alive(int(pid)):
                self.path.unlink()
                return self.__enter__()
            sys.exit(f"Motor já em execução (pid {pid}). Use o atalho existente ou --stop.")
        os.write(self.fd, str(os.getpid()).encode())
        return self

    def __exit__(self, *exc: object) -> None:
        if self.fd is not None:
            os.close(self.fd)
        self.path.unlink(missing_ok=True)


def _pid_alive(pid: int) -> bool:
    if os.name == "nt":
        # No Windows, os.kill(pid, 0) ENCERRA o processo; consultar via OpenProcess.
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel32.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def check_environment(settings: Settings) -> list[str]:
    problems = []
    if sys.version_info[:2] != (3, 12):
        problems.append(f"Python 3.12 esperado; encontrado {sys.version.split()[0]}")
    data = str(settings.data_dir).lower()
    if any(tag in data for tag in ("onedrive", "dropbox", "google drive", "\\\\")):
        problems.append("Pasta de dados em pasta sincronizada/rede: não suportado para o banco")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="coscip-launcher")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--dev-origin", default=None, help="ex.: http://localhost:5173")
    ap.add_argument("--stop", action="store_true", help="encerra a instância em execução")
    args = ap.parse_args(argv)

    base = Settings()
    lock_path = base.data_dir / "run" / "motor.lock"
    stop_path = base.data_dir / "run" / "stop.request"
    if args.stop:
        if not lock_path.exists():
            print("Nenhuma instância em execução.")
            return 0
        stop_path.write_text("stop", encoding="utf-8")
        print("Pedido de encerramento controlado registrado.")
        return 0

    for p in check_environment(base):
        print(f"[aviso] {p}")

    port = args.port or free_port()
    token = secrets.token_urlsafe(32)
    settings = Settings(port=port, launch_token=token, dev_origin=args.dev_origin)

    from coscip_api.main import create_app

    with InstallLock(lock_path):
        app = create_app(settings)
        url = f"http://127.0.0.1:{port}/#launch={token}"
        if args.dev_origin:
            url = f"{args.dev_origin}/#launch={token}"
        if not args.no_browser:
            threading.Thread(target=lambda: (time.sleep(1.2), webbrowser.open(url)),
                             daemon=True).start()
        print(f"Motor CAD/COSCIP em http://127.0.0.1:{port} (Ctrl+C para encerrar)", flush=True)
        if args.no_browser:
            print(f"Abrir: {url}", flush=True)
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port,
                                               log_level="warning", access_log=False))
        stop_path.unlink(missing_ok=True)

        def watch_stop() -> None:
            while not server.should_exit:
                if stop_path.exists():
                    stop_path.unlink(missing_ok=True)
                    server.should_exit = True
                time.sleep(1.0)

        threading.Thread(target=watch_stop, daemon=True).start()
        server.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
