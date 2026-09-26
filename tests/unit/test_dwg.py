"""DWG → DXF pelo ODA File Converter (ADR 0006), com o conversor simulado.

O conversor real não é executado aqui: o teste troca a chamada ao ODA por uma função que
recebe a CÓPIA do DWG e grava um DXF sintético. O que se testa é tudo em volta — cópia,
hashes, cache, erros e a integração com o MCP.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from coscip_cad import dwg as dwg_mod
from coscip_cad.dwg import DwgConversionError, dwg_to_dxf, find_oda
from coscip_cad.synthetic import make_fire_plan

FAKE_DWG = b"AC1032" + b"\x00" * 128  # cabeçalho de DWG 2018


@pytest.fixture
def ferramenta(tmp_path):
    exe = tmp_path / "ODA" / "ODAFileConverter 25.12.0" / "ODAFileConverter.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    return exe


@pytest.fixture
def conversor(tmp_path):
    modelo = make_fire_plan(tmp_path / "modelo.dxf")
    chamadas: list[Path] = []

    def runner(tool: Path, entrada: Path, saida: Path) -> None:
        chamadas.append(entrada)
        assert entrada.read_bytes().startswith(b"AC1032")
        shutil.copyfile(modelo, saida)

    runner.chamadas = chamadas
    return runner


@pytest.fixture
def original(tmp_path):
    p = tmp_path / "Projeto Térreo.dwg"
    p.write_bytes(FAKE_DWG)
    return p


def test_converte_uma_copia_e_registra_a_origem(original, ferramenta, conversor, tmp_path):
    antes = hashlib.sha256(original.read_bytes()).hexdigest()
    conv = dwg_to_dxf(original, tmp_path / "cache", tool=ferramenta, runner=conversor)
    assert conversor.chamadas[0] != original  # nunca a original
    assert hashlib.sha256(original.read_bytes()).hexdigest() == antes
    assert conv.dwg_sha256 == antes and conv.dwg_version == "AC1032"
    assert Path(conv.dxf_path).exists() and len(conv.dxf_sha256) == 64
    assert conv.tool_version == "25.12.0" and conv.dxf_version == "R2018"
    assert "não comercial" in conv.note and conv.cached is False
    meta = json.loads(Path(conv.dxf_path).with_suffix(".json").read_text(encoding="utf-8"))
    assert meta["dwg_sha256"] == antes


def test_mesmo_dwg_reaproveita_a_conversao(original, ferramenta, conversor, tmp_path):
    dwg_to_dxf(original, tmp_path / "cache", tool=ferramenta, runner=conversor)
    segunda = dwg_to_dxf(original, tmp_path / "cache", tool=ferramenta, runner=conversor)
    assert segunda.cached is True and len(conversor.chamadas) == 1


def test_sem_conversor_explica_como_instalar_e_a_licenca(original, tmp_path, monkeypatch):
    monkeypatch.setattr(dwg_mod, "find_oda", lambda: None)
    with pytest.raises(DwgConversionError) as exc:
        dwg_to_dxf(original, tmp_path / "cache")
    assert "COSCIP_ODA_PATH" in str(exc.value) and "não comercial" in str(exc.value)


def test_arquivo_que_nao_e_dwg_e_recusado(tmp_path, ferramenta, conversor):
    falso = tmp_path / "x.dwg"
    falso.write_bytes(b"%PDF-1.7")
    with pytest.raises(DwgConversionError, match="cabeçalho"):
        dwg_to_dxf(falso, tmp_path / "cache", tool=ferramenta, runner=conversor)


def test_conversor_sem_saida_e_erro(original, ferramenta, tmp_path):
    with pytest.raises(DwgConversionError, match="não produziu"):
        dwg_to_dxf(original, tmp_path / "cache", tool=ferramenta,
                   runner=lambda tool, entrada, saida: None)


def test_find_oda_pela_variavel_de_ambiente(ferramenta, monkeypatch, tmp_path):
    monkeypatch.setenv("COSCIP_ODA_PATH", str(ferramenta))
    assert find_oda() == ferramenta
    monkeypatch.setenv("COSCIP_ODA_PATH", str(tmp_path / "nao-existe.exe"))
    assert find_oda() is None


def test_mcp_abre_dwg_convertido(original, ferramenta, conversor, tmp_path, monkeypatch):
    from coscip_mcp.server import Server
    from tests.integration.test_mcp_server import call

    monkeypatch.setenv("COSCIP_ODA_PATH", str(ferramenta))
    monkeypatch.setenv("COSCIP_MCP_CACHE", str(tmp_path / "mcp"))
    monkeypatch.setattr(dwg_mod, "_oda_runner", conversor)
    erro, geral, _, _ = call(Server(), "abrir_planta", caminho=str(original))
    assert not erro
    origem = geral["convertido_de_dwg"]
    assert geral["planta_id"] == origem["dwg_sha256"][:10]  # id segue o DWG
    assert origem["tool"] == "ODA File Converter"
    assert any("handles são do DXF derivado" in a for a in geral["avisos"])
    assert geral["simbolos_por_classe"]["EXTINTOR"]["na_planta"] >= 2
