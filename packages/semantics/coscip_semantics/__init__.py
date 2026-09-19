"""Classificação assistida (plano §9).

Ordem: atributos explícitos → mapeamento confirmado → nomes/layers →
assinatura geométrica/contexto → classificador opcional.
Layer chamado EXTINTORES é evidência, não prova.
"""

from coscip_semantics.classify import Candidate, SemanticMapping, classify

__all__ = ["Candidate", "SemanticMapping", "classify"]
