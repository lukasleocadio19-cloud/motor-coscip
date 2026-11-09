"""Gera ``skills/projetar-pscip-cbmerj/references/medidas.md`` a partir de ``medidas.yaml``.

Uso (no .venv):  python scripts/projeto/gerar_referencia_medidas.py
O teste ``tests/unit/test_skill_projeto.py`` acusa quando o arquivo gerado fica desatualizado.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
ORIGEM = ROOT / "normative" / "projeto" / "medidas.yaml"
DESTINO = ROOT / "skills" / "projetar-pscip-cbmerj" / "references" / "medidas.md"

SITUACAO = {
    "CALCULA": "o motor dimensiona e gera memorial",
    "REQUISITOS": "o motor devolve só o que a NT fixa",
    "LER_NT": "sem cálculo: ler a NT e registrar as exigências",
}


def render() -> str:
    rows = yaml.safe_load(ORIGEM.read_text(encoding="utf-8"))["medidas"]
    out = [
        "# Medidas de segurança: como tratar cada uma",
        "",
        "Gerado de `normative/projeto/medidas.yaml` (não editar à mão). É o mesmo roteiro que",
        "`enquadrar_edificacao` devolve em `como_tratar`. A medida da tabela casa pelo início do",
        "nome.",
        "",
    ]
    for r in rows:
        out += [f"## {r['rotulo']}", "",
                f"- **Situação:** {r['situacao']} — {SITUACAO[r['situacao']]}"]
        if r.get("ferramenta"):
            out.append(f"- **Ferramenta:** `{r['ferramenta']}`")
        if r.get("nt"):
            out.append("- **Ler:** " + ", ".join(f"`consultar_norma(\"{n}\")`" for n in r["nt"]))
        if r.get("simbolos"):
            out.append("- **Símbolos:** " + ", ".join(f"`{s}`" for s in r["simbolos"]))
        out.append(f"- **Entrega:** {r['entrega']}")
        if r.get("falta"):
            out.append(f"- **O motor não cobre:** {r['falta']}")
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(render(), encoding="utf-8", newline="\n")
    print(DESTINO)
