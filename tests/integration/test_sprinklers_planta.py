"""Sprinklers na planta: malha, rede, hidráulica, isométrico e a ferramenta de dimensionamento."""
from __future__ import annotations

import re
from pathlib import Path

import ezdxf
import pytest

from coscip_mcp.autoria import Authoring, AuthoringError
from coscip_mcp.server import Server
from tests.integration.test_mcp_server import call

FONTES = Path(__file__).resolve().parents[2] / "normative" / "fontes"


@pytest.fixture
def real(tmp_path, monkeypatch):
    """Servidor com as NTs do repositório: os parâmetros só valem se a citação confere."""
    monkeypatch.setenv("COSCIP_NORMAS_DIR", str(FONTES))
    monkeypatch.setenv("COSCIP_PLANTAS_DIR", str(tmp_path / "plantas"))
    return Server()

SALA = {"tipo": "sala", "nome": "Salão", "retangulo": [0, 0, 16.6, 10.8]}
SPK = {"tipo": "sprinklers", "nome": "Z1", "sala": "Salão", "alimentacao": [17.5, 5.0],
       "z_ramal_m": 3.2}
ISO = {"tipo": "isometrico", "sprinklers": "Z1", "x": 40, "y": 5}


def gerar(tmp_path, ops):
    auth = Authoring(tmp_path / "s.dxf")
    auth.add(ops)
    resumo = auth.build()
    return ezdxf.readfile(tmp_path / "s.dxf"), resumo


def n(doc, tipo, camada):
    return len(doc.modelspace().query(f'{tipo}[layer=="{camada}"]'))


def textos(doc, camada):
    return [e.dxf.text for e in doc.modelspace().query(f'TEXT[layer=="{camada}"]')]


def test_sprinklers_desenha_bicos_oficiais_tubos_e_area_de_operacao(tmp_path):
    doc, resumo = gerar(tmp_path, [SALA, SPK])
    r = resumo["sprinklers"][0]
    assert r["bicos"] == 15 and r["ramais"] == 3 and r["bicos_em_operacao"] == 12
    inserts = [e for e in doc.modelspace().query("INSERT") if e.dxf.name.startswith("BICO")]
    assert len(inserts) == 15 and all(e.dxf.layer == "INC_SPK" for e in inserts)
    # o desenho do bico é o oficial da NT 1-03: regiões de tinta herdando a cor da camada
    bloco = doc.blocks.get("BICO_SPRINKLER_PENDENTE")
    assert len(bloco.query("HATCH")) >= 1
    # um trecho de ramal por bico (15) + subgeral (2) + geral (2); a prumada só no isométrico
    assert n(doc, "LINE", "INC_CHUV_TUBO") == 19
    assert any(t.startswith("DN") for t in textos(doc, "INC_CHUV_TEXTO"))
    assert n(doc, "LWPOLYLINE", "INC_CHUV_AREA") == 1
    assert any("ÁREA DE OPERAÇÃO Z1" in t for t in textos(doc, "INC_CHUV_TEXTO"))
    # a VGA da NT 1-03 na alimentação
    assert any(e.dxf.name == "VALVULA_GOVERNO_ALARME_VGA" for e in doc.modelspace().query("INSERT"))


def test_nome_do_ambiente_e_area_nao_ficam_sobre_os_bicos(tmp_path):
    from shapely.geometry import box

    doc, _ = gerar(tmp_path, [SALA, SPK])
    msp = doc.modelspace()
    nomes = [e for e in msp.query("TEXT") if e.dxf.layer == "TEXTOS"]
    assert len(nomes) == 2  # nome e área do ambiente
    for t in nomes:
        x, y = t.dxf.align_point[0], t.dxf.align_point[1]
        w = len(t.dxf.text) * t.dxf.height * 0.7
        caixa = box(x - w / 2, y - t.dxf.height / 2, x + w / 2, y + t.dxf.height / 2)
        for e in msp.query("INSERT"):
            if e.dxf.name.startswith("BICO"):
                bx, by = e.dxf.insert.x, e.dxf.insert.y
                assert not caixa.intersects(box(bx - 0.5, by - 0.13, bx + 0.5, by + 0.13))


def test_leitor_reconhece_os_bicos_e_nao_muda_as_paredes(srv):
    def rodar(com):
        _, geral, _, _ = call(srv, "criar_planta", caminho=f"sp_{int(com)}.dxf")
        ops = [SALA] + ([SPK, ISO] if com else [])
        erro, out, texts, _ = call(srv, "desenhar_planta", planta_id=geral["planta_id"],
                                   operacoes=ops)
        assert not erro, texts
        assert "ALERTA_simbolos_nao_reconhecidos" not in out
        return out["simbolos_reconhecidos"], out["segmentos_de_parede"]

    sem, seg_sem = rodar(False)
    com, seg_com = rodar(True)
    assert com == {"SPRINKLER": 15} and not sem
    assert seg_com == seg_sem  # tubos, textos e isométrico não viram parede nem obstáculo


def test_isometrico_tem_tubos_bicos_quadro_e_cotas(tmp_path):
    doc, resumo = gerar(tmp_path, [SALA, SPK, ISO])
    r = resumo["sprinklers"][0]["isometrico"]
    assert r["tubos"] == 20 and r["bicos"] == 15 and r["quadro"]["linhas"] == 20
    tubos = n(doc, "LINE", "ISO_TUBO") + n(doc, "LINE", "ISO_PRUMADA")
    assert tubos == 22  # 20 trechos + os 2 traços do X da VGA
    assert n(doc, "CIRCLE", "ISO_BICO") >= 15
    quadro = textos(doc, "ISO_QUADRO")
    assert "QUADRO DE CÁLCULO HIDRÁULICO" in quadro and "T20" in quadro and "prumada" in quadro
    assert any(t.startswith("Pressão na base da prumada") for t in quadro)
    assert any(t.startswith("Vazão total: 1037,") for t in quadro)
    assert "3,20" in textos(doc, "ISO_COTA")  # altura da prumada
    assert "ISOMÉTRICO DA REDE DE SPRINKLERS" in textos(doc, "ISO_TEXTO")


