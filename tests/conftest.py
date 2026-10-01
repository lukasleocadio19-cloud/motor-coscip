from __future__ import annotations

import os
from pathlib import Path

import pytest

from coscip_cad.synthetic import make_simple_floor

ROOT = Path(__file__).resolve().parents[1]


def pytest_collection_modifyitems(config, items):
    """Teste marcado ``windows`` é pulado fora do Windows, em vez de falhar (F0.1)."""
    if os.name == "nt":
        return
    skip = pytest.mark.skip(reason="depende do Windows")
    for item in items:
        if "windows" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def floor_dxf(tmp_path: Path) -> Path:
    return make_simple_floor(tmp_path / "planta.dxf")


@pytest.fixture
def floor_dxf_mm(tmp_path: Path) -> Path:
    return make_simple_floor(tmp_path / "planta_mm.dxf", insunits=4, scale=1000)


@pytest.fixture
def floor_dxf_no_units(tmp_path: Path) -> Path:
    return make_simple_floor(tmp_path / "planta_sem_unidade.dxf", insunits=0)
