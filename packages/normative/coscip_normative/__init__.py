"""Base normativa local: textos das NTs, índice de itens e verificação de citações."""

from coscip_normative.sources import (
    CitationCheck,
    Item,
    NormativeText,
    SourceError,
    fold,
    normalize_document_id,
    parse_markdown,
    verify_citation,
    verify_table_row,
)

__all__ = [
    "CitationCheck",
    "Item",
    "NormativeText",
    "SourceError",
    "fold",
    "normalize_document_id",
    "parse_markdown",
    "verify_citation",
    "verify_table_row",
]
