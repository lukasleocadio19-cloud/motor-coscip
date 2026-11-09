"""Autoria de plantas: a IA descreve a planta em operações e o motor gera o DXF.

A planta criada aqui é **sintética** (desenhada pela IA a partir do que o usuário descreveu),
não um projeto real. O estado é a lista de operações, guardada ao lado do DXF em
``<nome>.coscip.json``; cada alteração regenera o DXF inteiro a partir dela, então o arquivo
nunca fica pela metade e a IA pode retomar a planta depois.

Convenções do desenho gerado (as mesmas que o leitor do motor reconhece):

- coordenadas em METROS, eixo Y para cima, ``$INSUNITS`` = 6;
- paredes como contornos fechados de linhas (espessura real) na camada do estilo da parede
  (comum, corta-fogo, compartimentação, divisória — NT 1-03, p. 10), com os vãos das portas
  já recortados; portas na camada ``PORTAS`` (``PORTA_CORTA_FOGO`` para P-60/90/120);
- ambientes como polilinha fechada em ``AMBIENTES`` com nome e área em texto;
- símbolos como blocos do catálogo da NT 1-03 / NT 2-05 (``simbologia.py``), com o nome que o
  dicionário (``simbolos.yaml``) reconhece, e legenda gerada a partir deles (NT 1-03, 5.4).

Mesmo assim a unidade segue a regra do projeto: a análise só roda depois de
``confirmar_unidade`` (duas medidas em direções diferentes, ex. duas paredes cujo
comprimento o usuário informou).
"""

from __future__ import annotations

import difflib
import json
import math
import re
from pathlib import Path
from typing import Annotated, Any, Literal

import ezdxf
from ezdxf.enums import TextEntityAlignment
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
from shapely.geometry import LineString, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from coscip_mcp import simbologia
from coscip_mcp.simbologia import Entrada

SCHEMA = "coscip-autoria/1"
MIN_WALL_SEGMENTS = 20  # mesmo limite de coscip_analysis.analyze (walls_detected)
WALL_PIECE_M = 0.5

Pt = Annotated[list[float], Field(min_length=2, max_length=2)]

BASE_LAYERS = ("PAREDE", "PORTAS", "AMBIENTES", "TEXTOS", "COTAS", "LEGENDA")

# estilos de parede da NT 1-03 (p. 10): camada, preenchimento, espessura padrão, id no catálogo
WALL_STYLES: dict[str, tuple[str, str | None, float, str]] = {
    "comum": ("PAREDE", None, 0.15, "PAREDE_COMUM"),
    "corta_fogo": ("PAREDE_CORTA_FOGO", "solid", 0.20, "PAREDE_CORTA_FOGO"),
    "compartimentacao": ("PAREDE_COMPARTIMENTACAO", "hatch", 0.20, "PAREDE_COMPARTIMENTACAO"),
    "divisoria": ("DIVISORIA", None, 0.05, "DIVISORIA"),
}
WallStyle = Literal["comum", "corta_fogo", "compartimentacao", "divisoria"]

# classe do motor -> símbolo do catálogo usado quando a IA pede só a classe
CLASS_DEFAULTS: dict[str, str] = {
    "HIDRANTE": "HIDRANTE_SIMPLES", "HIDRANTE_URBANO": "HIDRANTE_URBANO",
    "REGISTRO_RECALQUE": "REGISTRO_RECALQUE", "BOMBA_INCENDIO": "BOMBA_INCENDIO",
    "ACIONADOR_BOMBA": "ACIONADOR_BOMBA_INCENDIO", "RESERVA_TECNICA": "RESERVA_TECNICA_INCENDIO",
    "SPRINKLER": "BICO_SPRINKLER_PENDENTE", "ILUMINACAO_EMERGENCIA": "PONTO_ILUMINACAO_EMERGENCIA",
    "DETECTOR": "DETECTOR_FUMACA", "ACIONADOR_MANUAL": "ACIONADOR_MANUAL",
    "AVISADOR": "AVISADOR_SONORO_ELETRONICO", "CENTRAL_ALARME": "CENTRAL_ALARME_DETECCAO",
    "CENTRAL_GLP": "CENTRAL_GLP", "SAIDA": "ROTA_DE_FUGA_FINAL",
}
# agente do extintor aceito -> sufixo do bloco (o dicionário lê o agente do nome)
EXTINGUISHER_AGENTS = {"CO2": "CO2", "AP": "AP", "AGUA": "AP", "ESPUMA": "ESPUMA",
                       "PQS_BC": "PQS_BC", "PQS_ABC": "PQS_ABC", "PO_D": "PO_D",
                       "PQS_D": "PO_D", "CLASSE_D": "PO_D"}
