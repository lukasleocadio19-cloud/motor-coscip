"""Conjunto de evidências de um processo: consulta por campo e consenso entre fontes.

§54: não encontrar um campo é ``ExtractionGap``, nunca "o documento não contém".
§55: quando mais de uma fonte informa o mesmo campo, o consenso é explícito.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict

from coscip_cbm import ConsensusStatus
from coscip_evidence.models import Evidence


class ExtractionGap(BaseModel):
    """Uma extração rodou e não achou o campo. Isso não é ausência documental (§54)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    process_id: str
    source_id: str
    source_version: int
    subject: str = ""
    field: str
    extraction_method: str
    reason: str = "NOT_FOUND_BY_EXTRACTION"


def _provides(evidence: Evidence) -> set[str]:
    """Nomes pelos quais a evidência pode satisfazer uma fonte exigida.

    Tipo de fonte (CAD, DOCUMENT...) e categoria documental (ART, CURVA_BOMBA...) valem
    igualmente: um check pode exigir "CAD" ou exigir "ART e CURVA_BOMBA".
    """
    names = {str(evidence.source_type)}
    if evidence.source_category:
        names.add(evidence.source_category)
    return names


def _comparable(value: object) -> object:
    """Números comparam por valor; texto compara sem espaço/caixa. O resto compara igual."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int | float | Decimal):
        return Decimal(str(value))
    if isinstance(value, str):
        stripped = value.strip()
        try:
            return Decimal(stripped.replace(",", "."))
        except InvalidOperation:
            return " ".join(stripped.casefold().split())
    return value


@dataclass(frozen=True)
class Consensus:
    """O que as fontes dizem sobre um campo de um sujeito (§55)."""

    subject: str
    field: str
    status: ConsensusStatus
    values: tuple[object, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    missing_sources: tuple[str, ...] = ()

    @property
    def agreed_value(self) -> object | None:
        """Valor único quando as fontes concordam; ``None`` em divergência ou ausência."""
        if self.status in {ConsensusStatus.SUPPORTED, ConsensusStatus.SINGLE_SOURCE}:
            return self.values[0] if self.values else None
        return None


@dataclass
class EvidenceSet:
    """Evidências e lacunas de extração de um processo, imutáveis depois de reunidas."""

    process_id: str
    items: tuple[Evidence, ...] = ()
    gaps: tuple[ExtractionGap, ...] = ()
    _index: dict[tuple[str, str], tuple[Evidence, ...]] = dataclass_field(
        default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        index: dict[tuple[str, str], list[Evidence]] = {}
        for item in self.items:
            index.setdefault((item.subject, item.field), []).append(item)
        self._index = {k: tuple(v) for k, v in index.items()}

    @classmethod
    def build(cls, process_id: str, items: Iterable[Evidence],
              gaps: Iterable[ExtractionGap] = ()) -> EvidenceSet:
        return cls(process_id=process_id, items=tuple(items), gaps=tuple(gaps))

    def __iter__(self) -> Iterator[Evidence]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def for_field(self, field: str, *, subject: str = "") -> tuple[Evidence, ...]:
        return self._index.get((subject, field), ())

    def subjects(self) -> tuple[str, ...]:
        return tuple(sorted({item.subject for item in self.items if item.subject}))

    def has_gap(self, field: str, *, subject: str = "") -> bool:
        return any(g.field == field and g.subject == subject for g in self.gaps)

    def consensus(self, field: str, *, subject: str = "",
                  required_sources: Iterable[str] = ()) -> Consensus:
        found = [e for e in self.for_field(field, subject=subject)
                 if e.normalized_value is not None and e.located]
        required = tuple(required_sources)
        present = {name for e in found for name in _provides(e)}
        missing = tuple(s for s in required if s not in present)
        ids = tuple(e.id for e in found)
        if not found:
            # Nenhuma fonte informou o campo. Quando há fontes obrigatórias declaradas,
            # elas entram no achado para o analista saber o que pedir.
            return Consensus(subject, field, ConsensusStatus.MISSING_REQUIRED_SOURCE,
                             missing_sources=missing)
        distinct: list[object] = []
        for evidence in found:
            key = _comparable(evidence.normalized_value)
            if key not in [_comparable(v) for v in distinct]:
                distinct.append(evidence.normalized_value)
        if len(distinct) > 1:
            return Consensus(subject, field, ConsensusStatus.CONFLICTING,
                             tuple(distinct), ids, missing)
        if missing:
            return Consensus(subject, field, ConsensusStatus.MISSING_REQUIRED_SOURCE,
                             tuple(distinct), ids, missing)
        status = (ConsensusStatus.SUPPORTED if len(found) > 1
                  else ConsensusStatus.SINGLE_SOURCE)
        return Consensus(subject, field, status, tuple(distinct), ids)
