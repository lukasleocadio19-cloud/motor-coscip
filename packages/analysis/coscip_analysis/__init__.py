"""Análise automática da planta: símbolos, áreas, percursos e regras sobre o DXF confirmado."""

from coscip_analysis.analyze import SCHEMA, AnalysisInput, RuleBinding, run
from coscip_analysis.dictionary import (
    DictionaryError,
    SymbolDictionary,
    load_dictionary,
    parse_dictionary,
)

__all__ = [
    "SCHEMA",
    "AnalysisInput",
    "DictionaryError",
    "RuleBinding",
    "SymbolDictionary",
    "load_dictionary",
    "parse_dictionary",
    "run",
]
