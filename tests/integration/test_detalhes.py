"""Frente G: detalhes de instalação cotados com medidas de NT conferidas (det.* no YAML)."""
from __future__ import annotations

import ezdxf
import pytest

from coscip_mcp.autoria import Authoring, AuthoringError

SALA = {"tipo": "sala", "nome": "Salão", "retangulo": [0, 0, 10, 6]}


def gerar(tmp_path, *detalhes):
    auth = Authoring(tmp_path / "d.dxf", escala=100)
    auth.add([SALA, *detalhes])
    r = auth.build()
    return ezdxf.readfile(tmp_path / "d.dxf"), r


def textos(doc):
    return [e.dxf.text for e in doc.modelspace().query('TEXT[layer=="DETALHE_TEXTO"]')]


def cotas(doc):
    out = []
    for d in doc.modelspace().query('DIMENSION[layer=="DETALHE_COTA"]'):
        out += [e.text for e in doc.blocks.get(d.dxf.geometry) if e.dxftype() == "MTEXT"]
    return out


def test_extintor_cota_a_alca_e_a_placa_com_as_medidas_da_nt(tmp_path):
    doc, r = gerar(tmp_path, {"tipo": "detalhe", "modelo": "extintor", "x": 30, "y": 0})
    det = r["detalhes"][0]
    assert det["escala"] == "1:15"
    fontes = {m["fonte"] for m in det["medidas_normativas"]}
    assert any(f.startswith("NT 2-01, 5.2.1") for f in fontes)
    assert any(f.startswith("NT 2-05, 4.7") for f in fontes)
    c = cotas(doc)
    assert "1,60" in c and "1,80" in c
    t = " ".join(textos(doc))
    assert "NO MÁXIMO 1,60 m" in t and "(NT 2-01, 5.2.1 b)" in t
    assert "DETALHE - INSTALAÇÃO DO EXTINTOR" in t
    assert "PISO SOB O EXTINTOR" not in t  # só com piso_demarcado


def test_extintor_com_piso_demarcado(tmp_path):
    doc, _ = gerar(tmp_path, {"tipo": "detalhe", "modelo": "extintor", "x": 30, "y": 0,
                              "piso_demarcado": True})
    t = " ".join(textos(doc))
    assert "0,70 x 0,70 m EM VERMELHO" in t and "(NT 2-01, 6.12)" in t
    assert "0,70" in cotas(doc)


@pytest.mark.parametrize(("risco", "dims", "registro"), [
    ("MEDIO_1", "75 cm DE ALTURA, 45 cm DE LARGURA E 17 cm", "63 mm"),
    ("GRANDE", "80 cm DE ALTURA, 60 cm DE LARGURA E 17 cm", "75 mm")])
def test_abrigo_pelo_risco(tmp_path, risco, dims, registro):
    doc, r = gerar(tmp_path, {"tipo": "detalhe", "modelo": "abrigo_mangueira", "x": 30, "y": 0,
                              "risco": risco, "base_m": 0.9})
    t = " ".join(textos(doc))
    assert dims in t and f"REGISTRO GLOBO ANGULAR DE {registro}" in t
    assert ("1,00 x 1,00 m PINTADO DE VERMELHO" in t) == (risco == "GRANDE")
    assert "base do abrigo a 0,90 m do piso" in r["detalhes"][0]["dados_informados"]


def test_abrigo_sem_base_e_recusado(tmp_path):
    with pytest.raises(AuthoringError, match="base_m"):
        gerar(tmp_path, {"tipo": "detalhe", "modelo": "abrigo_mangueira", "x": 30, "y": 0,
                         "risco": "MEDIO_1"})


def test_recalque_passeio_simples_e_duplo(tmp_path):
    doc, r = gerar(tmp_path, {"tipo": "detalhe", "modelo": "recalque_passeio", "x": 30, "y": 0,
                              "risco": "PEQUENO", "vazao_lpm": 200})
    assert r["detalhes"][0]["recalque_duplo"] is False
    t = " ".join(textos(doc))
    assert "0,30 x 0,40 m" in t and "PROFUNDIDADE MÁXIMA 0,40 m" in t
    assert "0,15" in cotas(doc) and "0,40" in cotas(doc)
    _, r2 = gerar(tmp_path, {"tipo": "detalhe", "modelo": "recalque_passeio", "x": 30, "y": 0,
                             "risco": "MEDIO_2", "vazao_lpm": 400})
    assert r2["detalhes"][0]["recalque_duplo"] is True


