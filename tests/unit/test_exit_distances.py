# ruff: noqa: E501  (linhas da tabela reproduzidas como estão no texto ingerido)
"""NT 2-08, Anexo C como dado conferível: transcrição, conferência e consulta.

O trecho abaixo reproduz a página 22 do texto convertido da NT 2-08 (tabela extraída e
observações), no mesmo formato da base ingerida — inclusive o "Edificaçoẽ s" do OCR.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from coscip_normative import parse_markdown
from coscip_normative.exit_distances import consult_exit_distance, verify_exit_distances

TABLE = Path(__file__).resolve().parents[2] / "normative" / "base" / "distancias-saida.yaml"

NT_208 = """---
documento: "NT-2-08"
titulo: "NT 2-08 - Saídas de emergência (trecho de teste)"
edicao: "1ª edição - 2019; Portaria 1.317/2025"
sha256_pdf: "0000"
---

## Página 21

5.3.3.1 As distâncias máximas a serem percorridas devem atender o Anexo C.

5.3.3.3 Para projeto arquitetônico, como, por exemplo, escritórios de plano espacial aberto \
e galpões sem o arranjo físico interno (leiaute), devem ser consideradas as distâncias \
diretas comparadas aos limites do Anexo C, reduzidas em 30%.

## Página 22

### ANEXO C - DISTÂNCIAS MÁXIMAS A SEREM PERCORRIDAS

Observações: A) Edificações exclusivamente térreas das divisões G-1, G-2, I-1, I-2, J-1, \
J-2, J-3 e J-4 terão suas distâncias máximas a serem percorridas acrescidas de 100%, desde \
que possuam controle de fumaça. B) Para a divisão F-3 deve ser consultada a NT 5-01. C) \
é necessária a apresentação de leiaute definido em planta baixa. Do contrário, as \
distâncias definidas acima serão reduzidas a 30%. E) para admitir os valores da coluna \
"mais de uma saída" deve haver uma distância mínima de 10 m entre elas; F) nas áreas \
técnicas a distância deve ser medida a partir da porta de entrada das mesmas. G) divisão \
M-9 deve seguir o previsto na NT 4-02.

