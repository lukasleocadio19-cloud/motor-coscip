"""Camada de evidências da arquitetura v2: localizador, consenso e lacuna de extração."""
from __future__ import annotations

import pytest
from coscip_evidence import Evidence, EvidenceLocator, EvidenceSet, ExtractionGap
from coscip_evidence.claims import claims_from_evidence
from pydantic import ValidationError

from coscip_cbm import ConsensusStatus, EvidenceSourceType, EvidenceStatus


def evidence(**kwargs) -> Evidence:
    base = dict(
        id="ev-1", process_id="p1", source_type=EvidenceSourceType.DOCUMENT,
        source_id="ART 123", source_version=1, source_hash="a" * 8,
        locator=EvidenceLocator(page=2), field="pressure_mca",
        raw_value="73 mca", normalized_value=73.0, unit="mca",
        extraction_method="MANUAL_TRANSCRIPTION")
    return Evidence(**{**base, **kwargs})


def test_sem_localizador_nao_ha_evidencia():
    """§53: valor extraído automaticamente sem origem apontável nasce UNVERIFIED."""
    sem_local = evidence(locator=EvidenceLocator(), extraction_method="LLM")
    assert sem_local.located is False
    assert sem_local.status is EvidenceStatus.UNVERIFIED
    assert evidence().located is True
    assert evidence().status is EvidenceStatus.SUFFICIENT


def test_declaracao_humana_e_calculo_dispensam_localizador():
    assert evidence(locator=EvidenceLocator(), extraction_method="MANUAL").located
    assert evidence(locator=EvidenceLocator(), extraction_method="CALCULATION").located


def test_evidencia_sem_valor_e_missing():
    assert evidence(raw_value=None, normalized_value=None).status is EvidenceStatus.MISSING


def test_evidencia_exige_campo():
    with pytest.raises(ValidationError):
        evidence(field="  ")


def test_hash_ignora_id_e_momento_mas_muda_com_o_valor():
    assert evidence().content_sha256 == evidence(id="outro").content_sha256
    assert evidence().content_sha256 != evidence(normalized_value=65.0).content_sha256


def test_evidencia_e_imutavel():
    with pytest.raises(ValidationError):
        evidence().normalized_value = 1


def test_consenso_fontes_que_concordam():
    conjunto = EvidenceSet.build("p1", [
        evidence(id="a", source_category="ART"),
        evidence(id="b", source_id="Curva X", source_category="CURVA_BOMBA"),
    ])
    resultado = conjunto.consensus("pressure_mca",
                                   required_sources=("ART", "CURVA_BOMBA"))
    assert resultado.status is ConsensusStatus.SUPPORTED
    assert resultado.agreed_value == 73.0


def test_consenso_detecta_divergencia():
    conjunto = EvidenceSet.build("p1", [
        evidence(id="a", source_category="ART"),
        evidence(id="b", source_id="Memorial", source_category="MEMORIAL",
                 normalized_value=65.0),
    ])
    resultado = conjunto.consensus("pressure_mca")
    assert resultado.status is ConsensusStatus.CONFLICTING
    assert set(resultado.values) == {73.0, 65.0}
    assert resultado.agreed_value is None


def test_consenso_fonte_unica_e_fonte_obrigatoria_ausente():
    conjunto = EvidenceSet.build("p1", [evidence(id="a", source_category="ART")])
    assert conjunto.consensus("pressure_mca").status is ConsensusStatus.SINGLE_SOURCE
    faltando = conjunto.consensus("pressure_mca",
                                  required_sources=("ART", "CURVA_BOMBA"))
    assert faltando.status is ConsensusStatus.MISSING_REQUIRED_SOURCE
    assert faltando.missing_sources == ("CURVA_BOMBA",)


def test_consenso_ignora_evidencia_sem_localizador():
    conjunto = EvidenceSet.build("p1", [
        evidence(id="a", locator=EvidenceLocator(), extraction_method="LLM")])
    assert conjunto.consensus("pressure_mca").status is ConsensusStatus.MISSING_REQUIRED_SOURCE


def test_consenso_compara_numero_e_texto_sem_ruido():
    conjunto = EvidenceSet.build("p1", [
        evidence(id="a", source_category="ART", raw_value="73", normalized_value="73,0"),
        evidence(id="b", source_category="CURVA_BOMBA", normalized_value=73),
    ])
    assert conjunto.consensus("pressure_mca").status is ConsensusStatus.SUPPORTED


def test_lacuna_de_extracao_nao_e_ausencia_documental():
    """§54: a extração não achou o campo — isso fica registrado como lacuna."""
    conjunto = EvidenceSet.build("p1", [], [ExtractionGap(
        process_id="p1", source_id="ART 123", source_version=1, field="manufacturer",
        extraction_method="LLM")])
    assert conjunto.has_gap("manufacturer")
    assert conjunto.gaps[0].reason == "NOT_FOUND_BY_EXTRACTION"
    assert conjunto.consensus("manufacturer").agreed_value is None


def test_claims_projetam_apenas_evidencia_localizada_e_com_valor():
    conjunto = [evidence(id="a", subject="fire_pump"),
                evidence(id="b", subject="fire_pump", normalized_value=None),
                evidence(id="c", subject="fire_pump", locator=EvidenceLocator(),
                         extraction_method="LLM")]
    claims = claims_from_evidence(conjunto)
    assert [c.evidence_id for c in claims] == ["a"]
    assert claims[0].property == "pressure_mca"
