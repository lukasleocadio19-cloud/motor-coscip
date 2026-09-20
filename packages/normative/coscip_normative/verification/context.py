"""Contexto do processo: o enquadramento que decide o que precisa ser verificado (§18).

A análise deixa de começar por "o que consigo encontrar nesta planta?" e passa a começar
por "o que o COSCIP exige verificar neste processo?". Este é o dado de entrada dessa
pergunta. Fato ausente é **desconhecido**, nunca ``False`` nem zero.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from coscip_rules import EvaluationContext
from coscip_rules.engine import Fact

CONTEXT_SCHEMA = "process-context/1.0"


class ProcessContext(BaseModel):
    """Enquadramento e condições do processo, sem nada inferido silenciosamente."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = CONTEXT_SCHEMA
    process_id: str
    occupancy: str | None = None
    risk_class: str | None = None
    risk_basis: str | None = None
    building_area_m2: float | None = Field(default=None, gt=0)
    building_floors: int | None = Field(default=None, ge=1)
    building_height_m: float | None = Field(default=None, ge=0)
    special_conditions: tuple[str, ...] = ()
    # Fatos livres do enquadramento (exigências efetivas, portas de qualidade, confirmações
    # do analista). Chave ausente = desconhecido.
    facts: dict[str, Any] = Field(default_factory=dict)

    def all_facts(self) -> dict[str, Any]:
        named = {
            "occupancy": self.occupancy,
            "risk_class": self.risk_class,
            "building_area_m2": self.building_area_m2,
            "building_floors": self.building_floors,
            "building_height_m": self.building_height_m,
        }
        merged = {k: v for k, v in named.items() if v is not None}
        for condition in self.special_conditions:
            merged[f"condition_{condition}"] = True
        # Os fatos livres têm precedência: é onde o analista e o compilador normativo
        # registram exigência efetiva, override e portas de qualidade.
        merged.update({k: v for k, v in self.facts.items() if v is not None})
        return merged

    def evaluation_context(self) -> EvaluationContext:
        facts = {name: Fact(value=value) for name, value in self.all_facts().items()}
        return EvaluationContext(subject_id=self.process_id, facts=facts)

    @property
    def content_sha256(self) -> str:
        payload = self.model_dump(mode="json", exclude={"process_id"})
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def effective_requirement(normative: bool | None, human_override: bool | None) -> dict[str, Any]:
    """§30 — exigência normativa, override humano e exigência efetiva, sem sobrescrita muda.

    O override do analista só vale declarado: a exigência normativa continua registrada
    ao lado dele e nunca é apagada.
    """
    effective = normative if human_override is None else human_override
    return {"normative_requirement": normative, "human_override": human_override,
            "effective_requirement": effective}
