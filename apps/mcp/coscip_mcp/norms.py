"""Base normativa do MCP: textos das NTs e do Decreto, pacote e catálogo conferidos.

Os textos vêm de pastas com os ``.md`` convertidos (os mesmos que a base do app ingere).
Ordem de busca: ``COSCIP_NORMAS_DIR`` (pastas separadas por ``;``) ou, se ausente, as skills
CBMERJ instaladas no Claude (grupos 1–5 e o Decreto; **nunca** o grupo 5 legado).

Mesma regra do app: citação que não confere impede o check. Aqui, em vez de recusar o
catálogo inteiro, o check sem citação conferida (e quem depende dele) fica fora do plano e
aparece na lista de "não verificados" — a análise diz o que deixou de verificar e por quê.
"""

from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from coscip_normative import NormativeText, fold, parse_markdown
from coscip_normative.package import RulePackageDef, load_package, verify_package
from coscip_normative.verification import CheckCatalog, load_catalog, verify_catalog

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_DIR = ROOT / "normative" / "base"
CHECKS_DIR = ROOT / "normative" / "checks"
SKILL_GROUPS = ("cbmerj-grupo-1-generalidades", "cbmerj-grupo-2-medidas-seguranca",
                "cbmerj-grupo-3-riscos-especificos", "cbmerj-grupo-4-estruturas-especiais",
                "cbmerj-grupo-5-eventos")
DECREE = ("orquestrar-analise-cbmerj", "decreto-42-2018-coscip-compilado.md")
_PAGE = re.compile(r"^## Página (\d+)\s*$", re.M)


def source_files() -> list[Path]:
    configured = os.environ.get("COSCIP_NORMAS_DIR")
    if configured:
        return sorted(f for d in configured.split(";") if d.strip()
                      for f in Path(d.strip()).glob("*.md"))
    roots = glob.glob(os.path.expandvars(
        r"%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\*\*\skills"))
    files: list[Path] = []
    for root in roots[:1]:
        for group in SKILL_GROUPS:  # lista explícita: o glob pegaria o grupo legado
            files += sorted((Path(root) / group / "references").glob("nt-*.md"))
        decree = Path(root) / DECREE[0] / "references" / DECREE[1]
        if decree.exists():
            files.append(decree)
    return files


@dataclass
class NormBase:
    sources: dict[str, NormativeText]
    files: list[str]
    rejected: list[str]
    package: RulePackageDef
    package_report: dict[str, Any]
    catalog: CheckCatalog
    excluded_checks: dict[str, str] = field(default_factory=dict)

    @property
    def dictionary(self) -> dict[str, Any]:
        return self.package.symbols

    def table(self, name: str) -> dict[str, Any] | None:
        """Tabela do pacote conferida (Anexo III, Anexo C, NT 1-04) ou ``None``."""
        out = self.package_report.get(name)
        if name == "classification":  # conferida linha a linha (cada divisão tem "verified")
            return out or None
        return out if out and out.get("verified") else None

    def summary(self) -> dict[str, Any]:
        return {"fontes": len(self.sources), "documentos": sorted(self.sources),
                "arquivos_recusados": self.rejected,
                "checks_no_plano": len(self.catalog.checks),
                "checks_fora_por_citacao": self.excluded_checks,
                "tabelas": {n: bool(self.table(n)) for n in
                            ("classification", "requirements", "exit_distances")}}


_CACHE: dict[tuple[str, ...], NormBase] = {}


def load_base() -> NormBase:
    files = source_files()
    key = tuple(str(f) for f in files)
    if key in _CACHE:
        return _CACHE[key]
    sources: dict[str, NormativeText] = {}
    rejected = []
    for f in files:
        try:
            text = parse_markdown(f.read_bytes(), f.name)
        except Exception as exc:  # noqa: BLE001 — arquivo ruim não derruba a base
            rejected.append(f"{f.name}: {exc}")
            continue
        sources[text.document] = text
    package = load_package(PACKAGE_DIR)
    report = verify_package(package, sources)
    catalog, excluded = _verified_catalog(load_catalog(CHECKS_DIR), sources)
    base = NormBase(sources, [str(f) for f in files], rejected, package, report, catalog,
                    excluded)
    _CACHE[key] = base
    return base


def _verified_catalog(catalog: CheckCatalog,
                      sources: dict[str, NormativeText]) -> tuple[CheckCatalog, dict[str, str]]:
    report = verify_catalog(catalog, sources)
    excluded: dict[str, str] = {}
    for check in report["checks"]:
        bad = [c for c in check["citations"] if not c["verified"]]
        if bad:
            excluded[check["id"]] = "; ".join(
                f"{c['document']} {c['item']}: {c.get('problem') or 'não confere'}" for c in bad)
    changed = True
    while changed:  # quem depende de check excluído também sai
        changed = False
        for check in catalog.checks:
            if check.id not in excluded:
                missing = [d for d in check.depends_on if d in excluded]
                if missing:
                    excluded[check.id] = f"depende de {', '.join(missing)}"
                    changed = True
    kept = tuple(c for c in catalog.checks if c.id not in excluded)
    return CheckCatalog(id=catalog.id, name=catalog.name, version=catalog.version,
                        jurisdiction=catalog.jurisdiction,
                        publication_state=catalog.publication_state, checks=kept,
                        raw=catalog.raw), excluded


def _page_at(text: str, pos: int) -> int | None:
    pages = [(m.start(), int(m.group(1))) for m in _PAGE.finditer(text[:pos])]
    return pages[-1][1] if pages else None


def item_text(base: NormBase, document: str, item: str, limit: int = 6000) -> dict[str, Any]:
    from coscip_normative import normalize_document_id

    doc = base.sources.get(normalize_document_id(document))
    if doc is None:
        return {"erro": f"documento ausente da base: {document}",
                "disponiveis": sorted(base.sources)}
    occ = doc.items.get(str(item))
    if not occ:
        near = sorted(k for k in doc.items if k.startswith(str(item).split(".")[0]))[:40]
        return {"erro": f"item {item} não encontrado em {doc.document}", "itens_proximos": near}
    out = []
    for it in occ[:3]:
        body = doc.text[it.start:it.end].strip()
        out.append({"pagina": it.page, "texto": body[:limit],
                    "truncado": len(body) > limit})
    return {"documento": doc.document, "edicao": doc.edition, "item": str(item),
            "ocorrencias": out}


def search(base: NormBase, query: str, document: str | None = None,
           limit: int = 20) -> list[dict[str, Any]]:
    terms = [fold(t) for t in query.split() if len(t) > 2]
    hits = []
    for name, doc in sorted(base.sources.items()):
        if document and fold(document) not in fold(name):
            continue
        for para in re.finditer(r"[^\n]+", doc.text):  # linha a linha no texto original
            line = fold(para.group(0))
            if terms and all(t in line for t in terms):
                hits.append({"documento": name, "pagina": _page_at(doc.text, para.start()),
                             "trecho": para.group(0).strip()[:400]})
                if len(hits) >= limit:
                    return hits
    return hits