def test_recalque_fachada_fora_da_faixa_e_recusado(tmp_path):
    with pytest.raises(AuthoringError, match="1,00 a 1,20"):
        gerar(tmp_path, {"tipo": "detalhe", "modelo": "recalque_fachada", "x": 30, "y": 0,
                         "risco": "PEQUENO", "altura_m": 1.5})


def test_bloco_autonomo_autonomia_por_divisao(tmp_path):
    doc, _ = gerar(tmp_path, {"tipo": "detalhe", "modelo": "bloco_autonomo", "x": 30, "y": 0,
                              "altura_m": 2.2, "divisao": "H-2"})
    t = " ".join(textos(doc))
    assert "AUTONOMIA MÍNIMA DE 120 min" in t and "2,20" in cotas(doc)
    doc, _ = gerar(tmp_path, {"tipo": "detalhe", "modelo": "bloco_autonomo", "x": 30, "y": 0,
                              "altura_m": 2.2, "divisao": "F-8"})
    assert "AUTONOMIA MÍNIMA DE 60 min" in " ".join(textos(doc))
    with pytest.raises(AuthoringError, match="altura_m"):
        gerar(tmp_path, {"tipo": "detalhe", "modelo": "bloco_autonomo", "x": 30, "y": 0})


def test_sinalizacao_niveis(tmp_path):
    doc, _ = gerar(tmp_path, {"tipo": "detalhe", "modelo": "sinalizacao_saida", "x": 30,
                              "y": 0})
    c = cotas(doc)
    assert "1,80" in c and "0,50" in c
    t = " ".join(textos(doc))
    assert "(NT 2-05, 4.7)" in t and "(NT 2-05, 4.5)" in t


def test_detalhes_nao_viram_equipamento_na_contagem(tmp_path):
    _, r = gerar(tmp_path, {"tipo": "detalhe", "modelo": "extintor", "x": 30, "y": 0},
                 {"tipo": "quadro_resumo", "x": 60, "y": 20})
    c = r["quadro_resumo"]["contagens"]
    assert c["extintores"] == 0 and c["placas"] == 0  # o detalhe é desenho, não equipamento


# --- G2: nível de desenho da prancha de referência ------------------------------------------


def test_extintor_parede_e_piso_com_baloes_tabela_e_placa_oficial(tmp_path):
    from coscip_analysis.symbols import _SIGN_CODE

    doc, _ = gerar(tmp_path, {"tipo": "detalhe", "modelo": "extintor", "x": 30, "y": 0})
    t = textos(doc)
    assert {"NA PAREDE", "NO PISO", "Nº", "DESCRIÇÃO", "SUPORTE PARA EXTINTOR NO PISO"} <= set(t)
    assert "SUPORTE DE FIXAÇÃO" in t and "PARAFUSO E BUCHA" in t and "ALVENARIA" in t
    assert {"SÍMBOLO: QUADRADA", "FUNDO: VERMELHA", "CÓDIGO: E-5"} <= set(t)
    picto = [i for i in doc.modelspace().query("INSERT") if i.dxf.name.startswith("DETV_PICT")]
    assert picto, "a placa usa o pictograma oficial vetorizado da NT 2-05"
    for i in picto:  # o leitor não pode contar a placa do detalhe como sinalização
        assert _SIGN_CODE.search(i.dxf.name) is None, i.dxf.name


def test_extintor_so_na_parede(tmp_path):
    doc, _ = gerar(tmp_path, {"tipo": "detalhe", "modelo": "extintor", "x": 30, "y": 0,
                              "montagem": "parede"})
    t = textos(doc)
    assert "NA PAREDE" in t and "NO PISO" not in t
    assert "SUPORTE PARA EXTINTOR NO PISO" not in t


