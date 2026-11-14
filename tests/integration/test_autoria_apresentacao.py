"""Desenho gerado pelo motor com o padrão de apresentação (frente D1): camadas com cor e
espessura, janelas e etiquetas de vão, cotas em metros com vírgula, cotas em cadeia, marcas de
corte e escala de impressão."""
from __future__ import annotations

import ezdxf
import pytest

from coscip_mcp.autoria import Authoring, AuthoringError
from tests.integration.test_mcp_server import call

SALA = {"tipo": "sala", "nome": "Sala 01", "retangulo": [0, 0, 10, 6]}


def gerar(tmp_path, ops, escala=100):
    auth = Authoring(tmp_path / "p.dxf", title="t", escala=escala)
    auth.add(ops)
    auth.build()
    return ezdxf.readfile(tmp_path / "p.dxf"), auth


def textos(doc):
    return [e.dxf.text for e in doc.modelspace().query("TEXT")]


def altura_x(doc):
    return [e.dxf.height for e in doc.modelspace().query("TEXT") if e.dxf.text == "X"][0]


def cotas_texto(doc):
    """Texto de cada DIMENSION, lido do bloco de geometria que o motor gerou."""
    out = []
    for d in doc.modelspace().query("DIMENSION"):
        blk = doc.blocks.get(d.dxf.geometry)
        out += [e.text for e in blk if e.dxftype() == "MTEXT"]
    return out


def test_camadas_saem_com_cor_e_espessura(tmp_path):
    doc, _ = gerar(tmp_path, [SALA, {"tipo": "janela", "x": 5, "y": -0.075},
                              {"tipo": "simbolo", "classe": "EXTINTOR", "x": 2, "y": 3,
                               "agente": "PQS_ABC"}])
    assert (doc.layers.get("PAREDE").dxf.color, doc.layers.get("PAREDE").dxf.lineweight) == (7, 50)
    # AAST 01/2025, 3.5: arquitetura em preto (o azul é da iluminação de emergência)
    assert doc.layers.get("JANELAS").dxf.color == 7
    assert doc.layers.get("INC_EXT").dxf.color == 1
    assert doc.layers.get("TEXTOS").dxf.lineweight == 13
    assert doc.header["$LWDISPLAY"] == 1 and doc.header["$INSUNITS"] == 6


def test_janela_recorta_o_vao_desenha_o_caixilho_e_escreve_a_etiqueta(tmp_path):
    doc, _ = gerar(tmp_path, [SALA, {"tipo": "janela", "x": 5, "y": -0.075, "largura_m": 1.5,
                                      "altura_m": 1.2, "peitoril_m": 0.9,
                                      "espessura_m": 0.15}])
    xs = []
    for e in doc.modelspace().query('LINE[layer=="PAREDE"]'):
        a, b = e.dxf.start, e.dxf.end
        if abs(a.y + 0.15) < 1e-6 and abs(b.y + 0.15) < 1e-6:  # face externa inferior
            xs += [a.x, b.x]
    assert sorted({round(x, 3) for x in xs if 4.0 < x < 6.0}) == [4.25, 5.75]  # vão de 1,5 m
    linhas = list(doc.modelspace().query('LINE[layer=="JANELAS"]'))
    assert len(linhas) == 3  # duas faces da parede e o vidro
    assert all(4.25 - 1e-6 <= min(e.dxf.start.x, e.dxf.end.x) for e in linhas)
    assert "150x120/90" in textos(doc)


def test_janela_em_parede_vertical_escreve_etiqueta_legivel(tmp_path):
    doc, _ = gerar(tmp_path, [SALA, {"tipo": "janela", "x": -0.075, "y": 3, "angulo_graus": 90}])
    et = [e for e in doc.modelspace().query("TEXT") if e.dxf.text == "150x120/90"][0]
    assert et.dxf.rotation == 90  # de baixo para cima, nunca de cabeça para baixo
    doc2, _ = gerar(tmp_path, [SALA, {"tipo": "janela", "x": 10.075, "y": 3,
                                      "angulo_graus": 270}])
    et2 = [e for e in doc2.modelspace().query("TEXT") if e.dxf.text == "150x120/90"][0]
    assert et2.dxf.rotation == 90  # 270 vira 90 (texto legível)


def test_porta_escreve_largura_x_altura_e_pode_omitir(tmp_path):
    ops = [SALA, {"tipo": "porta", "x": 5, "y": -0.075, "largura_m": 0.8, "altura_m": 2.1}]
    doc, _ = gerar(tmp_path, ops)
    assert "80x210" in textos(doc)
    # as etiquetas de vão ficam na própria camada, longe da camada da porta
    assert {e.dxf.layer for e in doc.modelspace().query("TEXT") if e.dxf.text == "80x210"} == {
        "ROTULOS"}
    assert not [e for e in doc.modelspace().query("TEXT") if e.dxf.layer == "PORTAS"]
    doc2, _ = gerar(tmp_path, [SALA, {**ops[1], "etiqueta": False}])
    assert "80x210" not in textos(doc2)


def test_porta_corta_fogo_mantem_o_tempo_e_a_etiqueta(tmp_path):
    doc, _ = gerar(tmp_path, [SALA, {"tipo": "porta", "x": 5, "y": -0.075, "largura_m": 0.9,
                                      "corta_fogo_min": 60}])
    t = textos(doc)
    assert "60" in t and "90x210" in t


def test_cota_em_metros_com_virgula(tmp_path):
    doc, _ = gerar(tmp_path, [SALA, {"tipo": "cota", "a": [0, 0], "b": [10, 0]}])
    assert cotas_texto(doc) == ["10,00"]
    assert doc.modelspace().query("DIMENSION")[0].dxf.dimstyle == "COSCIP-100"


