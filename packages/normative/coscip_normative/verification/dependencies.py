"""Ordem de execução e efeito de uma dependência sobre o check que depende dela (§20).

Regra de segurança: dependência inconclusiva **não libera** o dependente. Um check só
executa quando aquilo de que ele depende já foi respondido.
"""

from __future__ import annotations

from collections.abc import Iterable

from coscip_cbm import ComplianceStatus
from coscip_normative.verification.catalog import CatalogError, CheckCatalog


def execution_order(catalog: CheckCatalog, check_ids: Iterable[str]) -> tuple[str, ...]:
    """Ordem topológica estável: dependências antes dos dependentes.

    Só entram os checks pedidos; uma dependência fora do conjunto é tratada como não
    respondida pelo executor, nunca como satisfeita.
    """
    wanted = list(dict.fromkeys(check_ids))
    ordered: list[str] = []
    done: set[str] = set()
    visiting: set[str] = set()

    def visit(check_id: str) -> None:
        if check_id in done or check_id not in wanted:
            return
        if check_id in visiting:
            raise CatalogError(f"ciclo de dependência envolvendo {check_id}")
        visiting.add(check_id)
        for dep in catalog.get(check_id).depends_on:
            visit(dep)
        visiting.discard(check_id)
        done.add(check_id)
        ordered.append(check_id)

    for check_id in wanted:
        visit(check_id)
    return tuple(ordered)


def dependency_gate(depends_on: Iterable[str],
                    concluded: dict[str, ComplianceStatus]) -> tuple[str, str] | None:
    """Devolve ``(estado, motivo)`` quando a dependência impede executar; ``None`` libera.

    - dependência não aplicável → o dependente também não se aplica;
    - dependência inconclusiva ou não executada → o dependente fica inconclusivo.
    """
    for dep in depends_on:
        status = concluded.get(dep)
        if status is None:
            return ("UNDETERMINED", f"o check {dep} não foi executado nesta análise")
        if status is ComplianceStatus.NOT_APPLICABLE:
            return ("NOT_APPLICABLE", f"o check {dep} não se aplica a este processo")
        if status is ComplianceStatus.UNDETERMINED:
            return ("UNDETERMINED", f"o check {dep} ficou inconclusivo")
    return None
