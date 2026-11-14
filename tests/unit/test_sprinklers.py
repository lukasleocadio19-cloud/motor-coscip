"""Chuveiros automáticos: memorial da NT 2-03 parte 1, malha de bicos e hidráulica."""
from __future__ import annotations

import math

import pytest
from coscip_design import ParamError, load_params
from coscip_design.rede_sprinklers import (
    DN_SERIE,
    Criterios,
    Zona,
    escolher_dn,
    malha,
    perda_bar,
    projetar,
)
from coscip_design.sprinklers import REFERENCIA, dimensionar

from coscip_mcp import norms

OH1 = Criterios(densidade_mm_min=6.1, area_operacao_m2=139.0, area_max_bico_m2=12.1,
                espacamento_max_m=4.6)
RET = ((0, 0), (16.6, 0), (16.6, 10.8), (0, 10.8))


@pytest.fixture(scope="module")
def params():
    return load_params(norms.load_base().sources)


# --- parâmetros da NT 2-03 -----------------------------------------------------------------------


def test_parametros_da_nt_2_03_conferem_no_texto(params):
    for pid in ("spk.rti_duracao_min", "spk.shaft", "spk.recalque", "spk.dispensa_camara_fria",
                "spk.tubos_acima_do_solo", "spk.dispensa_sanitarios", "spk.vga"):
        p = params.get(pid)  # levanta ParamError se a citação não confere
        assert p.verificado and p.documento == "NT 2-03 P1" and p.pagina
    assert params.get("spk.rti_duracao_min").valor == {"LEVE": 30, "ORDINARIO": 30,
                                                       "EXTRAORDINARIO": 60}
    assert params.resumo()["nao_conferidos"] == {}


def test_citacao_por_pagina_recusa_termo_que_nao_esta_na_pagina():
    from coscip_normative.sources import verify_page_citation

    fontes = norms.load_base().sources
    ok = verify_page_citation(fontes, "NT 2-03 P1", "5.7.3", 7, ("storz",))
    assert ok.verified and ok.page == 7
    ruim = verify_page_citation(fontes, "NT 2-03 P1", "5.7.3", 7, ("termo inventado",))
    assert not ruim.verified and ruim.missing_terms == ("termo inventado",)
    assert not verify_page_citation(fontes, "NT 2-03 P1", "x", 99, ()).verified


# --- memorial ------------------------------------------------------------------------------


def base(**kw):
    return {"classe": "ORDINARIO_1", "grupo_divisao": "F-8",
            "ambientes": [{"nome": "Salão", "area_m2": 179.0}], **kw}


def passo(m, titulo):
    return next(p for p in m.as_dict()["memorial"] if p["passo"].startswith(titulo))


def test_rti_usa_o_tempo_do_anexo_b_e_a_vazao_do_maior_risco(params):
    m = dimensionar(params, base())
    q = m.resultados["vazao_do_sistema_lpm"]
    assert m.resultados["duracao_min"] == 30
    assert m.resultados["rti_sprinklers_l"] == pytest.approx(q * 30, abs=3)  # q sai com 1 casa
    p = passo(m, "Reserva técnica")
    assert "NT 2-03 P1, Anexo B - Tabela 1, p. 9" in p["base_normativa"]
    ext = dimensionar(params, base(classe="EXTRAORDINARIO_1"))
    assert ext.resultados["duracao_min"] == 60
    assert ext.resultados["rti_sprinklers_l"] == pytest.approx(
        ext.resultados["vazao_do_sistema_lpm"] * 60, abs=6)


def test_criterios_que_a_nt_nao_fixa_saem_como_premissa_a_conferir(params):
    m = dimensionar(params, base())
    ref = REFERENCIA["ORDINARIO_1"]
    assert m.resultados["criterios"]["densidade_mm_min"] == ref["densidade"]
    premissas = " ".join(m.premissas)
    assert "NFPA 13" in premissas and "NÃO está na base" in premissas
    assert "NBR 10897" in premissas  # a norma adotada, a conferir
    # valores informados pelo projetista não viram premissa de referência
    m2 = dimensionar(params, base(densidade_mm_min=7.0, area_operacao_m2=150, area_max_bico_m2=11,
                                   espacamento_max_m=4.0))
    assert m2.resultados["criterios"]["densidade_mm_min"] == 7.0
    assert not any("valores de referência" in p for p in m2.premissas)


