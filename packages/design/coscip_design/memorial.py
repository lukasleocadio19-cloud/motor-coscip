"""Memorial de cálculo: passos com fórmula, valores, resultado e a base normativa de cada um."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from coscip_design.params import Param

AVISO = ("RASCUNHO sem valor normativo: parâmetros não homologados e sem responsável técnico. "
         "O projeto precisa de profissional habilitado (ART/RRT) e da conferência das normas.")


@dataclass
class Passo:
    titulo: str
    formula: str = ""
    valores: dict[str, Any] = field(default_factory=dict)
    resultado: Any = None
    unidade: str = ""
    base: list[str] = field(default_factory=list)  # citações conferidas
    nota: str = ""

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"passo": self.titulo}
        if self.formula:
            out["formula"] = self.formula
        if self.valores:
            out["valores"] = self.valores
        out["resultado"] = self.resultado
        if self.unidade:
            out["unidade"] = self.unidade
        if self.base:
            out["base_normativa"] = self.base
        if self.nota:
            out["nota"] = self.nota
        return out


@dataclass
class Memorial:
    sistema: str
    titulo: str
    entradas: dict[str, Any] = field(default_factory=dict)
    passos: list[Passo] = field(default_factory=list)
    resultados: dict[str, Any] = field(default_factory=dict)
    premissas: list[str] = field(default_factory=list)  # o que a norma não fixa
    pendencias: list[str] = field(default_factory=list)  # o que falta decidir ou conferir
    verificar_na_planta: list[str] = field(default_factory=list)
    citacoes: dict[str, str] = field(default_factory=dict)

    def usa(self, p: Param) -> Any:
        """Registra a citação do parâmetro e devolve o valor."""
        seen = self.citacoes.get(p.citacao)
        if seen is None:
            self.citacoes[p.citacao] = p.titulo
        elif p.titulo not in seen:
            self.citacoes[p.citacao] = f"{seen}; {p.titulo}"
        return p.valor

    def passo(self, titulo: str, resultado: Any, *, formula: str = "", unidade: str = "",
              base: list[Param] | None = None, nota: str = "", **valores: Any) -> Any:
        for p in base or []:
            self.usa(p)
        self.passos.append(Passo(titulo, formula, valores, resultado, unidade,
                                 [p.citacao for p in base or []], nota))
        return resultado

    def as_dict(self) -> dict[str, Any]:
        return {"aviso": AVISO, "sistema": self.sistema, "titulo": self.titulo,
                "entradas": self.entradas, "resultados": self.resultados,
                "memorial": [p.as_dict() for p in self.passos],
                "premissas_do_projetista": self.premissas, "pendencias": self.pendencias,
                "verificar_na_planta": self.verificar_na_planta,
                "base_normativa": [f"{c} — {t}" for c, t in self.citacoes.items()]}

    def markdown(self) -> str:
        lines = [f"## {self.titulo}", ""]
        if self.entradas:
            lines += ["**Dados de entrada**", ""]
            lines += [f"- {k}: {_fmt(v)}" for k, v in self.entradas.items()] + [""]
        lines += ["**Memorial**", ""]
        for n, p in enumerate(self.passos, start=1):
            head = f"{n}. **{p.titulo}**"
            if p.resultado is not None:
                head += f": {_fmt(p.resultado)}" + (f" {p.unidade}" if p.unidade else "")
            lines.append(head)
            if p.formula:
                lines.append(f"   - Fórmula: `{p.formula}`")
            if p.valores:
                lines.append("   - Valores: " + "; ".join(f"{k} = {_fmt(v)}"
                                                         for k, v in p.valores.items()))
            if p.base:
                lines.append("   - Base: " + "; ".join(p.base))
            if p.nota:
                lines.append(f"   - Nota: {p.nota}")
        lines.append("")
        if self.resultados:
            lines += ["**Resultados**", ""]
            lines += [f"- {k}: {_fmt(v)}" for k, v in self.resultados.items()] + [""]
        for title, items in (("Premissas do projetista (a norma não fixa)", self.premissas),
                             ("Pendências", self.pendencias),
                             ("Verificar na planta", self.verificar_na_planta)):
            if items:
                lines += [f"**{title}**", ""] + [f"- {i}" for i in items] + [""]
        if self.citacoes:
            lines += ["**Base normativa conferida no texto**", ""]
            lines += [f"- {c} — {t}" for c, t in self.citacoes.items()] + [""]
        return "\n".join(lines)


def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.3f}".rstrip("0").rstrip(".").replace(".", ",")
    if isinstance(v, dict):
        return "; ".join(f"{k}: {_fmt(x)}" for k, x in v.items())
    if isinstance(v, (list, tuple)):
        return ", ".join(_fmt(x) for x in v)
    return str(v)
