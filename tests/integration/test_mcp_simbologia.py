"""MCP: a simbologia do COSCIP usada para construir plantas (catálogo, estilos, legenda)."""
from __future__ import annotations

from tests.integration.test_mcp_autoria import SALA, criar
from tests.integration.test_mcp_server import call


def test_listar_simbologia_filtra_por_grupo_e_busca(srv):
    erro, todos, _, _ = call(srv, "listar_simbologia")
    assert not erro and todos["total"] == 160
    assert todos["grupos"]["EXTINTORES"] == 12
    _, ext, _, _ = call(srv, "listar_simbologia", grupo="EXTINTORES", incluir_placas=False)
    assert ext["total"] == 12 and {s["classe_no_motor"] for s in ext["simbolos"]} == {"EXTINTOR"}
    _, det, _, _ = call(srv, "listar_simbologia", busca="fumaça")
    assert "DETECTOR_FUMACA" in {s["id"] for s in det["simbolos"]}
    _, placas, _, _ = call(srv, "listar_simbologia", grupo="PLACAS")
    assert placas["total"] == 56 and all(s["esquematico"] for s in placas["simbolos"])


def test_simbolo_por_id_do_catalogo_e_reconhecido(srv):
    pid = criar(srv)["planta_id"]
    erro, out, texts, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        SALA,
        {"tipo": "simbolo", "id": "EXTINTOR_CO2_SOBRERODAS", "x": 2, "y": 2},
        {"tipo": "simbolo", "id": "hidrante_duplo", "x": 3, "y": 2, "tamanho_m": 0.8},
        {"tipo": "simbolo", "id": "DETECTOR_FUMACA", "x": 4, "y": 2},
        {"tipo": "simbolo", "id": "E-5", "x": 5, "y": 2},
        {"tipo": "simbolo", "id": "TANQUE_VERTICAL_ENTERRADO", "x": 6, "y": 2}])
    assert not erro, texts
    assert out["simbolos_reconhecidos"] == {"EXTINTOR": 1, "HIDRANTE": 1, "DETECTOR": 1,
                                            "SINALIZACAO": 1}
    assert "ALERTA_simbolos_nao_reconhecidos" not in out  # tanque não tem classe: sem alerta
    _, simb, _, _ = call(srv, "listar_simbolos", planta_id=pid, classe="EXTINTOR")
    assert simb["simbolos"][0]["atributos"]["agent"] == "CO2"
    assert simb["simbolos"][0]["bloco"] == "EXTINTOR_CO2_SOBRERODAS"


def test_simbolo_erros_sugerem_a_correcao(srv):
    pid = criar(srv)["planta_id"]
    ou = "'id' (de listar_simbologia) OU 'classe'"
    for ruim, trecho in (
        ({"tipo": "simbolo", "id": "EXTINTOR_PQS_ABD", "x": 0, "y": 0}, "parecidos"),
        ({"tipo": "simbolo", "x": 0, "y": 0}, ou),
        ({"tipo": "simbolo", "id": "HIDRANTE_DUPLO", "classe": "HIDRANTE", "x": 0, "y": 0}, ou),
        ({"tipo": "simbolo", "id": "HIDRANTE_DUPLO", "agente": "CO2", "x": 0, "y": 0},
         "só valem com 'classe'"),
        ({"tipo": "simbolo", "id": "PAREDE_CORTA_FOGO", "x": 0, "y": 0}, "estilo de parede"),
        ({"tipo": "simbolo", "id": "PORTA_CORTA_FOGO_P60", "x": 0, "y": 0}, "corta_fogo_min"),
        ({"tipo": "simbolo", "id": "HIDRANTE_DUPLO", "capacidade": "6 kg", "x": 0, "y": 0},
         "só vale para extintor"),
    ):
        erro, _, texts, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[ruim])
        assert erro and trecho in texts[0], (ruim, texts)


def test_classe_extintor_aceita_agentes_oficiais_e_rodas(srv):
    pid = criar(srv)["planta_id"]
    erro, out, texts, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        SALA,
        {"tipo": "simbolo", "classe": "EXTINTOR", "agente": "pqs_d", "x": 1, "y": 1},
        {"tipo": "simbolo", "classe": "EXTINTOR", "agente": "agua", "sobre_rodas": True,
         "capacidade": "10 L", "x": 2, "y": 1}])
    assert not erro, texts
    _, simb, _, _ = call(srv, "listar_simbolos", planta_id=pid, classe="EXTINTOR")
    por_x = {round(s["x"]): s for s in simb["simbolos"]}
    assert por_x[1]["atributos"]["agent"] == "CLASSE_D"
    assert por_x[2]["atributos"]["agent"] == "AGUA" and por_x[2]["atributos"]["capacity"] == "10 l"
    erro, _, texts, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        {"tipo": "simbolo", "classe": "EXTINTOR", "agente": "CLASSE_K", "x": 0, "y": 0}])
    assert erro and "agente" in texts[0]


