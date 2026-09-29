"""Reconhecimento de símbolos de segurança contra incêndio na planta.

Ordem de evidência (a mais forte primeiro):
1. mapeamento do analista (``overrides``: nome de bloco → classe);
2. nome do bloco (padrões do dicionário);
3. layer, só para bloco anônimo/genérico sem sub-bloco reconhecido;
4. texto curto (códigos de placa "E-5", "SAÍDA"), para sinalização e saídas.

A inserção mais externa reconhecida vence: o conteúdo interno dela não gera outro símbolo.
Nenhum símbolo é "confirmado" aqui; cada um guarda o padrão que o reconheceu.

Balanço (plano de correção, F5): toda inserção e todo texto curto termina em exatamente um
destino — reconhecido(classe), ignorado(motivo) ou não reconhecido — e nada entra duas vezes:
MINSERT vem expandido do leitor, atributo (ATTRIB) é atributo da inserção e não texto solto,
texto junto de um símbolo da mesma classe vira atributo dele, bloco duplicado no mesmo ponto é
um objeto só e marcações de saída a até 1 m viram uma saída com várias evidências.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from coscip_analysis.dictionary import SymbolDictionary
from coscip_analysis.plan import InsertRec, Plan, TextRec

_SIGN_CODE = re.compile(r"(?:^|[^A-Z0-9])(?:PICTO_)?([SEAPM])-?(\d{1,2})(?![0-9])", re.I)
_ANON = re.compile(r"^\*[A-Z]\d*$|^A\$C[0-9A-F]+$", re.I)
# Código de placa sem hífen ("P1", "E5") é comum em legenda de portas/pilares: só vale como
# placa quando o layer é de segurança contra incêndio.
_SAFETY_LAYER = re.compile(r"SIN|PLACA|INC|EMERG|PSCIP|BOMB|PPCI|PSCI", re.I)
OBJECT_TOL_M = 0.05  # dois blocos iguais a até 5 cm = o mesmo objeto (erro de CAD)
EXIT_MERGE_M = 1.0  # marcações de saída (bloco, texto, placa S-12) da mesma porta
TEXT_MAX = 40  # texto curto: candidato a símbolo/atributo; mais longo é texto corrido


@dataclass
class Symbol:
    id: str
    cls: str
    x: float
    y: float
    handle: str
    path: tuple[str, ...]
    block: str | None
    layer: str
    stage: str  # override | block_name | layer | text
    evidence: str
    attrs: dict[str, Any] = field(default_factory=dict)
    excluded: str | None = None  # LEGEND | DEMOLISH | DUPLICATE | MERGED
    rotation: float = 0.0

    @property
    def protective(self) -> bool:
        return self.excluded is None

    @property
    def object_key(self) -> str:
        """Identidade do objeto físico (F5.2): classe + posição na tolerância + raiz."""
        root = self.path[0] if self.path else self.handle
        raw = f"{self.cls}|{round(self.x / OBJECT_TOL_M)}|{round(self.y / OBJECT_TOL_M)}|{root}"
        return hashlib.sha1(raw.encode()).hexdigest()[:16]

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "class": self.cls, "x": round(self.x, 4), "y": round(self.y, 4),
                "handle": self.handle, "instance_path": list(self.path), "block": self.block,
                "layer": self.layer, "stage": self.stage, "evidence": self.evidence,
                "attrs": self.attrs, "excluded": self.excluded,
                "object_key": self.object_key}


def _sid(path: tuple[str, ...], handle: str) -> str:
    return hashlib.sha1(("/".join(path) + "#" + handle).encode()).hexdigest()[:14]


def _sign_code(name: str) -> str | None:
    m = _SIGN_CODE.search(name)
    return f"{m.group(1).upper()}-{int(m.group(2))}" if m else None


def _match_block(d: SymbolDictionary, name: str) -> tuple[str, str] | None:
    for cls in d.classes.values():
        if cls.excluded(name):
            continue
        for p in cls.block:
            if p.search(name):
                return cls.id, p.pattern
    return None


def _match_layer(d: SymbolDictionary, layer: str) -> tuple[str, str] | None:
    for cls in d.classes.values():
        for p in cls.layer:
            if p.search(layer):
                return cls.id, p.pattern
    return None


def _under(path: tuple[str, ...], prefixes: set[tuple[str, ...]]) -> bool:
    return any(path[:i] in prefixes for i in range(1, len(path)))


def recognize(plan: Plan, d: SymbolDictionary,
              overrides: dict[str, str] | None = None,
              ledger: dict[str, Any] | None = None) -> tuple[list[Symbol], list[dict]]:
    """Devolve (símbolos, blocos frequentes não reconhecidos).

    ``ledger`` (opcional) recebe o destino de cada inserção e texto curto, para o balanço de
    reconhecimento (``recognition_ledger``)."""
    book = ledger if ledger is not None else {}
    book.setdefault("inserts", {})
    book.setdefault("texts", {})
    book.setdefault("unrecognized", [])
    overrides = {k.upper(): v for k, v in (overrides or {}).items()}
    by_block: dict[InsertRec, tuple[str, str, str]] = {}
    for ins in plan.inserts:
        cls = overrides.get(ins.block.upper())
        if cls:
            by_block[ins] = (cls, "override", f"mapeamento do analista: {ins.block}")
            continue
        hit = _match_block(d, ins.block)
        if hit:
            by_block[ins] = (hit[0], "block_name", f"bloco '{ins.block}' ~ /{hit[1]}/")
    matched_prefixes = {i.child_prefix for i in by_block}

    symbols: list[Symbol] = []
    taken: set[tuple[str, ...]] = set()
    unrecognized: Counter[tuple[str, str]] = Counter()
    for ins in plan.inserts:  # ordem DFS: pais antes dos filhos
        if _under(ins.path, taken):
            book["inserts"][ins.path] = "IGNORED:INSIDE_RECOGNIZED"
            continue
        if ins.block in plan.xrefs:  # conteúdo em arquivo externo: bloqueia o balanço
            book["inserts"][ins.path] = "IGNORED:XREF"
            continue
        found = by_block.get(ins)
        if found is None and (_ANON.match(ins.block) or ins.block.upper() in {"0", "BLOCO"}):
            # Layer só decide quando nenhum sub-bloco desta inserção foi reconhecido.
            has_child = any(p[:len(ins.child_prefix)] == ins.child_prefix
                            for p in matched_prefixes)
            hit = None if has_child else _match_layer(d, ins.layer)
            if hit:
                found = (hit[0], "layer", f"layer '{ins.layer}' ~ /{hit[1]}/ (bloco {ins.block})")
        if found is None:
            if len(ins.path) == 1:
                unrecognized[(ins.block, ins.layer)] += 1
            # não reconhecido em QUALQUER nível (bloco desconhecido dentro de outro também)
            book["inserts"][ins.path] = "NOT_RECOGNIZED"
            book["unrecognized"].append(ins)
            continue
        cls, stage, why = found
        attrs = _block_attrs(d, cls, ins.block)
        _attrib_attrs(d, cls, ins, attrs)
        x, y = ins.x, ins.y
        # Posição = centro do desenho do bloco quando ele é compacto (símbolo); o ponto de
        # inserção fica como evidência (há blocos com base a dezenas de metros do desenho).
        if ins.cx is not None and ins.size is not None and ins.size <= 5.0:
            x, y = ins.cx, ins.cy
            attrs["insert_point"] = [round(ins.x, 3), round(ins.y, 3)]
            attrs["size_m"] = round(ins.size, 3)
        symbols.append(Symbol(_sid(ins.path, ins.handle), cls, x, y, ins.handle,
                              ins.path, ins.block, ins.layer, stage, why, attrs,
                              rotation=ins.rotation))
        book["inserts"][ins.path] = f"RECOGNIZED:{cls}"
        taken.add(ins.child_prefix)

    _embedded_signs(plan, symbols)
    symbols.extend(_text_symbols(plan, d, taken, symbols, book))
    exits = {c for cls in d.classes.values() for c in cls.sign_codes}
    for s in list(symbols):
        # Placa S-12/S-14 (bloco ou texto) também marca a porta de saída.
        if s.cls == "SINALIZACAO" and s.attrs.get("code") in exits:
            symbols.append(Symbol(s.id + "x", "SAIDA", s.x, s.y, s.handle, s.path, s.block,
                                  s.layer, s.stage, f"placa {s.attrs['code']} indica saída",
                                  {**s.attrs, "derived_from": s.id}))
    symbols.extend(_presumed_extinguishers(plan, symbols))
    _texts_attrs(plan, d, symbols)
    for s in symbols:
        if s.attrs.get("state") == "DEMOLIR":
            s.excluded = "DEMOLISH"
    _dedupe(symbols)
    _merge_exits(symbols)
    book["exploded_candidates"] = _exploded_candidates(plan, d, symbols, book)
    frequent = [{"block": b, "layer": lay, "count": n}
                for (b, lay), n in unrecognized.most_common(25) if n >= 2]
    return symbols, frequent


def _block_attrs(d: SymbolDictionary, cls: str, name: str) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    for state, pats in d.state.items():
        if any(p.search(name) for p in pats):
            attrs["state"] = state
            break
    if cls == "EXTINTOR":
        attrs.update(_agent(d, name))
        if m := d.capacity.search(name.replace("_", " ")):
            attrs["capacity"] = f"{m.group(1).replace(',', '.')} {m.group(2).lower()}"
    if cls in {"SINALIZACAO", "SAIDA"} and (code := _sign_code(name)):
        attrs["code"] = code
    return attrs


def _agent(d: SymbolDictionary, text: str) -> dict[str, Any]:
    for agent, pats in d.agent.items():
        if any(p.search(text) for p in pats):
            return {"agent": agent}
    return {}


def _attrib_attrs(d: SymbolDictionary, cls: str, ins: InsertRec, attrs: dict[str, Any]) -> None:
    """Atributos (ATTRIB) da inserção: agente, carga e capacidade do extintor, código da placa."""
    if not ins.attribs:
        return
    attrs["attribs"] = {tag or f"#{i}": value for i, (tag, value) in enumerate(ins.attribs)}
    for _tag, value in ins.attribs:
        if cls == "EXTINTOR":
            if "agent" not in attrs and (a := _agent(d, value)):
                attrs.update(a, agent_text=value)
            if "capacity" not in attrs and (m := d.capacity.search(value.upper())):
                attrs["capacity"] = f"{m.group(1).replace(',', '.')} {m.group(2).lower()}"
            if "rating" not in attrs and (m := d.rating.search(value.upper())):
                attrs["rating"] = m.group(0).strip()
        if cls in {"SINALIZACAO", "SAIDA"} and "code" not in attrs and (c := _sign_code(value)):
            attrs["code"] = c


def _text_symbols(plan: Plan, d: SymbolDictionary, taken: set, blocks: list[Symbol],
                  book: dict[str, Any]) -> list[Symbol]:
    out = []
    r = d.attribute_radius_m
    for t in plan.texts:
        if len(t.text) > TEXT_MAX:
            continue
        if t.owner_path is not None:  # ATTRIB: atributo da inserção dona, não texto solto
            book["texts"][t.path] = "IGNORED:ATTRIBUTE"
            continue
        if _under(t.path, taken):
            book["texts"][t.path] = "IGNORED:INSIDE_RECOGNIZED"
            continue
        for cls in d.classes.values():
            if any(p.search(t.text) for p in cls.text):
                if (cls.id == "SINALIZACAO" and "-" not in t.text
                        and not _SAFETY_LAYER.search(t.layer)):
                    continue
                owner = next((s for s in blocks if s.cls == cls.id
                              and math.hypot(s.x - t.x, s.y - t.y) <= r), None)
                if owner is not None:
                    # "EXTINTOR" / "SAÍDA" escrito junto do símbolo: rótulo dele, não outro
                    owner.attrs.setdefault("labels", []).append(t.text)
                    book["texts"][t.path] = "IGNORED:TEXT_AS_ATTRIBUTE"
                    break
                attrs: dict[str, Any] = {}
                if code := _sign_code(t.text):
                    attrs["code"] = code
                out.append(Symbol(_sid(t.path, t.handle), cls.id, t.x, t.y, t.handle, t.path,
                                  t.block, t.layer, "text", f"texto '{t.text}'", attrs))
                book["texts"][t.path] = f"RECOGNIZED:{cls.id}"
                break
        else:
            book["texts"].setdefault(t.path, "NOT_RECOGNIZED")
    return out


def _dedupe(symbols: list[Symbol]) -> None:
    """Bloco igual no mesmo ponto (cópia sobreposta, erro comum de CAD) é um objeto só."""
    keep: dict[tuple, list[Symbol]] = {}
    for s in symbols:
        if s.excluded is not None or s.stage in {"text", "presumed"}:
            continue
        cell = (s.cls, s.block, round(s.rotation) % 360,
                math.floor(s.x / OBJECT_TOL_M), math.floor(s.y / OBJECT_TOL_M))
        keep.setdefault(cell[:3], []).append(s)
    for group in keep.values():
        group.sort(key=lambda s: (s.path, s.handle))
        kept: list[Symbol] = []
        for s in group:
            twin = next((k for k in kept if math.hypot(k.x - s.x, k.y - s.y) <= OBJECT_TOL_M),
                        None)
            if twin is None:
                kept.append(s)
                continue
            s.excluded = "DUPLICATE"
            twin.attrs.setdefault("duplicates", []).append(s.handle)


def _merge_exits(symbols: list[Symbol]) -> None:
    """Bloco de saída, texto "SAÍDA" e placa S-12/S-14 da mesma porta: uma saída só."""
    rank = {"override": 0, "block_name": 1, "layer": 2, "text": 3}
    exits = sorted((s for s in symbols if s.cls == "SAIDA" and s.excluded is None),
                   key=lambda s: (rank.get(s.stage, 4), s.path, s.handle))
    kept: list[Symbol] = []
    for s in exits:
        twin = next((k for k in kept if math.hypot(k.x - s.x, k.y - s.y) <= EXIT_MERGE_M), None)
        if twin is None:
            kept.append(s)
            continue
        s.excluded = "MERGED"
        twin.attrs.setdefault("merged_evidence", []).append(s.evidence)


def _exploded_candidates(plan: Plan, d: SymbolDictionary, symbols: list[Symbol],
                         book: dict[str, Any]) -> list[dict[str, Any]]:
    """Extintor desenhado com linhas soltas (sem bloco): texto de agente + carga sem símbolo
    por perto. Vira candidato à revisão — nunca símbolo, nunca conformidade."""
    ext = [s for s in symbols if s.cls == "EXTINTOR"]
    r = d.attribute_radius_m
    out = []
    for t in plan.texts:
        if len(t.text) > TEXT_MAX or book["texts"].get(t.path) != "NOT_RECOGNIZED":
            continue
        up = t.text.upper()
        if not (_agent(d, t.text) and (d.capacity.search(up) or d.rating.search(up))):
            continue
        if any(math.hypot(s.x - t.x, s.y - t.y) <= r for s in ext):
            continue
        out.append({"text": t.text, "x": round(t.x, 3), "y": round(t.y, 3), "handle": t.handle,
                    "layer": t.layer, "reason": "texto de agente/carga sem símbolo de extintor"})
    return out


def is_safety_layer(d: SymbolDictionary, layer: str) -> bool:
    return bool(_SAFETY_LAYER.search(layer)) or _match_layer(d, layer) is not None


def recognition_ledger(plan: Plan, symbols: list[Symbol], d: SymbolDictionary,
                       book: dict[str, Any]) -> dict[str, Any]:
    """Balanço de reconhecimento (F5.3): cada inserção e texto curto em exatamente um destino.

    Símbolo excluído depois do reconhecimento (legenda, demolir, duplicado, saída fundida)
    passa de "reconhecido" para "ignorado" com o motivo."""
    excluded = {s.path: s.excluded for s in symbols if s.excluded and s.stage != "presumed"
                and "derived_from" not in s.attrs}

    def final(path: tuple[str, ...], dest: str) -> str:
        return f"IGNORED:{excluded[path]}" if dest.startswith("RECOGNIZED") and path in excluded \
            else dest

    ins_dest = {p: final(p, v) for p, v in book["inserts"].items()}
    txt_dest = {p: final(p, v) for p, v in book["texts"].items()}
    for sk in plan.skipped:
        if sk.entity_type == "INSERT":
            ins_dest[tuple(sk.instance_path)] = f"IGNORED:{sk.reason}"
        elif sk.entity_type in {"TEXT", "MTEXT", "ATTRIB"} and sk.text and \
                len(" ".join(sk.text.split())) <= TEXT_MAX:
            txt_dest[tuple(sk.instance_path)] = f"IGNORED:{sk.reason}"

    def tally(dest: dict) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for v in dest.values():
            counts[v] = counts.get(v, 0) + 1
        total = len(dest)
        resolved = sum(n for k, n in counts.items() if not k.startswith("NOT_RECOGNIZED"))
        return {"total": total, "by_destination": dict(sorted(counts.items())),
                "coverage": round(resolved / total, 4) if total else 1.0}

    groups: dict[tuple[str, str, int], int] = {}
    for ins in book["unrecognized"]:
        key = (ins.block, ins.layer, len(ins.path))
        groups[key] = groups.get(key, 0) + 1
    unrec = [{"block": b, "layer": lay, "depth": depth, "count": n,
              "safety_layer": is_safety_layer(d, lay)}
             for (b, lay, depth), n in sorted(groups.items(), key=lambda kv: (-kv[1], kv[0]))]
    blocking = [u for u in unrec if u["safety_layer"]]
    return {
        "schema": "recognition-ledger/1.0",
        "inserts": tally(ins_dest), "short_texts": tally(txt_dest),
        "unrecognized_blocks": unrec,
        "unrecognized_in_safety_layers": sum(u["count"] for u in blocking),
        "exploded_candidates": book.get("exploded_candidates", []),
        "xrefs": list(plan.xrefs), "paper_space": dict(plan.paper_space),
        "complete": not blocking and not plan.xrefs,
    }


_E5 = re.compile(r"^\s*E\s*-?\s*5\s*$", re.I)
_E17 = re.compile(r"^\s*E\s*-?\s*17\s*$", re.I)
PRESUMED_PAIR_M = 1.6  # placa E-5 e marcação de piso E-17 do mesmo ponto
PRESUMED_CLEAR_M = 2.0  # sem símbolo de extintor já reconhecido por perto


def _presumed_extinguishers(plan: Plan, symbols: list[Symbol]) -> list[Symbol]:
    """Extintor indicado só pela sinalização: placa E-5 com marcação de piso E-17 juntas.

    Heurística (projetos que não desenham o símbolo do extintor): o símbolo sai marcado
    ``presumed`` e as regras de extintor vão para revisão humana quando o usam.
    """
    e5 = [t for t in plan.texts if _E5.match(t.text)]
    e17 = [t for t in plan.texts if _E17.match(t.text)]
    real = [s for s in symbols if s.cls == "EXTINTOR"]
    out: list[Symbol] = []
    for t in e5:
        floor = min((math.hypot(f.x - t.x, f.y - t.y) for f in e17), default=None)
        if floor is None or floor > PRESUMED_PAIR_M:
            continue
        if any(math.hypot(s.x - t.x, s.y - t.y) <= PRESUMED_CLEAR_M for s in (*real, *out)):
            continue
        out.append(Symbol(_sid(t.path, t.handle) + "p", "EXTINTOR", t.x, t.y, t.handle, t.path,
                          t.block, t.layer, "presumed",
                          f"placa '{t.text}' + marcação de piso E-17 a {floor:.1f} m "
                          "(sem símbolo de extintor desenhado)", {"presumed": True}))
    return out


def _embedded_signs(plan: Plan, symbols: list[Symbol]) -> None:
    """Placas desenhadas dentro do próprio bloco do equipamento (ex.: PICTO_E5 no 9715)."""
    by_prefix = {(*s.path[:-1], f"block:{s.block}@{s.handle}"): s for s in symbols if s.block}
    if not by_prefix:
        return
    for rec in (*plan.inserts, *plan.texts):
        name = rec.block if isinstance(rec, InsertRec) else rec.text
        if len(rec.path) < 2 or len(name) > 40:
            continue
        code = _sign_code(name)
        if not code:
            continue
        for i in range(len(rec.path) - 1, 0, -1):
            owner = by_prefix.get(rec.path[:i])
            if owner is not None:
                owner.attrs.setdefault("embedded_signs", []).append(code)
                break


def _texts_attrs(plan: Plan, d: SymbolDictionary, symbols: list[Symbol]) -> None:
    """Agente e carga do extintor por texto próximo (ex.: "PQS 6kg", "4-A:20-B:C")."""
    ext = [s for s in symbols if s.cls == "EXTINTOR"]
    if not ext or not plan.texts:
        return
    r = d.attribute_radius_m
    grid: dict[tuple[int, int], list[TextRec]] = {}
    for t in plan.texts:
        if len(t.text) <= 60:
            grid.setdefault((math.floor(t.x / r), math.floor(t.y / r)), []).append(t)
    for s in ext:
        near = []
        gx, gy = math.floor(s.x / r), math.floor(s.y / r)
        for ix in (gx - 1, gx, gx + 1):
            for iy in (gy - 1, gy, gy + 1):
                for t in grid.get((ix, iy), ()):
                    dist = math.hypot(t.x - s.x, t.y - s.y)
                    if dist <= r:
                        near.append((dist, t))
        for _, t in sorted(near, key=lambda p: p[0]):
            if "agent" not in s.attrs and (a := _agent(d, t.text)):
                s.attrs.update(a, agent_text=t.text)
            if "capacity" not in s.attrs and (m := d.capacity.search(t.text)):
                s.attrs["capacity"] = f"{m.group(1).replace(',', '.')} {m.group(2).lower()}"
            if "rating" not in s.attrs and (m := d.rating.search(t.text.upper())):
                s.attrs["rating"] = m.group(0).strip()


def mark_legends(symbols: list[Symbol], plan: Plan, d: SymbolDictionary) -> int:
    """Marca símbolos de quadro de legenda e devolve quantos foram marcados.

    Legenda = coluna de ≥ 3 símbolos de blocos diferentes, com descrições alinhadas à
    direita (mesma coluna de texto) e um título de legenda por perto — ou ≥ 5 linhas assim.
    Numa planta, símbolos empilhados têm textos soltos ao lado, mas não uma coluna de
    descrições alinhadas nem título "LEGENDA": ficam como estão.
    """
    col_tol, gap, reach = 0.6, 8.0, 12.0
    titles = [(t.x, t.y) for t in plan.texts if any(p.search(t.text) for p in d.legend_titles)]
    texts = [(t.x, t.y) for t in plan.texts if len(t.text) >= 10]
    cand = sorted((s for s in symbols if s.excluded is None), key=lambda s: s.x)
    groups: list[list[Symbol]] = []
    for s in cand:
        for g in groups:
            if abs(g[0].x - s.x) <= col_tol:
                g.append(s)
                break
        else:
            groups.append([s])
    marked = 0
    for g in groups:
        g.sort(key=lambda s: -s.y)
        chunk: list[Symbol] = []
        for s in [*g, None]:
            if s is not None and (not chunk or chunk[-1].y - s.y <= gap):
                chunk.append(s)
                continue
            if len(chunk) >= 3 and len({c.block or c.evidence for c in chunk}) >= 3:
                marked += _mark_if_legend(chunk, texts, titles, reach)
            chunk = [s] if s is not None else []
    return marked


def _mark_if_legend(chunk: list[Symbol], texts: list[tuple[float, float]],
                    titles: list[tuple[float, float]], reach: float) -> int:
    desc_x = []
    for c in chunk:
        right = [tx for tx, ty in texts if 0 < tx - c.x <= reach and abs(ty - c.y) <= 0.8]
        if right:
            desc_x.append(min(right))
    if len(desc_x) < 0.6 * len(chunk):
        return 0
    aligned = float(np.std(desc_x)) <= 1.0
    x0 = min(c.x for c in chunk)
    y_top, y_bot = max(c.y for c in chunk), min(c.y for c in chunk)
    titled = any(x0 - 5 <= tx <= x0 + 40 and y_bot - 5 <= ty <= y_top + 30 for tx, ty in titles)
    if not aligned or not (titled or len(chunk) >= 5):
        return 0
    for c in chunk:
        c.excluded = "LEGEND"
    return len(chunk)
