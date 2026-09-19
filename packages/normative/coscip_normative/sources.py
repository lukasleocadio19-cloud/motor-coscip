"""Base normativa: ingestão de textos das NTs e verificação de citações (REG-01).

Formato aceito: Markdown com front matter YAML, como as conversões integrais das NTs do
CBMERJ (``documento``, ``edicao``, ``fonte_oficial``, ``sha256_pdf``, ``data_captura``) e
marcadores ``## Página N``. O texto é preservado byte a byte (SHA-256); o índice de itens é
derivado de forma determinística a cada leitura.

Uma regra só entra num pacote se cada citação dela for encontrada no texto ingerido:
documento, item e todos os termos de ``quote`` dentro do trecho do item.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

import yaml

SOURCE_SCHEMA = "normative-source/1.0"
# Trecho considerado para itens numerados e tabelas (tabelas convertidas espalham células).
ITEM_WINDOW = 1800
TABLE_WINDOW = 3500
ANNEX_WINDOW = 60_000  # anexo vai até o próximo anexo (tabelas longas de símbolos)

_PAGE = re.compile(r"^##\s+P[áa]gina\s+(\d+)\s*$", re.M)
_NUMBERED = re.compile(r"^(?:#{1,6}\s*)?(\d+(?:\.\d+){1,5})\.?\s+\S", re.M)
_SECTION = re.compile(r"^#{2,6}\s*(\d{1,2})\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ]", re.M)
_TABLE = re.compile(r"Tabela\s+([A-Z]?\d{1,2}[A-Z]?)\s*[-–—]", re.I)
_ANNEX = re.compile(r"^(?:#{1,6}\s*)?ANEXO\s+([IVX]{1,5}|[A-Z])\b", re.M | re.I)
# Artigos de decretos/leis ("Art. 15 -", "Art. 4º -"), inclusive no meio da linha.
_ARTICLE = re.compile(r"\bArt\.\s*(\d{1,3})\s*[ºo°]?\s*[-–—]")
_DOC_FROM_NAME = re.compile(r"nt[-_ ]?(\d)[-_ ](\d{2})", re.I)


class SourceError(ValueError):
    pass


@dataclass(frozen=True)
class Item:
    id: str  # "5.2.4", "Tabela 3", "Anexo C", "Anexo III", "Art. 15", "5"
    kind: str  # NUMBERED | TABLE | ANNEX | SECTION | ARTICLE
    page: int | None
    start: int
    end: int


@dataclass
class NormativeText:
    document: str  # "NT 2-01"
    title: str
    edition: str
    official_url: str | None
    pdf_sha256: str | None
    captured_at: str | None
    effective: str | None
    text_sha256: str
    text: str
    meta: dict[str, Any]
    # Todas as ocorrências de cada item (tabelas aparecem no sumário e depois no corpo).
    items: dict[str, list[Item]] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "schema_version": SOURCE_SCHEMA, "document": self.document, "title": self.title,
            "edition": self.edition, "official_url": self.official_url,
            "pdf_sha256": self.pdf_sha256, "captured_at": self.captured_at,
            "effective": self.effective, "text_sha256": self.text_sha256,
            "item_count": len(self.items),
            "pages": max((i.page or 0 for occ in self.items.values() for i in occ), default=0),
        }


def normalize_document_id(raw: str) -> str:
    """"NT-2-01" → "NT 2-01"; "NT-2-03-PARTE-2" → "NT 2-03 P2";
    "DECRETO-42-2018" → "Decreto 42/2018"."""
    dec = re.fullmatch(r"\s*DECRETO\s*[-_ ]?\s*(?:N[ºo°.]?\s*)?([\d.]+)\s*[-_/ ]\s*(\d{4})\s*",
                       raw, re.I)
    if dec:
        return f"Decreto {dec.group(1).replace('.', '')}/{dec.group(2)}"
    m = re.search(r"(\d)\s*[-_ ]\s*(\d{2})", raw)
    if not m or not re.search(r"\bNT\b|^NT|NT[-_ ]", raw, re.I):
        raise SourceError(f"identificação de NT não reconhecida: {raw!r}")
    part = re.search(r"(?:PARTE|P)\s*[-_ ]?\s*(\d)\b", raw[m.end():], re.I)
    return f"NT {m.group(1)}-{m.group(2)}" + (f" P{part.group(1)}" if part else "")


def fold(text: str) -> str:
    """Forma de comparação: sem acentos, minúsculas, sem pipes de tabela, espaços únicos."""
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.replace("|", " ").replace("²", "2").replace("º", "o").replace("ª", "a")
    return re.sub(r"\s+", " ", t).strip().lower()


def _front_matter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        raise SourceError("front matter sem fechamento")
    meta = yaml.safe_load(text[3:end]) or {}
    if not isinstance(meta, dict):
        raise SourceError("front matter inválido")
    return meta, text[end + 4:]


def _page_at(pages: list[tuple[int, int]], pos: int) -> int | None:
    page = None
    for start, n in pages:
        if start > pos:
            break
        page = n
    return page


def _index(body: str, offset: int) -> dict[str, list[Item]]:
    pages = [(m.start() + offset, int(m.group(1))) for m in _PAGE.finditer(body)]
    anchors: list[tuple[int, str, str]] = []
    for m in _NUMBERED.finditer(body):
        anchors.append((m.start(), m.group(1), "NUMBERED"))
    for m in _SECTION.finditer(body):
        anchors.append((m.start(), m.group(1), "SECTION"))
    for m in _TABLE.finditer(body):
        anchors.append((m.start(), f"Tabela {m.group(1).upper()}", "TABLE"))
    for m in _ANNEX.finditer(body):
        anchors.append((m.start(), f"Anexo {m.group(1).upper()}", "ANNEX"))
    for m in _ARTICLE.finditer(body):
        anchors.append((m.start(), f"Art. {m.group(1)}", "ARTICLE"))
    anchors.sort()
    items: dict[str, list[Item]] = {}
    for i, (pos, ident, kind) in enumerate(anchors):
        if kind == "NUMBERED":
            nxt = next((p for p, _, k in anchors[i + 1:] if k == "NUMBERED"), len(body))
            end = min(nxt, pos + ITEM_WINDOW)
        elif kind == "ARTICLE":
            nxt = next((p for p, _, k in anchors[i + 1:] if k in ("ARTICLE", "ANNEX")),
                       len(body))
            end = min(nxt, pos + 2 * ITEM_WINDOW)
        elif kind == "ANNEX":
            nxt = next((p for p, _, k in anchors[i + 1:] if k == "ANNEX"), len(body))
            end = min(nxt, pos + ANNEX_WINDOW)
        else:
            end = min(len(body), pos + (TABLE_WINDOW if kind != "SECTION" else ITEM_WINDOW))
        end = max(end, min(len(body), pos + 200))
        items.setdefault(ident, []).append(
            Item(ident, kind, _page_at(pages, pos + offset), pos + offset, end + offset))
    return items


def parse_markdown(raw: bytes, filename: str = "") -> NormativeText:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SourceError("texto normativo precisa estar em UTF-8") from exc
    meta, body = _front_matter(text)
    doc_raw = str(meta.get("documento") or meta.get("document") or "")
    if not doc_raw:
        m = _DOC_FROM_NAME.search(filename)
        if not m:
            raise SourceError(f"{filename}: sem campo 'documento' e nome sem NT")
        doc_raw = f"NT {m.group(1)}-{m.group(2)}"
    document = normalize_document_id(doc_raw)
    offset = len(text) - len(body)
    items = _index(body, offset)
    if not items:
        raise SourceError(f"{document}: nenhum item numerado reconhecido")
    return NormativeText(
        document=document,
        title=str(meta.get("titulo") or meta.get("title") or document),
        edition=str(meta.get("edicao") or meta.get("edition") or "não informada"),
        official_url=meta.get("fonte_oficial") or meta.get("url"),
        pdf_sha256=meta.get("sha256_pdf"),
        captured_at=str(meta["data_captura"]) if meta.get("data_captura") else None,
        effective=str(meta["vigencia"]) if meta.get("vigencia") else None,
        text_sha256=hashlib.sha256(raw).hexdigest(),
        text=text, meta={k: str(v) for k, v in meta.items()}, items=items,
    )


@dataclass(frozen=True)
class CitationCheck:
    document: str
    item: str
    verified: bool
    page: int | None = None
    excerpt: str = ""
    missing_terms: tuple[str, ...] = ()
    problem: str | None = None
    text_sha256: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"document": self.document, "item": self.item, "verified": self.verified,
                "page": self.page, "excerpt": self.excerpt,
                "missing_terms": list(self.missing_terms), "problem": self.problem,
                "text_sha256": self.text_sha256}


def _excerpt(segment: str, terms: tuple[str, ...], size: int = 420) -> str:
    flat = re.sub(r"\s+", " ", segment.replace("|", " ")).strip()
    folded = fold(flat)
    pos = min((folded.find(fold(t)) for t in terms if fold(t) in folded), default=0)
    start = max(0, pos - 60)
    out = flat[start:start + size]
    return ("…" if start else "") + out + ("…" if start + size < len(flat) else "")


def verify_citation(sources: dict[str, NormativeText], document: str, item: str,
                    quote: tuple[str, ...] = ()) -> CitationCheck:
    item = str(item)
    try:
        doc_id = normalize_document_id(document)
    except SourceError as exc:
        return CitationCheck(document, item, False, problem=str(exc))
    src = sources.get(doc_id)
    if src is None:
        return CitationCheck(doc_id, item, False, problem="documento ausente da base")
    occurrences = src.items.get(item)
    if not occurrences:
        return CitationCheck(doc_id, item, False, problem="item não encontrado no texto",
                             text_sha256=src.text_sha256)
    # Vale a ocorrência que contém todos os termos (ou, na falta, a que contém mais).
    best = None
    for it in occurrences:
        segment = src.text[it.start:it.end]
        folded = fold(segment)
        missing = tuple(t for t in quote if fold(t) not in folded)
        if best is None or len(missing) < len(best[2]):
            best = (it, segment, missing)
        if not missing:
            break
    it, segment, missing = best
    return CitationCheck(doc_id, item, not missing, it.page, _excerpt(segment, quote),
                         missing, "termos não encontrados no item" if missing else None,
                         src.text_sha256)
