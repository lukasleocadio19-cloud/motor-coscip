"""MCP local: protocolo, processo real por stdio e o fluxo de leitura de uma planta.

A planta sintética é desenhada em MILÍMETROS com $INSUNITS dizendo metros — o erro que os
5 projetos reais tinham. As NTs são trechos de teste (NT 2-01 e NT 2-08): os checks que
citam outras NTs ficam fora do plano e aparecem como não verificados.
"""
from __future__ import annotations

import base64
import io
import json
import os
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

from coscip_cad.synthetic import make_fire_plan
from coscip_mcp.png import Canvas
from coscip_mcp.server import Server
from tests.unit.test_exit_distances import NT_208
from tests.unit.test_plant_analysis import NT_201

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def normas(tmp_path, monkeypatch):
    pasta = tmp_path / "normas"
    pasta.mkdir()
    (pasta / "nt-2-01.md").write_text(NT_201, encoding="utf-8")
    (pasta / "nt-2-08.md").write_text(NT_208, encoding="utf-8")
    monkeypatch.setenv("COSCIP_NORMAS_DIR", str(pasta))
    return pasta


@pytest.fixture
def srv(normas):
    return Server()


def call(srv: Server, name: str, **args):
    reply = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": name, "arguments": args}})
    result = reply["result"]
    texts = [c["text"] for c in result["content"] if c["type"] == "text"]
    images = [c for c in result["content"] if c["type"] == "image"]
    data = None
    if texts and not result["isError"]:
        data = json.loads(texts[-1])
    return result["isError"], data, texts, images


def _png_size(raw: bytes) -> tuple[int, int]:
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", raw[16:24])


# --- protocolo ---------------------------------------------------------------------------

def test_initialize_negocia_versao_e_lista_ferramentas(srv):
    init = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                       "params": {"protocolVersion": "2025-03-26"}})["result"]
    assert init["protocolVersion"] == "2025-03-26"
    assert init["capabilities"] == {"tools": {"listChanged": False}}
    assert "confirmar_unidade" in init["instructions"]
    novo = srv.handle({"jsonrpc": "2.0", "id": 2, "method": "initialize",
                       "params": {"protocolVersion": "2099-01-01"}})["result"]
    assert novo["protocolVersion"] == "2025-06-18"
    tools = srv.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})["result"]["tools"]
    assert {t["name"] for t in tools} == {
        "abrir_planta", "ver_planta", "listar_textos", "listar_simbolos", "classificar_blocos",
        "medir", "confirmar_unidade", "definir_pavimentos", "analisar_planta",
        "consultar_norma"}
    assert all(t["inputSchema"]["type"] == "object" and t["description"] for t in tools)


def test_notificacao_nao_responde_e_metodo_desconhecido_da_erro(srv):
    assert srv.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    err = srv.handle({"jsonrpc": "2.0", "id": 9, "method": "resources/list"})
    assert err["error"]["code"] == -32601
    assert srv.handle({"jsonrpc": "2.0", "id": 10, "method": "ping"})["result"] == {}


def test_linha_invalida_vira_erro_de_parse_sem_derrubar(srv):
    entrada = io.BytesIO(b'nao e json\n{"jsonrpc":"2.0","id":1,"method":"ping"}\n')
    saida = io.BytesIO()
    srv.serve(entrada, saida)
    linhas = [json.loads(x) for x in saida.getvalue().splitlines()]
    assert linhas[0]["error"]["code"] == -32700 and linhas[1]["result"] == {}


def test_processo_real_por_stdio(normas):
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(
        str(ROOT / p) for p in ("apps/mcp", "apps/api", "packages/analysis",
                                "packages/normative", "packages/cad", "packages/geometry",
                                "packages/cbm_schema", "packages/rules"))}
    entrada = "\n".join(json.dumps(m) for m in (
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )) + "\n"
    proc = subprocess.run([sys.executable, "-m", "coscip_mcp"], input=entrada.encode(),
                          capture_output=True, env=env, timeout=120, cwd=ROOT)
    linhas = [json.loads(x) for x in proc.stdout.decode("utf-8").splitlines()]
    assert [x["id"] for x in linhas] == [1, 2]  # stdout só tem protocolo
    assert linhas[0]["result"]["serverInfo"]["name"] == "coscip-plantas"
    assert len(linhas[1]["result"]["tools"]) == 10
    assert b"pronto" in proc.stderr


