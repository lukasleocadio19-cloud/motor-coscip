"""Tabelas das NTs em dois caminhos independentes (plano de correção, F2.2 e F2.3).

Cada tabela conferida é um arquivo ``normative/tabelas/<nt>/<tabela>.yaml`` com os caminhos de
leitura, cada um com as linhas lidas célula a célula:

- ``geometrica``: ``pdfplumber`` sobre o PDF oficial (células pelas linhas da tabela), gerado
  por ``python -m tools.normas.tabelas extrair`` (só onde há o PDF: CI/nuvem);
- ``visual``: leitura da imagem da página, célula a célula (sessão com leitura de imagem);
- ``texto``: a seção "Tabelas extraídas" do ``.md`` (camada de texto do PDF). Serve de segundo
  caminho **só** enquanto a geométrica não existir, e isso fica escrito no resultado.

``comparar`` decide o estado de cada célula — nunca em silêncio:

- iguais nos dois caminhos (depois de normalizar espaço, acento e erro de OCR com
  ``rapidfuzz``; **números têm de ser idênticos**) → ``verificada`` (com o score);
- diferentes → ``divergente``, com os dois valores;
- ilegível (``null``) ou só um caminho → ``pendente_humano``.

O estado da tabela é o pior das células. ``test_tabelas`` recalcula e compara: ninguém escreve
"verificada" à mão. ``publicar`` insere a tabela verificada no ``.md`` da NT, no fim da página,
entre marcadores (idempotente), e marca a seção antiga como bruta.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
TABELAS = ROOT / "normative" / "tabelas"
FONTES = ROOT / "normative" / "fontes"
SCHEMA = "tabela-conferida/1.0"
FUZZY_MIN = 90.0  # score mínimo (0-100) para texto com erro de OCR; números: identidade
ORDER = {"verificada": 0, "divergente": 2, "pendente_humano": 1}
RAW_HEADING = "### Tabelas extraídas"
RAW_MARKED = "### Tabelas extraídas (bruto, não usar para citação)"
_BEGIN = "<!-- tabela-conferida: {id} -->"
_END = "<!-- /tabela-conferida: {id} -->"


# ---------------------------------------------------------------- normalização e comparação

def norm(cell: str | None) -> str | None:
    """Forma de comparação: sem acento, minúscula, espaços únicos, OCR de acento solto."""
    if cell is None:
        return None
    text = unicodedata.normalize("NFKD", str(cell))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace(" ", " ").replace("–", "-").replace("—", "-").lower()
    text = re.sub(r"(?<=\w) (?=[a-z]\b)", "", text)  # "edificaco es" → "edificacoes"
    text = re.sub(r"(\d)\s*([m²%])", r"\1\2", text)  # "35,00 m" → "35,00m"
    return " ".join(text.split())


def _numbers(text: str) -> list[str]:
    return re.findall(r"\d+(?:[.,]\d+)*", text)


def compare_cell(a: str | None, b: str | None) -> dict[str, Any]:
    if a is None or b is None:
        return {"estado": "pendente_humano", "motivo": "ilegível ou ausente em um caminho"}
    na, nb = norm(a), norm(b)
    if na == nb:
        return {"estado": "verificada", "score": 100.0}
    if _numbers(na) != _numbers(nb):
        return {"estado": "divergente", "motivo": "números diferentes"}
    from rapidfuzz import fuzz

    score = round(float(fuzz.ratio(na, nb)), 1)
    if score >= FUZZY_MIN:
        return {"estado": "verificada", "score": score}
    return {"estado": "divergente", "score": score}


def compare(a_rows: list[list[str | None]], b_rows: list[list[str | None]]) -> dict[str, Any]:
    """Compara duas leituras célula a célula; forma diferente é divergência da tabela."""
    cells: list[dict[str, Any]] = []
    if len(a_rows) != len(b_rows) or any(len(x) != len(y) for x, y in zip(a_rows, b_rows,
                                                                        strict=False)):
        return {"estado": "divergente", "motivo": "número de linhas/colunas diferente",
                "forma": [[len(r) for r in a_rows], [len(r) for r in b_rows]], "celulas": []}
    for i, (ra, rb) in enumerate(zip(a_rows, b_rows, strict=True)):
        for j, (ca, cb) in enumerate(zip(ra, rb, strict=True)):
            res = compare_cell(ca, cb)
            if res["estado"] != "verificada" or res.get("score", 100.0) < 100.0:
                cells.append({"linha": i, "coluna": j, "a": ca, "b": cb, **res})
    worst = max((c["estado"] for c in cells), key=ORDER.__getitem__, default="verificada")
    return {"estado": worst, "celulas": cells}


def evaluate(table: dict[str, Any]) -> dict[str, Any]:
    """Resultado calculado a partir dos caminhos (``resultado`` do arquivo)."""
    paths = table.get("caminhos") or {}
    visual = paths.get("visual")
    second_name = "geometrica" if paths.get("geometrica") else (
        "texto" if paths.get("texto") else None)
    if not visual or second_name is None:
        have = sorted(k for k, v in paths.items() if v)
        return {"estado": "pendente_humano", "caminhos_comparados": have,
                "motivo": "é preciso a leitura visual e um segundo caminho independente"}
    res = compare(visual["linhas"], paths[second_name]["linhas"])
    out = {"estado": res["estado"], "caminhos_comparados": ["visual", second_name]}
    if second_name == "texto":
        out["observacao"] = ("segundo caminho = camada de texto do PDF (seção 'Tabelas "
                             "extraídas'); falta a extração geométrica do PDF oficial")
    for key in ("motivo", "forma"):
        if key in res:
            out[key] = res[key]
    if res["celulas"]:
        out["celulas"] = res["celulas"]
    return out


# ---------------------------------------------------------------- caminho "texto" (.md)

def raw_table(md_text: str, page: int, index: int = 1) -> list[list[str]]:
    """Linhas cruas da ``index``-ésima tabela (1-based) da seção "Tabelas extraídas" da página."""
    m = re.search(rf"^## Página {page}\s*$", md_text, re.M)
    if not m:
        raise ValueError(f"página {page} sem marcador")
    nxt = re.search(r"^## Página \d+\s*$", md_text[m.end():], re.M)
    section = md_text[m.end(): m.end() + nxt.start() if nxt else len(md_text)]
    section = section.split("<!-- tabela-conferida:")[0]  # o bloco publicado não é caminho
    raw = re.search(r"^### Tabelas extraídas.*$", section, re.M)
    if not raw:
        raise ValueError(f"página {page} sem 'Tabelas extraídas'")
    blocks = re.split(r"^#### ", section[raw.end():], flags=re.M)[1:]
    if index > len(blocks):
        raise ValueError(f"página {page}: só {len(blocks)} tabela(s) extraída(s)")
    rows = []
    for line in blocks[index - 1].splitlines():
        line = line.strip()
        if line.startswith("|") and not re.fullmatch(r"\|[\s|:-]+\|", line):
            rows.append([c.strip() for c in line.strip("|").split("|")])
    return rows


def texto_path(md_text: str, origem: dict[str, Any]) -> list[list[str]]:
    """Caminho "texto" calculado do ``.md`` (nunca digitado): junta as linhas de cabeçalho
    pela coluna original, descarta as linhas pedidas e remove as células vazias."""
    rows = raw_table(md_text, int(origem["pagina"]), int(origem.get("tabela_na_pagina", 1)))
    head_n = int(origem.get("linhas_cabecalho", 1))
    if origem.get("juntar_cabecalho", True):  # cabeçalho quebrado em linhas: junta por coluna
        head = [" ".join(filter(None, col)) for col in zip(*rows[:head_n], strict=False)]
        out = [[c for c in head if c]]
    else:  # cabeçalho com células mescladas: cada linha fica como está, sem as vazias
        out = [[c for c in r if c] for r in rows[:head_n]]
    skip = set(origem.get("descartar_linhas") or [])
    for i, row in enumerate(rows[head_n:], start=head_n):
        if i in skip:
            continue
        cells = [c for c in row if c]
        if cells:
            out.append(cells)
    return out


# ---------------------------------------------------------------- arquivos

def table_files() -> list[Path]:
    return sorted(TABELAS.glob("*/*.yaml"))


def load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dump(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


def refresh(path: Path) -> bool:
    """Recalcula o caminho "texto", ``resultado`` e ``estado``; ``True`` se o arquivo mudou."""
    data = load(path)
    texto = (data.get("caminhos") or {}).get("texto")
    if texto and texto.get("origem"):
        md = (FONTES / data["arquivo"]).read_text(encoding="utf-8")
        texto["linhas"] = texto_path(md, texto["origem"])
    res = evaluate(data)
    data["estado"] = res["estado"]
    data["resultado"] = res
    text = dump(data)
    if path.read_text(encoding="utf-8") != text:
        path.write_bytes(text.encode("utf-8"))
        return True
    return False


# ---------------------------------------------------------------- PDF (CI/nuvem)

def render_pages(pdf: bytes, pages: dict[int, Path], dpi: int = 150) -> list[Path]:
    """Renderiza as páginas pedidas (1-based) nos caminhos dados (PNG ou JPEG pela extensão)."""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(pdf)
    out = []
    for number, target in sorted(pages.items()):
        image = doc[number - 1].render(scale=dpi / 72).to_pil().convert("RGB")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix.lower() in (".jpg", ".jpeg"):
            image.save(target, "JPEG", quality=85, optimize=True, progressive=True)
        else:
            image.save(target, "PNG", optimize=True)
        out.append(target)
    return out


def extract_geometric(pdf: bytes, page: int) -> list[dict[str, Any]]:
    """Tabelas da página pelas linhas desenhadas (pdfplumber), com bbox de cada tabela."""
    import io

    import pdfplumber

    tables = []
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        p = doc.pages[page - 1]
        for t in p.find_tables({"vertical_strategy": "lines", "horizontal_strategy": "lines"}):
            rows = [[(" ".join(c.split()) if c is not None else None) for c in row]
                    for row in t.extract()]
            tables.append({"bbox": [round(v, 2) for v in t.bbox], "linhas": rows})
    return tables


# ---------------------------------------------------------------- publicação no .md

def to_markdown(table: dict[str, Any]) -> str:
    visual = table["caminhos"]["visual"]
    rows = visual["linhas"]
    n_head = int(visual.get("linhas_cabecalho", 1))
    header = visual.get("cabecalho_publicado") or rows[0]  # cabeçalho mesclado, achatado
    esc = [[(c or "").replace("|", "/") for c in r] for r in [header, *rows[n_head:]]]
    lines = [f"### {table['tabela']} — {table['titulo']} (conferida)", "",
             "| " + " | ".join(esc[0]) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(r) + " |" for r in esc[1:]]
    methods = " + ".join(table["resultado"]["caminhos_comparados"])
    lines += ["", f"Fonte: {table['documento']}, página {table['pagina']}, {table['tabela']}; "
                  f"conferida em {table['conferida_em']} ({methods})."]
    for note in table.get("notas") or []:
        lines.append(f"{note}")
    return "\n".join(lines)


def publish(table: dict[str, Any], md_text: str) -> str:
    """Insere (ou substitui) o bloco conferido no fim da página da tabela."""
    ident = f"{table['tabela']} p{table['pagina']}"
    begin, end = _BEGIN.format(id=ident), _END.format(id=ident)
    md_text = re.sub(re.escape(begin) + r".*?" + re.escape(end) + r"\n\n", "", md_text,
                     flags=re.S)
    if table.get("estado") != "verificada":
        return md_text
    marker = re.search(rf"^## Página {table['pagina']}\s*$", md_text, re.M)
    if not marker:
        raise ValueError(f"{table['documento']}: página {table['pagina']} sem marcador")
    nxt = re.search(r"^---\s*$", md_text[marker.end():], re.M)
    pos = marker.end() + nxt.start() if nxt else len(md_text)
    block = f"{begin}\n{to_markdown(table)}\n{end}\n\n"
    return md_text[:pos] + block + md_text[pos:]


def mark_raw(md_text: str) -> str:
    return re.sub(rf"^{re.escape(RAW_HEADING)}\s*$", RAW_MARKED, md_text, flags=re.M)


def publish_all() -> list[Path]:
    changed = []
    by_file: dict[Path, list[dict[str, Any]]] = {}
    for f in table_files():
        data = load(f)
        by_file.setdefault(FONTES / data["arquivo"], []).append(data)
    for md in sorted(FONTES.glob("*.md")):
        by_file.setdefault(md, [])
    for md, tables in sorted(by_file.items()):
        if md.name == "README.md":
            continue
        text = md.read_text(encoding="utf-8")
        new = mark_raw(text)
        for t in sorted(tables, key=lambda t: (t["pagina"], t["tabela"])):
            new = publish(t, new)
        if new != text:
            md.write_bytes(new.encode("utf-8"))
            changed.append(md)
    return changed


def report() -> str:
    rows = [load(f) for f in table_files()]
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["estado"]] = counts.get(r["estado"], 0) + 1
    lines = ["# Tabelas conferidas — relatório (gerado; não editar)", "",
             "Gerado por `python -m tools.normas.tabelas relatorio`. Estado de cada tabela "
             "conferida em dois caminhos independentes (plano de correção, F2.2). "
             "As demais tabelas da base seguem **brutas** (ver `normative/manifests/base.yaml`).",
             "", "| Estado | Tabelas |", "| --- | --- |"]
    lines += [f"| {k} | {v} |" for k, v in sorted(counts.items())]
    lines += ["", "Caminho `texto` = camada de texto do PDF (seção \"Tabelas extraídas\"): "
              "vale como segundo caminho só até a extração geométrica (`pdfplumber`, workflow "
              "`normas-midia.yml`) rodar sobre o PDF oficial conferido por hash."]
    lines += ["", "| Documento | Tabela | Pág. | Estado | Caminhos | Células a decidir | "
              "Inconsistências da fonte |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in sorted(rows, key=lambda r: (r["documento"], r["pagina"], r["tabela"])):
        res = r["resultado"]
        pend = len([c for c in res.get("celulas", []) if c["estado"] != "verificada"])
        lines.append(f"| {r['documento']} | {r['tabela']} | {r['pagina']} | {r['estado']} | "
                     f"{' + '.join(res['caminhos_comparados'])} | {pend} | "
                     f"{len(r.get('inconsistencias_da_fonte') or [])} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Tabelas conferidas (F2)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("comparar", help="recalcula o estado de todas as tabelas")
    sub.add_parser("publicar", help="insere as verificadas nos .md")
    sub.add_parser("relatorio", help="grava normative/tabelas/RELATORIO.md")
    ex = sub.add_parser("extrair", help="caminho geométrico a partir do PDF oficial")
    ex.add_argument("pdf", type=Path)
    ex.add_argument("--tabela", type=Path, required=True, help="arquivo .yaml da tabela")
    ex.add_argument("--indice", type=int, default=0, help="qual tabela da página")
    args = ap.parse_args(argv)
    if args.cmd == "comparar":
        for f in table_files():
            if refresh(f):
                print(f"atualizado: {f.relative_to(ROOT)}")
    elif args.cmd == "publicar":
        for md in publish_all():
            print(f"publicado: {md.relative_to(ROOT)}")
    elif args.cmd == "relatorio":
        (TABELAS / "RELATORIO.md").write_bytes(report().encode("utf-8"))
    elif args.cmd == "extrair":
        import hashlib

        import pdfplumber

        pdf = args.pdf.read_bytes()
        data = load(args.tabela)
        if hashlib.sha256(pdf).hexdigest() != data["fonte_pdf_sha256"]:
            raise SystemExit("SHA-256 do PDF não confere com o da base: recusado")
        found = extract_geometric(pdf, data["pagina"])
        if len(found) <= args.indice:
            raise SystemExit(f"página {data['pagina']}: {len(found)} tabela(s) geométricas")
        data["caminhos"]["geometrica"] = {
            "metodo": f"pdfplumber {pdfplumber.__version__}, estratégia por linhas",
            "bbox": found[args.indice]["bbox"], "linhas": found[args.indice]["linhas"]}
        args.tabela.write_bytes(dump(data).encode("utf-8"))
        refresh(args.tabela)
    return 0


if __name__ == "__main__":
    sys.exit(main())
