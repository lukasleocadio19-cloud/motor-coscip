"""D4: Quadro Resumo automático (dados informados + contagem do desenho + conferência)."""
from __future__ import annotations

import ezdxf
import pytest

from coscip_mcp.autoria import Authoring, AuthoringError
from tests.integration.test_mcp_server import call

SALA = {"tipo": "sala", "nome": "Salão", "retangulo": [0, 0, 10, 6]}
SALA2 = {"tipo": "sala", "nome": "Cozinha", "retangulo": [10.2, 0, 16, 6]}
EXT = {"tipo": "simbolo", "classe": "EXTINTOR", "agente": "PQS_ABC", "capacidade": "6 kg"}
LUZ = {"tipo": "simbolo", "classe": "ILUMINACAO_EMERGENCIA"}
SAIDA = {"tipo": "simbolo", "classe": "SAIDA"}


def desenho(extra_quadro=None, escala=100):
    ops = [SALA, SALA2,
           {**EXT, "x": 2, "y": 3}, {**EXT, "x": 5, "y": 3}, {**EXT, "x": 8, "y": 3},
           {"tipo": "simbolo", "classe": "EXTINTOR", "agente": "AP", "capacidade": "10 L",
            "x": 12, "y": 3},
           *({**LUZ, "x": x, "y": 2} for x in (1, 3, 5, 7, 9)),
           {**SAIDA, "x": 5, "y": 0.1}, {**SAIDA, "x": 0.1, "y": 3},
           {"tipo": "chamada", "codigo": "S-12", "x": 5, "y": 1.5, "dimensao": "600x300"},
           *({"tipo": "chamada", "codigo": "E-5", "x": x, "y": 4.5, "dimensao": "150x150"}
             for x in (2, 5, 8)),
           *({"tipo": "mobiliario", "id": "BOTIJAO_P45", "x": 14 + i * 0.45, "y": 5}
             for i in range(4)),
           {"tipo": "quadro_resumo", "x": 30, "y": 20, **(extra_quadro or {})}]
    return ops


def gerar(tmp_path, ops, escala=100):
    auth = Authoring(tmp_path / "q.dxf", escala=escala)
    auth.add(ops)
    resumo = auth.build()
    return ezdxf.readfile(tmp_path / "q.dxf"), resumo


def textos(doc):
    return [e.dxf.text for e in doc.modelspace().query('TEXT[layer=="QUADRO"]')]


def test_quadro_conta_o_desenho_e_leva_so_o_que_foi_informado(tmp_path):
    doc, resumo = gerar(tmp_path, desenho({
        "identificacao": {"endereco": "Rua Fictícia, 1", "anterior_ao_decreto": False},
        "classificacao": {"grupo": "F", "divisao": "F-8"},
        "medidas_de_seguranca": ["Extintores", "Saídas de emergência"]}))
    q = resumo["quadro_resumo"]
    assert q["contagens"] == {"extintores": 4, "placas": 4, "iluminacao": 5, "glp_kg": 180.0,
                              "hidrantes": 0, "alarme": 0,
                              "saidas_desenhadas": 2, "area_util_m2": 94.8}
    t = textos(doc)
    assert "QUADRO RESUMO" in t and "Endereço: Rua Fictícia, 1" in t
    assert "PQS ABC 6 kg" in t and "Água pressurizada (AP) 10 L" in t
    assert "Placa E-5" in t and "Placa S-12" in t and "150x150" in t
    assert "Extintores" in t and "X" in t and "NÃO ( X )" in " ".join(t)
    # as seções do modelo do CBMERJ, na ordem do modelo
    ordem = ["IDENTIFICAÇÃO DA EDIFICAÇÃO", "CLASSIFICAÇÃO – Decreto", "CLASSIFICAÇÃO DAS ",
             "ELEMENTOS ESTRUTURAIS", "MEDIDAS DE SEGURANÇA", "RISCOS ESPECIAIS",
             "RESERVATÓRIO/RTI", "BOMBA DE INCÊNDIO", "SISTEMA DE HIDRANTES", "GÁS GLP/GN",
             "QUADRO DE ÁREAS", "SISTEMA DE PROTEÇÃO POR EXTINTORES", "POSICIONAMENTO DOS ",
             "SISTEMA DE SINALIZAÇÃO", "SISTEMA DE ILUMINAÇÃO", "SISTEMA DE DETECÇÃO",
             "SAÍDAS DE EMERGÊNCIA", "CONTROLE DE MATERIAIS"]
    pos = [next(i for i, x in enumerate(t) if x.startswith(o)) for o in ordem]
    assert pos == sorted(pos)
    for titulo in ("IDENTIFICAÇÃO DA EDIFICAÇÃO E/OU ÁREA DE RISCO", "RESERVATÓRIO/RTI",
                   "BOMBA DE INCÊNDIO – NT 2-04", "GÁS GLP/GN – NT 3-02", "QUADRO DE ÁREAS",
                   "POSICIONAMENTO DOS HIDRANTES – NT 2-02",
                   "SISTEMA DE DETECÇÃO E ALARME DE INCÊNDIO – NT 2-07",
                   "CONTROLE DE MATERIAIS DE ACABAMENTO E REVESTIMENTO - NT 2-20"):
        assert titulo in t, titulo
    # o que o usuário não informou fica em branco: nada é inventado
    assert "Proprietário:" in t and "Responsável técnico de segurança:" in t
    assert not any("CREA" in x or "Ltda" in x for x in t)


