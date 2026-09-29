"""Validação de fidelidade (plano de correção, F9).

Métricas contra um gabarito (aqui sintético, em ``tmp_path``: o real fica fora do
repositório) e a trava de publicação: nada sai de rascunho sem homologação registrada.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from coscip_normative.package import load_package
from coscip_normative.verification import load_catalog
from coscip_normative.verification.catalog import parse_check
from coscip_normative.verification.models import CheckValidationError
from coscip_rules.dsl import RuleValidationError, parse_rule
from tools.validacao import fidelidade as fid

ROOT = Path(__file__).resolve().parents[2]
CHECK = yaml.safe_load((ROOT / "normative/checks/extintores/EXT-CAD-001.yaml").read_text("utf-8"))
HOMOLOGACAO = {"responsible": "Eng. Fictício", "registration": "CREA-RJ 0000000",
               "decided_on": "2026-10-01", "report": "docs/validacao/2026-10-01.md"}


# ------------------------------------------------------------------ métricas

def test_exigencias_casam_por_documento_e_item():
    gabarito = [{"documento": "NT 2-01", "item": "5.2.5"},
                {"documento": "NT 2-01", "item": "5.2.5"},
                {"documento": "NT 1-01 P1", "item": "item 5.3.7"}]
    sistema = [{"documento": "nt 2-01", "item": "5.2.5"}, {"documento": "NT 1-01 P1",
                                                          "item": "5.3.7"},
               {"documento": "NT 2-07", "item": "5.5.2"}]
    m = fid.exigencias_metrics(gabarito, sistema)
    assert (m["acertadas"], m["faltantes"], m["indevidas"]) == (2, 1, 1)
    assert m["precisao"] == pytest.approx(2 / 3) and m["revocacao"] == pytest.approx(2 / 3)
    assert m["faltantes_lista"] == ["NT 2-01 5.2.5"] and m["indevidas_lista"] == ["NT 2-07 5.5.2"]


def test_simbolos_casam_um_para_um_dentro_da_tolerancia():
    rot = [{"classe": "EXTINTOR", "x": 0, "y": 0}, {"classe": "EXTINTOR", "x": 10, "y": 0}]
    det = [{"classe": "EXTINTOR", "x": 0.2, "y": 0}, {"classe": "EXTINTOR", "x": 0.3, "y": 0},
           {"classe": "HIDRANTE", "x": 5, "y": 5}]
    m = fid.simbolos_metrics(rot, det)
    assert m["EXTINTOR"] == {"rotulados": 2, "detectados": 2, "casados": 1,
                             "precisao": 0.5, "revocacao": 0.5}
    assert m["HIDRANTE"]["revocacao"] is None and m["HIDRANTE"]["precisao"] == 0.0


def test_distancias_contra_a_medida_manual():
    analise = {"pavimentos": [{"pavimento": "Térreo", "maior_percurso_m": {
        "extinguisher": {"valor": 12.5, "incerteza": 0.12}}}]}
    rows = fid.distancias_metrics(
        [{"pavimento": "Térreo", "sistema": "extinguisher", "valor_m": 12.4,
          "tolerancia_m": 0.05},
         {"pavimento": "Térreo", "sistema": "hydrant", "valor_m": 20.0}], analise)
    assert rows[0]["erro_m"] == pytest.approx(0.1) and rows[0]["dentro"] is True
    assert rows[1]["motor_m"] is None and rows[1]["dentro"] is None


def test_corpus_de_pastas_e_relatorio(tmp_path):
    proc = tmp_path / "P01"
    (proc / "sistema").mkdir(parents=True)
    (proc / "gabarito.yaml").write_text(yaml.safe_dump({
        "processo": "P01", "exigencias": [{"documento": "NT 1-01 P1", "item": "5.3.7"}],
        "simbolos": [{"classe": "EXTINTOR", "x": 1, "y": 1}]}), "utf-8")
    achado = {"id": "A", "origem": "skill", "tema": "Documentação", "fato": "ART ausente.",
              "regra": {"documento": "NT 1-01 P1", "item": "5.3.7"},
              "compliance_status": "NON_COMPLIANT", "evidence_status": "SUFFICIENT",
              "review_status": "NOT_REQUIRED", "severidade": "MAJOR",
              "tipo": "NON_COMPLIANT"}
    (proc / "sistema" / "matriz.json").write_text(json.dumps({"achados": [achado]}), "utf-8")
    (proc / "sistema" / "bilhete.txt").write_text(
        "1. ART ausente — NT 1-01 P1:2019, item 5.3.7: x. Solicita-se y.", "utf-8")
    (proc / "sistema" / "simbolos.json").write_text(json.dumps(
        {"simbolos": [{"classe": "EXTINTOR", "x": 1.1, "y": 1}]}), "utf-8")
    (res,) = fid.corpus(tmp_path)
    assert res["exigencias"]["acertadas"] == 1 and res["citacoes"]["taxa"] == 1.0
    assert res["simbolos"]["EXTINTOR"]["revocacao"] == 1.0
    text = fid.relatorio("2026-09-29", [res], None, {"DRAFT": 3})
    assert "| P01 | 1 | 0 | 0 | 100,0 % | 100,0 % | 1/1 |" in text
    assert "Nenhum resultado tem valor normativo" in text


def test_relatorio_sem_corpus_diz_nao_medido():
    text = fid.relatorio("2026-09-29", None, None, {"DRAFT": 30})
    assert "**Não medido.**" in text and "| DRAFT | 30 |" in text


def test_corpus_dentro_do_repositorio_e_recusado():
    assert fid.main(["--corpus", str(ROOT / "tests")]) == 1


def test_relatorio_do_dia_esta_no_repositorio():
    reports = sorted((ROOT / "docs" / "validacao").glob("????-??-??.md"))
    assert reports, "docs/validacao/AAAA-MM-DD.md"
    assert "Nenhum resultado tem valor normativo" in reports[-1].read_text("utf-8")


# ------------------------------------------------------------------ homologação

def test_nada_sai_de_rascunho_hoje():
    checks = load_catalog(ROOT / "normative" / "checks").checks
    rules = load_package(ROOT / "normative" / "base").rules
    assert {c.publication_state for c in checks} == {"DRAFT"}
    assert {r.publication_state for r in rules} == {"DRAFT"}
    assert not any(c.production_eligible for c in checks)
    assert not any(r.production_eligible for r in rules)


@pytest.mark.parametrize("state", ["HOMOLOGATED", "PUBLISHED"])
def test_check_homologado_exige_registro(state):
    with pytest.raises(CheckValidationError, match="exige homologação"):
        parse_check({**CHECK, "publication_state": state})
    ok = parse_check({**CHECK, "publication_state": state, "homologation": HOMOLOGACAO})
    assert ok.homologation.registration == "CREA-RJ 0000000"


def test_producao_so_com_homologacao_e_relatorio_de_validacao():
    with pytest.raises(CheckValidationError):
        parse_check({**CHECK, "publication_state": "DEPRECATED", "production_eligible": True})
    with pytest.raises(CheckValidationError):  # relatório fora de docs/validacao
        parse_check({**CHECK, "publication_state": "HOMOLOGATED",
                     "homologation": {**HOMOLOGACAO, "report": "notas.txt"}})


def test_regra_homologada_exige_registro():
    rule = next(r for r in load_package(ROOT / "normative" / "base").rules)
    data = rule.model_dump(mode="json", exclude_none=True)
    with pytest.raises(RuleValidationError, match="exige homologação"):
        parse_rule({**data, "publication_state": "HOMOLOGATED"})
    assert parse_rule({**data, "publication_state": "HOMOLOGATED",
                       "homologation": HOMOLOGACAO}).homologation is not None
    # sem homologação, o hash de conteúdo é o mesmo de antes do campo existir
    assert parse_rule(data).content_hash == rule.content_hash
