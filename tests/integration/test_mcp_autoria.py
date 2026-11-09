"""MCP: a IA cria e edita uma planta sintética e o motor a lê de volta.

Cobre o ciclo criar → desenhar → conferir o que o leitor reconheceu → remover → retomar, e o
fluxo até a análise (que continua exigindo confirmar_unidade).
"""
from __future__ import annotations

from coscip_mcp.autoria import Authoring
from coscip_mcp.server import Server
from tests.integration.test_mcp_server import call

SALA = {"tipo": "sala", "nome": "Sala 01", "retangulo": [0, 0, 10, 6]}


def criar(srv, nome="p1.dxf"):
    erro, geral, texts, _ = call(srv, "criar_planta", caminho=nome, titulo="teste")
    assert not erro, texts
    return geral


def test_criar_planta_abre_em_metros_e_nao_sobrescreve(srv, tmp_path):
    geral = criar(srv)
    assert geral["planta_id"] and geral["unidade"]["confirmada"] is False
    assert geral["unidade"]["escala_m_por_unidade"] == 1.0
    assert (tmp_path / "plantas" / "p1.dxf").exists()
    assert (tmp_path / "plantas" / "p1.coscip.json").exists()
    assert any("SINTÉTICA" in a for a in geral["avisos"])
    erro, _, texts, _ = call(srv, "criar_planta", caminho="p1.dxf")
    assert erro and "já existe" in texts[0]
    erro, _, texts, _ = call(srv, "criar_planta", caminho="p2.txt")
    assert erro and ".dxf" in texts[0]


def test_nao_edita_planta_aberta_de_arquivo(srv, tmp_path):
    from coscip_cad.synthetic import make_fire_plan

    arq = make_fire_plan(tmp_path / "fora.dxf")
    _, geral, _, _ = call(srv, "abrir_planta", caminho=str(arq))
    erro, _, texts, _ = call(srv, "desenhar_planta", planta_id=geral["planta_id"],
                             operacoes=[SALA])
    assert erro and "não criada pelo motor" in texts[0]
    antes = arq.read_bytes()
    call(srv, "remover_elementos", planta_id=geral["planta_id"], indices=[0])
    assert arq.read_bytes() == antes


def test_desenhar_sala_porta_e_simbolos_sao_lidos_de_volta(srv):
    pid = criar(srv)["planta_id"]
    erro, out, texts, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        SALA,
        {"tipo": "porta", "x": 5, "y": -0.075, "largura_m": 1.2},
        {"tipo": "simbolo", "classe": "extintor", "x": 2, "y": 3, "agente": "pqs_abc",
         "capacidade": "6 kg"},
        {"tipo": "simbolo", "classe": "EXTINTOR", "x": 8, "y": 3, "agente": "CO2",
         "estado": "EXISTENTE"},
        {"tipo": "simbolo", "classe": "HIDRANTE", "x": 1, "y": 5},
        {"tipo": "simbolo", "classe": "SINALIZACAO", "x": 3, "y": 3, "codigo": "e-5"},
        {"tipo": "texto", "texto": "PLANTA BAIXA - TÉRREO", "x": 1, "y": -3},
        {"tipo": "cota", "a": [0, 0], "b": [10, 0]}])
    assert not erro, texts
    assert out["adicionados"] == list(range(8)) and out["total_de_elementos"] == 8
    assert out["ambientes"] == [{"nome": "Sala 01", "area_m2": 60.0}]
    assert out["simbolos_reconhecidos"]["EXTINTOR"] == 2
    assert out["simbolos_reconhecidos"]["HIDRANTE"] == 1
    assert "ALERTA_simbolos_nao_reconhecidos" not in out

    erro, simb, _, _ = call(srv, "listar_simbolos", planta_id=pid, classe="EXTINTOR")
    por_x = {round(s["x"]): s for s in simb["simbolos"]}
    assert por_x[2]["atributos"]["agent"] == "PQS_ABC"
    assert por_x[2]["atributos"]["capacity"] in ("6 KG", "6KG", "6 kg", "6kg") or \
        "6" in str(por_x[2]["atributos"])
    assert por_x[8]["atributos"]["agent"] == "CO2"

    erro, textos, _, _ = call(srv, "listar_textos", planta_id=pid, contem="m²")
    assert textos["textos"][0]["texto"] == "60,00 m²"

    _, ver, _, imagens = call(srv, "ver_planta", planta_id=pid, largura_px=800)
    assert imagens and imagens[0]["mimeType"] == "image/png"


def test_porta_recorta_o_vao_da_parede(srv):
    from coscip_cad import DxfReader

    pid = criar(srv)["planta_id"]
    call(srv, "desenhar_planta", planta_id=pid, operacoes=[SALA])
    _, geral, _, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        {"tipo": "porta", "x": 5, "y": -0.075, "largura_m": 1.2}])
    arq = srv.ws.get(pid).path
    doc = DxfReader().open(arq)
    xs = []
    for e in doc.modelspace().query('LINE[layer=="PAREDE"]'):
        a, b = e.dxf.start, e.dxf.end
        if abs(a.y + 0.15) < 1e-6 and abs(b.y + 0.15) < 1e-6:  # face externa inferior
            xs += [a.x, b.x]
    inside = [x for x in xs if 4.3 < x < 5.7]
    assert sorted(set(round(x, 3) for x in inside)) == [4.4, 5.6]  # vão de 1,2 m


