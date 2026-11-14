"""Parâmetros de dimensionamento (``normative/projeto/parametros.yaml``) com citação conferida."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from coscip_normative import NormativeText
from coscip_normative.sources import verify_citation, verify_page_citation, verify_table_row

SCHEMA = "design-params/1.0"
DEFAULT_PATH = Path(__file__).resolve().parents[3] / "normative" / "projeto" / "parametros.yaml"


class ParamError(ValueError):
    """Parâmetro ausente ou cuja citação não confere: o cálculo não pode usá-lo."""


@dataclass(frozen=True)
class Param:
    id: str
    titulo: str
    valor: Any
    unidade: str | None
    documento: str
    item: str
    verificado: bool
    pagina: int | None
    problema: str | None
    imagem: str | None = None

    @property
    def citacao(self) -> str:
        page = f", p. {self.pagina}" if self.pagina else ""
        return f"{self.documento}, {self.item}{page}"


def _check(sources: dict[str, NormativeText], fonte: dict[str, Any]):  # noqa: ANN202
    doc, item = fonte["document"], str(fonte.get("texto_em") or fonte["item"])
    if fonte.get("pagina"):  # item que o índice não alcança: conferência pela página
        return verify_page_citation(sources, doc, str(fonte["item"]), int(fonte["pagina"]),
                                    tuple(fonte.get("quote") or ()))
    if fonte.get("linha"):
        return verify_table_row(sources, doc, item, tuple(str(c) for c in fonte["linha"]))
    return verify_citation(sources, doc, item, tuple(fonte.get("quote") or ()))


@dataclass
class Parametros:
    params: dict[str, Param]
    populacao: list[dict[str, Any]]  # linhas do Anexo A da NT 2-08, cada uma com "verificado"
    populacao_fonte: str

    def get(self, pid: str) -> Param:
        """Parâmetro conferido; levanta ``ParamError`` se faltar ou a citação não conferir."""
        p = self.params.get(pid)
        if p is None:
            raise ParamError(f"parâmetro {pid!r} não existe em parametros.yaml")
        if not p.verificado:
            raise ParamError(
                f"{p.titulo} ({p.citacao}): citação não conferida no texto da norma "
                f"({p.problema}). O cálculo não usa valor sem conferência.")
        return p

    def populacao_de(self, divisao: str) -> dict[str, Any]:
        div = divisao.strip().upper()
        for row in self.populacao:
            if div in row.get("divisoes", ()) or row.get("grupo") == div.split("-")[0]:
                if not row["verificado"]:
                    raise ParamError(f"NT 2-08, Anexo A, linha de {div}: não conferida no texto "
                                     f"({row['problema']})")
                return row
        raise ParamError(f"divisão {div!r} sem linha no Anexo A da NT 2-08 (ex.: M-1 e outras "
                         "marcadas '+' pedem norma específica)")

    def resumo(self) -> dict[str, Any]:
        bad = {p.id: p.problema for p in self.params.values() if not p.verificado}
        bad_rows = [r["linha"][0] for r in self.populacao if not r["verificado"]]
        return {"parametros": len(self.params), "conferidos": len(self.params) - len(bad),
                "nao_conferidos": bad, "linhas_de_populacao": len(self.populacao),
                "linhas_de_populacao_nao_conferidas": bad_rows}


def load_params(sources: dict[str, NormativeText], path: Path | None = None) -> Parametros:
    data = yaml.safe_load((path or DEFAULT_PATH).read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA:
        raise ParamError(f"esquema esperado {SCHEMA}")
    params: dict[str, Param] = {}
    for pid, spec in (data.get("parametros") or {}).items():
        chk = _check(sources, spec["fonte"])
        problem = chk.problem
        if problem and chk.missing_terms:
            problem = f"{problem}: {list(chk.missing_terms)}"
        params[pid] = Param(pid, spec["titulo"], spec["valor"], spec.get("unidade"),
                            chk.document, str(spec["fonte"]["item"]), chk.verified, chk.page,
                            problem, spec.get("imagem"))
    pop = data.get("populacao") or {}
    fonte = pop.get("fonte") or {}
    rows = []
    for row in pop.get("linhas") or []:
        chk = _check(sources, {**fonte, "linha": row["linha"]})
        rows.append({**row, "verificado": chk.verified, "problema": chk.problem,
                     "pagina": chk.page})
    return Parametros(params, rows, f"{fonte.get('document')}, {fonte.get('item')}")
