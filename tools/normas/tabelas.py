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

# Fonte Symbol do PDF extraída como área de uso privado (U+F0xx = código Symbol xx).
_SYMBOL_GREEK = "αβχδεφγηιϕκλμνοπθρστυϖωξψζ"  # códigos Symbol 0x61 a 0x7A
_SYMBOL_PUA = str.maketrans({0xF03C: "<", 0xF03E: ">", 0xF03D: "=", 0xF0A3: "≤", 0xF0B3: "≥",
                             0xF0B1: "±", 0xF0B4: "×", 0xF0B0: "°", 0xF02D: "-",
                             **{0xF061 + i: ch for i, ch in enumerate(_SYMBOL_GREEK)}})


def norm(cell: str | None) -> str | None:
    """Forma de comparação: sem acento, minúscula, espaços únicos, OCR de acento solto."""
    if cell is None:
        return None
    text = unicodedata.normalize("NFKD", str(cell).translate(_SYMBOL_PUA))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace(" ", " ").replace("–", "-").replace("—", "-").lower()
    text = re.sub(r"(?<=\w) (?=[a-z]\b)", "", text)  # "edificaco es" → "edificacoes"
    text = re.sub(r"(\d)\s*([m²%])", r"\1\2", text)  # "35,00 m" → "35,00m"
    text = re.sub(r"\s*:\s*", ":", text)  # "2-A : 10-B" → "2-a:10-b"
    text = re.sub(r"\s*,\s*", ",", text)  # "X 5 ,6" → "x 5,6"
    text = re.sub(r"\bx\s+(?=\d)", "x", text)  # nota colada ao X: "X 5,6" → "x5,6"
    text = re.sub(r"\bm2\b", "m²", text)  # sobrescrito achatado pela conversão: "MJ/m2"
    text = re.sub(r"(?<=[a-z]) (?=\d)", "", text)  # nota sobrescrita: "NE 1" = "NE1"
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


FORMA_KEYS = ("faixa", "mesclar_linhas", "rotulos_quebrados", "linhas_cabecalho",
              "juntar_cabecalho", "descartar_linhas")


def forma_of(table: dict[str, Any], path: dict[str, Any] | None = None) -> dict[str, Any]:
    """Forma comum aos caminhos brutos (cabeçalho, linhas descartadas). O caminho pode ter a
    sua própria (``forma``), quando a estrutura bruta dele for outra."""
    base = dict(table.get("forma") or {})
    origem = ((table.get("caminhos") or {}).get("texto") or {}).get("origem") or {}
    for k in FORMA_KEYS:  # formato antigo: forma dentro de texto.origem
        if k in origem and k not in base:
            base[k] = origem[k]
    if path and path.get("forma"):
        base.update(path["forma"])
    return base


MERGED_UP = "^"  # na leitura visual: célula mesclada com a de cima (o valor está lá)
MERGED_LEFT = "<"  # na leitura visual: célula mesclada com a da esquerda


def compact(rows: list[list[str | None]]) -> list[list[str | None]]:
    """Leitura visual na forma dos caminhos brutos: a célula mesclada aparece uma vez só (na
    primeira linha da mescla), então as marcadas ``^`` saem antes de comparar; célula em
    branco na imagem (``""``, ex. fundo cinza = não se aplica) também, como nos brutos.
    ``None`` (ilegível) fica: vira pendência."""
    return [[c for c in r if c not in (MERGED_UP, MERGED_LEFT, "")] for r in rows]