def test_dispensas_da_nt_por_ambiente(params):
    m = dimensionar(params, {"classe": "ORDINARIO_1", "ambientes": [
        {"nome": "WC", "area_m2": 10, "tipo": "SANITARIO"},
        {"nome": "Vestiário", "area_m2": 15, "tipo": "VESTIARIO"},
        {"nome": "Subestação pequena", "area_m2": 18, "tipo": "SUBESTACAO"},
        {"nome": "Subestação grande", "area_m2": 30, "tipo": "SUBESTACAO"},
        {"nome": "Câmara fria", "area_m2": 10, "tipo": "CAMARA_FRIA", "temperatura_c": 2},
        {"nome": "Câmara quente", "area_m2": 10, "tipo": "CAMARA_FRIA", "temperatura_c": 12},
        {"nome": "CPD", "area_m2": 15, "tipo": "CPD", "compartimentado_30min": True,
         "substituir_por_detector": True},
        {"nome": "CPD grande", "area_m2": 30, "tipo": "CPD", "compartimentado_30min": True,
         "substituir_por_detector": True},
        {"nome": "Varanda", "area_m2": 20, "tipo": "VARANDA_ABERTA"},
        {"nome": "Entreforro", "area_m2": 50, "tipo": "ENTREFORRO"},
        {"nome": "Entreforro com termo", "area_m2": 50, "tipo": "ENTREFORRO",
         "termo_de_compromisso": True}]})
    dec = {a["ambiente"]: a["decisao"] for a in m.resultados["ambientes"]}
    assert dec == {"WC": "DISPENSADO", "Vestiário": "PROTEGER",
                   "Subestação pequena": "DISPENSADO", "Subestação grande": "PROTEGER",
                   "Câmara fria": "DISPENSADO", "Câmara quente": "PROTEGER",
                   "CPD": "DETECTORES", "CPD grande": "PROTEGER", "Varanda": "DISPENSADO",
                   "Entreforro": "PROTEGER", "Entreforro com termo": "DISPENSADO"}
    protegida = sum(a["area_m2"] for a in m.resultados["ambientes"] if a["decisao"] == "PROTEGER")
    assert m.resultados["area_protegida_m2"] == protegida
    pend = " ".join(m.pendencias)
    assert "Quadro 1" in pend and "NT 2-18" in pend and "30 min de TRRF" in pend


def test_bicos_minimos_por_area(params):
    m = dimensionar(params, {"classe": "ORDINARIO_1", "ambientes": [
        {"nome": "A", "area_m2": 100}, {"nome": "B", "area_m2": 12.1}]})
    assert m.resultados["bicos_minimos_por_area"] == math.ceil(100 / 12.1) + 1


def test_hidrantes_conjugados_somam_a_reserva_e_o_reservatorio_unico_acusa_70_por_cento(params):
    m = dimensionar(params, base(hidrantes_conjugados=True, rti_hidrantes_l=12000,
                                  volume_reservatorio_l=40000))
    assert m.resultados["rti_total_l"] == m.resultados["rti_sprinklers_l"] + 12000
    assert any("5.4.4" in p and "abastecimento predial" in p for p in m.pendencias)
    folgado = dimensionar(params, base(hidrantes_conjugados=True, rti_hidrantes_l=12000,
                                        volume_reservatorio_l=500000))
    assert not any("5.4.4" in p for p in folgado.pendencias)
    sem_dado = dimensionar(params, base(hidrantes_conjugados=True))
    assert any("rti_hidrantes_l" in p for p in sem_dado.pendencias)


def test_cpvc_so_no_risco_leve_com_bico_de_resposta_rapida(params):
    ruim = dimensionar(params, base(tubo="CPVC"))
    assert any("CPVC" in p and "5.3.1" in p for p in ruim.pendencias)
    bom = dimensionar(params, {"classe": "LEVE", "resposta": "RAPIDA", "tubo": "CPVC"})
    assert not any("CPVC" in p for p in bom.pendencias)


def test_controle_shaft_e_recalque(params):
    m = dimensionar(params, base(pavimentos_protegidos=3, prumada_atravessa_pavimentos=True,
                                  reservatorio_acima_do_teto=False))
    texto = passo(m, "Dispositivos")["resultado"]
    assert "5.5.1" in texto and "comando secundário" not in texto.split(";")[0].replace(
        "não admite comando secundário", "")
    assert "5.5.5" in texto
    shaft = passo(m, "Prisma vertical")
    assert shaft["resultado"] == "exigido" and shaft["valores"]["largura_min_cm"] == 50
    rec = passo(m, "Hidrante de recalque")
    assert "2 saídas Storz" in rec["resultado"] and "SPRINKLER" in rec["resultado"]
    isento = dimensionar(params, {"classe": "LEVE", "grupo_divisao": "A-2",
                                   "prumada_atravessa_pavimentos": True,
                                   "pavimentos_computaveis": 4})
    assert "dispensado" in passo(isento, "Prisma vertical")["resultado"]


