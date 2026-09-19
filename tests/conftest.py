from __future__ import annotations

from pathlib import Path

import pytest

from coscip_cad.synthetic import make_simple_floor

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def floor_dxf(tmp_path: Path) -> Path:
    return make_simple_floor(tmp_path / "planta.dxf")


@pytest.fixture
def floor_dxf_mm(tmp_path: Path) -> Path:
    return make_simple_floor(tmp_path / "planta_mm.dxf", insunits=4, scale=1000)


@pytest.fixture
def floor_dxf_no_units(tmp_path: Path) -> Path:
    return make_simple_floor(tmp_path / "planta_sem_unidade.dxf", insunits=0)