def evaluate(table: dict[str, Any]) -> dict[str, Any]:
    """Resultado calculado a partir dos caminhos (``resultado`` do arquivo).

    Segundo caminho: a extração geométrica, quando existe (entre as tabelas candidatas da
    página vale a que mais concorda com a leitura visual — a escolha fica registrada); senão
    a camada de texto, com observação."""
    paths = table.get("caminhos") or {}
    visual = paths.get("visual")
    geo = paths.get("geometrica")
    texto = paths.get("texto")
    if not visual or not (geo or texto):
        have = sorted(k for k, v in paths.items() if v)
        return {"estado": "pendente_humano", "caminhos_comparados": have,
                "motivo": "é preciso a leitura visual e um segundo caminho independente"}
    if geo:
        forma = forma_of(table, geo)
        tries = []
        for i, c in enumerate(geo["candidatos"]):
            try:
                shaped = shape(c["linhas"], forma)
            except IndexError:  # a forma não cabe nesta candidata: outra tabela da página
                continue
            tries.append((compare(compact(visual["linhas"]), shaped), i))
        if not tries:
            return {"estado": "pendente_humano", "caminhos_comparados": ["visual"],
                    "motivo": "nenhuma tabela geométrica encontrada na página"}
        res, idx = min(tries, key=lambda t: (ORDER[t[0]["estado"]],
                                             len([c for c in t[0]["celulas"]
                                                  if c["estado"] != "verificada"]), t[1]))
        out = {"estado": res["estado"], "caminhos_comparados": ["visual", "geometrica"],
               "candidato_geometrico": idx, "candidatos_na_pagina": len(tries),
               "bbox": geo["candidatos"][idx].get("bbox")}
        if texto:
            out["texto"] = compare(compact(visual["linhas"]), texto["linhas"])["estado"]
    else:
        res = compare(compact(visual["linhas"]), texto["linhas"])
        out = {"estado": res["estado"], "caminhos_comparados": ["visual", "texto"],
               "observacao": ("segundo caminho = camada de texto do PDF (seção 'Tabelas "
                              "extraídas'); falta a extração geométrica do PDF oficial")}
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


def shape(rows: list[list[str | None]], forma: dict[str, Any]) -> list[list[str]]:
    """Normaliza um caminho bruto (texto ou geométrico) para a forma da leitura visual:
    junta as linhas de cabeçalho pela coluna original (ou as mantém, se mescladas), descarta
    as linhas pedidas (observações) e remove as células vazias (``None`` = célula mesclada)."""
    rows = [[(c or "").strip() for c in r] for r in rows]
    if forma.get("faixa"):  # só as linhas [início, fim) da extração (título/texto em volta fora)
        ini, fim = forma["faixa"]
        rows = rows[ini:fim]
    for i, j in sorted(forma.get("mesclar_linhas") or [], reverse=True):
        # célula com texto em duas linhas ("Médio" / "1 e 2"): junta pela coluna
        rows[i] = [" ".join(filter(None, (a, b))) for a, b in zip(rows[i], rows[j], strict=False)]
        del rows[j]
    if forma.get("rotulos_quebrados"):
        rows = _join_split_labels(rows)
    head_n = int(forma.get("linhas_cabecalho", 1))
    if head_n == 0:
        out: list[list[str]] = []
    elif forma.get("juntar_cabecalho", True):  # cabeçalho quebrado em linhas: junta por coluna
        head = [" ".join(filter(None, col)) for col in zip(*rows[:head_n], strict=False)]
        out = [[c for c in head if c]]
    else:  # cabeçalho com células mescladas: cada linha fica como está, sem as vazias
        out = [[c for c in r if c] for r in rows[:head_n]]
    out = [r for r in out if r]
    skip = set(forma.get("descartar_linhas") or [])
    for i, row in enumerate(rows[head_n:], start=head_n):
        if i in skip:
            continue
        cells = [c for c in row if c]
        if cells:
            out.append(cells)
    return out


_VALUE = re.compile(r"^(X.*|-+|—)$")


def _join_split_labels(rows: list[list[str]]) -> list[list[str]]:
    """Rótulo quebrado pela extração em três linhas — "Acesso de viatura em" / valores /
    "edificações" — volta a ser uma linha: rótulo inteiro + valores."""
    out: list[list[str]] = []
    i = 0
    while i < len(rows):
        cells = [c for c in rows[i] if c]
        nxt = [c for c in rows[i + 1] if c] if i + 1 < len(rows) else []
        after = [c for c in rows[i + 2] if c] if i + 2 < len(rows) else []
        if (len(cells) == 1 and not _VALUE.match(cells[0]) and nxt
                and all(_VALUE.match(c) for c in nxt) and len(after) == 1
                and not _VALUE.match(after[0])):
            out.append([f"{cells[0]} {after[0]}", *nxt])
            i += 3
            continue
        out.append(rows[i])
        i += 1
    return out


