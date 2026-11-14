"""D5: cortes e fachadas derivados da planta (modelo da edificação) e D6 (medidor de referência)."""
from __future__ import annotations

import ezdxf
import pytest

from coscip_mcp.autoria import Authoring, AuthoringError
from tests.integration.test_mcp_server import call

SALA = {"tipo": "sala", "nome": "Salão", "retangulo": [0, 0, 10, 6]}
EDIF = {"tipo": "edificacao", "pe_direito_m": 3.6, "laje_m": 0.2, "platibanda_m": 0.6}
JAN = {"tipo": "janela", "x": 5, "y": 6.075, "largura_m": 1.5, "altura_m": 1.2, "peitoril_m": 0.9}
PORTA = {"tipo": "porta", "x": 2, "y": -0.075, "largura_m": 1.0, "altura_m": 2.1}
SECAO = {"tipo": "secao", "nome": "a", "a": [-1, 3], "b": [11, 3], "x": 30, "y": 0}


def gerar(tmp_path, ops):
    auth = Authoring(tmp_path / "v.dxf")
    auth.add(ops)
    resumo = auth.build()
    return ezdxf.readfile(tmp_path / "v.dxf"), resumo


def textos(doc, camada=None):
    q = f'TEXT[layer=="{camada}"]' if camada else "TEXT"
    return [e.dxf.text for e in doc.modelspace().query(q)]


def cotas(doc):
    out = []
    for d in doc.modelspace().query('DIMENSION[layer=="VISTA_COTA"]'):
        out += [e.text for e in doc.blocks.get(d.dxf.geometry) if e.dxftype() == "MTEXT"]
    return out


def n(doc, tipo, camada):
    return len(doc.modelspace().query(f'{tipo}[layer=="{camada}"]'))


# --- seção -------------------------------------------------------------------------------------


def test_secao_corta_as_duas_paredes_e_cota_a_largura_total(tmp_path):
    doc, resumo = gerar(tmp_path, [EDIF, SALA, SECAO])
    r = resumo["vistas"]["secoes"][0]
    assert r["nome"] == "A" and r["trechos_de_parede_cortados"] == 2
    assert r["pe_direito_m"] == 3.6 and r["altura_total_m"] == 4.4
    c = cotas(doc)
    assert "10,30" in c  # 10 m de ambiente + 2 x 0,15 de parede: o mesmo da planta
    assert "3,60" in c and "4,40" in c
    t = textos(doc, "VISTA_TEXTO")
    assert "CORTE A-A" in t and "ESCALA 1:100" in t
    assert any("+3,60 (forro)" in x for x in t) and any("+4,40 (platibanda)" in x for x in t)
    # paredes, piso e laje hachurados (duas paredes + piso + laje)
    assert n(doc, "HATCH", "VISTA_CORTE") == 4


def test_secao_pela_janela_mostra_peitoril_verga_e_vidro(tmp_path):
    doc, _ = gerar(tmp_path, [EDIF, SALA, JAN, {**SECAO, "a": [5, -1], "b": [5, 7],
                                                "sentido": "direita"}])
    # a linha corta a parede sul (inteira) e a norte (com a janela): peitoril e verga na norte
    assert n(doc, "LWPOLYLINE", "VISTA_ESQ") == 1  # vidro
    # parede sul inteira (1) + peitoril e verga sob/sobre a janela na norte (2) + piso e laje (2)
    assert n(doc, "HATCH", "VISTA_CORTE") == 5


def test_secao_mostra_o_que_esta_alem_do_plano_so_dentro_da_profundidade(tmp_path):
    ops = [EDIF, SALA,
           {"tipo": "simbolo", "classe": "EXTINTOR", "agente": "PQS_ABC", "x": 3, "y": 5},
           {"tipo": "simbolo", "classe": "ILUMINACAO_EMERGENCIA", "x": 6, "y": 4.5},
           {"tipo": "mobiliario", "id": "MESA", "x": 8, "y": 4.5}]
    doc, _ = gerar(tmp_path, [*ops, {**SECAO, "y": 0, "profundidade_m": 3.0}])
    assert n(doc, "LWPOLYLINE", "VISTA_INCENDIO") == 1 and n(doc, "LWPOLYLINE", "VISTA_ILUM") == 1
    assert n(doc, "LWPOLYLINE", "VISTA_AUX") == 1  # a mesa, em traço fino
    # com profundidade curta nada além do plano aparece
    doc2, _ = gerar(tmp_path, [*ops, {**SECAO, "profundidade_m": 1.0}])
    assert n(doc2, "LWPOLYLINE", "VISTA_INCENDIO") == 0 and n(doc2, "LWPOLYLINE", "VISTA_AUX") == 0


def test_secao_que_corta_equipamento_hachura_e_usa_a_altura_da_biblioteca(tmp_path):
    doc, _ = gerar(tmp_path, [EDIF, SALA, {"tipo": "mobiliario", "id": "FOGAO", "x": 5, "y": 3},
                              SECAO])
    ys = [p[1] for e in doc.modelspace().query('LWPOLYLINE[layer=="VISTA_CORTE"]')
          for p in e.get_points("xy")]
    assert max(ys) <= 4.4 + 1e-6 and 0.9 in [round(v, 3) for v in ys]  # fogão com 0,90 m


