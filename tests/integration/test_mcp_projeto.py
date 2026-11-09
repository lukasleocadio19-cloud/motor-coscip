"""MCP, modo projeto: enquadrar → dimensionar → desenhar (com corte) → salvar o memorial.

Usa as NTs do repositório (``normative/fontes``): os parâmetros só valem se a citação confere.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from coscip_mcp.server import Server
from tests.integration.test_mcp_server import call

FONTES = Path(__file__).resolve().parents[2] / "normative" / "fontes"


@pytest.fixture
def real(tmp_path, monkeypatch):
    monkeypatch.setenv("COSCIP_NORMAS_DIR", str(FONTES))
    monkeypatch.setenv("COSCIP_PLANTAS_DIR", str(tmp_path / "plantas"))
    return Server()


def test_fluxo_de_projeto_ate_o_memorial(real, tmp_path):
    erro, enq, texts, _ = call(real, "enquadrar_edificacao", occupancy="D-2",
                               building_area_m2=800, building_floors=2, single_occupancy=True)
    assert not erro, texts
    assert enq["risco_nt_1_04"] == "MÉDIO 1" and enq["risco_para_hidrantes"] == "MEDIO_1"
    assert "Extintores" in enq["medidas_exigidas"]

    erro, ext, texts, _ = call(real, "dimensionar_extintores",
                               risco=enq["risco_para_extintores"],
                               pavimentos=[{"nome": "Térreo", "area_m2": 420}])
    assert not erro and ext["resultados"]["total_de_extintores"] == 3
    erro, sai, _, _ = call(real, "dimensionar_saidas", ocupacao="D-2",
                           pavimentos=[{"nome": "Térreo", "area_m2": 420}])
    assert sai["resultados"]["quadro_por_pavimento"][0]["populacao"] == 60
    erro, hid, _, _ = call(real, "dimensionar_hidrantes", risco="MEDIO_1",
                           numero_de_hidrantes=2)
    assert hid["resultados"]["rti_l"] == 6000
    assert any("Nenhum trecho de recalque" in p for p in hid["pendencias"])
    # recalcular substitui o memorial do mesmo sistema
    call(real, "dimensionar_hidrantes", risco="MEDIO_1", numero_de_hidrantes=6)
    erro, _, _, _ = call(real, "requisitos_iluminacao_alarme", sistema="alarme")
    assert not erro

    erro, memo, texts, _ = call(real, "salvar_memorial", caminho="memorial.md",
                                titulo="Memorial de teste",
                                dados_da_edificacao={"ocupação": "D-2"})
    assert not erro, texts
    assert memo["sistemas"] == ["extintores", "saidas", "hidrantes", "alarme"]
    texto = (tmp_path / "plantas" / "memorial.md").read_text(encoding="utf-8")
    assert "RASCUNHO sem valor normativo" in texto and "NT 2-02, Tabela 1, p. 5" in texto
    assert "Reserva técnica de incêndio (RTI)**: 7000 L" in texto  # o segundo cálculo (6 hid.)
    erro, _, texts, _ = call(real, "salvar_memorial", caminho="memorial.md")
    assert erro and "já existe" in texts[0]
    erro, _, texts, _ = call(real, "salvar_memorial", caminho="memorial.txt")
    assert erro and ".md" in texts[0]


def test_edificacao_grande_usa_as_tabelas_5_a_32_com_o_roteiro(real):
    grande = {"occupancy": "D-2", "building_area_m2": 5000, "building_floors": 8,
              "single_occupancy": True}
    erro, enq, _, _ = call(real, "enquadrar_edificacao", **grande)
    assert not erro and enq["anexo_iii"]["status"] == "MISSING_DATA"  # falta a altura
    assert enq["medidas_exigidas"] == []  # sem coluna escolhida não há "nada exigido"

    erro, enq, texts, _ = call(real, "enquadrar_edificacao", **grande, building_height_m=24)
    assert not erro, texts
    anexo = enq["anexo_iii"]
    assert anexo["status"] == "INDICATIVE" and anexo["tabela"] == "Anexo III, Tabela 8 (p. 32)"
    assert anexo["conferencia"].startswith("duas leituras independentes concordam")
    assert {"Extintores", "Hidrantes e mangotinhos", "Alarme de Incêndio"} <= set(
        enq["medidas_exigidas"])
    por_nome = {m["medida"]: m for m in enq["medidas"]}
    assert por_nome["Hidrantes e mangotinhos"]["como_tratar"]["ferramenta"] == \
        "dimensionar_hidrantes"
    saidas = por_nome["Saídas de Emergência"]
    assert saidas["situacao"] == "EXIGIDA COM OBSERVAÇÃO"
    assert any("Enclausurada" in o for o in saidas["observacoes"])  # tipo de escada vem daqui
    assert por_nome["Segurança Estrutural contra Incêndio"]["como_tratar"]["nt"] == ["NT 2-19"]
    assert "Chuveiros automáticos" in enq["medidas_sem_marcacao"]

    # até 900 m² e 2 pavimentos continua na Tabela 2, conferida no PDF
    _, pequeno, _, _ = call(real, "enquadrar_edificacao", occupancy="D-2", building_area_m2=800,
                            building_floors=2, single_occupancy=True)
    assert pequeno["anexo_iii"]["tabela"].startswith("Anexo III, Tabela 2")
    assert "conferencia" not in pequeno["anexo_iii"]

    # grupo M por outro critério: a tabela do motor não escolhe a coluna; vale a leitura que
    # devolve as colunas para escolher
    _, m2, _, _ = call(real, "enquadrar_edificacao", occupancy="M-2", building_area_m2=500,
                       building_floors=1, building_height_m=4, single_occupancy=True)
    assert m2["anexo_iii"]["status"] == "CHOOSE_COLUMN" and len(m2["colunas_da_tabela"]) == 5
    erro, _, texts, _ = call(real, "enquadrar_edificacao", building_area_m2=100)
    assert erro and "occupancy" in texts[0]


def test_sem_a_nt_o_calculo_e_recusado(srv):
    """A base de teste só tem trechos das NT 2-01 e 2-08: hidrantes (NT 2-02) não confere."""
    erro, _, texts, _ = call(srv, "dimensionar_hidrantes", risco="MEDIO_1",
                             numero_de_hidrantes=2)
    assert erro and "não conferida" in texts[0]
    erro, _, texts, _ = call(srv, "salvar_memorial", caminho="m.md")
    assert erro and "nenhum cálculo" in texts[0]


def test_corte_esquematico_nao_conta_como_equipamento(real):
    from coscip_cad import DxfReader

    _, geral, _, _ = call(real, "criar_planta", caminho="p.dxf")
    pid = geral["planta_id"]
    erro, out, texts, _ = call(real, "desenhar_planta", planta_id=pid, operacoes=[
        {"tipo": "sala", "nome": "Salão", "retangulo": [0, 0, 20, 10]},
        {"tipo": "simbolo", "id": "HIDRANTE_SIMPLES", "x": 2, "y": 2},
        {"tipo": "corte", "x": 40, "y": 0, "largura_m": 12,
         "pavimentos": [{"nome": "Térreo", "pe_direito_m": 3.0}, {"nome": "2º pavimento"}],
         "prumada_hidrantes": True, "reservatorio": "superior", "rti_l": 6000}])
    assert not erro, texts
    assert out["simbolos_reconhecidos"] == {"HIDRANTE": 1}  # os 2 do corte não contam
    doc = DxfReader().open(real.ws.get(pid).path)
    textos = {t.dxf.text for t in doc.modelspace().query("TEXT")}
    assert {"CORTE ESQUEMÁTICO", "TÉRREO", "2º PAVIMENTO", "+0,00", "+3,15", "+6,10",
            "RESERVATÓRIO - RTI 6.000 L", "H1", "H2", "RR"} <= textos
    assert len(doc.modelspace().query('INSERT[name=="ESQV_TOMADA_H"]')) == 2
    assert len(doc.modelspace().query("DIMENSION")) == 1
    erro, _, texts, _ = call(real, "desenhar_planta", planta_id=pid, operacoes=[
        {"tipo": "corte", "x": 0, "y": 0, "pavimentos": []}])
    assert erro and "operação inválida" in texts[0]