def texto_path(md_text: str, origem: dict[str, Any],
               forma: dict[str, Any] | None = None) -> list[list[str]]:
    """Caminho "texto" calculado do ``.md`` (nunca digitado)."""
    rows = raw_table(md_text, int(origem["pagina"]), int(origem.get("tabela_na_pagina", 1)))
    return shape(rows, forma if forma is not None else origem)


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
        texto["linhas"] = texto_path(md, texto["origem"], forma_of(data, texto))
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


def geometric_path(pdf: bytes, page: int) -> dict[str, Any]:
    """Todas as tabelas geométricas da página (a escolha é feita em ``evaluate``)."""
    import pdfplumber

    return {"metodo": f"pdfplumber {pdfplumber.__version__}, estratégia por linhas",
            "todas_da_pagina": True, "candidatos": extract_geometric(pdf, page)}


# ---------------------------------------------------------------- publicação no .md

def to_markdown(table: dict[str, Any]) -> str:
    visual = table["caminhos"]["visual"]
    rows = visual["linhas"]
    n_head = int(visual.get("linhas_cabecalho", 1))
    header = visual.get("cabecalho_publicado") or rows[0]  # cabeçalho mesclado, achatado
    body, prev = [], list(header)
    for r in rows[n_head:]:
        if MERGED_UP in r or MERGED_LEFT in r:  # grade completa: "^" de cima, "<" da esquerda
            if len(r) != len(header):
                raise ValueError(f"{table['tabela']}: linha com '^'/'<' precisa de todas as "
                                 "colunas")
            full = []
            for j, c in enumerate(r):
                full.append(prev[j] if c == MERGED_UP else full[-1] if c == MERGED_LEFT else c)
        else:  # linha mais curta = células mescladas à esquerda: herda de cima
            full = prev[: len(header) - len(r)] + list(r)
        body.append(full)
        prev = full
    esc = [[(c or "").replace("|", "/") for c in r] for r in [header, *body]]
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


SOLICITADAS = TABELAS / "imagens-solicitadas.yaml"


def ensure_images(md_text: str, slug: str, pages: list[int]) -> str:
    """Garante a referência à imagem de cada página pedida, logo após o marcador."""
    ext = ".jpg"
    for page in sorted(pages):
        rel = f"media/{slug}/pagina-{page:02d}{ext}"
        if f"]({rel})" in md_text or re.search(rf"\]\(media/{re.escape(slug)}/pagina-{page:02d}"
                                               r"\.(png|jpg)\)", md_text):
            continue
        m = re.search(rf"^## Página {page}[ \t]*$", md_text, re.M)
        if not m:
            raise ValueError(f"{slug}: página {page} sem marcador")
        md_text = (md_text[:m.end()] + f"\n\n![Representação visual da página {page}]({rel})"
                   + md_text[m.end():])
    return md_text


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
    wanted = (yaml.safe_load(SOLICITADAS.read_text(encoding="utf-8")) or {}).get("paginas", {}) \
        if SOLICITADAS.exists() else {}
    for md, tables in sorted(by_file.items()):
        if md.name == "README.md":
            continue
        text = md.read_text(encoding="utf-8")
        new = mark_raw(text)
        if md.name in wanted:
            from tools.normas.manifesto import media_refs, media_slug

            slug = media_slug(media_refs(new), md.name)
            new = ensure_images(new, slug, wanted[md.name])
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


        pdf = args.pdf.read_bytes()
        data = load(args.tabela)
        if hashlib.sha256(pdf).hexdigest() != data["fonte_pdf_sha256"]:
            raise SystemExit("SHA-256 do PDF não confere com o da base: recusado")
        data["caminhos"]["geometrica"] = geometric_path(pdf, data["pagina"])
        args.tabela.write_bytes(dump(data).encode("utf-8"))
        refresh(args.tabela)
    return 0


if __name__ == "__main__":
    sys.exit(main())