def test_quadro_vazio_nao_inventa_nada(tmp_path):
    doc, resumo = gerar(tmp_path, [SALA, {"tipo": "quadro_resumo", "x": 30, "y": 20}])
    t = textos(doc)
    assert "(nenhum extintor desenhado)" in t and "(nenhuma placa desenhada)" in t
    assert "(nenhuma medida informada)" in t
    # materiais: as linhas do modelo (Piso, Paredes, Tetos, Fachadas) em branco
    assert {"Piso", "Paredes / Divisórias", "Tetos / Forros", "Fachadas"} <= set(t)
    assert resumo["quadro_resumo"]["contagens"]["extintores"] == 0


def test_conferencia_diz_confere_diverge_ou_sem_dado(tmp_path):
    _, resumo = gerar(tmp_path, desenho({"declarado": {
        "extintores": 6, "saidas": 2, "glp_kg": 180, "atc_m2": 90}}))
    conf = {c["item"]: c for c in resumo["quadro_resumo"]["conferencia"]}
    assert conf["extintores"]["situacao"] == "diverge"  # desenho 4, calculado 6
    assert conf["saídas"]["situacao"] == "confere"
    assert conf["GLP (kg)"]["situacao"] == "confere"
    assert conf["pontos de iluminação de emergência"]["situacao"] == "sem dado declarado"
    # área útil (94,80) maior que a ATC declarada (90): incoerente
    assert conf["área útil dos ambientes não passa da área construída"]["situacao"] == "diverge"
    # 2 saídas desenhadas e só 1 placa S-12
    assert conf["placa de saída (S-12/S-14) por saída"]["situacao"] == "diverge"


def test_extintor_a_mais_do_que_o_calculado_ainda_confere(tmp_path):
    _, resumo = gerar(tmp_path, desenho({"declarado": {"extintores": 3}}))
    conf = {c["item"]: c for c in resumo["quadro_resumo"]["conferencia"]}
    assert conf["extintores"]["situacao"] == "confere"


def test_contagem_por_pavimento_usa_a_janela_de_cada_um(tmp_path):
    ops = desenho({"pavimentos": [
        {"nome": "Térreo", "janela": [-1, -1, 10.1, 7], "atc_m2": 60},
        {"nome": "1º Pav.", "janela": [10.1, -1, 20, 7], "atc_m2": 40}]})
    doc, resumo = gerar(tmp_path, ops)
    t = textos(doc)
    assert "Térreo" in t and "1º Pav." in t
    # extintores: 3 PQS no térreo (x < 10,1); o AP (x = 12) no 1º pavimento
    assert resumo["quadro_resumo"]["contagens"]["extintores"] == 4
    assert "ATC (m²)" in t and "60,00" in t and "40,00" in t and "100,00" in t


def test_so_um_quadro_por_planta_e_escala_muda_o_tamanho(tmp_path):
    auth = Authoring(tmp_path / "q.dxf")
    auth.add([SALA, {"tipo": "quadro_resumo", "x": 30, "y": 20},
              {"tipo": "quadro_resumo", "x": 60, "y": 20}])
    with pytest.raises(AuthoringError, match="só um quadro_resumo"):
        auth.build()
    _, r100 = gerar(tmp_path, [SALA, {"tipo": "quadro_resumo", "x": 30, "y": 20}], 100)
    _, r50 = gerar(tmp_path, [SALA, {"tipo": "quadro_resumo", "x": 30, "y": 20}], 50)
    assert r100["quadro_resumo"]["largura_m"] == 18.0
    assert r50["quadro_resumo"]["largura_m"] == 9.0  # 180 mm impressos em 1:50


def test_tabela_nao_vira_simbolo_para_o_leitor_do_motor(srv):
    """As células com códigos de placa não podem ser lidas como placas da planta."""
    def reconhecidos(com_quadro):
        nome = f"qr_{int(com_quadro)}.dxf"
        _, geral, _, _ = call(srv, "criar_planta", caminho=nome)
        ops = desenho()[:-1] + ([{"tipo": "quadro_resumo", "x": 30, "y": 20}]
                                if com_quadro else [])
        erro, out, texts, _ = call(srv, "desenhar_planta", planta_id=geral["planta_id"],
                                   operacoes=ops)
        assert not erro, texts
        assert "ALERTA_simbolos_nao_reconhecidos" not in out
        return out["simbolos_reconhecidos"]

    assert reconhecidos(True) == reconhecidos(False)


def test_quadro_na_janela_de_uma_folha(tmp_path):
    doc, resumo = gerar(tmp_path, [*desenho({"identificacao": {"endereco": "X"}}), {
        "tipo": "folha", "nome": "PRANCHA 02", "formato": "A1", "quadro_de_areas": False,
        "vistas": [{"titulo": "Quadro resumo", "janela": [29.5, -2, 43, 20.5], "escala": 100}]}])
    assert resumo["folhas"][0]["vistas"][0]["titulo"] == "Quadro resumo"
    assert "PRANCHA 02" in doc.layout_names()


def test_quadro_vai_no_json_e_retoma(tmp_path):
    auth = Authoring(tmp_path / "q.dxf")
    auth.add(desenho({"identificacao": {"endereco": "Rua A"}})[-1:])
    auth.build()
    de_novo = Authoring.load(tmp_path / "q.dxf")
    assert de_novo.ops[-1].identificacao.endereco == "Rua A"
