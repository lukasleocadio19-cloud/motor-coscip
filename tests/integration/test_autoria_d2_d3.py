"""D2 (chamadas de placa, mobiliário e equipamentos) e D3 (folhas em paper space e PDF)."""
from __future__ import annotations

import json

import ezdxf
import pytest

from coscip_mcp.autoria import Authoring, AuthoringError
from tests.integration.test_mcp_server import call

SALA = {"tipo": "sala", "nome": "Sala 01", "retangulo": [0, 0, 10, 6]}
SELO = {"obra": "Restaurante de teste", "endereco": "Rua X, 1", "proprietario": "Fulano",
        "autor_projeto": "Autora", "data": "09/11/2026"}


def folha(**kw):
    base = {"tipo": "folha", "nome": "PRANCHA 01", "formato": "A2", "prancha": "1/1",
            "titulo": "PLANTA BAIXA", "selo": SELO,
            "vistas": [{"titulo": "Planta baixa", "escala": 50}]}
    return {**base, **kw}


def gerar(tmp_path, ops, escala=100):
    auth = Authoring(tmp_path / "p.dxf", title="t", escala=escala)
    auth.add(ops)
    summary = auth.build()
    return ezdxf.readfile(tmp_path / "p.dxf"), summary


def textos(lay):
    return [e.dxf.text for e in lay.query("TEXT")]


# --- D2: chamadas ---------------------------------------------------------------------------


def test_chamada_vira_placa_com_atributos_e_conta_como_sinalizacao(srv):
    erro, geral, _, _ = call(srv, "criar_planta", caminho="c1.dxf")
    pid = geral["planta_id"]
    erro, out, texts, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        SALA,
        {"tipo": "chamada", "codigo": "s-12", "x": 3, "y": 3, "dimensao": "252X126",
         "alvo": [3, 0.4]},
        {"tipo": "chamada", "codigo": "E-5", "x": 6, "y": 3, "dimensao": "150x150"},
        {"tipo": "chamada", "codigo": "P-1", "x": 8, "y": 3}])
    assert not erro, texts
    rec = out["simbolos_reconhecidos"]
    assert rec["SINALIZACAO"] == 3 and rec["SAIDA"] == 1  # S-12 também marca a saída
    assert "ALERTA_simbolos_nao_reconhecidos" not in out
    doc = ezdxf.readfile(srv.ws.get(pid).path)
    por_nome = {i.dxf.name: i for i in doc.modelspace().query("INSERT")}
    assert set(por_nome) >= {"PLACA_CHAMADA_S-12", "PLACA_CHAMADA_E-5", "PLACA_CHAMADA_P-1"}
    s12 = por_nome["PLACA_CHAMADA_S-12"]
    assert {a.dxf.tag: a.dxf.text for a in s12.attribs} == {"CODIGO": "S-12",
                                                            "DIMENSAO": "252x126"}
    assert por_nome["PLACA_CHAMADA_P-1"].attribs[1].dxf.text == ""  # sem dimensão: não inventa
    # linha de chamada do S-12 até o alvo, na camada da sinalização
    linhas = [e for e in doc.modelspace().query('LINE[layer=="SINALIZACAO"]')]
    assert len(linhas) == 1 and abs(linhas[0].dxf.end.y - 0.4) < 1e-9


def test_chamada_na_escala_da_planta(tmp_path):
    doc, _ = gerar(tmp_path, [SALA, {"tipo": "chamada", "codigo": "E-5", "x": 5, "y": 3}], 50)
    ins = doc.modelspace().query("INSERT")[0]
    assert ins.dxf.xscale == 0.5  # 0,9 m de diâmetro a 1:100 vira 0,45 m a 1:50


@pytest.mark.parametrize("op", [{"codigo": "X-99"}, {"codigo": "EXTINTOR_PQS_ABC"},
                                {"codigo": "E-5", "dimensao": "150 por 150"}])
def test_chamada_invalida_devolve_erro_legivel_e_nao_altera(srv, op):
    erro, geral, _, _ = call(srv, "criar_planta", caminho="c2.dxf")
    erro, _, texts, _ = call(srv, "desenhar_planta", planta_id=geral["planta_id"],
                             operacoes=[{"tipo": "chamada", "x": 1, "y": 1, **op}])
    assert erro
    _, el, _, _ = call(srv, "listar_elementos", planta_id=geral["planta_id"])
    assert el["total"] == 0