def test_erros_de_uso_voltam_legiveis_e_nao_alteram_a_planta(srv):
    pid = criar(srv)["planta_id"]
    call(srv, "desenhar_planta", planta_id=pid, operacoes=[SALA])
    for ruim, trecho in (
        ({"tipo": "simbolo", "classe": "PORTAO", "x": 0, "y": 0}, "não desenhável"),
        ({"tipo": "simbolo", "classe": "EXTINTOR", "x": 0, "y": 0}, "agente"),
        ({"tipo": "simbolo", "classe": "EXTINTOR", "x": 0, "y": 0, "agente": "CO2",
          "capacidade": "muito"}, "capacidade"),
        ({"tipo": "simbolo", "classe": "SINALIZACAO", "x": 0, "y": 0}, "codigo"),
        ({"tipo": "sala", "nome": "X"}, "retangulo OU poligono"),
        ({"tipo": "sala", "nome": "X", "retangulo": [5, 5, 1, 1]}, "x1 > x0"),
        ({"tipo": "parede", "pontos": [[0, 0]]}, "operação inválida"),
        ({"tipo": "foguete"}, "operação inválida"),
    ):
        erro, _, texts, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[ruim])
        assert erro and trecho in texts[0], (ruim, texts)
    _, lista, _, _ = call(srv, "listar_elementos", planta_id=pid)
    assert lista["total"] == 1


def test_remover_e_retomar(srv, tmp_path):
    pid = criar(srv)["planta_id"]
    call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        SALA, {"tipo": "simbolo", "classe": "HIDRANTE", "x": 1, "y": 1},
        {"tipo": "simbolo", "classe": "ACIONADOR_MANUAL", "x": 2, "y": 1}])
    erro, out, _, _ = call(srv, "remover_elementos", planta_id=pid, indices=[1])
    assert not erro and out["removidos"][0]["classe"] == "HIDRANTE"
    assert "HIDRANTE" not in out["simbolos_reconhecidos"]
    erro, _, texts, _ = call(srv, "remover_elementos", planta_id=pid, indices=[9])
    assert erro and "inexistentes" in texts[0]

    # Outra sessão do servidor retoma do .coscip.json e continua de onde parou.
    outro = Server()
    erro, geral, texts, _ = call(outro, "criar_planta", caminho="p1.dxf", retomar=True)
    assert not erro and geral["elementos"] == 2
    _, lista, _, _ = call(outro, "listar_elementos", planta_id=geral["planta_id"])
    assert [e["tipo"] for e in lista["elementos"]] == ["sala", "simbolo"]
    erro, _, texts, _ = call(outro, "criar_planta", caminho="nao-existe.dxf", retomar=True)
    assert erro and "não há planta criada" in texts[0]


def test_analise_continua_exigindo_confirmar_unidade(srv):
    pid = criar(srv)["planta_id"]
    erro, out, texts, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        {"tipo": "sala", "nome": "Sala 01", "retangulo": [0, 0, 20, 10]},
        {"tipo": "porta", "x": 10, "y": -0.075, "largura_m": 1.2},
        {"tipo": "simbolo", "classe": "EXTINTOR", "x": 5, "y": 5, "agente": "PQS_ABC"},
        {"tipo": "simbolo", "classe": "EXTINTOR", "x": 15, "y": 5, "agente": "PQS_ABC"},
        {"tipo": "texto", "texto": "PLANTA BAIXA - TÉRREO", "x": 5, "y": -3}])
    assert not erro, texts
    erro, _, texts, _ = call(srv, "analisar_planta", planta_id=pid)
    assert erro and "confirmar_unidade" in texts[0]
    # Parede de 20 m informada pelo usuário ao pedir a planta.
    erro, conf, texts, _ = call(srv, "confirmar_unidade", planta_id=pid, ponto_a=[0, 0],
                                ponto_b=[20, 0], medida_real_m=20.0,
                                justificativa="largura da sala informada pelo usuário no pedido")
    assert not erro, texts
    assert conf["confirmado"]["unidade"] == "m" and not conf["escala_mudou"]
    call(srv, "definir_pavimentos", planta_id=pid,
         pavimentos=[{"nome": "Térreo", "janela": [-2, -4, 22, 12]}])
    erro, rel, texts, _ = call(srv, "analisar_planta", planta_id=pid,
                               contexto={"occupancy": "D-2", "exits_confirmed": True,
                                         "layout_defined": True})
    assert not erro, texts
    (terreo,) = rel["pavimentos"]
    assert terreo["paredes"] == {"detectadas": True, "modo": "WALL_LAYERS"}
    assert 185 < terreo["area_util_m2"] < 205  # 20 × 10 m declarados (grade do motor)
    assert terreo["simbolos"]["EXTINTOR"] == 2
    assert 5 < terreo["maior_percurso_m"]["extinguisher"]["valor"] < 12


def test_sala_pequena_ainda_tem_paredes_reconhecidas(srv):
    """2 x 2 m teria 8 linhas; o leitor do motor exige 20 segmentos para ver parede."""
    pid = criar(srv)["planta_id"]
    _, out, _, _ = call(srv, "desenhar_planta", planta_id=pid, operacoes=[
        {"tipo": "sala", "nome": "WC", "retangulo": [0, 0, 2, 2]}])
    assert out["segmentos_de_parede"] >= 20 and "ALERTA_paredes" not in out
    _, vazio, _, _ = call(srv, "criar_planta", caminho="vazia.dxf")
    _, out, _, _ = call(srv, "desenhar_planta", planta_id=vazio["planta_id"], operacoes=[
        {"tipo": "texto", "texto": "so texto", "x": 0, "y": 0}])
    assert "ALERTA_paredes" in out


def test_ops_roundtrip_json(tmp_path):
    a = Authoring(tmp_path / "x.dxf")
    a.add([SALA, {"tipo": "texto", "texto": "oi", "x": 1, "y": 1}])
    a.build()
    b = Authoring.load(tmp_path / "x.dxf")
    assert b.describe() == a.describe()