def test_isometrico_e_quadro_vem_do_mesmo_calculo_do_resumo(tmp_path):
    doc, resumo = gerar(tmp_path, [SALA, SPK, ISO])
    r = resumo["sprinklers"][0]
    quadro = textos(doc, "ISO_QUADRO")
    total = f"{r['vazao_total_lpm']:.1f}".replace(".", ",")
    assert f"Vazão total: {total} L/min" in quadro


def test_nomes_do_isometrico_nao_viram_placa_para_o_leitor(tmp_path):
    doc, _ = gerar(tmp_path, [SALA, SPK, ISO])
    placa = re.compile(r"^[SEAPM]-?[0-9]{1,2}")
    todos = [e.dxf.text for e in doc.modelspace().query("TEXT")
             if e.dxf.layer.startswith(("ISO_", "INC_CHUV"))]
    assert not [t for t in todos if placa.match(t.strip())]


def test_zona_por_retangulo_e_poligono(tmp_path):
    ret = {"tipo": "sprinklers", "nome": "R", "retangulo": [0, 0, 8, 6], "alimentacao": [-1, 3]}
    poli = {"tipo": "sprinklers", "nome": "L", "alimentacao": [-1, 4.5],
            "poligono": [[20, 0], [32, 0], [32, 4], [26, 4], [26, 9], [20, 9]],
            "orientacao": "y"}
    _, resumo = gerar(tmp_path, [ret, poli])
    nomes = {r["nome"]: r for r in resumo["sprinklers"]}
    assert nomes["R"]["bicos"] == 4 and not nomes["R"]["avisos"]
    assert nomes["L"]["bicos"] >= 8 and not nomes["L"]["avisos"]


def test_criterios_informados_mudam_a_malha(tmp_path):
    _, a = gerar(tmp_path, [SALA, SPK])
    apertado = {**SPK, "area_max_bico_m2": 8.0, "espacamento_max_m": 3.0}
    _, b = gerar(tmp_path, [SALA, apertado])
    assert b["sprinklers"][0]["bicos"] > a["sprinklers"][0]["bicos"]
    leve = {**SPK, "classe": "LEVE"}
    _, c = gerar(tmp_path, [SALA, leve])
    assert c["sprinklers"][0]["vazao_total_lpm"] < a["sprinklers"][0]["vazao_total_lpm"]


def test_erros_legiveis(tmp_path):
    with pytest.raises(AuthoringError, match="sala OU retangulo OU poligono"):
        Authoring(tmp_path / "e.dxf").add([{**SPK, "retangulo": [0, 0, 1, 1]}])
    with pytest.raises(AuthoringError, match="x1 > x0"):
        Authoring(tmp_path / "e.dxf").add([{"tipo": "sprinklers", "nome": "Z",
                                            "retangulo": [5, 5, 1, 1], "alimentacao": [0, 0]}])
    a = Authoring(tmp_path / "e.dxf")
    a.add([SALA, {**SPK, "sala": "Cozinha"}])
    with pytest.raises(AuthoringError, match="não há sala 'Cozinha'.*Salão"):
        a.build()
    b = Authoring(tmp_path / "f.dxf")
    b.add([SALA, SPK, SPK])
    with pytest.raises(AuthoringError, match="mesmo nome"):
        b.build()
    c = Authoring(tmp_path / "g.dxf")
    c.add([SALA, {**ISO, "sprinklers": "Outra"}])
    with pytest.raises(AuthoringError, match="não há operação sprinklers 'Outra'"):
        c.build()


def test_sprinklers_vao_no_json_e_voltam(tmp_path):
    auth = Authoring(tmp_path / "s.dxf")
    auth.add([SALA, SPK, ISO])
    auth.build()
    de_novo = Authoring.load(tmp_path / "s.dxf")
    assert de_novo.ops[1].nome == "Z1" and de_novo.ops[2].sprinklers == "Z1"


# --- ferramenta MCP ------------------------------------------------------------------------


def test_ferramenta_dimensionar_sprinklers_devolve_memorial_com_citacoes(real):
    erro, out, texts, _ = call(real, "dimensionar_sprinklers", classe="ORDINARIO_1",
                               grupo_divisao="F-8", ambientes=[
                                   {"nome": "Salão", "area_m2": 179.28},
                                   {"nome": "WC", "area_m2": 12, "tipo": "SANITARIO"}],
                               zonas=[{"nome": "Salão", "retangulo": [0, 0, 16.6, 10.8],
                                       "alimentacao": [17.5, 5]}])
    assert not erro, texts
    assert out["sistema"] == "sprinklers" and out["resultados"]["area_protegida_m2"] == 179.28
    assert out["resultados"]["rti_sprinklers_l"] > 0
    cit = " ".join(out["base_normativa"])
    assert "NT 2-03 P1" in cit and "Anexo B" in cit
    assert any("NFPA 13" in p for p in out["premissas_do_projetista"])
    assert any(p["passo"].startswith("Rede da zona Salão") for p in out["memorial"])


def test_ferramenta_recusa_classe_invalida(real):
    erro, _, texts, _ = call(real, "dimensionar_sprinklers", classe="MEDIO")
    assert erro
