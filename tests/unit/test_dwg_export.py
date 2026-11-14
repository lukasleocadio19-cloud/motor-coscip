"""D7: DXF → DWG pelo ODA File Converter, com conferência de ida e volta.

O conversor é simulado (grava um DWG de mentira e, na volta, devolve um DXF escolhido pelo
teste); o que se testa é a cópia, a conferência, os erros e a ligação com o MCP. Um teste usa o
ODA real quando ele está instalado e é ignorado quando não está.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import ezdxf
import pytest

from coscip_cad import dwg as dwg_mod
from coscip_cad.dwg import DwgConversionError, find_oda
from coscip_cad.dwg_export import comparar_desenhos, exportar_dwg
from coscip_mcp.autoria import Authoring

FAKE_DWG = b"AC1032" + b"\x00" * 128


def _planta(caminho: Path) -> Path:
    auth = Authoring(caminho)
    auth.add([
        {"tipo": "sala", "nome": "Salão", "retangulo": [0, 0, 10, 6]},
        {"tipo": "porta", "x": 2, "y": -0.075, "largura_m": 1.0},
        {"tipo": "janela", "x": 6, "y": -0.075, "largura_m": 1.5},
        {"tipo": "simbolo", "classe": "EXTINTOR", "agente": "PQS_ABC", "x": 3, "y": 5},
        {"tipo": "folha", "nome": "PRANCHA 01", "formato": "A3", "prancha": "1/1",
         "titulo": "PLANTA", "vistas": [{"titulo": "Planta", "janela": [-1, -1, 11, 7],
                                         "escala": 100}]},
    ])
    auth.build()
    return caminho


@pytest.fixture
def dxf(tmp_path):
    return _planta(tmp_path / "planta.dxf")


@pytest.fixture
def ferramenta(tmp_path):
    exe = tmp_path / "ODA" / "ODAFileConverter 25.12.0" / "ODAFileConverter.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    return exe


def conversor(volta: Path):
    """Ida: grava um DWG de mentira. Volta: devolve o DXF ``volta``."""
    chamadas: list[tuple[str, str]] = []

    def runner(tool: Path, entrada: Path, saida: Path) -> None:
        chamadas.append((entrada.name, saida.name))
        if saida.suffix == ".dwg":
            assert entrada.suffix == ".dxf" and entrada.stem == "origem"  # nome simples
            saida.write_bytes(FAKE_DWG)
        else:
            assert entrada.read_bytes().startswith(b"AC1032")
            shutil.copyfile(volta, saida)

    runner.chamadas = chamadas
    return runner


# --- exportação ---------------------------------------------------------------------------------


def test_exporta_uma_copia_e_confere_a_ida_e_volta(dxf, ferramenta, tmp_path):
    antes = hashlib.sha256(dxf.read_bytes()).hexdigest()
    run = conversor(dxf)
    r = exportar_dwg(dxf, tmp_path / "saida" / "planta.dwg", tool=ferramenta, runner=run)
    assert hashlib.sha256(dxf.read_bytes()).hexdigest() == antes  # o DXF não é tocado
    assert Path(r.dwg_path).read_bytes() == FAKE_DWG and r.dwg_version == "AC1032"
    assert r.conferencia["confere"] is True and r.conferencia["diferencas"] == []
    assert r.tool_version == "25.12.0" and "não comercial" in r.note
    assert r.dxf_sha256 == antes and len(r.dwg_sha256) == 64
    assert run.chamadas == [("origem.dxf", "saida.dwg"), ("origem.dwg", "reaberto.dxf")]
    assert not list((tmp_path / "saida").glob("*.tmp"))  # só o DWG inteiro


def test_conferencia_acusa_o_que_a_volta_perdeu(dxf, ferramenta, tmp_path):
    perdido = ezdxf.readfile(dxf)
    msp = perdido.modelspace()
    msp.delete_entity(next(iter(msp.query("TEXT"))))  # um texto some na volta
    parcial = tmp_path / "volta.dxf"
    perdido.saveas(parcial)
    r = exportar_dwg(dxf, tmp_path / "p.dwg", tool=ferramenta, runner=conversor(parcial))
    assert r.conferencia["confere"] is False
    assert any("TEXT" in d or "texto" in d for d in r.conferencia["diferencas"])
    assert Path(r.dwg_path).exists()  # o arquivo é entregue; decidir é do usuário


def test_nao_sobrescreve_sem_pedir_e_exige_extensao_dwg(dxf, ferramenta, tmp_path):
    alvo = tmp_path / "p.dwg"
    alvo.write_bytes(b"existente")
    run = conversor(dxf)
    with pytest.raises(DwgConversionError, match="já existe"):
        exportar_dwg(dxf, alvo, tool=ferramenta, runner=run)
    assert alvo.read_bytes() == b"existente"
    exportar_dwg(dxf, alvo, tool=ferramenta, runner=run, sobrescrever=True)
    assert alvo.read_bytes() == FAKE_DWG
    with pytest.raises(DwgConversionError, match=r"\.dwg"):
        exportar_dwg(dxf, tmp_path / "p.dxf", tool=ferramenta, runner=run)


def test_sem_conversor_explica_como_instalar_e_a_licenca(dxf, tmp_path, monkeypatch):
    monkeypatch.setattr(dwg_mod, "find_oda", lambda: None)
    with pytest.raises(DwgConversionError) as exc:
        exportar_dwg(dxf, tmp_path / "p.dwg")
    assert "COSCIP_ODA_PATH" in str(exc.value) and "não comercial" in str(exc.value)


def test_conversor_sem_saida_ou_com_saida_que_nao_e_dwg_e_erro(dxf, ferramenta, tmp_path):
    with pytest.raises(DwgConversionError, match="não produziu"):
        exportar_dwg(dxf, tmp_path / "a.dwg", tool=ferramenta, runner=lambda t, i, o: None)

    def lixo(tool, entrada, saida):  # noqa: ANN001
        saida.write_bytes(b"%PDF-1.7")

    with pytest.raises(DwgConversionError, match="cabeçalho"):
        exportar_dwg(dxf, tmp_path / "b.dwg", tool=ferramenta, runner=lixo)
    assert not (tmp_path / "a.dwg").exists() and not (tmp_path / "b.dwg").exists()


def test_dwg_que_nao_reabre_e_erro_e_nao_fica_arquivo(dxf, ferramenta, tmp_path):
    def so_ida(tool, entrada, saida):  # noqa: ANN001
        if saida.suffix == ".dwg":
            saida.write_bytes(FAKE_DWG)

    with pytest.raises(DwgConversionError, match="não reabriu"):
        exportar_dwg(dxf, tmp_path / "c.dwg", tool=ferramenta, runner=so_ida)
    assert not (tmp_path / "c.dwg").exists()


def test_sem_conferir_so_converte(dxf, ferramenta, tmp_path):
    run = conversor(dxf)
    r = exportar_dwg(dxf, tmp_path / "d.dwg", tool=ferramenta, runner=run, conferir=False)
    assert r.conferencia == {} and len(run.chamadas) == 1


def test_dxf_inexistente(tmp_path, ferramenta):
    with pytest.raises(DwgConversionError, match="não encontrado"):
        exportar_dwg(tmp_path / "nao.dxf", tmp_path / "x.dwg", tool=ferramenta)


# --- comparação ---------------------------------------------------------------------------------


def _par(dxf):
    return ezdxf.readfile(dxf), ezdxf.readfile(dxf)


def test_desenhos_iguais_conferem(dxf):
    a, b = _par(dxf)
    r = comparar_desenhos(a, b)
    assert r["confere"] and r["metricas"]["entidades"] == r["metricas"]["entidades_no_dwg"] > 0
    assert r["metricas"]["viewports_por_layout"]["PRANCHA 01"] == (1, 1)


def test_camada_extra_no_dwg_nao_e_diferenca_mas_camada_perdida_e(dxf):
    a, b = _par(dxf)
    b.layers.add("NOVA")
    assert comparar_desenhos(a, b)["confere"]
    a.layers.add("SO_NO_ORIGINAL")
    r = comparar_desenhos(a, b)
    assert not r["confere"] and any("so_no_original" in d for d in r["diferencas"])


def test_propriedade_de_camada_alterada(dxf):
    a, b = _par(dxf)
    b.layers.get("PAREDE").dxf.lineweight = 13
    r = comparar_desenhos(a, b)
    assert any("PAREDE".casefold() in d and "propriedades" in d for d in r["diferencas"])


def test_entidade_e_texto_a_mais_ou_a_menos(dxf):
    a, b = _par(dxf)
    b.modelspace().add_line((0, 0), (1, 1), dxfattribs={"layer": "PAREDE"})
    b.modelspace().add_text("INVENTADO", dxfattribs={"layer": "TEXTOS", "height": 0.25})
    r = comparar_desenhos(a, b)
    assert any("LINE" in d for d in r["diferencas"])
    assert any("INVENTADO" in d for d in r["diferencas"])


def test_escala_de_viewport_e_extensao_e_unidade(dxf):
    a, b = _par(dxf)
    vp = next(v for v in b.layouts.get("PRANCHA 01").viewports() if v.dxf.id != 1)
    vp.dxf.view_height *= 2
    b.modelspace().add_line((0, 0), (500, 0), dxfattribs={"layer": "PAREDE"})
    b.header["$INSUNITS"] = 4
    r = comparar_desenhos(a, b)
    texto = " | ".join(r["diferencas"])
    assert "escalas das viewports" in texto and "extensão" in texto and "$INSUNITS" in texto


def test_bloco_perdido(dxf):
    a, b = _par(dxf)
    a.blocks.new("MOB_TESTE_100X100")
    r = comparar_desenhos(a, b)
    assert any("mob_teste_100x100" in d for d in r["diferencas"])
    a2, b2 = _par(dxf)
    b2.blocks.new("*U99")  # anônimos são renumerados pelo conversor e não contam
    assert comparar_desenhos(a2, b2)["confere"]


# --- MCP ----------------------------------------------------------------------------------------


def test_mcp_exporta_a_planta_criada(ferramenta, tmp_path, monkeypatch):
    from coscip_mcp.server import Server
    from tests.integration.test_mcp_server import call

    monkeypatch.setenv("COSCIP_ODA_PATH", str(ferramenta))
    srv = Server()
    _, geral, _, _ = call(srv, "criar_planta", caminho=str(tmp_path / "e.dxf"))
    erro, _, texts, _ = call(srv, "desenhar_planta", planta_id=geral["planta_id"],
                             operacoes=[{"tipo": "sala", "nome": "A", "retangulo": [0, 0, 6, 4]}])
    assert not erro, texts
    monkeypatch.setattr(dwg_mod, "_oda_runner", conversor(tmp_path / "e.dxf"))
    erro, out, texts, _ = call(srv, "exportar_dwg", planta_id=geral["planta_id"])
    assert not erro, texts
    assert out["dwg_path"].endswith("e.dwg") and out["conferencia"]["confere"] is True
    assert "confere" in out["resumo"] and "AutoCAD" in out["aviso"]
    erro, _, texts, _ = call(srv, "exportar_dwg", planta_id=geral["planta_id"])
    assert erro and "já existe" in " ".join(texts)  # não sobrescreve sem pedir
    erro, _, texts, _ = call(srv, "exportar_dwg", planta_id=geral["planta_id"],
                             caminho="x.pdf")
    assert erro and ".dwg" in " ".join(texts)


# --- ODA real (só se instalado) -----------------------------------------------------------------


@pytest.mark.skipif(find_oda() is None, reason="ODA File Converter não instalado")
def test_ida_e_volta_com_o_oda_real(dxf, tmp_path):
    r = exportar_dwg(dxf, tmp_path / "real.dwg")
    assert r.dwg_version and r.dwg_version.startswith("AC10")
    assert r.conferencia["confere"], r.conferencia["diferencas"]
    assert r.conferencia["metricas"]["viewports_por_layout"]["PRANCHA 01"] == (1, 1)
