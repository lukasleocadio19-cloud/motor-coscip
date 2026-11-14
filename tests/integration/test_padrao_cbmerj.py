"""Padrão de apresentação do CBMERJ: cores do AAST 01/2025 (3.5), carimbo com os campos do
AAST 01/2025 (3.2) no formato de uma prancha aprovada e legendas em tabela."""
from __future__ import annotations

import ezdxf
import pytest

from coscip_mcp import apresentacao
from coscip_mcp.autoria import Authoring, AuthoringError

SALA = {"tipo": "sala", "nome": "Sala 01", "retangulo": [0, 0, 10, 6]}
PLACAS = [
    {"tipo": "simbolo", "classe": "EXTINTOR", "agente": "PQS_ABC", "capacidade": "6 kg",
     "x": 2, "y": 5},
    {"tipo": "simbolo", "id": "E-5", "x": 2, "y": 5.6},
    {"tipo": "chamada", "codigo": "E-5", "x": 2, "y": 4, "dimensao": "150x150",
     "alvo": [2, 5.6]},
    {"tipo": "chamada", "codigo": "S-12", "x": 5, "y": 1.5, "dimensao": "240x120"},
    {"tipo": "chamada", "codigo": "P-1", "x": 8, "y": 3, "dimensao": "150x150"},
    {"tipo": "chamada", "codigo": "A-5", "x": 8, "y": 1.5},
]


def gerar(tmp_path, ops, escala=100):
    auth = Authoring(tmp_path / "p.dxf", escala=escala)
    auth.add(ops)
    resumo = auth.build()
    return ezdxf.readfile(tmp_path / "p.dxf"), resumo, auth


def test_cores_do_aast_01_2025():
    c = apresentacao.CAMADAS
    assert c["INC_EXT"].cor == c["INC_HID"].cor == c["INC_SPK"].cor == apresentacao.VERMELHO
    assert c["ILUMINACAO"].cor == apresentacao.AZUL
    assert c["INC_ALARME"].cor == apresentacao.ROXO
    assert c["ROTAS"].cor == c["SINALIZACAO"].cor == apresentacao.VERDE
    assert c["PAREDE"].cor == c["PORTAS"].cor == c["JANELAS"].cor == apresentacao.PRETO
    # placas: E (extintores e equipamentos) em vermelho, S em verde, P e A em laranja
    assert apresentacao.cor_placa("E-5") == apresentacao.cor_placa("PICTO_E-8") == 1
    assert apresentacao.cor_placa("S-12") == apresentacao.VERDE
    assert apresentacao.cor_placa("P-1") == apresentacao.cor_placa("A-5") == apresentacao.LARANJA


def test_placa_e_chamada_de_extintor_em_vermelho(tmp_path):
    doc, _, _ = gerar(tmp_path, [SALA, *PLACAS])
    msp = doc.modelspace()
    por_nome = {i.dxf.name: i for i in msp.query("INSERT")}
    assert por_nome["PICTO_E-5"].dxf.layer == "SINAL_EQUIPAMENTOS"
    assert doc.layers.get("SINAL_EQUIPAMENTOS").dxf.color == 1
    assert por_nome["PLACA_CHAMADA_E-5"].dxf.layer == "SINAL_EQUIPAMENTOS"
    circulo = next(e for e in doc.blocks.get("PLACA_CHAMADA_E-5") if e.dxftype() == "CIRCLE")
    assert circulo.dxf.color == 1
    assert por_nome["PLACA_CHAMADA_S-12"].dxf.layer == "SINALIZACAO"
    assert por_nome["PLACA_CHAMADA_P-1"].dxf.layer == "SINAL_DEMAIS"
    # a linha de chamada do E-5 vai na cor da placa
    linha = next(iter(msp.query('LINE[layer=="SINAL_EQUIPAMENTOS"]')))
    assert linha.dxf.color == 1


def test_legenda_em_tabela_com_codigo_e_tamanho(tmp_path):
    doc, _, auth = gerar(tmp_path, [SALA, *PLACAS, {"tipo": "legenda", "x": 20, "y": 10}])
    t = [e.dxf.text for e in doc.modelspace().query('TEXT[layer=="LEGENDA"]')]
    assert "LEGENDA SISTEMA DE INCÊNDIO" in t and "LEGENDA - SINALIZAÇÃO DE EMERGÊNCIA" in t
    assert {"SÍMBOLO", "DESCRIÇÃO", "CÓDIGO E", "TAMANHO"} <= set(t)
    assert "Extintor de incêndio" in t and "Saída de emergência" in t
    # o círculo com o código e o tamanho vindo da chamada da planta
    bolhas = {i.attribs[0].dxf.text: i.attribs[1].dxf.text
              for i in doc.modelspace().query('INSERT[name=="PLACA_CHAMADA_E-5"]')}
    assert bolhas == {"E-5": "150x150"}
    # ordem do modelo: proibição, alerta, orientação e salvamento, equipamentos
    ys = {c: next(i.dxf.insert.y for i in doc.modelspace().query("INSERT")
                  if i.dxf.name == f"PICTO_{c}" and i.dxf.insert.x > 19) for c in
          ("P-1", "A-5", "S-12", "E-5")}
    assert ys["P-1"] > ys["A-5"] > ys["S-12"] > ys["E-5"]
    assert len(auth.legend_boxes) == 2


