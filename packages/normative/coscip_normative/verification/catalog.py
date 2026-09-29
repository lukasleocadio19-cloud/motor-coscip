"""Catálogo de checks: carregamento, validação, versão e conferência das citações.

Como no pacote de regras, **nenhum check entra sem citação conferida** no texto normativo
ingerido. Um check em rascunho nunca pode ir à produção.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from coscip_normative.sources import NormativeText, verify_citation
from coscip_normative.verification.models import (
    CHECK_SCHEMA,
    CheckDefinition,
    CheckValidationError,
)

CATALOG_SCHEMA = "check-catalog/1.0"

# Cada pergunta executável exige exatamente os campos que consegue usar.
_QUESTION_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "presence": ("field",),
    "required_fields": ("required_fields",),
    "minimum_count": ("field", "required_value"),
    "minimum_value": ("field",),
    "maximum_value": ("field",),
    "consistency": ("field",),
    "composition": ("field", "alternatives", "value_classes"),
}


class CatalogError(ValueError):
    pass


def parse_check(data: dict[str, Any]) -> CheckDefinition:
    try:
        check = CheckDefinition.model_validate(data)
    except ValidationError as exc:
        raise CheckValidationError(str(exc)) from exc
    _validate(check)
    return check


def _validate(check: CheckDefinition) -> None:
    if check.production_eligible and check.publication_state in {"DRAFT", "TEST_ONLY"}:
        raise CheckValidationError(
            f"{check.id}: check {check.publication_state} não pode ir à produção")
    if not check.normative_basis and not check.manual:
        raise CheckValidationError(f"{check.id}: check executável sem base normativa")
    for src in check.normative_basis:
        if not src.quote and not src.document.startswith("EXEMPLO"):
            raise CheckValidationError(f"{check.id}: citação {src.item} sem termos de conferência")
        if check.production_eligible and src.document.startswith("EXEMPLO"):
            raise CheckValidationError(f"{check.id}: fonte de exemplo não pode ir à produção")
    if check.interpretation is not None:
        if not check.interpretation.basis:
            raise CheckValidationError(f"{check.id}: interpretação sem texto de apoio")
        if any(not b.quote for b in check.interpretation.basis):
            raise CheckValidationError(f"{check.id}: apoio da interpretação sem termos")
    question = check.question
    if question is None:
        if check.type != "MANUAL_CONFIRMATION":
            raise CheckValidationError(
                f"{check.id}: check sem pergunta precisa ser MANUAL_CONFIRMATION")
        return
    if check.type == "MANUAL_CONFIRMATION":
        raise CheckValidationError(f"{check.id}: MANUAL_CONFIRMATION não pode ter pergunta")
    for name in _QUESTION_REQUIREMENTS[question.kind]:
        value = getattr(question, name)
        if value is None or value == () or value == "":
            raise CheckValidationError(f"{check.id}: pergunta {question.kind} exige {name}")
    if question.kind in {"minimum_value", "maximum_value"}:
        if (question.required_value is None) == (question.required_fact is None):
            raise CheckValidationError(
                f"{check.id}: pergunta {question.kind} exige exatamente um entre "
                "required_value e required_fact")
    elif question.required_fact is not None:
        raise CheckValidationError(
            f"{check.id}: required_fact só vale em minimum_value/maximum_value")
    if question.kind != "required_fields" and question.required_fields:
        raise CheckValidationError(
            f"{check.id}: required_fields só vale na pergunta required_fields")


@dataclass
class CheckCatalog:
    """Conjunto versionado de checks. O hash entra no manifesto da análise (§52)."""

    id: str
    name: str
    version: int
    jurisdiction: str
    publication_state: str
    checks: tuple[CheckDefinition, ...]
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    def __post_init__(self) -> None:
        ids = [c.id for c in self.checks]
        if len(ids) != len(set(ids)):
            raise CatalogError("check duplicado no catálogo")
        known = set(ids)
        for check in self.checks:
            unknown = [d for d in check.depends_on if d not in known]
            if unknown:
                raise CatalogError(f"{check.id}: depende de check inexistente: {unknown}")
        _check_cycles(self.checks)

    def get(self, check_id: str) -> CheckDefinition:
        for check in self.checks:
            if check.id == check_id:
                return check
        raise KeyError(check_id)

    @property
    def content_sha256(self) -> str:
        canonical = json.dumps({
            "catalog": {k: v for k, v in self.raw.items() if k != "checks"},
            "checks": sorted(c.content_hash for c in self.checks),
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def evidence_matrix(self) -> list[dict[str, Any]]:
        """Matriz de evidências (§24) compilada a partir dos metadados dos checks."""
        rows = []
        for check in self.checks:
            accepted = check.question.accepted_evidence if check.question else ()
            rows.append({"check": check.id, "title": check.title, "system": check.system,
                         "accepted_evidence": list(accepted), "manual": check.manual,
                         "human_review": check.human_review.always})
        return rows


def _check_cycles(checks: tuple[CheckDefinition, ...]) -> None:
    graph = {c.id: set(c.depends_on) for c in checks}
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(node: str) -> None:
        if node in done:
            return
        if node in visiting:
            raise CatalogError(f"ciclo de dependência envolvendo {node}")
        visiting.add(node)
        for dep in graph.get(node, ()):
            visit(dep)
        visiting.discard(node)
        done.add(node)

    for check_id in graph:
        visit(check_id)


def _catalog_yaml(root: Path, relative: str) -> dict:
    path = (root / relative).resolve()
    if root.resolve() not in path.parents:
        raise CatalogError(f"arquivo fora do catálogo: {relative}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise CatalogError(f"não foi possível ler {relative}: {exc}") from exc
    if not isinstance(data, dict) or not data:
        raise CatalogError(f"objeto YAML vazio ou inválido: {relative}")
    return data


def load_catalog(directory: str | Path) -> CheckCatalog:
    root = Path(directory)
    manifest = root / "catalogo.yaml"
    if not manifest.exists():
        raise CatalogError(f"catalogo.yaml não encontrado em {root}")
    raw = _catalog_yaml(root, "catalogo.yaml")
    if raw.get("schema_version") != CATALOG_SCHEMA:
        raise CatalogError(f"esquema esperado {CATALOG_SCHEMA}")
    checks = []
    for relative in raw.get("checks") or []:
        data = _catalog_yaml(root, relative)
        if data.get("schema_version") != CHECK_SCHEMA:
            raise CatalogError(f"{relative}: esquema esperado {CHECK_SCHEMA}")
        try:
            checks.append(parse_check(data))
        except CheckValidationError as exc:
            raise CatalogError(f"{relative}: {exc}") from exc
    if raw.get("publication_state") in {"DRAFT", "TEST_ONLY"} and any(
            c.production_eligible for c in checks):
        raise CatalogError("catálogo em rascunho não pode conter check de produção")
    return CheckCatalog(
        id=raw["id"], name=raw["name"], version=int(raw["version"]),
        jurisdiction=raw["jurisdiction"], publication_state=raw["publication_state"],
        checks=tuple(checks), raw=raw)


def verify_catalog(catalog: CheckCatalog,
                   sources: dict[str, NormativeText]) -> dict[str, Any]:
    """Confere cada citação do catálogo contra os textos ingeridos."""
    checks_out: list[dict[str, Any]] = []
    failures: list[str] = []
    for check in catalog.checks:
        citations = []
        basis = check.interpretation.basis if check.interpretation else ()
        for role, src in ([("normative_basis", s) for s in check.normative_basis]
                          + [("interpretation", s) for s in basis]):
            if src.document.startswith("EXEMPLO"):
                continue
            result = verify_citation(sources, src.document, src.item, tuple(src.quote))
            citations.append({**result.as_dict(), "edition_declared": src.edition,
                              "role": role})
            if not result.verified:
                missing = f" ({', '.join(result.missing_terms)})" if result.missing_terms else ""
                failures.append(f"{check.id}: {src.document} {src.item} — "
                                f"{result.problem}{missing}")
        checks_out.append({"id": check.id, "version": check.version, "title": check.title,
                           "system": check.system, "type": check.type,
                           "severity": str(check.severity), "manual": check.manual,
                           "content_sha256": check.content_hash, "citations": citations,
                           "interpretation": (check.interpretation.as_dict()
                                              if check.interpretation else None)})
    used = sorted({c["document"] for check in checks_out for c in check["citations"]})
    return {
        "catalog": {"id": catalog.id, "name": catalog.name, "version": catalog.version,
                    "jurisdiction": catalog.jurisdiction,
                    "publication_state": catalog.publication_state,
                    "content_sha256": catalog.content_sha256},
        "checks": checks_out,
        "sources": [sources[d].summary() for d in used if d in sources],
        "verified": not failures, "failures": failures,
    }
