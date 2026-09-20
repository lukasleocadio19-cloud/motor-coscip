"""Consolidação de achados: causa raiz, severidade, contagem e texto determinístico."""
from __future__ import annotations

from coscip_findings import Divergence, Finding, consolidate, group_findings
from coscip_findings.wording import compose_explanation, divergence_block, missing_block

from coscip_cbm import (
    ComplianceStatus,
    EvidenceStatus,
    FindingKind,
    ReviewStatus,
    Severity,
)

ROTULOS = {"manufacturer": "fabricante", "power_cv": "potência"}


def achado(**kwargs) -> Finding:
    base = dict(
        check_id="X-001", check_version=1, system="HIDRANTES",
        compliance_status=ComplianceStatus.UNDETERMINED,
        evidence_status=EvidenceStatus.PARTIAL, review_status=ReviewStatus.PENDING,
        severity=Severity.MAJOR, kind=FindingKind.DOCUMENT_INCOMPLETE,
        reason_code="MISSING_REQUIRED_FIELD", title="ART incompleta",
        group_key="hidrantes/motobomba")
    return Finding(**{**base, **kwargs})


def test_quatro_falhas_da_mesma_causa_viram_um_item():
    """§32: internamente quatro failures, externamente um FindingGroup."""
    achados = [achado(check_id=f"X-00{i}", missing=(campo,))
               for i, campo in enumerate(["manufacturer", "model", "rpm", "power_cv"])]
    grupos = group_findings(achados)
    assert len(grupos) == 1
    assert grupos[0].missing == ("manufacturer", "model", "rpm", "power_cv")
    assert len(grupos[0].finding_ids) == 4


def test_grupo_assume_a_pior_severidade_e_o_pior_tipo():
    grupos = group_findings([
        achado(severity=Severity.MINOR, kind=FindingKind.DATA_MISSING),
        achado(check_id="X-002", severity=Severity.CRITICAL,
               kind=FindingKind.NON_COMPLIANT),
    ])
    assert grupos[0].severity is Severity.CRITICAL
    assert grupos[0].kind is FindingKind.NON_COMPLIANT


def test_grupo_mantem_revisao_pendente_se_algum_achado_pede():
    grupos = group_findings([
        achado(review_status=ReviewStatus.NOT_REQUIRED),
        achado(check_id="X-002", review_status=ReviewStatus.PENDING),
    ])
    assert grupos[0].review_status is ReviewStatus.PENDING


def test_ordem_da_tela_poe_o_que_nao_atende_primeiro():
    grupos = group_findings([
        achado(group_key="a", kind=FindingKind.ANALYST_REVIEW),
        achado(group_key="b", kind=FindingKind.NON_COMPLIANT),
        achado(group_key="c", kind=FindingKind.DIVERGENCE),
    ])
    assert [g.kind for g in grupos] == [FindingKind.NON_COMPLIANT, FindingKind.DIVERGENCE,
                                        FindingKind.ANALYST_REVIEW]


def test_resumo_executivo_conta_por_tipo():
    achados = [
        achado(group_key="a", kind=FindingKind.NON_COMPLIANT,
               compliance_status=ComplianceStatus.NON_COMPLIANT),
        achado(group_key="b", kind=FindingKind.DATA_MISSING),
        achado(group_key="c", kind=FindingKind.DIVERGENCE),
        achado(group_key="d", kind=FindingKind.NO_PENDING_ISSUE,
               compliance_status=ComplianceStatus.COMPLIANT,
               review_status=ReviewStatus.NOT_REQUIRED),
        achado(group_key="e", kind=FindingKind.NO_PENDING_ISSUE,
               compliance_status=ComplianceStatus.NOT_APPLICABLE,
               review_status=ReviewStatus.NOT_REQUIRED),
    ]
    resumo = consolidate(achados).summary
    assert resumo.pendencies == 1
    assert resumo.missing_data == 1
    assert resumo.divergences == 1
    assert resumo.review_required == 3
    assert resumo.without_pending_issue == 1
    assert resumo.not_applicable == 1


def test_itens_sem_pendencia_ficam_fora_da_lista_principal():
    resultado = consolidate([
        achado(group_key="a"),
        achado(group_key="b", kind=FindingKind.NO_PENDING_ISSUE,
               compliance_status=ComplianceStatus.COMPLIANT),
    ])
    assert len(resultado.groups) == 2
    assert len(resultado.pending_groups) == 1


def test_texto_lista_os_campos_pelo_rotulo_do_analista():
    texto = missing_block(["manufacturer", "power_cv"], ROTULOS)
    assert texto == "Não foram localizados:\n• fabricante\n• potência"


def test_texto_da_divergencia_mostra_fonte_e_valor():
    divergencia = Divergence(subject="fire_pump", field="pressure_mca",
                             values=(73.0, 65.0), sources=("ART", "Memorial"))
    texto = divergence_block([divergencia], {"pressure_mca": "pressão"})
    assert "ART: 73.0" in texto
    assert "Memorial: 65.0" in texto


def test_explicacao_junta_base_ausencias_e_divergencias():
    texto = compose_explanation("A documentação é insuficiente.", ["manufacturer"], [],
                                ROTULOS)
    assert texto.startswith("A documentação é insuficiente.")
    assert "• fabricante" in texto


def test_achado_sem_pendencia_nao_entra_na_lista():
    assert achado(kind=FindingKind.NO_PENDING_ISSUE).is_pending is False
    assert achado().is_pending is True
