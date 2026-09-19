"""Contratos de IA substituíveis.

- DocumentAssistant: trechos autorizados + tarefa → extrações com referência ao trecho
  (LLM multimodal econômico; candidato inicial Gemini 2.5 Flash / 3.1 Flash-Lite).
- DecisionClassifier: texto/JSON + opções delimitadas → escolha + distribuição
  (Jev da TypeSafe, opcional; não recebe imagens nem gera texto livre).

Sem ferramentas de escrita, navegação ou acesso a arquivos para o modelo.
Resposta sem evidência verificável é descartada ou fica pendente de revisão.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class AIDisabledError(RuntimeError):
    code = "AI_DISABLED"


@dataclass(frozen=True)
class Excerpt:
    evidence_id: str
    text: str | None = None
    image_png: bytes | None = None


@dataclass(frozen=True)
class Extraction:
    field: str
    value: Any
    evidence_ids: tuple[str, ...]
    model: str
    prompt_version: str


@dataclass(frozen=True)
class Decision:
    choice: str
    distribution: dict[str, float]
    model: str


class DocumentAssistant(Protocol):
    def extract(
        self, task: str, excerpts: list[Excerpt], output_schema: dict[str, Any]
    ) -> list[Extraction]: ...


class DecisionClassifier(Protocol):
    def decide(self, payload: dict[str, Any], options: list[str]) -> Decision: ...


class DisabledProvider:
    """Provedor padrão: IA desligada até configuração explícita da chave."""

    def extract(self, task: str, excerpts: list[Excerpt], output_schema: dict[str, Any]):
        raise AIDisabledError("IA desativada nas configurações locais")

    def decide(self, payload: dict[str, Any], options: list[str]):
        raise AIDisabledError("IA desativada nas configurações locais")


def verify_evidence(extractions: list[Extraction], allowed: set[str]) -> list[Extraction]:
    """Mantém apenas extrações cujas evidências existem e foram fornecidas."""
    return [x for x in extractions if x.evidence_ids and set(x.evidence_ids) <= allowed]