# --- D2: mobiliário e equipamentos ------------------------------------------------------------


def test_mobiliario_entra_nas_camadas_certas_e_nao_vira_equipamento(srv):
    erro, geral, _, _ = call(srv, "criar_planta", caminho="m1.dxf")
    pid = geral["planta_id"]
    erro, out, texts, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        SALA,
        {"tipo": "mobiliario", "id": "fogão", "x": 2, "y": 1.5},
        {"tipo": "mobiliario", "id": "coifa", "x": 2, "y": 1.5, "largura_m": 2.0,
         "profundidade_m": 1.2},
        {"tipo": "mobiliario", "id": "botijao_p45", "x": 9, "y": 1},
        {"tipo": "mobiliario", "id": "pilar", "x": 5, "y": 3, "rotacao_graus": 45},
        {"tipo": "mobiliario", "id": "escada", "x": 8, "y": 3, "largura_m": 1.0}])
    assert not erro, texts
    assert out["simbolos_reconhecidos"] == {}  # nada vira extintor, hidrante, sinalização...
    doc = ezdxf.readfile(srv.ws.get(pid).path)
    camadas = {i.dxf.name: i.dxf.layer for i in doc.modelspace().query("INSERT")}
    assert camadas["MOB_FOGAO_160X90"] == "MOBILIARIO"
    assert camadas["MOB_COIFA_200X120"] == "MOBILIARIO"
    assert camadas["MOB_PILAR_30X30"] == "PILARES"
    assert camadas["MOB_ESCADA_100X300"] == "ESCADA"
    assert doc.layers.get("PILARES").dxf.lineweight == 50


def test_mobiliario_erros_de_uso(srv):
    erro, geral, _, _ = call(srv, "criar_planta", caminho="m2.dxf")
    pid = geral["planta_id"]
    erro, _, texts, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        {"tipo": "mobiliario", "id": "fogao6", "x": 1, "y": 1}])
    assert erro and "FOGAO" in texts[0]
    erro, _, texts, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        {"tipo": "mobiliario", "id": "botijao_p45", "x": 1, "y": 1, "profundidade_m": 1.0}])
    assert erro and "redondo" in texts[0]


def test_listar_blocos_filtra_por_grupo_e_busca(srv):
    _, todos, _, _ = call(srv, "listar_blocos")
    assert todos["total"] >= 18 and "biblioteca própria" in todos["origem"]
    _, glp, _, _ = call(srv, "listar_blocos", grupo="glp")
    assert {b["id"] for b in glp["blocos"]} == {"BOTIJAO_P45", "BOTIJAO_P190"}
    for busca in ("fogão", "FOGAO", "fog"):  # sem acento e sem caixa
        _, fogao, _, _ = call(srv, "listar_blocos", busca=busca)
        assert [b["id"] for b in fogao["blocos"]] == ["FOGAO"], busca
    _, lou, _, _ = call(srv, "listar_blocos", grupo="louças")
    assert {b["id"] for b in lou["blocos"]} >= {"VASO_SANITARIO", "LAVATORIO", "PIA"}


# --- D3: folhas -----------------------------------------------------------------------------


def test_folha_cria_layout_com_viewport_na_escala_pedida(tmp_path):
    doc, resumo = gerar(tmp_path, [SALA, folha()])
    assert "PRANCHA 01" in doc.layout_names()
    lay = doc.layouts.get("PRANCHA 01")
    assert (lay.dxf.paper_width, lay.dxf.paper_height) == (594.0, 420.0)
    vps = [v for v in lay.query("VIEWPORT") if v.dxf.id != 1]
    assert len(vps) == 1
    vp = vps[0]
    # 1:50 → altura da vista em metros = altura no papel em mm × 50 / 1000
    assert abs(vp.dxf.view_height - vp.dxf.height * 50 / 1000) < 1e-6
    assert vp.dxf.layer == "VIEWPORT" and doc.layers.get("VIEWPORT").dxf.plot == 0
    assert resumo["folhas"][0]["vistas"][0]["escala"] == "1:50"
    t = textos(lay)
    assert "ESCALA 1:50" in t and "PLANTA BAIXA" in t  # título da vista e do selo
    assert "RESTAURANTE DE TESTE" in t and "FULANO" in t and "AUTORA" in t
    # carimbo no formato do CBMERJ: título, campos e as três assinaturas
    assert "PROJETO DE SEGURANÇA CONTRA INCÊNDIO E PÂNICO" in t
    assert {"CONTEÚDO:", "Nº DA PRANCHA:", "PROPRIETÁRIO:", "ENDEREÇO:", "ESCALA:", "DATA:",
            "ÁREA:", "REVISÃO:", "PROPRIETÁRIO", "O AUTOR DO LEV. ARQUITETÔNICO",
            "O AUTOR DO PROJETO DE SEGURANÇA", "APROVAÇÃO CORPO DE BOMBEIROS:"} <= set(t)
    assert "01" in t and "1:50" in t  # número da prancha e escala única das vistas


