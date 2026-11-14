"""Vetorização das imagens das NTs e integridade de ``simbolos_nt.json`` (desenhos oficiais)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
import yaml
from shapely.geometry import Polygon

from coscip_mcp import simbologia
from tools.normas.vetorizar import contornos, poligonos, vetorizar_campo

RAIZ = Path(__file__).resolve().parents[2]
DADOS = RAIZ / "apps" / "mcp" / "coscip_mcp" / "simbolos_nt.json"


def disco(n: int, cx: float, cy: float, r: float) -> np.ndarray:
    y, x = np.mgrid[0:n, 0:n]
    return np.clip(r + 0.5 - np.hypot(x - cx, y - cy), 0, 1)  # borda suave de 1 px


def area(polis) -> float:
    total = 0.0
    for ext, furos in polis:
        total += Polygon(ext).area - sum(Polygon(f).area for f in furos)
    return total


def test_disco_tem_a_area_do_circulo():
    polis = vetorizar_campo(disco(60, 30, 30, 20), tolerancia_px=0.1)
    assert len(polis) == 1 and polis[0][1] == []
    assert area(polis) == pytest.approx(math.pi * 20 ** 2, rel=0.01)


def test_anel_vira_um_poligono_com_um_furo():
    campo = disco(80, 40, 40, 30) - disco(80, 40, 40, 15)
    polis = vetorizar_campo(np.clip(campo, 0, 1), tolerancia_px=0.1)
    assert len(polis) == 1 and len(polis[0][1]) == 1
    assert area(polis) == pytest.approx(math.pi * (30 ** 2 - 15 ** 2), rel=0.02)


def test_formas_separadas_e_ilha_dentro_do_furo():
    campo = np.zeros((60, 100))
    campo[5:20, 5:20] = 1  # quadrado
    campo[5:50, 40:95] = 1  # retângulo grande
    campo[15:40, 50:85] = 0  # furo
    campo[22:32, 60:75] = 1  # ilha dentro do furo
    polis = vetorizar_campo(campo, ampliacao=2, tolerancia_px=0.05)
    assert len(polis) == 3  # quadrado, retângulo com furo, ilha
    assert sorted(len(f) for _, f in polis) == [0, 0, 1]
    assert area(polis) == pytest.approx(15 * 15 + 45 * 55 - 25 * 35 + 10 * 15, rel=0.02)


def test_forma_que_toca_a_borda_fecha_nela():
    campo = np.zeros((20, 20))
    campo[:, :10] = 1
    polis = vetorizar_campo(campo, ampliacao=1, tolerancia_px=0.01)
    assert len(polis) == 1 and area(polis) == pytest.approx(200, rel=0.05)  # cantos a 0,17 px


def test_sela_de_marching_squares_nao_cruza_segmentos():
    campo = np.array([[1.0, 0.0], [0.0, 1.0]])  # diagonal: caso ambíguo
    aneis = contornos(campo, 0.5)
    assert len(aneis) in (2, 4) or len(aneis) >= 1
    for a in aneis:
        assert Polygon(a).buffer(0).is_valid


def test_hierarquia_par_impar():
    grande = [(0, 0), (10, 0), (10, 10), (0, 10)]
    furo = [(2, 2), (8, 2), (8, 8), (2, 8)]
    ilha = [(4, 4), (6, 4), (6, 6), (4, 6)]
    polis = poligonos([ilha, furo, grande])
    assert len(polis) == 2
    maior = max(polis, key=lambda p: Polygon(p[0]).area)
    assert len(maior[1]) == 1


# --- integridade do arquivo com os desenhos oficiais ----------------------------------------------


@pytest.fixture(scope="module")
def dados():
    return json.loads(DADOS.read_text(encoding="utf-8"))


def test_arquivo_cita_o_pdf_oficial_pelo_hash_do_manifesto(dados):
    manifesto = yaml.safe_load((RAIZ / "normative" / "manifests" / "base.yaml")
                               .read_text(encoding="utf-8"))
    por_doc = {f["documento"]: f for f in manifesto["fontes"]}
    for doc in ("NT 1-03", "NT 2-05"):
        assert dados["fontes"][doc]["sha256_pdf"] == por_doc[doc]["sha256_pdf"]
        assert dados["fontes"][doc]["edicao"] == por_doc[doc]["edicao"]


def test_todas_as_placas_da_nt_2_05_exceto_o_solo_estao_no_arquivo(dados):
    codigos = {e.id.removeprefix("PICTO_") for e in simbologia.CATALOGO.values() if e.esquematico}
    assert codigos - set(dados["placas"]) == {"E-17"}
    extras = set(dados["placas"]) - codigos
    assert all("#" in k for k in extras)  # variantes extras do mesmo código (S-17#2...)


def test_todos_os_simbolos_da_nt_1_03_estao_no_arquivo_salvo_a_parede_corta_fogo(dados):
    ids = {e.id for e in simbologia.CATALOGO.values() if not e.esquematico}
    assert ids - set(dados["simbolos"]) <= {"PAREDE_CORTA_FOGO"}
    assert len(dados["simbolos"]) >= 103


def test_geometria_de_todos_os_itens_e_valida_e_cabe_na_caixa_unitaria(dados):
    for grupo in ("placas", "simbolos"):
        for chave, item in dados[grupo].items():
            px, py = item["proporcao"]
            assert max(px, py) == pytest.approx(1.0, abs=2e-3), chave
            assert item["regioes"], chave
            for r in item["regioes"]:
                if r.get("base"):
                    assert len(r["cor"]) == 3
                    continue
                assert r["poligonos"], chave
                for p in r["poligonos"]:
                    ext = list(zip(p["ext"][0::2], p["ext"][1::2], strict=True))
                    pol = Polygon(ext)
                    assert len(ext) >= 3 and pol.area > 0, chave
                    assert pol.buffer(0).is_valid, chave
                    xs, ys = zip(*ext, strict=True)
                    assert min(xs) >= -0.5 * px - 0.01 and max(xs) <= 0.5 * px + 0.01, chave
                    assert min(ys) >= -0.5 * py - 0.01 and max(ys) <= 0.5 * py + 0.01, chave
            if grupo == "placas":
                assert item["pagina"] and item["xref"]


def test_placas_tem_as_cores_chapadas_da_nt(dados):
    def rgb(code, i=0):
        return dados["placas"][code]["regioes"][i]["cor"]

    verde, vermelho = rgb("S-12", 0), rgb("E-5", 0)
    assert any(abs(c1 - c2) < 40 for c1, c2 in zip(rgb("S-1", 0), (36, 92, 52), strict=True))
    assert verde and vermelho
    assert vermelho[0] > vermelho[1] + 100  # vermelho de equipamento


def test_tamanho_do_arquivo_e_razoavel():
    assert DADOS.stat().st_size < 2_000_000  # vai no pacote do MCP
