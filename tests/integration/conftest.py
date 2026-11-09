"""Fixtures dos testes de integração do MCP (NTs de teste e pasta de plantas criadas)."""
from __future__ import annotations

import pytest

from coscip_mcp.server import Server
from tests.unit.test_exit_distances import NT_208
from tests.unit.test_plant_analysis import NT_201


@pytest.fixture
def normas(tmp_path, monkeypatch):
    pasta = tmp_path / "normas"
    pasta.mkdir()
    (pasta / "nt-2-01.md").write_text(NT_201, encoding="utf-8")
    (pasta / "nt-2-08.md").write_text(NT_208, encoding="utf-8")
    monkeypatch.setenv("COSCIP_NORMAS_DIR", str(pasta))
    monkeypatch.setenv("COSCIP_PLANTAS_DIR", str(tmp_path / "plantas"))
    return pasta


@pytest.fixture
def srv(normas):
    return Server()
