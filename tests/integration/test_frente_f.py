"""Frente F: elementos tirados das pranchas de referência (telhado nos cortes e fachadas, figura
humana, rótulos de classe da NT 2-20, letreiro, planta de situação, títulos de vista e quadros)."""
from __future__ import annotations

import math

import ezdxf
import pytest

from coscip_mcp.autoria import Authoring, AuthoringError

SALA = {"tipo": "sala", "nome": "Salão", "retangulo": [0, 0, 10, 6]}
SALA2 = {"tipo": "sala", "nome": "Cozinha", "retangulo": [10.15, 0, 14, 6]}
PORTA = {"tipo": "porta", "x": 2, "y": -0.075, "largura_m": 1.0, "altura_m": 2.1}
JAN = {"tipo": "janela", "x": 6, "y": -0.075, "largura_m": 2.0, "altura_m": 1.2,
       "peitoril_m": 0.9}
TELHADO = {"tipo": "duas_aguas", "cumeeira": "x", "inclinacao_pct": 20, "beiral_m": 0.5,
           "telha": "telha ondulada de fibrocimento"}
EDIF = {"tipo": "edificacao", "pe_direito_m": 3.0, "laje_m": 0.2, "forro": "forro de gesso",
        "cobertura": TELHADO}
SECAO_Y = {"tipo": "secao", "nome": "a", "a": [5, -2], "b": [5, 8], "sentido": "direita",
           "x": 40, "y": 0, "classe_parede": "I"}


def gerar(tmp_path, ops, escala=100):
    auth = Authoring(tmp_path / "f.dxf", escala=escala)
    auth.add(ops)
    resumo = auth.build()
    return ezdxf.readfile(tmp_path / "f.dxf"), resumo


def textos(doc, camada=None):
    q = f'TEXT[layer=="{camada}"]' if camada else "TEXT"
    return [e.dxf.text for e in doc.modelspace().query(q)]


def test_corte_transversal_mostra_as_duas_aguas_e_a_cumeeira(tmp_path):
    doc, r = gerar(tmp_path, [EDIF, SALA, SALA2, PORTA, SECAO_Y])
    s = r["vistas"]["secoes"][0]
    # pegada de 6,30 m (6 + 2 x 0,15): meia largura 3,15 x 20 % = 0,63 acima da laje (3,20)
    assert s["cumeeira_m"] == pytest.approx(3.2 + 0.63 + 0.06, abs=0.01)
    assert s["altura_total_m"] == s["cumeeira_m"]
    tel = doc.modelspace().query('LWPOLYLINE[layer=="VISTA_COBERTURA"]')
    assert len(tel) == 1
    zs = [p[1] for p in tel[0].get_points("xy")]
    assert max(zs) == pytest.approx(s["cumeeira_m"], abs=0.01)
    assert min(zs) == pytest.approx(3.2 - 0.5 * 0.2, abs=0.01)  # beiral abaixo da laje
    t = textos(doc, "VISTA_TEXTO")
    assert "TELHA ONDULADA DE FIBROCIMENTO" in t and "FORRO DE GESSO" in t
    assert any("(cumeeira)" in x for x in t)


def test_corte_leva_figura_humana_e_rotulos_de_classe(tmp_path):
    doc, r = gerar(tmp_path, [EDIF, SALA, SECAO_Y])
    s = r["vistas"]["secoes"][0]
    assert s["figura_humana"] is True and s["rotulos_de_classe"] == 1
    msp = doc.modelspace()
    fig = msp.query('LWPOLYLINE[layer=="VISTA_ESCALA"]')
    assert len(fig) == 1 and len(msp.query('CIRCLE[layer=="VISTA_ESCALA"]')) == 1
    ys = [p[1] for p in fig[0].get_points("xy")]
    assert min(ys) == pytest.approx(0.0) and max(ys) == pytest.approx(1.49)
    assert sorted(textos(doc, "ROTULO_CLASSE")) == ["CLASSE", "I", "PAREDE"]


def test_figura_humana_desligada(tmp_path):
    doc, r = gerar(tmp_path, [EDIF, SALA, {**SECAO_Y, "figura_humana": False}])
    assert "figura_humana" not in r["vistas"]["secoes"][0] or \
        r["vistas"]["secoes"][0]["figura_humana"] is False
    assert not doc.modelspace().query('LWPOLYLINE[layer=="VISTA_ESCALA"]')


def test_classe_invalida_e_recusada(tmp_path):
    with pytest.raises(ValueError, match="classe_parede"):  # validação do esquema
        gerar(tmp_path, [EDIF, SALA, {**SECAO_Y, "classe_parede": "Z"}])


def test_fachada_com_telhado_vidro_e_letreiro(tmp_path):
    edif = {**EDIF, "platibanda_m": 0.0, "pe_direito_m": 3.6}
    doc, r = gerar(tmp_path, [edif, SALA, SALA2, PORTA, JAN,
                              {"tipo": "fachada", "lado": "sul", "x": 40, "y": 20,
                               "letreiro": "Restaurante"}])
    f = r["vistas"]["fachadas"][0]
    assert f["letreiro"] == "desenhado" and f["altura_total_m"] > 3.8
    msp = doc.modelspace()
    assert "RESTAURANTE" in textos(doc, "VISTA_TEXTO")
    assert len(msp.query('LINE[layer=="VISTA_ESQ"]')) >= 4  # traços de vidro (2 por folha)
    assert len(msp.query('LWPOLYLINE[layer=="VISTA_COBERTURA"]')) == 2  # silhueta e beiral