def test_ferramenta_com_argumento_errado_devolve_erro_legivel(srv):
    erro, _, texts, _ = call(srv, "abrir_planta")
    assert erro and "caminho" in texts[0]
    erro, _, texts, _ = call(srv, "ver_planta", planta_id="nada")
    assert erro and "abrir_planta" in texts[0]
    erro, _, texts, _ = call(srv, "abrir_planta", caminho="planta.dwg")
    assert erro


# --- fluxo de leitura --------------------------------------------------------------------

@pytest.fixture
def planta_mm(tmp_path):
    return make_fire_plan(tmp_path / "planta.dxf", scale=1000)


def test_fluxo_completo_com_unidade_errada_no_cabecalho(srv, planta_mm):
    erro, geral, _, _ = call(srv, "abrir_planta", caminho=str(planta_mm))
    assert not erro and geral["unidade"]["confirmada"] is False
    assert "PROVISÓRIA" in geral["unidade"]["nota"]
    pid = geral["planta_id"]
    assert any(c["camada"] == "PAREDE" and c["parede_provavel"] for c in geral["camadas"])

    erro, _, texts, _ = call(srv, "analisar_planta", planta_id=pid)
    assert erro and "confirmar_unidade" in texts[0]

    # Parede inferior de 14 m: na escala provisória (metros) ela mede 14 000.
    erro, _, texts, _ = call(srv, "confirmar_unidade", planta_id=pid, ponto_a=[0, 0],
                             ponto_b=[14000, 0], medida_real_m=15.0,
                             justificativa="cota da parede inferior informada pelo usuário")
    assert erro and "não bate" in texts[0]  # 15/14 não é unidade padrão
    erro, conf, _, _ = call(srv, "confirmar_unidade", planta_id=pid, ponto_a=[0, 0],
                            ponto_b=[14000, 0], medida_real_m=14.0,
                            justificativa="cota da parede inferior informada pelo usuário")
    assert not erro and conf["confirmado"]["unidade"] == "mm" and conf["escala_mudou"]

    erro, simb, _, _ = call(srv, "listar_simbolos", planta_id=pid, classe="EXTINTOR")
    assert [round(s["x"]) for s in simb["simbolos"]] == [5, 20]  # legenda fora, em metros

    erro, textos, _, _ = call(srv, "listar_textos", planta_id=pid, contem="bombas")
    assert textos["textos"][0]["texto"] == "BOMBAS" and textos["textos"][0]["x"] == 26.5

    erro, med, _, _ = call(srv, "medir", planta_id=pid, pontos=[[0, 0], [3, 4], [3, 10]])
    assert med["total_m"] == 11.0 and med["total_unidades_do_desenho"] == 11000.0

    erro, pav, _, _ = call(srv, "definir_pavimentos", planta_id=pid,
                           pavimentos=[{"nome": "Térreo", "janela": [-1, -1, 31, 13]}])
    assert pav["simbolos_de_seguranca_por_pavimento"]["Térreo"] >= 5

    erro, rel, _, _ = call(srv, "analisar_planta", planta_id=pid,
                           contexto={"occupancy": "D-2", "exits_confirmed": True,
                                     "layout_defined": True})
    assert not erro, rel
    assert rel["enquadramento"]["risco"] is None  # NT 1-04 não está nesta base de teste
    (terreo,) = rel["pavimentos"]
    assert terreo["paredes"]["detectadas"] and 320 < terreo["area_util_m2"] < 350
    assert 11 < terreo["maior_percurso_m"]["extinguisher"]["valor"] < 13.5
    assert "Mínimo de duas unidades extintoras por pavimento (Térreo)" in rel["sem_pendencia"]
    fora = rel["checks_nao_verificados_por_citacao"]
    assert "HID-CAD-001" in fora and "HID-CAD-002" in fora  # NT 2-02 ausente → e dependente
    assert "EXT-CAD-001" not in fora

    erro, cap, _, imagens = call(srv, "ver_planta", planta_id=pid, janela=[-1, -1, 31, 13],
                                 percurso="extinguisher", largura_px=900)
    raw = base64.b64decode(imagens[0]["data"])
    assert _png_size(raw)[0] == 900 and imagens[0]["mimeType"] == "image/png"
    assert cap["percursos"][0]["pavimento"] == "Térreo" and cap["grade_m"] == 5
    assert {s["n"] for s in cap["simbolos_na_vista"]} >= {1, 2}


def test_percurso_so_depois_de_analisar(srv, planta_mm):
    _, geral, _, _ = call(srv, "abrir_planta", caminho=str(planta_mm))
    erro, _, texts, _ = call(srv, "ver_planta", planta_id=geral["planta_id"],
                             percurso="extinguisher")
    assert erro and "analisar_planta" in texts[0]