def test_folha_leva_so_o_que_foi_informado_e_o_aviso_de_rascunho(tmp_path):
    doc, _ = gerar(tmp_path, [SALA, folha(selo={})])
    t = textos(doc.layouts.get("PRANCHA 01"))
    assert any(x.startswith("RASCUNHO GERADO PELO MOTOR COSCIP - SEM VALOR NORMATIVO") for x in t)
    assert any("SEM RESPONSÁVEL TÉCNICO" in x for x in t)
    assert "FULANA" not in t  # não inventa responsável
    doc2, r2 = gerar(tmp_path, [SALA, folha(selo={**SELO, "responsavel_tecnico": "Fulana"})])
    t2 = textos(doc2.layouts.get("PRANCHA 01"))
    assert "FULANA" in t2 and any("REQUER CONFERÊNCIA" in x for x in t2)
    # o resumo diz o que o AAST 01/2025 (3.2) exige no carimbo e ficou em branco
    faltam = r2["folhas"][0]["carimbo"]["campos_aast_01_2025_em_branco"]
    assert any(f.startswith("registro_profissional") for f in faltam)
    assert not any(f.startswith("responsavel_tecnico") for f in faltam)


def test_quadro_de_areas_soma_os_ambientes_e_mostra_a_atc(tmp_path):
    doc, _ = gerar(tmp_path, [SALA, {**SALA, "nome": "Sala 02", "retangulo": [10.2, 0, 14, 6]},
                              folha(atc_m2=90)])
    t = textos(doc.layouts.get("PRANCHA 01"))
    assert "QUADRO DE ÁREAS" in t and "60,00 m²" in t and "22,80 m²" in t
    assert "82,80 m²" in t and "90,00 m²" in t  # soma útil e ATC informada
    doc2, _ = gerar(tmp_path, [SALA, folha(quadro_de_areas=False)])
    assert "QUADRO DE ÁREAS" not in textos(doc2.layouts.get("PRANCHA 01"))


def test_notas_e_revisoes_aparecem_na_coluna(tmp_path):
    doc, _ = gerar(tmp_path, [SALA, folha(
        notas=["Cotas em metros.", "Extintores conforme NT 2-01."],
        revisoes=[{"rev": "A", "data": "10/11/2026", "descricao": "Emissão para análise"}])])
    t = textos(doc.layouts.get("PRANCHA 01"))
    assert "NOTAS" in t and "1. Cotas em metros." in t and "2. Extintores conforme NT 2-01." in t
    assert "REV" in t and "A" in t and "Emissão para análise" in t


def test_duas_vistas_ficam_dentro_da_area_e_sem_sobrepor(tmp_path):
    ops = [SALA, folha(vistas=[
        {"titulo": "Planta", "janela": [-1, -1, 11, 7], "escala": 100},
        {"titulo": "Detalhe", "janela": [0, 0, 3, 2], "escala": 25}])]
    doc, resumo = gerar(tmp_path, ops)
    vps = [v for v in doc.layouts.get("PRANCHA 01").query("VIEWPORT") if v.dxf.id != 1]
    assert len(vps) == 2
    caixas = [(v.dxf.center.x - v.dxf.width / 2, v.dxf.center.y - v.dxf.height / 2,
               v.dxf.center.x + v.dxf.width / 2, v.dxf.center.y + v.dxf.height / 2) for v in vps]
    a, b = caixas
    assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]  # não se sobrepõem
    for x0, y0, x1, y1 in caixas:
        assert 10 < x0 and x1 < 594 - 10 - 80 and 10 + 42 < y0 and y1 < 420 - 10


