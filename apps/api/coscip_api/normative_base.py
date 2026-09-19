"""Base normativa local: ingestão dos textos das NTs e importação de pacotes verificados.

- Texto ingerido é imutável (SHA-256); reenviar o mesmo texto não duplica a fonte.
- Um documento pode ter várias ingestões (edições/correções): vale a mais recente.
- Pacote só é importado se TODAS as citações conferirem com as fontes vigentes; o hash do
  pacote inclui o hash dos textos usados, então nova ingestão gera novo pacote.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from coscip_api.db import write_tx
from coscip_api.models import AuditEvent, FileObject, NormativeSource, RulePackage, RuleVersion
from coscip_normative import NormativeText, SourceError, parse_markdown
from coscip_normative.package import PackageError, load_package, verify_package

BUNDLED_BASE = Path(__file__).resolve().parents[3] / "normative" / "base"
MAX_SOURCE_BYTES = 5 * 1024 * 1024


class NormativeError(ValueError):
    def __init__(self, message: str, details: list[str] | None = None) -> None:
        super().__init__(message)
        self.details = details or []


def ingest_sources(factory, storage, files: list[tuple[str, bytes]],  # noqa: ANN001
                   actor_id: str | None = None) -> list[dict[str, Any]]:
    out = []
    for name, raw in files:
        if len(raw) > MAX_SOURCE_BYTES:
            out.append({"file": name, "status": "REJECTED", "problem": "arquivo acima de 5 MB"})
            continue
        try:
            nt = parse_markdown(raw, name)
        except SourceError as exc:
            out.append({"file": name, "status": "REJECTED", "problem": str(exc)})
            continue
        with factory() as s:
            existing = s.scalar(select(NormativeSource).where(
                NormativeSource.text_sha256 == nt.text_sha256))
        if existing:
            out.append({"file": name, "status": "ALREADY_PRESENT", "id": existing.id,
                        "document": nt.document, "text_sha256": nt.text_sha256})
            continue
        obj = storage.write_stream(f"normative/sources/{nt.text_sha256}.md", [raw])
        with write_tx(factory) as s:
            fo = FileObject(tenant_id=_tenant(s), key=obj.key, sha256=obj.sha256,
                            size=obj.size, mime="text/markdown",
                            inspection={"kind": "NORMATIVE_SOURCE", "file": name})
            s.add(fo)
            s.flush()
            summary = nt.summary()
            row = NormativeSource(
                document=nt.document, edition=nt.edition[:100], url=nt.official_url,
                file_sha256=nt.pdf_sha256, collected_at=(nt.captured_at or "")[:10] or None,
                title=nt.title[:300], text_sha256=nt.text_sha256, artifact_id=fo.id,
                meta={**summary, "file": name, "effective": nt.effective})
            s.add(row)
            s.flush()
            s.add(AuditEvent(tenant_id=fo.tenant_id, actor_id=actor_id,
                             action="normative.source_ingested", resource=row.id,
                             diff={"document": nt.document, "text_sha256": nt.text_sha256}))
            out.append({"file": name, "status": "INGESTED", "id": row.id,
                        "document": nt.document, "text_sha256": nt.text_sha256,
                        "items": summary["item_count"]})
    return out


def _tenant(s: Session) -> str:
    from coscip_api.models import Organization

    return s.scalars(select(Organization.id).limit(1)).one()


def list_sources(s: Session) -> list[dict[str, Any]]:
    rows = s.scalars(select(NormativeSource).where(NormativeSource.text_sha256.is_not(None))
                     .order_by(NormativeSource.document, NormativeSource.created_at.desc())).all()
    current: set[str] = set()
    out = []
    for r in rows:
        is_current = r.document not in current
        current.add(r.document)
        out.append({"id": r.id, "document": r.document, "title": r.title,
                    "edition": r.edition, "url": r.url, "pdf_sha256": r.file_sha256,
                    "text_sha256": r.text_sha256, "collected_at": r.collected_at,
                    "items": (r.meta or {}).get("item_count"), "current": is_current,
                    "created_at": r.created_at})
    return out


def current_texts(s: Session, storage) -> dict[str, NormativeText]:  # noqa: ANN001
    texts: dict[str, NormativeText] = {}
    for row in list_sources(s):
        if not row["current"]:
            continue
        src = s.get(NormativeSource, row["id"])
        fo = s.get(FileObject, src.artifact_id)
        with storage.open(fo.key) as fh:
            raw = fh.read()
        if hashlib.sha256(raw).hexdigest() != src.text_sha256:
            raise NormativeError(f"texto de {src.document} não confere com o hash gravado")
        texts[src.document] = parse_markdown(raw, fo.key)
    return texts


def import_package(factory, storage, directory: Path | None = None,  # noqa: ANN001
                   actor_id: str | None = None) -> dict[str, Any]:
    try:
        pkg = load_package(directory or BUNDLED_BASE)
    except (PackageError, ValueError) as exc:
        raise NormativeError(f"pacote inválido: {exc}") from exc
    with factory() as s:
        texts = current_texts(s, storage)
    report = verify_package(pkg, texts)
    if not report["verified"]:
        raise NormativeError("citações do pacote não conferem com a base ingerida",
                             report["failures"])
    sources_hash = hashlib.sha256(json.dumps(
        sorted(src["text_sha256"] for src in report["sources"])).encode()).hexdigest()
    content = hashlib.sha256(f"{pkg.content_sha256}:{sources_hash}".encode()).hexdigest()
    with write_tx(factory) as s:
        existing = s.scalar(select(RulePackage).where(RulePackage.content_sha256 == content))
        if existing:
            return {"id": existing.id, "status": "ALREADY_PRESENT", **_pkg_out(existing)}
        bindings = []
        for rule, rep in zip(pkg.rules, report["rules"], strict=True):
            rv = s.scalar(select(RuleVersion).where(RuleVersion.rule_id == rule.id,
                                                    RuleVersion.version == rule.version))
            if rv is None:
                rv = RuleVersion(rule_id=rule.id, version=rule.version,
                                 dsl=rule.model_dump(mode="json"),
                                 content_sha256=rule.content_hash,
                                 publication_state=rule.publication_state,
                                 production_eligible=rule.production_eligible)
                s.add(rv)
                s.flush()
            elif rv.content_sha256 != rule.content_hash:
                raise NormativeError(f"{rule.id} v{rule.version} já existe com outro conteúdo; "
                                     "incremente a versão da regra")
            bindings.append({"rule_id": rule.id, "version": rule.version,
                             "rule_version_id": rv.id, "citations": rep["citations"],
                             "title": rule.title, "measure": rule.measure,
                             "subject": rule.subject})
        row = RulePackage(
            name=pkg.name, jurisdiction=pkg.jurisdiction, content_sha256=content,
            state=pkg.publication_state,
            manifest={"package": report["package"], "sources_sha256": sources_hash,
                      "rules": bindings, "symbols": pkg.symbols,
                      "symbols_citation": report["symbols_citation"],
                      "coverage": report["coverage"], "sources": report["sources"],
                      "verified": True})
        s.add(row)
        s.flush()
        s.add(AuditEvent(tenant_id=_tenant(s), actor_id=actor_id,
                         action="normative.package_imported", resource=row.id,
                         diff={"package": pkg.id, "content_sha256": content}))
        return {"id": row.id, "status": "IMPORTED", **_pkg_out(row)}


def _pkg_out(p: RulePackage) -> dict[str, Any]:
    m = p.manifest or {}
    return {"name": p.name, "jurisdiction": p.jurisdiction, "state": p.state,
            "content_sha256": p.content_sha256, "verified": m.get("verified", False),
            "rules": len(m.get("rules", [])), "package": m.get("package"),
            "created_at": p.created_at}
