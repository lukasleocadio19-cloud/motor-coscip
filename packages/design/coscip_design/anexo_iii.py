"""Decreto 42/2018, Anexo III, Tabelas 5 a 32: exigências por divisão, nº de pavimentos e altura.

As Tabelas 2, 3 e 4 foram transcritas à mão e conferidas no PDF (``sistemas-exigidos.yaml``).
As demais são **lidas direto do texto ingerido do Decreto** a cada carga: não há transcrição
para divergir da fonte. Em troca, cada tabela passa por conferência ESTRUTURAL antes de valer:

- toda linha de medida tem uma célula por coluna e só células ``-`` ou ``X`` com números de
  observação;
- toda observação citada numa célula existe nas "Observações específicas" da tabela;
- as divisões do título batem com as da linha "Divisão";
- nas tabelas padrão, os seis cabeçalhos de classe (Térrea … H > 30m) conferem.

Tabela com problema estrutural não é usada. Isso NÃO substitui a conferência visual no PDF
(célula trocada de coluna na extração passaria): a consulta sai marcada como "extraída do
texto, sem conferência visual" até alguém conferir e registrar em ``anexo-iii.yaml``.

Regras que continuam valendo: traço não é dispensa global; ausência de tabela não vira "nada
exigido"; nada tem valor normativo.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from coscip_normative import NormativeText, fold

DOCUMENT = "Decreto 42/2018"
_PROJETO = Path(__file__).resolve().parents[3] / "normative" / "projeto"
REGISTRO = _PROJETO / "anexo-iii.yaml"
MEDIDAS = _PROJETO / "medidas.yaml"
PRIMEIRA, ULTIMA = 5, 32
CLASSES = ("Térrea", "2pav", "3pav", "4, 5 e 6pav", "Acima de 6pav com H ≤ 30m", "H > 30m")
_CLASSES_FOLD = tuple(re.sub(r"\s+", "", fold(c)) for c in CLASSES)
_START = re.compile(r"^\| Tabela (\d+)\s*- Exig", re.M)
_CELL = re.compile(r"^(-|X\s*(\d+(\s*,\s*\d+)*)?)$")
_DIV = re.compile(r"\b([A-M])\s*-\s*(\d{1,2})\b")
_LABEL_REF = re.compile(r"^(.*?[^\d\s])\s*(\d{1,2})$")
_PAGE = re.compile(r"^## Página (\d+)\s*$", re.M)


@dataclass
class Coluna:
    indice: int  # posição na linha da tabela (1 = primeira coluna de células)
    divisoes: tuple[str, ...]
    rotulo: str
    classe: int | None = None  # 0..5 nas tabelas padrão (Térrea … H > 30m)
    observacoes: tuple[int, ...] = ()  # observação presa ao cabeçalho da coluna


@dataclass
class Medida:
    rotulo: str
    celulas: list[str]
    observacoes_da_linha: tuple[int, ...] = ()


@dataclass
class Tabela:
    numero: int
    titulo: str
    pagina: int | None
    colunas: list[Coluna] = field(default_factory=list)
    medidas: list[Medida] = field(default_factory=list)
    observacoes: dict[int, str] = field(default_factory=dict)
    gerais: list[str] = field(default_factory=list)
    padrao: bool = False  # colunas = classes por nº de pavimentos e altura
    qualquer_area: bool = False
    problemas: list[str] = field(default_factory=list)
    conferencia_visual: str | None = None

    @property
    def divisoes(self) -> set[str]:
        return {d for c in self.colunas for d in c.divisoes}

    @property
    def valida(self) -> bool:
        return not self.problemas

    def digest(self) -> str:
        """Resumo do que foi lido (divisões por coluna, medidas, células, observações).

        A conferência visual registrada só vale enquanto a leitura der este mesmo resumo: se o
        texto ou o leitor mudarem, a tabela volta a "sem conferência visual".
        """
        body = {"colunas": [list(c.divisoes) for c in self.colunas],
                "medidas": [[m.rotulo, m.celulas, list(m.observacoes_da_linha)]
                            for m in self.medidas],
                "observacoes": {str(k): v for k, v in sorted(self.observacoes.items())}}
        raw = json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def citacao(self) -> str:
        page = f", p. {self.pagina}" if self.pagina else ""
        return f"{DOCUMENT}, Anexo III, Tabela {self.numero}{page}"


def _divs(text: str) -> list[str]:
    return [f"{g}-{int(n)}" for g, n in _DIV.findall(text)]


def _split(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_cells(cells: list[str]) -> bool:
    return any(cells) and all(_CELL.match(c) for c in cells)


def parse_tables(src: NormativeText) -> dict[int, Tabela]:
    """Lê as Tabelas 5 a 32 do texto ingerido do Decreto."""
    text = src.text
    starts = [(m.start(), int(m.group(1))) for m in _START.finditer(text)]
    # A Tabela 28 vem colada ao fim da 27 na extração (título sem espaço antes do hífen).
    limit = text.find("Tabela 33", starts[-1][0]) if starts else -1
    out: dict[int, Tabela] = {}
    for i, (pos, num) in enumerate(starts):
        if not PRIMEIRA <= num <= ULTIMA:
            continue
        end = starts[i + 1][0] if i + 1 < len(starts) else (limit if limit > 0 else len(text))
        rows = [_split(ln) for ln in text[pos:end].splitlines() if ln.startswith("|")]
        rows = [r for r in rows if any(r) and not set(r) <= {"---", ""}]
        pages = _PAGE.findall(text, 0, pos)
        out[num] = _parse_table(num, rows, int(pages[-1]) if pages else None)
    return out


def _parse_table(num: int, rows: list[list[str]], page: int | None) -> Tabela:
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    first_data = next((i for i, r in enumerate(rows) if r[0] and _is_cells(r[1:])), None)
    note_at = next((i for i, r in enumerate(rows) if fold(r[0]).startswith("observacoes")),
                   len(rows))
    t = Tabela(num, "", page)
    if first_data is None or first_data > note_at:
        t.problemas.append("nenhuma linha de medida reconhecida")
        return t
    head = rows[:first_data]
    group_at = next((i for i, r in enumerate(head) if fold(r[0]).startswith("grupo de ocupacao")),
                    None)
    if group_at is None:
        t.problemas.append("linha 'Grupo de ocupação e uso' não encontrada")
        return t
    t.titulo = " ".join(r[0] for r in head[:group_at] if r[0])
    t.qualquer_area = "qualquer" in fold(t.titulo) or "areas de risco" in fold(t.titulo)

    # --- colunas: divisões e rótulos -----------------------------------------------------------
    region = head[group_at + 1:]
    class_at = next((i for i, r in enumerate(region)
                     if any("classificacao quanto" in fold(c) for c in r)), None)
    div_rows = region[:class_at] if class_at is not None else region
    by_col: dict[int, list[str]] = {}
    for r in div_rows:
        for c in range(1, width):
            for d in _divs(r[c]):
                if d not in by_col.setdefault(c, []):
                    by_col[c].append(d)
    if not by_col:
        t.problemas.append("divisões não encontradas no cabeçalho")
        return t
    group_starts = sorted(by_col)
    label_rows = region[class_at:] if class_at is not None else region
    label_rows = [r for r in label_rows
                  if not any("classificacao" in fold(c) or "(em metros)" in c for c in r)]
    for c in range(1, width):
        start = max(g for g in group_starts if g <= c) if c >= group_starts[0] else group_starts[0]
        label = " ".join(r[c] for r in label_rows if r[c])
        t.colunas.append(Coluna(c, tuple(by_col[start]), re.sub(r"\s+", " ", label).strip()))
    per_group = [[col for col in t.colunas if col.divisoes == tuple(by_col[g])]
                 for g in group_starts]
    if class_at is not None:
        t.padrao = True
        for cols in per_group:
            got = tuple(re.sub(r"\s+", "", fold(col.rotulo)) for col in cols)
            if got != _CLASSES_FOLD:
                t.problemas.append(f"cabeçalho das classes não confere: {[c.rotulo for c in cols]}")
            for k, col in enumerate(cols[:6]):
                col.classe, col.rotulo = k, CLASSES[k]
    titled = set(_divs(t.titulo))
    if titled and titled != t.divisoes:
        t.problemas.append(f"divisões do título {sorted(titled)} ≠ da linha Divisão "
                           f"{sorted(t.divisoes)}")

    # --- medidas (rótulo pode vir quebrado em linhas acima e abaixo das células) --------------
    body = rows[first_data:note_at]
    i = 0
    while i < len(body):
        r = body[i]
        label, cells = r[0], r[1:]
        if label and _is_cells(cells):
            i += 1
        elif (label and not any(cells) and i + 2 < len(body) + 1 and i + 1 < len(body)
              and not body[i + 1][0] and _is_cells(body[i + 1][1:])):
            tail = body[i + 2][0] if i + 2 < len(body) and not any(body[i + 2][1:]) else ""
            label, cells = f"{label} {tail}".strip(), body[i + 1][1:]
            i += 3 if tail else 2
        else:
            t.problemas.append(f"linha não reconhecida no corpo da tabela: {r[:3]}")
            i += 1
            continue
        refs: tuple[int, ...] = ()
        if m := _LABEL_REF.match(label):
            label, refs = m.group(1).strip(), (int(m.group(2)),)
        if len(cells) != len(t.colunas) or not all(cells):
            t.problemas.append(f"'{label}': {sum(1 for c in cells if c)} células para "
                               f"{len(t.colunas)} colunas")
        t.medidas.append(Medida(label, cells, refs))

    # --- observações -------------------------------------------------------------------------
    notes = " ".join(r[0] for r in rows[note_at:] if r[0])
    notes = re.sub(r"\s+", " ", notes)
    spec, _, general = notes.partition("OBSERVAÇÕES GERAIS:")
    spec = spec.replace("OBSERVAÇÕES ESPECÍFICAS:", "").strip()
    t.observacoes = _numbered(spec)
    t.gerais = [g.strip() for g in re.split(r"(?:^|\s)(?=[a-z]\)\s)", general.strip()) if g.strip()]
    used = {n for m in t.medidas for c in m.celulas for n in map(int, re.findall(r"\d+", c))}
    used |= {n for m in t.medidas for n in m.observacoes_da_linha}
    missing = sorted(used - set(t.observacoes))
    if missing:
        t.problemas.append(f"observações citadas e não encontradas: {missing}")
    if not t.medidas:
        t.problemas.append("tabela sem medidas")
    return t


def _numbered(text: str) -> dict[int, str]:
    """Separa "1- … 2- …" em ordem crescente (evita casar "F-4" ou "A-2" no meio do texto)."""
    out: dict[int, str] = {}
    marks: list[tuple[int, int, int]] = []
    pos, n = 0, 1
    while True:
        m = re.compile(rf"(?:^|\s){n}\s*-\s").search(text, pos)
        if not m:
            break
        marks.append((n, m.start(), m.end()))
        pos, n = m.end(), n + 1
    for k, (num, _start, end) in enumerate(marks):
        stop = marks[k + 1][1] if k + 1 < len(marks) else len(text)
        out[num] = text[end:stop].strip()
    return out


def load(sources: dict[str, NormativeText], registro: Path | None = None) -> dict[int, Tabela]:
    """Tabelas 5 a 32 lidas do Decreto, com o registro de conferência visual aplicado."""
    src = sources.get(DOCUMENT)
    if src is None:
        return {}
    tables = parse_tables(src)
    path = registro or REGISTRO
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        same_pdf = data.get("pdf_sha256") == src.pdf_sha256
        for num, entry in (data.get("conferidas") or {}).items():
            t = tables.get(int(num))
            if t is None or not same_pdf or entry.get("digest") != t.digest():
                continue
            t.conferencia_visual = str(entry.get("nota") or "conferida")
            # Cabeçalhos mesclados que a leitura do texto não reconstrói (só com a conferência).
            for col, fix in zip(t.colunas, entry.get("colunas") or [], strict=False):
                col.rotulo = fix["rotulo"]
                col.observacoes = tuple(fix.get("observacoes") or ())
    return tables


def classe_de(floors: int, height_m: float | None) -> tuple[int | None, str]:
    """Coluna das tabelas padrão pelo nº de pavimentos e pela altura; ``None`` se faltar dado."""
    if height_m is not None and height_m > 30:
        return 5, f"altura de {height_m:g} m acima de 30 m"
    if floors == 1:
        return 0, "edificação térrea"
    if floors in (2, 3):
        return floors - 1, f"{floors} pavimentos"
    if floors <= 6:
        return 3, f"{floors} pavimentos (classe 4, 5 e 6)"
    if height_m is None:
        return None, "acima de 6 pavimentos: informe building_height_m (H ≤ 30 m ou H > 30 m)"
    return 4, f"{floors} pavimentos com altura de {height_m:g} m (até 30 m)"


def _measures(t: Tabela, col: Coluna) -> list[dict[str, Any]]:
    out = []
    for m in t.medidas:
        cell = m.celulas[col.indice - 1]
        refs = [int(n) for n in re.findall(r"\d+", cell)] + list(m.observacoes_da_linha)
        if cell != "-":
            refs += [n for n in col.observacoes if n not in refs]
        status = ("NOT_MARKED" if cell == "-" else "CONDITIONAL" if refs else "REQUIRED")
        out.append({"label": m.rotulo, "cell": cell, "status": status,
                    "observacoes": [f"{n}- {t.observacoes.get(n, '(não encontrada)')}"
                                    for n in refs]})
    return out


def consult(tables: dict[int, Tabela], context: dict[str, Any]) -> dict[str, Any] | None:
    """Exigências das Tabelas 5 a 32 para o contexto; ``None`` se nenhuma se aplica.

    ``status``: INDICATIVE (coluna escolhida), CHOOSE_COLUMN (tabela por outro critério: devolve
    todas as colunas), MISSING_DATA (falta pavimentos ou altura) ou UNVERIFIED (tabela com
    problema estrutural, não usada).
    """
    occ = context.get("occupancy")
    area, floors = context.get("building_area_m2"), context.get("building_floors")
    found = [t for t in tables.values() if occ in t.divisoes]
    if not found:
        return None
    t = found[0]
    if not t.qualquer_area and area is not None and floors is not None \
            and area <= 900 and floors <= 2:
        return None  # vale a Tabela 2
    base = {"source": {"document": DOCUMENT, "item": f"Anexo III, Tabela {t.numero}",
                       "page": t.pagina, "title": t.titulo},
            "table": t.numero, "measures": [], "notes": t.gerais,
            "conferencia": (f"conferida no PDF oficial: {t.conferencia_visual}"
                            if t.conferencia_visual
                            else "extraída do texto do Decreto com conferência estrutural; "
                                 "SEM conferência visual no PDF oficial")}
    if not t.valida:
        return {**base, "status": "UNVERIFIED",
                "message": f"Tabela {t.numero} com problema na extração; não usada: "
                           f"{t.problemas}. Ler com consultar_norma."}
    cols = [c for c in t.colunas if occ in c.divisoes]
    if not t.padrao:
        if len(cols) == 1:
            return {**base, "status": "INDICATIVE", "column": cols[0].rotulo,
                    "measures": _measures(t, cols[0]),
                    "message": "Tabela de coluna única; conferir observações e notas técnicas."}
        return {**base, "status": "CHOOSE_COLUMN",
                "message": "Esta tabela não é por nº de pavimentos: escolha a coluna pelo "
                           "critério do cabeçalho (extensão, volume, área). Cabeçalhos "
                           "mesclados: conferir no PDF.",
                "columns": [{"column": c.rotulo, "measures": _measures(t, c)} for c in cols]}
    if floors is None:
        return {**base, "status": "MISSING_DATA", "message": "Informe building_floors."}
    cls, why = classe_de(int(floors), context.get("building_height_m"))
    if cls is None:
        return {**base, "status": "MISSING_DATA", "message": why}
    col = next(c for c in cols if c.classe == cls)
    return {**base, "status": "INDICATIVE", "column": f"{', '.join(col.divisoes)} — {col.rotulo}",
            "criterio": why, "measures": _measures(t, col),
            "message": "Consulta em rascunho; conferir as observações de cada medida. "
                       "Traço não é dispensa global."}


@lru_cache(maxsize=1)
def roteiro() -> list[dict[str, Any]]:
    """Medidas do Anexo III → ferramenta, NTs, símbolos e entrega (``medidas.yaml``)."""
    data = yaml.safe_load(MEDIDAS.read_text(encoding="utf-8"))
    return list(data.get("medidas") or [])


def como_tratar(label: str) -> dict[str, Any] | None:
    """Entrada do roteiro cujo rótulo é o início do nome da medida na tabela."""
    name = fold(label)
    for row in roteiro():
        if name.startswith(fold(row["rotulo"])):
            return {k: v for k, v in row.items() if k != "rotulo"}
    return None