def test_vista_que_nao_cabe_diz_a_escala_ou_o_formato(tmp_path):
    auth = Authoring(tmp_path / "p.dxf")
    auth.add([SALA, folha(formato="A4", vistas=[{"titulo": "Planta", "escala": 20}])])
    with pytest.raises(AuthoringError, match=r"use 1:\d+ ou um formato maior"):
        auth.build()


def test_nota_longa_demais_e_layout_repetido_dao_erro_legivel(tmp_path):
    auth = Authoring(tmp_path / "p.dxf")
    auth.add([SALA, folha(formato="A4", vistas=[{"titulo": "P", "escala": 200}],
                          notas=["nota longa " * 40] * 12)])
    with pytest.raises(AuthoringError, match="notas ocupam"):
        auth.build()
    auth2 = Authoring(tmp_path / "q.dxf")
    auth2.add([SALA, folha(), folha()])
    with pytest.raises(AuthoringError, match="já existe um layout"):
        auth2.build()


def test_folha_vai_no_json_e_a_planta_continua_lida_pelo_motor(srv):
    erro, geral, _, _ = call(srv, "criar_planta", caminho="f1.dxf")
    pid = geral["planta_id"]
    erro, out, texts, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        SALA, {"tipo": "simbolo", "classe": "EXTINTOR", "x": 2, "y": 3, "agente": "PQS_ABC"},
        folha()])
    assert not erro, texts
    assert out["folhas"][0]["formato"] == "A2"
    assert out["simbolos_reconhecidos"]["EXTINTOR"] == 1  # o paper space não conta como planta
    dados = json.loads(srv.ws.get(pid).path.with_suffix(".coscip.json").read_text("utf-8"))
    assert dados["operacoes"][-1]["tipo"] == "folha"
    retomada = Authoring.load(srv.ws.get(pid).path)
    assert retomada.ops[-1].nome == "PRANCHA 01"


# --- D3: PDF --------------------------------------------------------------------------------


def test_exportar_pdf_gera_uma_pagina_por_folha_com_as_vistas(srv):
    pymupdf = pytest.importorskip("pymupdf")
    erro, geral, _, _ = call(srv, "criar_planta", caminho="pdf1.dxf")
    pid = geral["planta_id"]
    call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        SALA, {"tipo": "chamada", "codigo": "E-5", "x": 5, "y": 3, "dimensao": "150x150"},
        folha(), folha(nome="PRANCHA 02", prancha="2/2", formato="A3",
                       vistas=[{"titulo": "Detalhe", "janela": [0, 0, 4, 3], "escala": 25}])])
    erro, out, texts, _ = call(srv, "exportar_pdf", planta_id=pid)
    assert not erro, texts
    assert out["paginas"] == ["PRANCHA 01", "PRANCHA 02"]
    pdf = pymupdf.open(out["arquivo"])
    assert len(pdf) == 2
    assert [round(p.rect.width / 72 * 25.4) for p in pdf] == [594, 420]  # A2 e A3 em mm
    # a vista tem de estar no PDF: dezenas de traços, não só o selo
    assert len(pdf[0].get_drawings()) > 150
    # o PDF não tem fundo preto: o pixel do canto é branco
    pix = pdf[0].get_pixmap(dpi=20)
    assert pix.pixel(5, 5) == (255, 255, 255)
    pdf.close()  # o Windows não troca um arquivo aberto
    erro, _, texts, _ = call(srv, "exportar_pdf", planta_id=pid)
    assert erro and "já existe" in texts[0]
    erro, _, texts, _ = call(srv, "exportar_pdf", planta_id=pid, sobrescrever=True)
    assert not erro


def test_exportar_pdf_sem_folha_e_nome_invalido_dao_erro(srv):
    pytest.importorskip("pymupdf")
    erro, geral, _, _ = call(srv, "criar_planta", caminho="pdf2.dxf")
    pid = geral["planta_id"]
    call(srv, "desenhar_planta", planta_id=pid, operacoes=[SALA])
    erro, _, texts, _ = call(srv, "exportar_pdf", planta_id=pid)
    assert erro and "nada a exportar" in texts[0]
    erro, _, texts, _ = call(srv, "exportar_pdf", planta_id=pid, caminho="x.txt")
    assert erro and ".pdf" in texts[0]