def test_classificar_bloco_exige_classe_do_dicionario(srv, planta_mm):
    _, geral, _, _ = call(srv, "abrir_planta", caminho=str(planta_mm))
    pid = geral["planta_id"]
    erro, _, texts, _ = call(srv, "classificar_blocos", planta_id=pid,
                             mapa={"ACIONADOR_MANUAL": "PORTAO"})
    assert erro and "classes inexistentes" in texts[0]
    erro, out, _, _ = call(srv, "classificar_blocos", planta_id=pid,
                           mapa={"ACIONADOR_MANUAL": "SAIDA"})
    assert not erro and "SAIDA" in out["simbolos_por_classe"]


def test_consultar_norma_item_busca_e_resumo(srv):
    _, item, _, _ = call(srv, "consultar_norma", documento="NT 2-01", item="5.2.4")
    assert "50 m" in item["ocorrencias"][0]["texto"] and item["ocorrencias"][0]["pagina"] == 4
    _, busca, _, _ = call(srv, "consultar_norma", busca="distância percorrida")
    assert any(r["documento"] == "NT 2-01" for r in busca["resultados"])
    _, falta, _, _ = call(srv, "consultar_norma", documento="NT 2-01", item="9.9")
    assert "não encontrado" in falta["erro"]
    _, resumo, _, _ = call(srv, "consultar_norma")
    assert resumo["documentos"] == ["NT 2-01", "NT 2-08"]
    assert resumo["tabelas"]["exit_distances"] is True


def test_png_valido_com_pixels_desenhados():
    canvas = Canvas(20, 10)
    canvas.lines([0], [0], [19], [9], (255, 0, 0))
    canvas.text(1, 1, "12", (0, 0, 255))
    raw = canvas.png()
    assert _png_size(raw) == (20, 10)
    data = zlib.decompress(raw[raw.index(b"IDAT") + 4:raw.index(b"IEND") - 8])
    rows = [data[r * 61 + 1:(r + 1) * 61] for r in range(10)]
    assert rows[9][19 * 3:19 * 3 + 3] == b"\xff\x00\x00"  # ponta da linha


def test_autoteste_da_instalacao(normas, capsys):
    from coscip_mcp.diagnostico import run

    assert run() == 0
    saida = capsys.readouterr().out
    assert "planta sintética lida e desenhada" in saida
    assert "textos das NTs: 2 documentos" in saida
    assert "Instalação OK." in saida


# --- registro no Claude Desktop ----------------------------------------------------------

def test_registro_preserva_a_configuracao_do_aplicativo(tmp_path):
    from coscip_mcp.registro import register

    cfg = tmp_path / "claude_desktop_config.json"
    original = {"preferences": {"sidebarMode": "epitaxy", "lista": [], "vazio": {}},
                "mcpServers": {"outro": {"command": "x.exe", "args": []}}}
    cfg.write_text(json.dumps(original, indent=2), encoding="utf-8")
    out = register(cfg, "C:/py.exe", {"COSCIP_ODA_PATH": "C:/oda.exe"})
    raw = cfg.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")  # o aplicativo não aceita BOM
    data = json.loads(raw)
    assert data["preferences"] == original["preferences"]
    assert data["mcpServers"]["outro"] == original["mcpServers"]["outro"]
    assert data["mcpServers"]["coscip-plantas"] == {
        "command": "C:/py.exe", "args": ["-m", "coscip_mcp"],
        "env": {"COSCIP_ODA_PATH": "C:/oda.exe"}}
    assert json.loads(Path(out["backup"]).read_text(encoding="utf-8")) == original
    register(cfg, "C:/py.exe", remove=True)
    assert "coscip-plantas" not in json.loads(cfg.read_text(encoding="utf-8"))["mcpServers"]


def test_registro_nao_sobrescreve_json_invalido(tmp_path):
    from coscip_mcp.registro import register

    cfg = tmp_path / "claude_desktop_config.json"
    cfg.write_text("{ quebrado", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        register(cfg, "C:/py.exe")
    assert cfg.read_text(encoding="utf-8") == "{ quebrado"


def test_normas_do_repositorio_sao_encontradas(monkeypatch):
    from coscip_mcp import norms

    monkeypatch.delenv("COSCIP_NORMAS_DIR", raising=False)
    files = norms.source_files()
    assert len(files) == 53 and all(f.parent == norms.BUNDLED_SOURCES for f in files)
    assert not any("legado" in f.name for f in files)