def test_carimbo_no_formato_do_cbmerj_com_campos_do_aast(tmp_path):
    selo = {"destinacao": "Residencial multifamiliar", "conteudo": ["Plantas baixas", "Cortes"],
            "proprietario": "Fulano", "endereco": "Rua X, 1",
            "responsavel_tecnico": "Beltrana", "registro_profissional": "CREA-RJ 123",
            "cadastro_cbmerj": "456", "empresa": "Projetos Teste", "data": "12/11/2026"}
    doc, r, _ = gerar(tmp_path, [SALA, {
        "tipo": "folha", "nome": "PRANCHA 02", "formato": "A0", "prancha": "2/4",
        "selo": selo, "atc_m2": 8066, "vistas": [
            {"titulo": "Planta", "escala": 50}, {"titulo": "Detalhe", "escala": 25}]}])
    lay = doc.layouts.get("PRANCHA 02")
    t = [e.dxf.text for e in lay.query("TEXT")]
    assert "DESTINADO À EDIFICAÇÃO RESIDENCIAL MULTIFAMILIAR" in t
    assert {"PLANTAS BAIXAS", "CORTES", "02", "DE 04", "INDICADA", "8.066,00 m²",
            "12/11/2026", "00"} <= set(t)
    assert "CREA-RJ 123 - CBMERJ 456" in t and "EMPRESA: Projetos Teste" in t
    car = r["folhas"][0]["carimbo"]
    assert car["modelo"].endswith("completo 175 x 283 mm")
    faltam = car["campos_aast_01_2025_em_branco"]
    assert any(f.startswith("autor_levantamento") for f in faltam)
    assert any(f.startswith("registro_empresa") for f in faltam)
    # moldura da NBR 10068: 25 mm à esquerda e 10 mm nas demais (A0)
    moldura = next(e for e in lay.query("LWPOLYLINE"))
    xs = [p[0] for p in moldura.get_points()]
    ys = [p[1] for p in moldura.get_points()]
    assert (min(xs), max(xs), min(ys), max(ys)) == (25.0, 1179.0, 10.0, 831.0)


def test_carimbo_compacto_em_a4_e_janela_da_legenda(tmp_path):
    doc, r, _ = gerar(tmp_path, [SALA, *PLACAS, {"tipo": "legenda", "x": 20, "y": 10}, {
        "tipo": "folha", "nome": "P1", "formato": "A2", "selo": {},
        "vistas": [{"titulo": "Planta", "janela": [-1, -1, 11, 7], "escala": 100}],
        "legenda": {"titulo": "Legenda"},
        "quadro_de_areas": False}], escala=100)
    f = r["folhas"][0]
    assert f["legenda"]["escala"] == "1:100" and f["legenda"]["tamanho_mm"][0] <= 178 - 12
    vps = [v for v in doc.layouts.get("P1").query("VIEWPORT") if v.dxf.id != 1]
    assert len(vps) == 2
    leg = max(vps, key=lambda v: v.dxf.center.x)
    assert leg.dxf.center.x > 594 - 7 - 178  # na coluna do carimbo
    doc4, r4, _ = gerar(tmp_path, [SALA, {"tipo": "folha", "nome": "A4", "formato": "A4",
                                          "vistas": [{"titulo": "P", "escala": 200}]}])
    assert "compacto" in r4["folhas"][0]["carimbo"]["modelo"]
    t4 = [e.dxf.text for e in doc4.layouts.get("A4").query("TEXT")]
    assert "APROVAÇÃO CORPO DE BOMBEIROS:" in t4


def test_folha_que_pede_legenda_sem_legenda_desenhada(tmp_path):
    auth = Authoring(tmp_path / "p.dxf")
    auth.add([SALA, {"tipo": "folha", "nome": "P1", "formato": "A2",
                     "vistas": [{"titulo": "Planta"}], "legenda": {"titulo": "Legenda"}}])
    with pytest.raises(AuthoringError, match="não tem a operação legenda"):
        auth.build()