def test_letreiro_sem_espaco_e_avisado(tmp_path):
    edif = {"tipo": "edificacao", "pe_direito_m": 2.4, "laje_m": 0.1}
    porta_alta = {**PORTA, "altura_m": 2.3}
    _, r = gerar(tmp_path, [edif, SALA, porta_alta,
                            {"tipo": "fachada", "lado": "sul", "x": 40, "y": 20,
                             "letreiro": "Loja"}])
    assert "sem espaço" in r["vistas"]["fachadas"][0]["letreiro"]


def test_rotulo_classe_na_planta(tmp_path):
    doc, _ = gerar(tmp_path, [SALA, {"tipo": "rotulo_classe", "elemento": "piso",
                                     "classe": "II-A", "x": 5, "y": 3}])
    assert sorted(textos(doc, "ROTULO_CLASSE")) == ["CLASSE", "II-A", "PISO"]
    assert len(doc.modelspace().query('LWPOLYLINE[layer=="ROTULO_CLASSE"]')) == 1


SIT = {"tipo": "situacao", "escala": 500,
       "lote": [[100, 0], [130, 0], [130, 40], [100, 40]],
       "edificacoes": [{"poligono": [[105, 10], [125, 10], [125, 30], [105, 30]],
                        "rotulo": "Bloco A", "caimentos": [[110, 15, -90]]}],
       "ruas": [{"nome": "Rua A", "eixo": [[90, -6], [160, -6]], "largura_m": 10},
                {"nome": "Rua B", "eixo": [[150, -40], [150, 60]], "largura_m": 12}],
       "distancias": [{"a": [130, -3], "b": [144, -3]}],
       "norte_graus": 30}


def test_situacao_desenha_lote_ruas_edificacao_e_norte(tmp_path):
    doc, r = gerar(tmp_path, [SALA, SIT])
    s = r["situacao"]
    assert s["area_do_lote_m2"] == 1200.0 and s["area_projecao_edificacoes_m2"] == 400.0
    assert s["taxa_de_ocupacao"] == pytest.approx(0.333, abs=0.001)
    msp = doc.modelspace()
    assert len(msp.query('HATCH[layer=="SITUACAO_EDIF"]')) == 1
    assert {"RUA A", "RUA B", "BLOCO A"} <= set(textos(doc, "SITUACAO_TEXTO"))
    norte = msp.query('INSERT[layer=="NORTE"]')
    assert len(norte) == 1 and norte[0].dxf.name == "NORTE"
    assert norte[0].dxf.rotation == 30
    assert len(msp.query('LWPOLYLINE[layer=="SITUACAO_RUA"]')) >= 6  # meios-fios e quebras
    # nomes e cotas sempre legíveis (nada de cabeça para baixo)
    for e in msp.query('TEXT[layer=="SITUACAO_TEXTO"]'):
        assert -90 < (e.dxf.rotation + 180) % 360 - 180 <= 90
    cotas = msp.query('DIMENSION[layer=="SITUACAO_COTA"]')
    assert len(cotas) == 5  # 4 lados do lote + a distância à esquina
    for d in cotas:
        p1, p2 = d.dxf.defpoint2, d.dxf.defpoint3
        ang = math.degrees(math.atan2(p2.y - p1.y, p2.x - p1.x)) % 360
        assert not 90 < ang <= 270


def test_situacao_cota_da_frente_vai_para_dentro_do_lote(tmp_path):
    doc, _ = gerar(tmp_path, [SALA, SIT])
    frente = [d for d in doc.modelspace().query('DIMENSION[layer=="SITUACAO_COTA"]')
              if abs(d.dxf.defpoint2.y) < 1e-6 and abs(d.dxf.defpoint3.y) < 1e-6]
    assert len(frente) == 1 and frente[0].dxf.defpoint.y > 0  # linha de cota dentro do lote


def test_situacao_recusa_edificacao_fora_do_lote(tmp_path):
    ruim = {**SIT, "edificacoes": [{"poligono": [[125, 10], [140, 10], [140, 20], [125, 20]]}]}
    with pytest.raises(AuthoringError, match="sai do lote"):
        gerar(tmp_path, [SALA, ruim])


def test_folha_titulo_numerado_e_quadro(tmp_path):
    folha = {"tipo": "folha", "nome": "P1", "formato": "A3", "quadro_de_areas": False,
             "vistas": [{"titulo": "Planta baixa", "janela": [-1, -1, 11, 7]}],
             "quadros": [{"titulo": "Cálculo das saídas", "linhas": ["N = P / C"]}]}
    doc, r = gerar(tmp_path, [SALA, folha])
    assert r["folhas"][0]["quadros"] == 1
    lay = doc.layouts.get("P1")
    t = [e.dxf.text for e in lay.query("TEXT")]
    assert "1" in t and "PLANTA BAIXA" in t and "ESCALA 1:100" in t
    assert "CÁLCULO DAS SAÍDAS" in t and "• N = P / C" in t
    assert lay.query("CIRCLE")  # círculo com o número da vista