def test_sem_zonas_avisa_que_nao_ha_perda_de_carga(params):
    m = dimensionar(params, base())
    assert any("zonas" in p for p in m.pendencias)
    assert m.resultados["vazao_do_sistema_lpm"] == pytest.approx(
        m.resultados["bicos_na_area_de_operacao"] * 6.1 * 12.1, abs=0.2)


def test_com_zona_a_vazao_inclui_as_perdas_e_a_pressao_na_base_aparece(params):
    m = dimensionar(params, base(zonas=[{"nome": "Salão", "retangulo": [0, 0, 16.6, 10.8],
                                          "alimentacao": [17.5, 5]}]))
    z = m.resultados["zonas"][0]
    assert z["vazao_total_lpm"] >= m.resultados["bicos_na_area_de_operacao"] * 6.1 * 12.1 - 1
    assert m.resultados["vazao_do_sistema_lpm"] == z["vazao_total_lpm"]
    assert passo(m, "Pressão exigida")["resultado"] == z["pressao_na_base_da_prumada_mca"]


def test_entrada_invalida_e_recusada(params):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        dimensionar(params, {"classe": "INVENTADA"})
    with pytest.raises(ValidationError):
        dimensionar(params, base(zonas=[{"nome": "Z", "alimentacao": [0, 0]}]))  # sem forma
    assert ParamError  # a importação existe para quem precisa tratar parâmetro não conferido


# --- malha ---------------------------------------------------------------------------------


def test_malha_respeita_espacamento_e_area_por_bico():
    pontos, ori, esp = malha(Zona("Z", RET, (17, 5)), OH1)
    assert ori == "x" and esp["entre_bicos_m"] <= 4.6 and esp["entre_ramais_m"] <= 4.6
    assert esp["area_por_bico_m2"] <= 12.1
    assert len(pontos) == math.ceil(16.6 / esp["entre_bicos_m"] - 1e-9) * 3
    xs = sorted({round(x, 3) for _, _, x, _ in pontos})
    assert xs[0] == pytest.approx(esp["entre_bicos_m"] / 2, abs=1e-3)  # meio espaço da parede


def test_area_pequena_ainda_recebe_bico():
    pontos, _, _ = malha(Zona("Z", ((0, 0), (2, 0), (2, 2), (0, 2)), (3, 1)), OH1)
    assert len(pontos) == 1


def test_area_maxima_por_bico_aumenta_o_numero_de_bicos():
    zona = Zona("Z", ((0, 0), (9, 0), (9, 9), (0, 9)), (10, 4))
    risco_leve = Criterios(4.1, 139, 20.9, 4.6)
    n_leve = len(malha(zona, risco_leve)[0])
    n_oh = len(malha(zona, OH1)[0])
    extra = len(malha(zona, Criterios(12.2, 232, 9.3, 3.7))[0])
    assert n_leve <= n_oh <= extra and n_leve < extra


def test_zona_em_l_cobre_todos_os_pontos():
    z = Zona("L", ((0, 0), (12, 0), (12, 4), (6, 4), (6, 9), (0, 9)), (-1, 4.5), orientacao="y")
    r = projetar(z, OH1)
    assert r.resumo["distancia_maxima_ao_bico_m"] <= math.sqrt(2) / 2 * 4.6 + 1e-6
    assert not r.avisos


# --- hidráulica ----------------------------------------------------------------------------


def test_hazen_williams_em_bar_bate_com_a_formula_da_nfpa():
    # p = 6,05e5 · Q^1,85 / (C^1,85 · d^4,87) bar/m (Q em L/min, d em mm)
    esperado = 6.05e5 * 100 ** 1.85 / (120 ** 1.85 * 52.5 ** 4.87)
    assert perda_bar(100, 52.5, 1.0, 120, 0) == pytest.approx(esperado, rel=0.03)
    assert perda_bar(100, 52.5, 10.0, 120, 20) == pytest.approx(esperado * 12, rel=0.03)
    assert perda_bar(0, 52.5, 10, 120, 0) == 0


def test_dn_cresce_com_a_vazao_e_respeita_velocidade_e_perda():
    dns = [escolher_dn(q, OH1)[0] for q in (50, 150, 400, 900, 1500)]
    assert dns == sorted(dns) and dns[0] == 25 and dns[-1] > dns[0]
    dn, di = escolher_dn(900, OH1)
    assert (900 / 60000) / (math.pi * (di / 1000) ** 2 / 4) <= OH1.v_max_ms
    assert dict(DN_SERIE)[dn] == di


