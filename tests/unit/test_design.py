"""Modo projeto: parâmetros conferidos nas NTs do repositório e os cálculos de dimensionamento.

O teste central é o dos parâmetros: cada valor de ``normative/projeto/parametros.yaml`` precisa
ter a citação encontrada no texto ingerido. Se uma NT for atualizada e o trecho mudar, acusa aqui.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest
from coscip_design import ParamError, extintores, hidrantes, load_params, saidas, sistemas

from coscip_normative import parse_markdown

FONTES = Path(__file__).resolve().parents[2] / "normative" / "fontes"


@pytest.fixture(scope="module")
def params():
    sources = {}
    for f in FONTES.glob("nt-2-0*.md"):
        text = parse_markdown(f.read_bytes(), f.name)
        sources[text.document] = text
    return load_params(sources)


def test_todos_os_parametros_conferem_no_texto_das_nts(params):
    resumo = params.resumo()
    assert resumo["nao_conferidos"] == {}
    assert resumo["linhas_de_populacao_nao_conferidas"] == []
    assert resumo["parametros"] >= 42 and resumo["linhas_de_populacao"] == 24
    assert params.get("hid.sistema.MEDIO_2").citacao == "NT 2-02, Tabela 1, p. 5"


def test_parametro_sem_citacao_conferida_e_recusado():
    vazio = load_params({})  # nenhuma NT carregada: nada confere
    assert vazio.resumo()["conferidos"] == 0
    with pytest.raises(ParamError, match="não conferida"):
        vazio.get("ext.area_max_m2")
    with pytest.raises(ParamError, match="não conferida"):
        saidas.dimensionar(vazio, {"ocupacao": "D-2",
                                   "pavimentos": [{"nome": "T", "area_m2": 100}]})


# --- extintores ---------------------------------------------------------------------------

def test_extintores_pela_area_e_pelo_minimo(params):
    m = extintores.dimensionar(params, {"risco": "MEDIO", "pavimentos": [
        {"nome": "Térreo", "area_m2": 420, "instalacoes_especiais": ["casa de bombas"]},
        {"nome": "2º", "area_m2": 100}]})
    terreo, segundo = m.resultados["quadro_por_pavimento"]
    assert terreo["por_area"] == 3 and terreo["total"] == 4  # 420/150 → 3, + casa de bombas
    assert segundo["por_area"] == 1 and segundo["adotado"] == 2  # mínimo de dois
    assert m.resultados["total_de_extintores"] == 6
    assert m.resultados["distancia_maxima_a_percorrer_m"] == 15
    assert "NT 2-01, Tabela 3, p. 5" in m.citacoes
    assert any("analisar_planta" in v for v in m.verificar_na_planta)


def test_extintor_unico_so_no_risco_pequeno_abaixo_de_50_m2(params):
    um = extintores.dimensionar(params, {"risco": "PEQUENO",
                                         "pavimentos": [{"nome": "Loja", "area_m2": 40}]})
    assert um.resultados["total_de_extintores"] == 1
    dois = extintores.dimensionar(params, {"risco": "MEDIO",
                                           "pavimentos": [{"nome": "Loja", "area_m2": 40}]})
    assert dois.resultados["total_de_extintores"] == 2


def test_risco_grande_pede_sobre_rodas_e_4a(params):
    m = extintores.dimensionar(params, {"risco": "GRANDE",
                                        "pavimentos": [{"nome": "Galpão", "area_m2": 950}]})
    assert m.resultados["quadro_por_pavimento"][0]["por_area"] == 10
    assert m.resultados["sobre_rodas"]["obrigatorio"] is True
    assert m.resultados["tipo_sugerido"]["capacidade_minima_classe_a"] == "4-A"


# --- saídas ---------------------------------------------------------------------------------

def test_saidas_populacao_e_larguras(params):
    m = saidas.dimensionar(params, {"ocupacao": "d-2", "pavimentos": [
        {"nome": "Térreo", "area_m2": 420, "descarga": True}, {"nome": "2º", "area_m2": 380}]})
    terreo, segundo = m.resultados["quadro_por_pavimento"]
    assert terreo["populacao"] == 60 and segundo["populacao"] == 55  # 420/7 e teto(380/7)
    assert terreo["largura_minima_acessos_m"] == 1.2
    assert m.resultados["escadas"]["populacao_de_calculo"] == 55


def test_saidas_grupo_f_com_lotacao_alta(params):
    m = saidas.dimensionar(params, {"ocupacao": "F-2",
                                    "pavimentos": [{"nome": "Salão", "area_m2": 450}]})
    (q,) = m.resultados["quadro_por_pavimento"]
    assert q["populacao"] == 450 and q["unidades_de_passagem_acesso"] == 5
    assert q["largura_minima_acessos_m"] == 2.75  # 5 × 0,55
    assert q["portas"].startswith("2 portas")  # N = 5 → duas portas
    assert m.resultados["minimo_de_saidas"] == 2
    assert any("barra" in p for p in m.pendencias)


def test_saidas_pede_o_dado_que_a_divisao_usa(params):
    with pytest.raises(ParamError, match="dormitorios"):
        saidas.dimensionar(params, {"ocupacao": "A-2",
                                    "pavimentos": [{"nome": "Tipo", "area_m2": 300}]})
    m = saidas.dimensionar(params, {"ocupacao": "A-2", "numero_de_pavimentos": 16,
                                    "pavimentos": [{"nome": "Tipo", "dormitorios": 12}]})
    assert m.resultados["quadro_por_pavimento"][0]["populacao"] == 24
    assert "minimo_de_escadas" not in m.resultados["escadas"]  # A-2 é exceção do 5.3.2.2
    with pytest.raises(ParamError, match="sem linha no Anexo A"):
        saidas.dimensionar(params, {"ocupacao": "M-1",
                                    "pavimentos": [{"nome": "T", "area_m2": 100}]})


# --- hidrantes ------------------------------------------------------------------------------

def test_hazen_williams_bate_com_a_conta_a_mao():
    # Q = 400 L/min, C = 120, D = 68 mm → J ≈ 0,0692 m/m; V = Q/A ≈ 1,84 m/s
    assert math.isclose(hidrantes.hazen_williams(400, 120, 68), 0.0692, rel_tol=0.01)
    assert math.isclose(hidrantes.velocidade(400, 68), 1.836, rel_tol=0.01)


def test_rti_base_acrescimo_e_teto(params):
    def rti(risco, n):
        return hidrantes.dimensionar(params, {"risco": risco, "numero_de_hidrantes": n}
                                     ).resultados["rti_l"]
    assert rti("MEDIO_1", 4) == 6000 and rti("MEDIO_2", 6) == 13000
    assert rti("GRANDE", 4) == 30000 and rti("GRANDE", 200) == 60000  # limite máximo


def test_altura_manometrica_soma_as_parcelas_do_anexo_b(params):
    m = hidrantes.dimensionar(params, {
        "risco": "MEDIO_2", "numero_de_hidrantes": 6, "desnivel_m": 8,
        "succao": [{"nome": "sucção", "comprimento_m": 2, "comprimento_equivalente_m": 6,
                    "diametro_interno_mm": 80, "colar": True}],
        "recalque": [{"nome": "prumada", "comprimento_m": 25, "comprimento_equivalente_m": 18,
                      "diametro_interno_mm": 68}]})
    r = m.resultados
    perdas = r["perdas_mca"]
    assert r["vazao_por_hidrante_lpm"] == 200  # 400 L/min entre 2 hidrantes
    total = perdas["succao"] + perdas["recalque"] + perdas["mangueira"] + 35 + 8
    assert math.isclose(r["bomba"]["altura_manometrica_mca"], total, abs_tol=0.02)
    assert r["hidrante_de_recalque"]["tipo"].startswith("duplo")
    assert any("Hazen-Williams" in p for p in m.premissas)  # o que a NT não fixa fica à vista


def test_velocidade_e_pressao_acima_do_limite_viram_pendencia(params):
    m = hidrantes.dimensionar(params, {
        "risco": "GRANDE", "numero_de_hidrantes": 4, "desnivel_m": 60,
        "recalque": [{"nome": "tubo fino", "comprimento_m": 80, "diametro_interno_mm": 53}]})
    assert any("velocidade" in p and "5 m/s" in p for p in m.pendencias)
    assert any("100 mca" in p for p in m.pendencias)


def test_reservatorio_elevado_pode_dispensar_bomba_no_calculo(params):
    m = hidrantes.dimensionar(params, {
        "risco": "PEQUENO", "numero_de_hidrantes": 2, "desnivel_m": -25,
        "recalque": [{"nome": "prumada", "comprimento_m": 20, "diametro_interno_mm": 68}]})
    assert m.resultados["bomba"]["necessaria"] is False


# --- iluminação e alarme ----------------------------------------------------------------------

def test_iluminacao_e_alarme_trazem_so_o_que_as_nts_fixam(params):
    ilu = sistemas.iluminacao(params, "H-3")
    assert ilu.resultados["autonomia_min"] == 120 and "refúgio" in ilu.resultados["locais"]
    assert sistemas.iluminacao(params, "D-2").resultados["autonomia_min"] == 60
    assert any("NBR 10898" in p for p in ilu.pendencias)
    ala = sistemas.alarme(params)
    assert ala.resultados["acionador_distancia_max_m"] == 30
    assert "## Alarme de incêndio (NT 2-07)" in ala.markdown()