def test_estilos_de_parede_e_porta_corta_fogo(srv):
    from coscip_cad import DxfReader

    pid = criar(srv)["planta_id"]
    erro, out, texts, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        {"tipo": "sala", "nome": "A", "retangulo": [0, 0, 6, 4], "estilo_parede": "corta_fogo"},
        {"tipo": "parede", "pontos": [[3, 0], [3, 4]], "estilo": "divisoria"},
        {"tipo": "parede", "pontos": [[0, 8], [6, 8]], "estilo": "compartimentacao"},
        {"tipo": "porta", "x": 3, "y": -0.1, "corta_fogo_min": 90, "largura_m": 1.0}])
    assert not erro, texts
    doc = DxfReader().open(srv.ws.get(pid).path)
    camadas = {e.dxf.layer for e in doc.modelspace().query("LINE")}
    assert {"PAREDE_CORTA_FOGO", "DIVISORIA", "PAREDE_COMPARTIMENTACAO",
            "PORTA_CORTA_FOGO"} <= camadas
    assert {h.dxf.layer for h in doc.modelspace().query("HATCH")} == {
        "PAREDE_CORTA_FOGO", "PAREDE_COMPARTIMENTACAO"}
    assert [t.dxf.text for t in doc.modelspace().query("TEXT")
            if t.dxf.layer == "PORTA_CORTA_FOGO"] == ["90"]
    _, lista, _, _ = call(srv, "listar_elementos", planta_id=pid)
    assert lista["elementos"][0]["estilo_parede"] == "corta_fogo"


def test_legenda_lista_os_usados_com_o_nome_oficial(srv):
    pid = criar(srv)["planta_id"]
    erro, out, texts, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        {"tipo": "sala", "nome": "A", "retangulo": [0, 0, 10, 6], "estilo_parede": "corta_fogo"},
        {"tipo": "simbolo", "classe": "EXTINTOR", "agente": "PQS_ABC", "x": 2, "y": 2},
        {"tipo": "simbolo", "id": "HIDRANTE_SIMPLES", "x": 4, "y": 2},
        {"tipo": "simbolo", "id": "DETECTOR_FUMACA", "x": 6, "y": 2},
        {"tipo": "simbolo", "id": "MANOMETRO", "x": 7, "y": 2},
        {"tipo": "legenda", "x": 20, "y": 10}])
    assert not erro, texts
    _, textos, _, _ = call(srv, "listar_textos", planta_id=pid, janela=[19, -5, 40, 11])
    nomes = {t["texto"] for t in textos["textos"]}
    assert {"LEGENDA SISTEMA DE INCÊNDIO", "SÍMBOLO", "DESCRIÇÃO", "EXTINTOR DE PÓ ABC",
            "HIDRANTE SIMPLES", "DETECTOR DE FUMAÇA", "MANÔMETRO", "PAREDE CORTA-FOGO"} <= nomes
    # a legenda não vira equipamento: o motor marca a região da tabela como legenda
    assert out["simbolos_reconhecidos"] == {"EXTINTOR": 1, "HIDRANTE": 1, "DETECTOR": 1}
    assert "ALERTA_legenda" not in out


def test_legenda_com_poucos_simbolos_nao_conta_como_equipamento(srv):
    """A tabela que o motor desenha é marcada como legenda pela região, mesmo com 2 símbolos
    (o reconhecimento geométrico exige 3)."""
    pid = criar(srv)["planta_id"]
    erro, out, _, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        SALA, {"tipo": "legenda", "x": 20, "y": 10,
               "ids": ["EXTINTOR_CO2", "HIDRANTE_SIMPLES", "E-5", "S-12"]}])
    assert not erro and "ALERTA_legenda" not in out
    assert out["simbolos_reconhecidos"] == {}
    erro, _, texts, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        {"tipo": "legenda", "x": 0, "y": 0, "ids": ["NAO_EXISTE"]}])
    assert erro and "não existe no catálogo" in texts[0]
