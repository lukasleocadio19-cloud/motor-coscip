"""Fluxo v2 sobre uma análise da planta gravada: Evidence → Plano de Verificação → Finding.

Fase 3 da arquitetura v2. Lê o ``analysis.json`` publicado (conferido pelo hash), nunca o
relatório. Invariantes:

- catálogo com citação que não confere contra a base ingerida é recusado inteiro;
- nada é gravado: plano, evidências e achados ainda vivem em memória (V2-13 pendente);
- nenhum resultado tem valor normativo — catálogo em rascunho.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from coscip_findings import consolidate

from coscip_analysis.evidence import plant_evidence
from coscip_api.models import Analysis
from coscip_api.normative_base import BUNDLED_BASE, current_texts
from coscip_api.plant_service import load_output
from coscip_normative.verification import (
    compile_verification_plan,
    execute_plan,
    load_catalog,
    verify_catalog,
)

SCHEMA = "plant-findings/1.0"
CHECKS_DIR = BUNDLED_BASE.parent / "checks"


class VerificationRefused(RuntimeError):
    def __init__(self, message: str, details: list[str] | None = None) -> None:
        super().__init__(message)
        self.details = details or []


def findings_for_analysis(factory, storage, analysis_id: str,  # noqa: ANN001
                          checks_dir: Path | None = None) -> dict[str, Any]:
    with factory() as s:
        a = s.get(Analysis, analysis_id)
        if a is None:
            raise LookupError(f"análise {analysis_id} não encontrada")
        if a.state != "SUCCEEDED":
            raise VerificationRefused(f"análise em estado {a.state}, sem saída concluída")
        data = load_output(s, storage, a)
        texts = current_texts(s, storage)
        drawing_id = a.drawing_id
    catalog = load_catalog(checks_dir or CHECKS_DIR)
    verification = verify_catalog(catalog, texts)
    if not verification["verified"]:
        raise VerificationRefused("citações do catálogo não conferem com a base ingerida",
                                  verification["failures"])
    pe = plant_evidence(data, process_id=f"analysis:{analysis_id}", source_id=drawing_id)
    plan = compile_verification_plan(catalog, pe.context)
    findings = execute_plan(plan, catalog, pe.process_evidence, pe.context.all_facts(),
                            floors=pe.floors)
    result = consolidate(findings)
    return {
        "schema_version": SCHEMA,
        "analysis_id": analysis_id,
        "drawing_sha256": pe.drawing_sha256,
        "catalog": verification["catalog"],
        "plan_sha256": plan.plan_sha256,
        "floors": [{"id": f.id, "label": f.label, "evidence": len(f.evidence)}
                   for f in pe.floors],
        "skipped_regions": [{"name": n, "reason": r} for n, r in pe.skipped_regions],
        # §30: sistema com X na tabela que o analista declarou não exigido.
        "requirement_overrides": list(pe.overrides),
        "summary": result.summary.as_dict(),
        "groups": [g.model_dump(mode="json") for g in result.groups],
        "findings": [{"ref": f.ref, **f.model_dump(mode="json")} for f in findings],
        "evidence": [e.model_dump(mode="json") for e in pe.evidence],
        "normative_value": False,
    }
