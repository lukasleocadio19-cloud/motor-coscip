"""Pacote normativo (package/1.0): regras + dicionário de símbolos + matriz de cobertura.

A importação confere TODAS as citações contra os textos ingeridos. Uma citação que não
confere impede o pacote: nenhuma regra entra sem fonte verificada.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from coscip_normative.requirements import verify_requirements
from coscip_normative.sources import NormativeText, verify_citation, verify_table_row
from coscip_rules.dsl import RuleDefinition, check_dependency_cycles, parse_rule

PACKAGE_SCHEMA = "package/1.0"


class PackageError(ValueError):
    pass


@dataclass
class RulePackageDef:
    id: str
    name: str
    version: int
    jurisdiction: str
    publication_state: str
    rules: list[RuleDefinition]
    symbols: dict[str, Any]
    coverage: list[dict[str, Any]]
    raw: dict[str, Any] = field(repr=False, default_factory=dict)
    # Tabela de enquadramento (ocupação → risco), opcional.
    classification: dict[str, Any] | None = None
    requirements: dict[str, Any] | None = None

    @property
    def content_sha256(self) -> str:
        canonical = json.dumps({
            "package": {k: v for k, v in self.raw.items() if k not in {"rules", "symbols"}},
            "rules": sorted(r.content_hash for r in self.rules),
            "symbols": self.symbols,
            "classification": self.classification,
            "requirements": self.requirements,
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _package_yaml(root: Path, relative: str) -> dict:
    path = (root / relative).resolve()
    if root.resolve() not in path.parents:
        raise PackageError(f"arquivo fora do pacote: {relative}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PackageError(f"não foi possível ler {relative}: {exc}") from exc
    if not isinstance(data, dict) or not data:
        raise PackageError(f"objeto YAML vazio ou inválido: {relative}")
    return data


def load_package(directory: str | Path) -> RulePackageDef:
    root = Path(directory)
    manifest_path = root / "pacote.yaml"
    if not manifest_path.exists():
        raise PackageError(f"pacote.yaml não encontrado em {root}")
    raw = _package_yaml(root, "pacote.yaml")
    if raw.get("schema_version") != PACKAGE_SCHEMA:
        raise PackageError(f"esquema esperado {PACKAGE_SCHEMA}")
    rules = []
    for rel in raw.get("rules") or []:
        path = (root / rel).resolve()
        if root.resolve() not in path.parents:
            raise PackageError(f"regra fora do pacote: {rel}")
        rules.append(parse_rule(_package_yaml(root, rel)))
    ids = [r.id for r in rules]
    if len(ids) != len(set(ids)):
        raise PackageError("regras duplicadas no pacote")
    check_dependency_cycles(rules)
    symbols = _package_yaml(root, raw["symbols"])
    if raw.get("publication_state") in {"DRAFT", "TEST_ONLY"} and any(
            r.production_eligible for r in rules):
        raise PackageError("pacote em rascunho não pode conter regra de produção")
    classification = None
    if raw.get("classification"):
        classification = _package_yaml(root, raw["classification"])
        divisions = [d["id"] for d in classification.get("divisions") or []]
        if len(divisions) != len(set(divisions)):
            raise PackageError("divisões duplicadas na tabela de enquadramento")
        if set(classification.get("risk_to_rules") or {}) != set(
                classification.get("risks") or []):
            raise PackageError("risk_to_rules precisa mapear exatamente os riscos declarados")
    return RulePackageDef(
        id=raw["id"], name=raw["name"], version=int(raw["version"]),
        jurisdiction=raw["jurisdiction"], publication_state=raw["publication_state"],
        rules=rules, symbols=symbols, coverage=list(raw.get("coverage") or []), raw=raw,
        classification=classification,
        requirements=(_package_yaml(root, raw["requirements"])
                      if raw.get("requirements") else None),
    )


def verify_classification(table: dict[str, Any], sources: dict[str, NormativeText],
                          failures: list[str]) -> dict[str, Any]:
    """Cada divisão: divisão + começo da descrição + risco na mesma linha da tabela.

    Célula mesclada (``merged_from``): a linha da divisão precisa existir sem risco próprio
    e a linha da divisão de origem precisa trazer o risco (conferido também na imagem da
    página, registrado em ``notes``).
    """
    doc, item = table["source"]["document"], table["source"]["item"]
    risks = table["risks"]
    out = []
    for d in table["divisions"]:
        key = (d["id"], d["description"][:40])
        row = verify_table_row(sources, doc, item, key)
        ok, problem, origin = row.verified, row.problem, None
        if ok and not d.get("merged_from"):
            ok = verify_table_row(sources, doc, item, (*key, d["risk"])).verified
            problem = None if ok else f"risco {d['risk']} não está na linha"
        elif ok:
            if any(verify_table_row(sources, doc, item, (*key, r)).verified for r in risks):
                ok, problem = False, "linha tem risco próprio; retire merged_from"
            else:
                origin = verify_table_row(sources, doc, item, (d["merged_from"], d["risk"]))
                ok, problem = origin.verified, origin.problem
        if not ok:
            failures.append(f"enquadramento {d['id']}: {doc} {item} — {problem}")
        out.append({**d, "verified": ok, "page": row.page, "excerpt": row.excerpt,
                    "origin_excerpt": origin.excerpt if origin else None})
    mapping = table.get("risk_to_rules_source")
    mapping_check = None
    if mapping:
        c = verify_citation(sources, mapping["document"], mapping["item"],
                            tuple(mapping.get("quote") or ()))
        mapping_check = c.as_dict()
        if not c.verified:
            failures.append(f"enquadramento (mapa de risco): {c.document} {c.item} — "
                            f"{c.problem}")
    return {"source": table["source"], "risks": risks, "risk_to_rules": table["risk_to_rules"],
            "risk_to_rules_citation": mapping_check, "notes": table.get("notes") or [],
            "divisions": out,
            "source_sha256": sources[doc].text_sha256 if doc in sources else None}


def verify_package(pkg: RulePackageDef, sources: dict[str, NormativeText]) -> dict[str, Any]:
    """Confere cada citação (regras, dicionário e cobertura). Devolve o relatório completo."""
    rules_out = []
    failures = []
    for rule in pkg.rules:
        checks = []
        for src in (rule.source, *rule.extra_sources):
            if src.document.startswith("EXEMPLO"):
                continue
            c = verify_citation(sources, src.document, src.item, tuple(src.quote))
            checks.append({**c.as_dict(), "edition_declared": src.edition})
            if not c.verified:
                failures.append(f"{rule.id}: {src.document} {src.item} — {c.problem}"
                                + (f" ({', '.join(c.missing_terms)})" if c.missing_terms else ""))
        rules_out.append({"id": rule.id, "version": rule.version, "title": rule.title,
                          "measure": rule.measure, "subject": rule.subject,
                          "content_sha256": rule.content_hash, "citations": checks})
    sym_src = pkg.symbols.get("source") or {}
    symbols_check = None
    if sym_src:
        c = verify_citation(sources, sym_src["document"], sym_src["item"],
                            tuple(sym_src.get("quote") or ()))
        symbols_check = c.as_dict()
        if not c.verified:
            failures.append(f"dicionário de símbolos: {c.document} {c.item} — {c.problem}")
    coverage_out = []
    for item in pkg.coverage:
        c = verify_citation(sources, item["document"], item["item"],
                            tuple(item.get("quote") or ()))
        coverage_out.append({**item, "citation": c.as_dict()})
        if not c.verified:
            failures.append(f"cobertura: {c.document} {c.item} — {c.problem}")
    classification_out = (verify_classification(pkg.classification, sources, failures)
                          if pkg.classification else None)
    used = {c["document"] for r in rules_out for c in r["citations"]}
    if pkg.classification:
        used.add(pkg.classification["source"]["document"])
    requirements_out = (verify_requirements(pkg.requirements, sources, failures)
                        if pkg.requirements is not None else None)
    if requirements_out and requirements_out.get("source"):
        used.add(requirements_out["source"]["document"])
    used_docs = sorted(used)
    return {
        "package": {"id": pkg.id, "name": pkg.name, "version": pkg.version,
                    "jurisdiction": pkg.jurisdiction,
                    "publication_state": pkg.publication_state,
                    "content_sha256": pkg.content_sha256},
        "rules": rules_out, "symbols_citation": symbols_check, "coverage": coverage_out,
        "classification": classification_out, "requirements": requirements_out,
        "sources": [sources[d].summary() for d in used_docs if d in sources],
        "verified": not failures, "failures": failures,
    }