| Tipo de edificação | Grupo e divisão de ocupação | Pavimento | Sem chuveiros ou sem detectores automáticos |  | Com chuveiros ou com detectores automáticos |  |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  | Saída única | Mais de uma saída | Saída única | Mais de uma saída |
| (α) Edificaçoẽ s em que a propagação do fogo é fácil | Qualquer | Qualquer | 10,00 m | 20,00 m | 25,00 m | 35,00 m |
| (β) Edificaçoẽ s com estrutura mediana resistência ao fogo | Qualquer | Qualquer | 20,00 m | 30,00 m | 35,00m | 45,00 m |
| (γ) Edificaçoẽ s em que a propagação do fogo seja difícil | C, D, E, F, G-3, G-4, H, I, L e M | De saída da edificação (piso de descarga) | 35,00 m | 40,00 m | 45,00 m | 55,00 m |
|  |  | Demais | 35,00 m | 35,00 m | 35,00 m | 35,00 m |
|  | A, B, G-1, G-2, G-5, G-6 e J | De saída da edificação (piso de descarga) | 40,00 m | 50,00 m | 55,00 m | 65,00 m |
|  |  | Demais | 35,00 m | 35,00 m | 35,00 m | 35,00 m |
"""


def _sources():
    text = parse_markdown(NT_208.encode("utf-8"), "nt-2-08.md")
    return {text.document: text}


def _table():
    return yaml.safe_load(TABLE.read_text(encoding="utf-8"))


@pytest.fixture
def checked():
    failures: list[str] = []
    out = verify_exit_distances(_table(), _sources(), failures)
    assert failures == [] and out["verified"]
    return out


def test_toda_linha_confere_na_pagina_22(checked):
    assert len(checked["row_checks"]) == 6
    assert all(r["verified"] and r["page"] == 22 for r in checked["row_checks"])


def test_limite_adulterado_e_recusado():
    table = _table()
    table["rows"][2]["limits_m"][3] = 60  # a célula diz 55,00 m
    failures: list[str] = []
    assert not verify_exit_distances(table, _sources(), failures)["verified"]
    assert any("GAMA-CDEFHILM-DESCARGA" in f and "sem célula" in f for f in failures)


def test_linha_que_nao_existe_no_texto_e_recusada():
    table = _table()
    table["rows"][0]["verify"][2] = "12,00 m"
    table["rows"][0]["limits_m"][0] = 12
    failures: list[str] = []
    assert not verify_exit_distances(table, _sources(), failures)["verified"]


def test_documento_ausente_recusa_tudo():
    failures: list[str] = []
    assert not verify_exit_distances(_table(), {}, failures)["verified"] and failures


CTX = {"occupancy": "D-2", "construction_type": "GAMA", "sprinklers_or_detection": False,
       "multiple_exits": True, "layout_defined": True, "building_floors": 1}


@pytest.mark.parametrize(("extra", "status", "limit"), [
    ({}, "FOUND", 40),                                            # térrea: piso de descarga
    ({"sprinklers_or_detection": True}, "FOUND", 55),
    ({"multiple_exits": False}, "FOUND", 35),
    ({"occupancy": "A-3"}, "FOUND", 50),                           # linha A, B, G-1...
    ({"occupancy": "G-1"}, "FOUND", 50),                           # subdivisão explícita
    ({"occupancy": "G-3"}, "FOUND", 40),
    ({"construction_type": "ALFA", "building_floors": 5}, "FOUND", 20),
    ({"construction_type": "BETA", "sprinklers_or_detection": True}, "FOUND", 45),
    ({"building_floors": 3}, "DEPENDS_ON_FLOOR", None),            # 40 na descarga, 35 demais
    ({"building_floors": 3, "multiple_exits": False}, "FOUND", 35),  # iguais nos dois pisos
    ({"layout_defined": False}, "FOUND", 28),                      # 5.3.3.3: 40 × 0,7
    ({"layout_defined": False, "construction_type": "ALFA"}, "FOUND", 14),
    ({"occupancy": "F-3"}, "OUT_OF_SCOPE", None),                  # NT 5-01
    ({"construction_type": None}, "MISSING_DATA", None),
])
def test_consulta(checked, extra, status, limit):
    out = consult_exit_distance(checked, {**CTX, **extra})
    assert out["status"] == status, out
    assert out["limit_m"] == limit


def test_limite_por_piso_indica_as_duas_linhas(checked):
    out = consult_exit_distance(checked, {**CTX, "building_floors": 3})
    assert out["by_floor_m"] == {"DISCHARGE": 40, "OTHER": 35}
    assert out["rows"] == {"DISCHARGE": "GAMA-CDEFHILM-DESCARGA",
                           "OTHER": "GAMA-CDEFHILM-DEMAIS"}
    assert out["page"] == 22 and "fica em aberto" in out["message"]


def test_sem_leiaute_reduz_em_30_e_mede_em_linha_reta(checked):
    out = consult_exit_distance(checked, {**CTX, "layout_defined": False})
    assert out["measure"] == "DIRECT" and out["base_limit_m"] == 40 and out["limit_m"] == 28
    assert out["reduction"]["item"] == "5.3.3.3" and out["reduction"]["factor"] == 0.7
    assert "linha reta" in out["message"]
    com = consult_exit_distance(checked, CTX)
    assert com["measure"] == "TRAVEL" and "reduction" not in com


def test_sem_leiaute_por_piso_reduz_os_dois_limites(checked):
    out = consult_exit_distance(checked, {**CTX, "layout_defined": False, "building_floors": 3})
    assert out["status"] == "DEPENDS_ON_FLOOR"
    assert out["base_by_floor_m"] == {"DISCHARGE": 40, "OTHER": 35}
    assert out["by_floor_m"] == {"DISCHARGE": 28, "OTHER": 24.5}


@pytest.mark.parametrize("mudanca", [
    {"factor": 0.3},                                              # leitura "a 30%"
    {"basis": {"document": "NT 2-08", "item": "Anexo C", "quote": ["reduzidas a 30%"]}},
])
def test_regra_sem_leiaute_diferente_do_5333_e_recusada(mudanca):
    table = _table()
    table["layout_reduction"] = {**table["layout_reduction"], **mudanca}
    failures: list[str] = []
    assert not verify_exit_distances(table, _sources(), failures)["verified"]
    assert any("redução sem leiaute" in f for f in failures)


def test_pacote_sem_regra_de_reducao_nao_consulta_sem_leiaute(checked):
    sem = {k: v for k, v in checked.items() if k != "layout_reduction"}
    out = consult_exit_distance(sem, {**CTX, "layout_defined": False})
    assert out["status"] == "REVIEW_REQUIRED" and out["limit_m"] is None


def test_observacoes_que_aumentam_o_limite_nao_sao_aplicadas(checked):
    out = consult_exit_distance(checked, {**CTX, "occupancy": "J-1"})
    assert out["limit_m"] == 50  # linha A, B, G-1... e J; sem os 100% da observação A (seria 100)
    assert any(n["id"] == "A" and n["effect"] == "INCREASES" for n in out["notes"])


def test_tabela_nao_verificada_nao_responde(checked):
    nao = copy.deepcopy(checked)
    nao["verified"] = False
    assert consult_exit_distance(nao, CTX)["status"] == "UNAVAILABLE"
    assert consult_exit_distance(None, CTX)["status"] == "UNAVAILABLE"