STATES = ("NOVO", "EXISTENTE", "DEMOLIR", "REALOCADO")
_CAPACITY = re.compile(r"^\s*([0-9]+(?:[.,][0-9]+)?)\s*(kg|l)\s*$", re.I)


def classes_desenhaveis() -> list[str]:
    return sorted({"EXTINTOR", "SINALIZACAO", *CLASS_DEFAULTS})


class AuthoringError(ValueError):
    """Erro de uso: a mensagem diz à IA o que corrigir."""


class _Op(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Parede(_Op):
    """Parede pelo EIXO: poligonal com espessura. ``fechar`` liga o último ponto ao primeiro."""

    tipo: Literal["parede"]
    pontos: list[Pt] = Field(min_length=2)
    espessura_m: float | None = Field(default=None, gt=0, le=1.0)
    fechar: bool = False
    estilo: WallStyle = "comum"


class Sala(_Op):
    """Ambiente pela face INTERNA (área útil = área do desenho), com parede por fora.

    ``retangulo`` = [x0, y0, x1, y1] ou ``poligono``. Salas vizinhas separadas por uma
    distância igual à espessura dividem uma única parede.
    """

    tipo: Literal["sala"]
    nome: str = Field(min_length=1, max_length=60)
    retangulo: Annotated[list[float], Field(min_length=4, max_length=4)] | None = None
    poligono: list[Pt] | None = Field(default=None, min_length=3)
    espessura_m: float | None = Field(default=None, gt=0, le=1.0)
    estilo_parede: WallStyle = "comum"
    sem_paredes: bool = False
    area_no_desenho: bool = True


class Porta(_Op):
    """Porta sobre uma parede: recorta o vão e desenha a folha e o arco de giro."""

    tipo: Literal["porta"]
    x: float
    y: float
    largura_m: float = Field(default=0.9, ge=0.4, le=6.0)
    angulo_graus: float = Field(default=0.0, description="direção da parede (0 = horizontal)")
    abre_para: Literal["esquerda", "direita"] = "esquerda"
    corte_m: float = Field(default=0.4, gt=0, le=2.0,
                           description="espessura recortada; use ≥ espessura da parede")
    corta_fogo_min: Literal[60, 90, 120] | None = None  # P-60/P-90/P-120 (NT 1-03, p. 10)


class Simbolo(_Op):
    """Símbolo do catálogo, por ``id`` OU por ``classe`` do motor (+ agente, código…)."""

    tipo: Literal["simbolo"]
    id: str | None = None
    classe: str | None = None
    x: float
    y: float
    rotacao_graus: float = 0.0
    tamanho_m: float | None = Field(default=None, gt=0, le=10)
    agente: str | None = None  # só com classe EXTINTOR
    sobre_rodas: bool = False  # só com classe EXTINTOR
    capacidade: str | None = None  # extintores, ex. "6 kg"
    estado: Literal["NOVO", "EXISTENTE", "DEMOLIR", "REALOCADO"] | None = None
    codigo: str | None = None  # só com classe SINALIZACAO, ex. "E-5", "S-12"


class Texto(_Op):
    tipo: Literal["texto"]
    texto: str = Field(min_length=1, max_length=200)
    x: float
    y: float
    altura_m: float = Field(default=0.25, gt=0, le=5)
    camada: str = "TEXTOS"
    centralizado: bool = False


class Cota(_Op):
    """Cota linear (DIMENSION) entre dois pontos; ajuda a confirmar a unidade."""

    tipo: Literal["cota"]
    a: Pt
    b: Pt
    afastamento_m: float = 0.8


class Legenda(_Op):
    """Legenda dos símbolos (NT 1-03, 5.4): título, o desenho de cada um e o nome oficial.

    Sem ``ids`` lista os símbolos, estilos de parede e portas corta-fogo realmente usados na
    planta. Com ``ids`` lista exatamente esses (ex.: para ver a simbologia inteira). ``x, y``
    é o canto superior esquerdo; as linhas descem.
    """

    tipo: Literal["legenda"]
    x: float
    y: float
    ids: list[str] | None = None
    titulo: str = "LEGENDA"
    escala: float = Field(default=1.0, gt=0, le=5)
    altura_linha_m: float = Field(default=1.0, gt=0.2, le=10)


class PavimentoCorte(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=40)
    pe_direito_m: float = Field(default=2.8, ge=2.0, le=20.0)


class Corte(_Op):
    """Corte esquemático / esquema vertical: pavimentos empilhados com níveis e, se pedido, a
    prumada de hidrantes e o reservatório com a RTI.

    É ESQUEMÁTICO: sai das alturas informadas, não da geometria da planta (uma planta 2D não
    tem altura). ``x, y`` é o canto inferior esquerdo, no nível do piso do primeiro pavimento;
    ``pavimentos`` vai de baixo para cima. Desenhe-o afastado da planta baixa.
    """

    tipo: Literal["corte"]
    x: float
    y: float
    largura_m: float = Field(default=12.0, ge=4.0, le=200.0)
    pavimentos: list[PavimentoCorte] = Field(min_length=1, max_length=80)
    laje_m: float = Field(default=0.15, gt=0.05, le=1.0)
    titulo: str = Field(default="CORTE ESQUEMÁTICO", max_length=80)
    prumada_hidrantes: bool = False
    reservatorio: Literal["superior", "inferior"] | None = None
    rti_l: float | None = Field(default=None, gt=0)


Operacao = Annotated[Parede | Sala | Porta | Simbolo | Texto | Cota | Legenda | Corte,
                     Field(discriminator="tipo")]
_OPS = TypeAdapter(list[Operacao])


def parse_ops(raw: list[dict[str, Any]]) -> list[_Op]:
    return _OPS.validate_python(raw)


def sidecar(path: Path) -> Path:
    return path.with_suffix(".coscip.json")


# --- resolução de símbolos ------------------------------------------------------------------------


def resolve_symbol(op: Simbolo) -> Entrada:
    """Entrada do catálogo para o pedido; levanta ``AuthoringError`` com a correção."""
    if (op.id is None) == (op.classe is None):
        raise AuthoringError("simbolo: informe 'id' (de listar_simbologia) OU 'classe'")
    if op.id is not None:
        entry = simbologia.achar(op.id)
        if entry is None:
            near = difflib.get_close_matches(op.id.upper(), list(simbologia.CATALOGO), n=4,
                                             cutoff=0.5)
            raise AuthoringError(f"símbolo {op.id!r} não existe no catálogo"
                                 + (f"; parecidos: {near}" if near else "")
                                 + "; veja listar_simbologia")
        if op.agente or op.sobre_rodas or op.codigo:
            raise AuthoringError("agente, sobre_rodas e codigo só valem com 'classe'; com 'id' "
                                 "o símbolo já é específico")
    else:
        cls = (op.classe or "").upper()
        if cls == "EXTINTOR":
            if not op.agente:
                raise AuthoringError("classe EXTINTOR exige agente: "
                                     f"{sorted(set(EXTINGUISHER_AGENTS))}")
            agent = EXTINGUISHER_AGENTS.get(op.agente.upper())
            if agent is None:
                raise AuthoringError(f"agente {op.agente!r} inválido; use "
                                     f"{sorted(set(EXTINGUISHER_AGENTS))}")
            entry = simbologia.CATALOGO[
                f"EXTINTOR_{agent}" + ("_SOBRERODAS" if op.sobre_rodas else "")]
        elif cls == "SINALIZACAO":
            found = simbologia.achar(op.codigo) if op.codigo else None
            if found is None or not found.esquematico:
                raise AuthoringError("classe SINALIZACAO exige codigo da NT 2-05, ex. 'E-5', "
                                     "'S-12' (listar_simbologia grupo='PLACAS')")
            entry = found
        elif cls in CLASS_DEFAULTS:
            entry = simbologia.CATALOGO[CLASS_DEFAULTS[cls]]
        else:
            raise AuthoringError(f"classe {op.classe!r} não desenhável; use uma de "
                                 f"{classes_desenhaveis()} ou 'id' (listar_simbologia)")
        if cls != "EXTINTOR" and (op.agente or op.sobre_rodas):
            raise AuthoringError("agente e sobre_rodas só valem para EXTINTOR")
        if cls != "SINALIZACAO" and op.codigo:
            raise AuthoringError("codigo só vale para SINALIZACAO")
    if entry.uso == "parede":
        raise AuthoringError(f"{entry.id} é um estilo de parede: use a operação 'parede' ou "
                             "'sala' com estilo (corta_fogo, compartimentacao, comum, divisoria)")
    if entry.uso == "porta":
        raise AuthoringError(f"{entry.id} é uma porta: use a operação 'porta' com "
                             "corta_fogo_min (60, 90 ou 120)")
    if op.capacidade:
        if entry.classe != "EXTINTOR":
            raise AuthoringError("capacidade só vale para extintor")
        if not _CAPACITY.match(op.capacidade):
            raise AuthoringError(f"capacidade {op.capacidade!r}: use '6 kg' ou '10 L'")
    return entry


def block_name(op: Simbolo, entry: Entrada | None = None) -> str:
    """Nome do bloco: id do catálogo + estado + capacidade (a capacidade vai por último: o
    dicionário a lê com "\\b" depois da unidade, ex. "6KG")."""
    entry = entry or resolve_symbol(op)
    parts = [entry.id]
    if op.estado:
        parts.append(op.estado)
    m = _CAPACITY.match(op.capacidade or "")
    if m:
        parts.append(m.group(1).replace(",", ".") + m.group(2).upper())
    return "_".join(parts)


class Authoring:
    """Planta em construção: lista de operações + o DXF que elas geram."""

    def __init__(self, path: Path, ops: list[_Op] | None = None, title: str = "") -> None:
        self.path = path
        self.ops: list[_Op] = ops or []
        self.title = title
        # Posições dos símbolos de legenda (x, y, classe do motor), da última geração.
        self.legend_marks: list[tuple[float, float, str]] = []

    # --- persistência ---------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> Authoring:
        side = sidecar(path)
        if not side.exists():
            raise AuthoringError(f"não há planta criada pelo motor em {path} (falta {side.name})")
        data = json.loads(side.read_text(encoding="utf-8"))
        if data.get("schema") != SCHEMA:
            raise AuthoringError(f"{side.name}: esquema desconhecido {data.get('schema')!r}")
        return cls(path, parse_ops(data["operacoes"]), data.get("titulo", ""))

    def save(self) -> None:
        body = {"schema": SCHEMA, "titulo": self.title,
                "aviso": "planta sintética criada pelo MCP do motor COSCIP; não é projeto real",
                "operacoes": [o.model_dump(exclude_none=True) for o in self.ops]}
        sidecar(self.path).write_text(json.dumps(body, ensure_ascii=False, indent=1),
                                      encoding="utf-8")

    # --- edição ---------------------------------------------------------------------------

    def add(self, raw: list[dict[str, Any]]) -> list[int]:
        new = parse_ops(raw)
        for op in new:
            _validate(op)
        first = len(self.ops)
        self.ops.extend(new)
        return list(range(first, len(self.ops)))

    def remove(self, indices: list[int]) -> list[_Op]:
        bad = [i for i in indices if not 0 <= i < len(self.ops)]
        if bad:
            raise AuthoringError(f"índices inexistentes: {bad}; há {len(self.ops)} elementos "
                                 "(0 a n-1, de listar_elementos)")
        gone = [self.ops[i] for i in sorted(set(indices))]
        keep = set(range(len(self.ops))) - set(indices)
        self.ops = [op for i, op in enumerate(self.ops) if i in keep]
        return gone

    def describe(self) -> list[dict[str, Any]]:
        return [{"i": i, **op.model_dump(exclude_none=True)} for i, op in enumerate(self.ops)]

    def used_entries(self) -> list[Entrada]:
        """Símbolos, estilos de parede e portas corta-fogo usados, sem repetir, na ordem."""
        out: dict[str, Entrada] = {}
        for op in self.ops:
            ent: Entrada | None = None
            if isinstance(op, Simbolo):
                ent = resolve_symbol(op)
            elif isinstance(op, Parede) and op.estilo != "comum":
                ent = simbologia.CATALOGO[WALL_STYLES[op.estilo][3]]
            elif isinstance(op, Sala) and op.estilo_parede != "comum" and not op.sem_paredes:
                ent = simbologia.CATALOGO[WALL_STYLES[op.estilo_parede][3]]
            elif isinstance(op, Porta) and op.corta_fogo_min:
                ent = simbologia.CATALOGO[f"PORTA_CORTA_FOGO_P{op.corta_fogo_min}"]
            if ent is not None:
                out.setdefault(ent.id, ent)
        return list(out.values())

    # --- geração do DXF --------------------------------------------------------------------

    def build(self) -> dict[str, Any]:
        """Regenera o DXF (substitui o arquivo) e devolve um resumo do que foi desenhado."""
        doc = ezdxf.new("R2018", setup=True)
        doc.header["$INSUNITS"] = 6
        for name in BASE_LAYERS:
            doc.layers.add(name)
        msp = doc.modelspace()
        blocks: set[str] = set()

        def layer(name: str) -> str:
            if name not in doc.layers:
                doc.layers.add(name)
            return name

        walls: dict[str, list[BaseGeometry]] = {}
        openings: list[BaseGeometry] = []
        rooms: list[dict[str, Any]] = []
        for op in self.ops:
            if isinstance(op, Parede):
                t = op.espessura_m or WALL_STYLES[op.estilo][2]
                pts = [tuple(p) for p in op.pontos]
                if op.fechar:
                    pts.append(pts[0])
                walls.setdefault(op.estilo, []).append(
                    LineString(pts).buffer(t / 2, cap_style="square", join_style="mitre"))
            elif isinstance(op, Sala):
                poly = _room_polygon(op)
                if not op.sem_paredes:
                    t = op.espessura_m or WALL_STYLES[op.estilo_parede][2]
                    walls.setdefault(op.estilo_parede, []).append(
                        poly.buffer(t, join_style="mitre").difference(poly))
                rooms.append({"nome": op.nome, "area_m2": round(poly.area, 2)})
            elif isinstance(op, Porta):
                openings.append(_door_opening(op))

        cut = unary_union(openings) if openings else None
        wall_loops = wall_segments = 0
        for style, parts in walls.items():
            geom = unary_union(parts)
            if cut is not None:
                geom = geom.difference(cut)
            if geom.is_empty:
                continue
            wall_layer, fill, _, _ = WALL_STYLES[style]
            lname = layer(wall_layer)
            for poly in getattr(geom, "geoms", [geom]):
                for ring in (poly.exterior, *poly.interiors):
                    pts = list(ring.coords)
                    for a, b in zip(pts, pts[1:], strict=False):
                        for p, q in _chop(a, b):
                            msp.add_line(p, q, dxfattribs={"layer": lname})
                            wall_segments += 1
                    wall_loops += 1
                if fill:
                    _fill_wall(msp, poly, lname, fill)

        self.legend_marks = []
        legends: list[Legenda] = []
        for op in self.ops:
            if isinstance(op, Sala):
                _draw_room(msp, op)
            elif isinstance(op, Porta):
                if op.corta_fogo_min:
                    layer("PORTA_CORTA_FOGO")
                _draw_door(msp, op)
            elif isinstance(op, Simbolo):
                entry = resolve_symbol(op)
                _place(doc, msp, entry, block_name(op, entry), layer(entry.camada), op.x, op.y,
                       op.rotacao_graus, op.tamanho_m or entry.tamanho_m, blocks)
            elif isinstance(op, Texto):
                _text(msp, op.texto, op.x, op.y, op.altura_m, layer(op.camada), op.centralizado)
            elif isinstance(op, Cota):
                _draw_dim(msp, op)
            elif isinstance(op, Legenda):
                legends.append(op)
            elif isinstance(op, Corte):
                _draw_section(doc, msp, op, layer("CORTE"), layer("CORTE_INC"), blocks)
        for leg in legends:  # por último: "usados" depende de todas as outras operações
            self._draw_legend(doc, msp, leg, blocks)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        doc.saveas(tmp)  # grava inteiro e só então troca: nunca fica DXF pela metade
        tmp.replace(self.path)
        self.save()
        out: dict[str, Any] = {"contornos_de_parede": wall_loops,
                               "segmentos_de_parede": wall_segments, "ambientes": rooms,
                               "operacoes": len(self.ops)}
        if wall_segments < MIN_WALL_SEGMENTS:
            out["ALERTA_paredes"] = (
                f"só {wall_segments} segmentos de parede: o motor só reconhece paredes com "
                f"{MIN_WALL_SEGMENTS} ou mais e, sem elas, a área útil e os percursos "
                "viram estimativa do recorte. Desenhe as salas/paredes antes de analisar.")
        return out

    def _draw_legend(self, doc, msp, op: Legenda, blocks: set[str]) -> None:  # noqa: ANN001
        if op.ids is None:
            entries = self.used_entries()
        else:
            entries = []
            for key in op.ids:
                found = simbologia.achar(key)
                if found is None:
                    raise AuthoringError(f"legenda: {key!r} não existe no catálogo")
                entries.append(found)
        lname = "LEGENDA"
        _text(msp, op.titulo, op.x, op.y, 0.4 * op.escala, lname, False)
        pitch = op.altura_linha_m * op.escala
        for i, e in enumerate(entries):
            y = op.y - pitch * (i + 1)
            gx = op.x + 1.3 * op.escala
            _place(doc, msp, e, e.id, lname, gx, y, 0.0, e.tamanho_m * op.escala, blocks)
            if e.classe:
                self.legend_marks.append((gx, y, e.classe))
            _text(msp, e.nome, op.x + 3.0 * op.escala, y, 0.25 * op.escala, lname, False)


# --- validação e desenho ----------------------------------------------------------------------


def _validate(op: _Op) -> None:
    if isinstance(op, Sala):
        if (op.retangulo is None) == (op.poligono is None):
            raise AuthoringError(f"sala {op.nome!r}: informe retangulo OU poligono")
        poly = _room_polygon(op)
        if not poly.is_valid or poly.area <= 0:
            raise AuthoringError(f"sala {op.nome!r}: geometria inválida ou sem área")
    elif isinstance(op, Simbolo):
        resolve_symbol(op)
    elif isinstance(op, Texto):
        if not re.fullmatch(r"[A-Za-z0-9_\-]{1,40}", op.camada):
            raise AuthoringError(f"nome de camada inválido: {op.camada!r}")
    elif isinstance(op, Cota):
        if math.dist(op.a, op.b) <= 0:
            raise AuthoringError("cota com os dois pontos iguais")
    elif isinstance(op, Legenda):
        for key in op.ids or []:
            if simbologia.achar(key) is None:
                raise AuthoringError(f"legenda: {key!r} não existe no catálogo")


def _chop(a: tuple[float, ...], b: tuple[float, ...]) -> list[tuple[tuple[float, float],
                                                                  tuple[float, float]]]:
    """Divide a parede em trechos de até ``WALL_PIECE_M``.

    O leitor do motor só reconhece paredes quando a camada tem ``MIN_WALL_SEGMENTS`` segmentos
    ou mais (heurística contra linhas soltas). Projetos reais têm milhares; uma sala pequena
    desenhada com 8 linhas ficaria de fora. A geometria é idêntica à de linhas inteiras.
    """
    n = max(1, math.ceil(math.dist(a[:2], b[:2]) / WALL_PIECE_M))
    pts = [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]
    return list(zip(pts, pts[1:], strict=False))


def _fill_wall(msp, poly: Polygon, layer_name: str, fill: str) -> None:  # noqa: ANN001
    """Preenchimento da parede: sólido (corta-fogo) ou hachura (compartimentação)."""
    from ezdxf import const

    hatch = msp.add_hatch(color=7, dxfattribs={"layer": layer_name})
    if fill == "solid":
        hatch.set_solid_fill()
    else:
        hatch.set_pattern_fill("ANSI31", scale=0.1)
    hatch.paths.add_polyline_path(list(poly.exterior.coords)[:-1], is_closed=True,
                                  flags=const.BOUNDARY_PATH_EXTERNAL)
    for ring in poly.interiors:
        hatch.paths.add_polyline_path(list(ring.coords)[:-1], is_closed=True,
                                      flags=const.BOUNDARY_PATH_OUTERMOST)


def _room_polygon(op: Sala) -> Polygon:
    if op.retangulo is not None:
        x0, y0, x1, y1 = op.retangulo
        if not (x1 > x0 and y1 > y0):
            raise AuthoringError(f"sala {op.nome!r}: retangulo precisa de x1 > x0 e y1 > y0")
        return box(x0, y0, x1, y1)
    return Polygon([tuple(p) for p in op.poligono or []])


def _door_opening(op: Porta) -> BaseGeometry:
    from shapely import affinity

    rect = box(op.x - op.largura_m / 2, op.y - op.corte_m / 2,
               op.x + op.largura_m / 2, op.y + op.corte_m / 2)
    return affinity.rotate(rect, op.angulo_graus, origin=(op.x, op.y))


def _draw_door(msp, op: Porta) -> None:  # noqa: ANN001
    """Folha aberta a 90° e arco de giro, com a dobradiça numa das pontas do vão."""
    a = math.radians(op.angulo_graus)
    ux, uy = math.cos(a), math.sin(a)
    side = 1 if op.abre_para == "esquerda" else -1
    hx, hy = op.x - ux * op.largura_m / 2, op.y - uy * op.largura_m / 2
    leaf = (hx - side * uy * op.largura_m, hy + side * ux * op.largura_m)
    attrs = {"layer": "PORTA_CORTA_FOGO" if op.corta_fogo_min else "PORTAS"}
    msp.add_line((hx, hy), leaf, dxfattribs=attrs)
    start = op.angulo_graus
    end = op.angulo_graus + 90 * side
    lo, hi = (start, end) if side > 0 else (end, start)
    msp.add_arc((hx, hy), op.largura_m, lo, hi, dxfattribs=attrs)
    if op.corta_fogo_min:  # o número do tempo (60/90/120) fica do lado oposto ao giro
        _text(msp, str(op.corta_fogo_min), op.x + side * uy * 0.4, op.y - side * ux * 0.4, 0.25,
              attrs["layer"], True)


def _draw_room(msp, op: Sala) -> None:  # noqa: ANN001
    poly = _room_polygon(op)
    msp.add_lwpolyline(list(poly.exterior.coords)[:-1], close=True,
                       dxfattribs={"layer": "AMBIENTES"})
    c = poly.representative_point()
    _text(msp, op.nome.upper(), c.x, c.y + (0.2 if op.area_no_desenho else 0.0), 0.25,
          "TEXTOS", True)
    if op.area_no_desenho:
        _text(msp, f"{poly.area:.2f} m²".replace(".", ","), c.x, c.y - 0.2, 0.25, "TEXTOS", True)


def _text(msp, s: str, x: float, y: float, h: float, layer: str,  # noqa: ANN001
          centered: bool) -> None:
    t = msp.add_text(s, dxfattribs={"layer": layer, "height": h})
    t.set_placement((x, y), align=TextEntityAlignment.MIDDLE_CENTER if centered
                    else TextEntityAlignment.LEFT)


def _place(doc, msp, entry: Entrada, name: str, layer: str, x: float, y: float,  # noqa: ANN001
           rotation: float, size: float, defined: set[str]) -> None:
    """Define o bloco (uma vez) com o desenho do catálogo e o insere escalado."""
    from coscip_mcp.simbologia import emit

    if name not in defined and name not in doc.blocks:
        emit(doc.blocks.new(name), entry.glyph())
        defined.add(name)
    msp.add_blockref(name, (x, y), dxfattribs={
        "layer": layer, "rotation": rotation, "xscale": size, "yscale": size, "zscale": size})


def _draw_dim(msp, op: Cota) -> None:  # noqa: ANN001
    (ax, ay), (bx, by) = op.a, op.b
    ang = math.degrees(math.atan2(by - ay, bx - ax))
    nx, ny = -math.sin(math.radians(ang)), math.cos(math.radians(ang))
    mx, my = (ax + bx) / 2 + nx * op.afastamento_m, (ay + by) / 2 + ny * op.afastamento_m
    dim = msp.add_linear_dim(base=(mx, my), p1=(ax, ay), p2=(bx, by), angle=ang,
                             dimstyle="EZDXF", dxfattribs={"layer": "COTAS"})
    dim.render()


def _draw_section(doc, msp, op: Corte, lay: str, lay_inc: str,  # noqa: ANN001
                  defined: set[str]) -> None:
    """Corte esquemático: lajes, paredes externas, níveis, cota total e a parte de incêndio.

    Os símbolos da prumada usam blocos com nomes que o dicionário NÃO reconhece (``ESQV_*``):
    o esquema vertical repete os hidrantes da planta e não pode ser contado como equipamento.
    """
    x0, x1, wall = op.x, op.x + op.largura_m, 0.2
    a = {"layer": lay}

    def rect(xa: float, ya: float, xb: float, yb: float, attrs: dict[str, Any] = a) -> None:
        msp.add_lwpolyline([(xa, ya), (xb, ya), (xb, yb), (xa, yb)], close=True, dxfattribs=attrs)

    msp.add_line((x0 - 2.0, op.y - op.laje_m), (x1 + 2.0, op.y - op.laje_m), dxfattribs=a)
    levels = [op.y]
    for pav in op.pavimentos:
        levels.append(levels[-1] + pav.pe_direito_m + op.laje_m)
    for i, pav in enumerate(op.pavimentos):
        z = levels[i]
        rect(x0, z - op.laje_m, x1, z)  # laje de piso
        rect(x0, z, x0 + wall, z + pav.pe_direito_m)
        rect(x1 - wall, z, x1, z + pav.pe_direito_m)
        _text(msp, pav.nome.upper(), (x0 + x1) / 2, z + pav.pe_direito_m / 2, 0.3, lay, True)
        _level_mark(msp, x1 + 3.6, z, z - op.y, lay)
    top = levels[-1]
    rect(x0, top - op.laje_m, x1, top)  # laje de cobertura
    _level_mark(msp, x1 + 3.6, top, top - op.y, lay)
    dim = msp.add_linear_dim(base=(x0 - 1.2, op.y), p1=(x0, op.y), p2=(x0, top), angle=90,
                             dimstyle="EZDXF", dxfattribs={"layer": "COTAS"})
    dim.render()
    _text(msp, op.titulo, (x0 + x1) / 2, op.y - 1.6, 0.4, lay, True)
    _text(msp, "ESQUEMÁTICO, SEM ESCALA DE DETALHE", (x0 + x1) / 2, op.y - 2.2, 0.2, lay, True)

    ai = {"layer": lay_inc}
    tank: tuple[float, float, float, float] | None = None
    if op.reservatorio == "superior":
        tank = (x1 - 4.0, top + 0.3, x1 - 1.0, top + 1.8)
    elif op.reservatorio == "inferior":
        tank = (x0 - 4.5, op.y - op.laje_m - 2.0, x0 - 1.5, op.y - op.laje_m - 0.5)
    if tank:
        rect(*tank, attrs=ai)
        label = "RESERVATÓRIO" + (f" - RTI {op.rti_l:,.0f} L".replace(",", ".")
                                  if op.rti_l else "")
        _text(msp, label, (tank[0] + tank[2]) / 2, tank[3] + 0.3, 0.22, lay_inc, True)
    if op.prumada_hidrantes:
        px = x1 - 1.5
        lo = op.y + 0.3
        hi = top - op.laje_m - 0.3
        if op.reservatorio == "superior" and tank:
            hi = tank[1]
        msp.add_line((px, lo), (px, hi), dxfattribs=ai)
        if op.reservatorio == "inferior" and tank:  # sucção até a prumada, por baixo do piso
            yb = (tank[1] + tank[3]) / 2
            msp.add_lwpolyline([(tank[2], yb), (px, yb), (px, lo)], dxfattribs=ai)
        glyph = simbologia.CATALOGO["HIDRANTE_SIMPLES"]
        for i in range(len(op.pavimentos)):
            zy = levels[i] + 1.2  # registro entre 1,0 e 1,5 m do piso (NT 2-02, 5.6.1 a)
            msp.add_line((px, zy), (px - 0.8, zy), dxfattribs=ai)
            _place(doc, msp, glyph, "ESQV_TOMADA_H", lay_inc, px - 1.1, zy + 0.1, 0.0, 0.5,
                   defined)
            _text(msp, f"H{i + 1}", px - 1.9, zy, 0.2, lay_inc, True)
        rr = simbologia.CATALOGO["REGISTRO_RECALQUE"]
        msp.add_lwpolyline([(px, lo), (x1 + 1.2, lo)], dxfattribs=ai)
        _place(doc, msp, rr, "ESQV_RR", lay_inc, x1 + 1.6, lo, 180.0, 0.6, defined)
        _text(msp, "RR", x1 + 2.3, lo + 0.35, 0.2, lay_inc, True)


def _level_mark(msp, x: float, y: float, level: float, lay: str) -> None:  # noqa: ANN001
    """Marca de nível: triângulo e a cota relativa ao piso do primeiro pavimento."""
    msp.add_lwpolyline([(x, y), (x - 0.15, y + 0.2), (x + 0.15, y + 0.2)], close=True,
                       dxfattribs={"layer": lay})
    msp.add_line((x - 0.5, y), (x + 1.6, y), dxfattribs={"layer": lay})
    sign = "+" if level >= 0 else "-"
    _text(msp, f"{sign}{abs(level):.2f}".replace(".", ","), x + 0.9, y + 0.3, 0.2, lay, True)