def test_secao_sem_edificacao_ou_com_dois_dao_erro_legivel(tmp_path):
    auth = Authoring(tmp_path / "v.dxf")
    auth.add([SALA, SECAO])
    with pytest.raises(AuthoringError, match="edificacao"):
        auth.build()
    auth2 = Authoring(tmp_path / "w.dxf")
    auth2.add([EDIF, EDIF, SALA, SECAO])
    with pytest.raises(AuthoringError, match="só uma edificacao"):
        auth2.build()


def test_secao_desenha_a_marca_na_planta_quando_pedido(tmp_path):
    doc, _ = gerar(tmp_path, [EDIF, SALA, SECAO])
    assert n(doc, "CIRCLE", "CORTES") == 2
    doc2, _ = gerar(tmp_path, [EDIF, SALA, {**SECAO, "marca_na_planta": False}])
    assert n(doc2, "CIRCLE", "CORTES") == 0


# --- fachada -----------------------------------------------------------------------------------


def test_fachada_sul_leva_porta_janela_e_etiquetas(tmp_path):
    janela_sul = {**JAN, "y": -0.075}
    doc, resumo = gerar(tmp_path, [EDIF, SALA, PORTA, janela_sul,
                                   {"tipo": "fachada", "lado": "sul", "x": 30, "y": 12}])
    r = resumo["vistas"]["fachadas"][0]
    assert r["lado"] == "sul" and r["aberturas"] == 2 and r["largura_m"] == 10.3
    t = textos(doc, "VISTA_TEXTO")
    assert "100x210" in t and "150x120/90" in t and "FACHADA SUL" in t
    assert n(doc, "LWPOLYLINE", "VISTA_PORTA") == 1 and n(doc, "LWPOLYLINE", "VISTA_ESQ") == 1
    assert "10,30" in cotas(doc)


def test_fachada_so_mostra_as_aberturas_do_proprio_lado(tmp_path):
    doc, resumo = gerar(tmp_path, [EDIF, SALA, PORTA,  # a porta está na parede sul
                                   {"tipo": "fachada", "lado": "norte", "x": 30, "y": 12}])
    assert resumo["vistas"]["fachadas"][0]["aberturas"] == 0
    assert n(doc, "LWPOLYLINE", "VISTA_PORTA") == 0


def test_volume_que_passa_do_telhado_aparece_na_fachada(tmp_path):
    edif = {**EDIF, "volumes": [{"nome": "Duto", "retangulo": [4.5, 2.5, 5.0, 3.0],
                                 "base_m": 2.7, "topo_m": 5.4}]}
    doc, _ = gerar(tmp_path, [edif, SALA, {"tipo": "fachada", "lado": "sul", "x": 30, "y": 12}])
    ys = [p[1] for e in doc.modelspace().query('LWPOLYLINE[layer=="VISTA_CONTORNO"]')
          for p in e.get_points("xy")]
    assert 12 + 5.4 in [round(v, 3) for v in ys]  # topo do duto, acima da platibanda (4,40)
    assert "Duto" in textos(doc, "VISTA_TEXTO")


def test_fachada_leste_e_oeste_usam_a_profundidade_da_planta(tmp_path):
    doc, resumo = gerar(tmp_path, [EDIF, SALA, {"tipo": "fachada", "lado": "leste", "x": 30,
                                                "y": 12},
                                   {"tipo": "fachada", "lado": "oeste", "x": 50, "y": 12}])
    assert [f["largura_m"] for f in resumo["vistas"]["fachadas"]] == [6.3, 6.3]


# --- coerência com a planta e com o leitor -------------------------------------------------------


def test_as_vistas_nao_mudam_o_que_o_leitor_enxerga_na_planta(srv):
    def reconhecidos(com_vistas):
        _, geral, _, _ = call(srv, "criar_planta", caminho=f"vi_{int(com_vistas)}.dxf")
        ops = [EDIF, SALA, PORTA, {**JAN, "y": -0.075},
               {"tipo": "simbolo", "classe": "EXTINTOR", "agente": "PQS_ABC", "x": 3, "y": 5},
               {"tipo": "chamada", "codigo": "S-12", "x": 2, "y": 1, "dimensao": "300x150"}]
        if com_vistas:
            ops += [SECAO, {"tipo": "fachada", "lado": "sul", "x": 30, "y": 12}]
        erro, out, texts, _ = call(srv, "desenhar_planta", planta_id=geral["planta_id"],
                                   operacoes=ops)
        assert not erro, texts
        assert "ALERTA_simbolos_nao_reconhecidos" not in out
        return out["simbolos_reconhecidos"], out["segmentos_de_parede"]

    assert reconhecidos(True) == reconhecidos(False)


def test_edificacao_e_vistas_vao_no_json(tmp_path):
    auth = Authoring(tmp_path / "v.dxf")
    auth.add([EDIF, SALA, SECAO])
    auth.build()
    de_novo = Authoring.load(tmp_path / "v.dxf")
    assert de_novo.ops[0].pe_direito_m == 3.6 and de_novo.ops[2].nome == "a"
