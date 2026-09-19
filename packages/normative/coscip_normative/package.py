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

from coscip_normative.sources import NormativeText, verify_citation
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

    @property
    def content_sha256(self) -> str:
        canonical = json.dumps({
            "package": {k: v for k, v in self.raw.items() if k not in {"rules", "symbols"}},
            "rules": sorted(r.content_hash for r in self.rules),
            "symbols": self.symbols,
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_package(directory: str | Path) -> RulePackageDef:
    root = Path(directory)
    manifest_path = root / "pacote.yaml"
    if not manifest_path.exists():
        raise PackageError(f"pacote.yaml não encontrado em {root}")
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != PACKAGE_SCHEMA:
        raise PackageError(f"esquema esperado {PACKAGE_SCHEMA}")
    rules = []
    for rel in raw.get("rules") or []:
        path = (root / rel).resolve()
        if root.resolve() not in path.parents:
            raise PackageError(f"regra fora do pacote: {rel}")
        rules.append(parse_rule(yaml.safe_load(path.read_text(encoding="utf-8"))))
    ids = [r.id for r in rules]
    if len(ids) != len(set(ids)):
        raise PackageError("regras duplicadas no pacote")
    check_dependency_cycles(rules)
    symbols = yaml.safe_load((root / raw["symbols"]).read_text(encoding="utf-8"))
    if raw.get("publication_state") in {"DRAFT", "TEST_ONLY"} and any(
            r.production_eligible for r in rules):
        raise PackageError("pacote em rascunho não pode conter regra de produção")
    return RulePackageDef(
        id=raw["id"], name=raw["name"], version=int(raw["version"]),
        jurisdiction=raw["jurisdiction"], publication_state=raw["publication_state"],
        rules=rules, symbols=symbols, coverage=list(raw.get("coverage") or []), raw=raw,
    )


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
    used_docs = sorted({c["document"] for r in rules_out for c in r["citations"]})
    return {
        "package": {"id": pkg.id, "name": pkg.name, "version": pkg.version,
                    "jurisdiction": pkg.jurisdiction,
                    "publication_state": pkg.publication_state,
                    "content_sha256": pkg.content_sha256},
        "rules": rules_out, "symbols_citation": symbols_check, "coverage": coverage_out,
        "sources": [sources[d].summary() for d in used_docs if d in sources],
        "verified": not failures, "failures": failures,
    }