def test_extintor_alto_demais_e_recusado(tmp_path):
    with pytest.raises(AuthoringError, match="não cabe"):
        gerar(tmp_path, {"tipo": "detalhe", "modelo": "extintor", "x": 30, "y": 0,
                         "extintor_m": [0.25, 1.55]})


def test_baloes_do_abrigo_batem_com_a_tabela(tmp_path):
    doc, _ = gerar(tmp_path, {"tipo": "detalhe", "modelo": "abrigo_mangueira", "x": 30, "y": 0,
                              "risco": "MEDIO_1", "base_m": 0.9})
    t = textos(doc)
    numeros = [s for s in t if s.isdigit()]
    for n in "123456":
        assert numeros.count(n) >= 2, n  # o balão no desenho e a linha na tabela
    assert "ESGUICHO REGULÁVEL Ø38 mm" in t


# --- G3: GLP (NT 3-02) ------------------------------------------------------------------------


def test_central_glp_ate_90kg_e_acima(tmp_path):
    doc, r = gerar(tmp_path, {"tipo": "detalhe", "modelo": "central_glp", "x": 30, "y": 0,
                              "recipiente": "P-13", "recipientes": 2})
    t = " ".join(textos(doc))
    assert "CAPACIDADE 26 kg (ATÉ 90 kg): PAREDES E COBERTURA EM ALVENARIA OU CONCRETO" in t
    assert "1 EXTINTOR(ES) 20-B:C OU PQS 6 kg" in t and "NT 3-02, 5.4.2)" in t
    assert "1,80" in cotas(doc)  # altura interna útil mínima
    assert "0,64 m²" in t  # 0,32 + 0,32 domina 10% da planta pequena
    _, r2 = gerar(tmp_path, {"tipo": "detalhe", "modelo": "central_glp", "x": 30, "y": 0,
                             "recipiente": "P-190", "recipientes": 10})
    m = {x["o_que"]: x["valor"] for x in r2["detalhes"][0]["medidas_normativas"]}
    assert any("SOBRE RODAS" in v for v in m.values())  # 1900 kg > 1800


def test_central_glp_placa_e_recusas(tmp_path):
    doc, _ = gerar(tmp_path, {"tipo": "detalhe", "modelo": "central_glp", "x": 30, "y": 0,
                              "recipiente": "P-45", "recipientes": 4})
    t = textos(doc)
    assert {"PERIGO", "GÁS INFLAMÁVEL", "PROIBIDO FUMAR"} <= set(t)
    assert any("190 x 95 mm" in s for s in t)
    with pytest.raises(AuthoringError, match="recipientes"):
        gerar(tmp_path, {"tipo": "detalhe", "modelo": "central_glp", "x": 30, "y": 0})
    with pytest.raises(AuthoringError, match="pedem abrigo"):
        gerar(tmp_path, {"tipo": "detalhe", "modelo": "central_glp", "x": 30, "y": 0,
                         "recipiente": "P-45", "recipientes": 4, "abrigo_m": [1.0, 0.5]})


def test_reguladores_de_glp(tmp_path):
    doc, r = gerar(tmp_path,
                   {"tipo": "detalhe", "modelo": "regulador_1_estagio", "x": 30, "y": 0,
                    "bitola_rede": '3/4"', "bitola_regulador": '1/2"'},
                   {"tipo": "detalhe", "modelo": "regulador_2_estagio", "x": 40, "y": 0})
    t = textos(doc)
    assert 'REGISTRO GERAL DE CORTE 3/4"' in t and "MANÔMETRO" in t
    assert "REGULADOR DE 1º ESTÁGIO COM MANÔMETRO" in t
    assert "REGISTRO DO REGULADOR" in t and "MANGUEIRA FLEXÍVEL" in t
    j = " ".join(t)
    assert "(NT 3-02, 6.2)" in j and "(NT 3-02, 6.1)" in j
    assert "(DIÂMETROS NÃO INFORMADOS)" in j  # o 2º estágio veio sem bitola