def test_cota_cadeia_faz_um_trecho_por_vao_e_o_total(tmp_path):
    doc, _ = gerar(tmp_path, [SALA, {"tipo": "cota_cadeia",
                                      "pontos": [[0, -1], [2, -1], [5, -1], [10, -1]],
                                      "afastamento_m": -0.8}])
    assert sorted(cotas_texto(doc)) == sorted(["2,00", "3,00", "5,00", "10,00"])


def test_cota_cadeia_sem_total_e_na_vertical(tmp_path):
    doc, _ = gerar(tmp_path, [SALA, {"tipo": "cota_cadeia", "pontos": [[11, 0], [11, 2.5],
                                                                      [11, 6]],
                                      "total": False}])
    assert sorted(cotas_texto(doc)) == ["2,50", "3,50"]


@pytest.mark.parametrize("pontos", [[[0, 0], [5, 0], [3, 0]], [[0, 0], [0, 0], [4, 0]],
                                    [[1, 1], [1, 1]]])
def test_cota_cadeia_rejeita_pontos_fora_de_ordem(tmp_path, pontos):
    auth = Authoring(tmp_path / "p.dxf")
    with pytest.raises(AuthoringError):
        auth.add([{"tipo": "cota_cadeia", "pontos": pontos}])


def test_marca_de_corte_tem_linha_setas_e_letras(tmp_path):
    doc, _ = gerar(tmp_path, [SALA, {"tipo": "marca_corte", "nome": "a", "a": [-1, 3],
                                      "b": [11, 3]}])
    msp = doc.modelspace()
    assert doc.layers.get("CORTES").dxf.linetype == "DASHDOT"
    assert [e.dxf.text for e in msp.query('TEXT[layer=="CORTES"]')] == ["A", "A"]
    assert len(msp.query('CIRCLE[layer=="CORTES"]')) == 2
    assert len(msp.query('HATCH[layer=="CORTES"]')) == 2
    # olhando para a esquerda de a->b (a linha vai para +x, então para cima): círculos acima
    assert all(c.dxf.center.y > 3 for c in msp.query('CIRCLE[layer=="CORTES"]'))


def test_marca_de_corte_olhando_para_a_direita(tmp_path):
    doc, _ = gerar(tmp_path, [SALA, {"tipo": "marca_corte", "nome": "B", "a": [-1, 3],
                                      "b": [11, 3], "sentido": "direita"}])
    assert all(c.dxf.center.y < 3 for c in doc.modelspace().query('CIRCLE[layer=="CORTES"]'))


def test_escala_decide_o_tamanho_do_texto_e_da_cota(tmp_path):
    ops = [SALA, {"tipo": "texto", "texto": "X", "x": 1, "y": 1}]
    d100, a100 = gerar(tmp_path, ops, 100)
    d50, a50 = gerar(tmp_path, ops, 50)
    assert (altura_x(d100), altura_x(d50)) == (0.25, 0.125)
    assert "COSCIP-50" in [d.dxf.name for d in d50.dimstyles]
    assert a50.escala == 50


def test_nome_do_ambiente_usa_estilo_proprio_e_tamanho_de_3_mm(tmp_path):
    doc, _ = gerar(tmp_path, [SALA])
    nome = [e for e in doc.modelspace().query("TEXT") if e.dxf.text == "SALA 01"][0]
    assert nome.dxf.style == "COSCIP-AMBIENTE" and nome.dxf.height == 0.3


def test_escala_vai_no_json_e_planta_antiga_abre_em_1_100(tmp_path):
    auth = Authoring(tmp_path / "p.dxf", escala=75)
    auth.add([SALA])
    auth.build()
    assert Authoring.load(tmp_path / "p.dxf").escala == 75
    import json

    side = tmp_path / "p.coscip.json"
    dados = json.loads(side.read_text(encoding="utf-8"))
    del dados["escala"]  # planta criada antes da D1
    side.write_text(json.dumps(dados), encoding="utf-8")
    assert Authoring.load(tmp_path / "p.dxf").escala == 100


def test_pelo_mcp_escala_janela_e_leitura_do_motor(srv):
    erro, geral, texts, _ = call(srv, "criar_planta", caminho="d1.dxf", escala=50)
    assert not erro, texts
    pid = geral["planta_id"]
    erro, out, texts, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        SALA,
        {"tipo": "janela", "x": 5, "y": -0.075, "largura_m": 2},
        {"tipo": "cota_cadeia", "pontos": [[0, -1], [5, -1], [10, -1]]},
        {"tipo": "marca_corte", "nome": "A", "a": [-1, 3], "b": [11, 3]},
        {"tipo": "simbolo", "classe": "EXTINTOR", "x": 2, "y": 3, "agente": "PQS_ABC"}])
    assert not erro, texts
    assert out["escala_de_impressao"] == "1:50"
    assert out["simbolos_reconhecidos"]["EXTINTOR"] == 1
    assert "ALERTA_simbolos_nao_reconhecidos" not in out and "ALERTA_paredes" not in out

    erro, _, texts, _ = call(srv, "criar_planta", caminho="d1b.dxf", escala=7)
    assert erro


def test_retomar_com_nova_escala_regenera_o_desenho(srv):
    erro, geral, _, _ = call(srv, "criar_planta", caminho="d2.dxf")
    assert not erro
    call(srv, "desenhar_planta", planta_id=geral["planta_id"], operacoes=[SALA])
    erro, geral2, texts, _ = call(srv, "criar_planta", caminho="d2.dxf", retomar=True, escala=200)
    assert not erro, texts
    doc = ezdxf.readfile(srv.ws.get(geral2["planta_id"]).path)
    assert "COSCIP-200" in [d.dxf.name for d in doc.dimstyles]