def test_area_remota_atende_a_densidade_e_a_pressao_minima():
    r = projetar(Zona("Z", RET, (17.5, 5.0), 3.2), OH1)
    s = r.resumo
    assert s["bicos"] == 15 and s["ramais"] == 3
    area = s["area_de_operacao_m2"]
    assert area >= 139 - s["area_por_bico_m2"]  # ao menos a área de operação, em bicos inteiros
    minimo = 6.1 * area
    assert s["vazao_total_lpm"] >= minimo - 1  # nenhum bico entrega menos que a densidade
    assert s["vazao_total_lpm"] <= minimo * 1.5  # e a rede não superdimensiona a vazão
    assert s["pressao_do_bico_remoto_bar"] >= OH1.pressao_min_bar
    operando = [b for b in r.bicos if b.opera]
    assert len(operando) == round(area / s["area_por_bico_m2"])
    for b in operando:
        assert b.vazao_lpm >= 6.1 * s["area_por_bico_m2"] - 0.05
        assert b.vazao_lpm == pytest.approx(80 * math.sqrt(b.pressao_bar), rel=1e-6)  # q = K·√P
    assert all(b.vazao_lpm == 0 for b in r.bicos if not b.opera)


def test_pressoes_crescem_da_ponta_para_a_alimentacao_e_a_vazao_se_acumula():
    r = projetar(Zona("Z", RET, (17.5, 5.0), 3.2), OH1)
    ramal = [b for b in r.bicos if b.ramal == max(b.ramal for b in r.bicos)]
    ramal.sort(key=lambda b: b.ordem)
    ps = [b.pressao_bar for b in ramal if b.opera]
    assert ps == sorted(ps, reverse=True)  # mais perto da subgeral, mais pressão
    q_prumada = next(t for t in r.tubos if t.tipo == "prumada").vazao_lpm
    assert q_prumada == pytest.approx(sum(b.vazao_lpm for b in r.bicos), rel=1e-6)
    assert q_prumada == pytest.approx(r.resumo["vazao_total_lpm"], abs=0.05)


def test_pressao_na_base_soma_perdas_altura_e_vga():
    r = projetar(Zona("Z", RET, (17.5, 5.0), 3.2), OH1)
    s = r.resumo
    perdas = s["perdas_bar"]
    soma = sum(perdas[k] for k in ("ramal", "subgeral", "geral", "prumada", "estatica", "vga"))
    # a pressão no bico remoto entra uma vez (ramal inclui a perda acumulada, não o bico)
    assert s["pressao_na_base_da_prumada_bar"] == pytest.approx(
        s["pressao_do_bico_remoto_bar"] + soma - perdas["ramal"] + _perda_remota_ramal(r), abs=0.02)
    assert perdas["estatica"] == pytest.approx(3.2 * 0.0980665, abs=1e-3)
    assert perdas["vga"] == OH1.perda_vga_bar


def _perda_remota_ramal(r):
    """Perda dos trechos do ramal mais distante (a que entra na soma até a base)."""
    remoto = max(b.ramal for b in r.bicos)
    nomes = {b.id for b in r.bicos if b.ramal == remoto}
    return sum(t.perda_bar for t in r.tubos if t.tipo == "ramal"
               and (t.para in nomes or t.de in nomes))


def test_vga_e_perdas_maiores_pedem_mais_pressao():
    z = Zona("Z", RET, (17.5, 5.0), 3.2)
    base_ = projetar(z, OH1).resumo["pressao_na_base_da_prumada_bar"]
    mais = projetar(z, Criterios(**{**OH1.__dict__, "perda_vga_bar": 1.0}))
    assert mais.resumo["pressao_na_base_da_prumada_bar"] == pytest.approx(base_ + 0.7, abs=0.01)
    alto = projetar(Zona("Z", RET, (17.5, 5.0), 9.2), OH1)
    assert alto.resumo["pressao_na_base_da_prumada_bar"] > base_ + 0.5


def test_classe_de_risco_maior_exige_mais_vazao():
    z = Zona("Z", RET, (17.5, 5.0), 3.2)
    leve = projetar(z, Criterios(4.1, 139, 20.9, 4.6)).resumo["vazao_total_lpm"]
    oh = projetar(z, OH1).resumo["vazao_total_lpm"]
    eh = projetar(z, Criterios(12.2, 232, 9.3, 3.7)).resumo["vazao_total_lpm"]
    assert leve < oh < eh


def test_nomes_de_bicos_e_trechos_nao_parecem_placa():
    import re

    r = projetar(Zona("Z", RET, (17.5, 5.0), 3.2), OH1)
    placa = re.compile(r"^[SEAPM]-?[0-9]{1,2}")
    nomes = [b.id for b in r.bicos] + [t.id for t in r.tubos] + [t.de for t in r.tubos] \
        + [t.para for t in r.tubos]
    assert not [n for n in nomes if placa.match(n)]
