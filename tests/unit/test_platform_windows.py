"""Comportamento que só existe no Windows (marcador ``windows``; pulado no Linux)."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from coscip_api.launcher import _pid_alive

pytestmark = pytest.mark.windows


def test_pid_alive_does_not_kill_process():
    # No Windows, os.kill(pid, 0) encerraria o processo; _pid_alive usa OpenProcess.
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        assert _pid_alive(child.pid)
        assert child.poll() is None, "consultar o processo não pode encerrá-lo"
    finally:
        child.kill()
        child.wait()
    assert not _pid_alive(child.pid)


def test_pid_alive_self():
    assert _pid_alive(os.getpid())
