from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import ezdxf
from ezdxf.document import Drawing
from ezdxf.entities import DXFGraphic, Insert
from ezdxf.math import Matrix44

from coscip_cbm import ExtractionQuality
from coscip_geometry.units import INSUNITS_NAMES

# Matriz de suporte inicial (plano §8). Ajustar com o corpus da POC.
SUPPORT: dict[str, ExtractionQuality] = {
    "LINE": ExtractionQuality.SUPPORTED,
    "LWPOLYLINE": ExtractionQuality.SUPPORTED,
    "POLYLINE": ExtractionQuality.SUPPORTED,
    "ARC": ExtractionQuality.SUPPORTED,
    "CIRCLE": ExtractionQuality.SUPPORTED,
    "INSERT": ExtractionQuality.SUPPORTED,
    "TEXT": ExtractionQuality.SUPPORTED,
    "MTEXT": ExtractionQuality.SUPPORTED,
    "ATTRIB": ExtractionQuality.SUPPORTED,
    "HATCH": ExtractionQuality.INVENTORY_ONLY,
    "DIMENSION": ExtractionQuality.INVENTORY_ONLY,  # fonte documental, não medida real
    "LEADER": ExtractionQuality.INVENTORY_ONLY,
    "MULTILEADER": ExtractionQuality.INVENTORY_ONLY,
    "ARC_DIMENSION": ExtractionQuality.INVENTORY_ONLY,
    "POINT": ExtractionQuality.INVENTORY_ONLY,
    "ATTDEF": ExtractionQuality.INVENTORY_ONLY,  # definição solta fora de bloco
    "OLE2FRAME": ExtractionQuality.INVENTORY_ONLY,  # objeto incorporado; conteúdo não lido
    "IMAGE": ExtractionQuality.INVENTORY_ONLY,
    "SPLINE": ExtractionQuality.VISUAL_ONLY,
    "ELLIPSE": ExtractionQuality.VISUAL_ONLY,
    "SOLID": ExtractionQuality.VISUAL_ONLY,  # preenchimento 2D (setas, símbolos)
    "WIPEOUT": ExtractionQuality.VISUAL_ONLY,
    # REGION, ACAD_PROXY_ENTITY, 3DSOLID etc. → UNSUPPORTED (inventariados).
}

MAX_BLOCK_DEPTH = 16
DEFAULT_MAX_EXPANDED = 2_000_000


class DxfReadError(RuntimeError):
    pass


@dataclass
class Inventory:
    dxf_version: str
    insunits: int
    insunits_name: str
    layouts: list[str]
    layers: list[str]
    blocks: list[str]
    xrefs: list[str]
    entity_counts: dict[str, int]
    expanded_count: int = 0
    unsupported_counts: dict[str, int] = field(default_factory=dict)
    extents: tuple[float, float, float, float] | None = None
    warnings: list[str] = field(default_factory=list)
    layout_entity_counts: dict[str, int] = field(default_factory=dict)
    proxy_object_count: int = 0

    @property
    def units_declared(self) -> bool:
        return self.insunits != 0


@dataclass(frozen=True)
class ExtractedEntity:
    handle: str
    entity_type: str
    layer: str
    layout: str
    instance_path: tuple[str, ...]
    block_name: str | None
    world_transform: list[list[float]]
    quality: ExtractionQuality
    points: tuple[tuple[float, float], ...] = ()
    text: str | None = None


class DxfReader:
    """Adaptador DXF → inventário + entidades com identidade de origem."""

    def __init__(self, max_expanded: int = DEFAULT_MAX_EXPANDED) -> None:
        self.max_expanded = max_expanded

    def open(self, path: Path) -> Drawing:
        try:
            return ezdxf.readfile(path)
        except (OSError, ezdxf.DXFStructureError) as exc:
            raise DxfReadError(f"DXF ilegível: {exc}") from exc

    def inventory(self, doc: Drawing) -> Inventory:
        msp = doc.modelspace()
        counts = Counter(e.dxftype() for e in msp)
        insunits = int(doc.header.get("$INSUNITS", 0))
        xrefs = [b.name for b in doc.blocks if b.block and b.block.is_xref]
        inv = Inventory(
            dxf_version=doc.dxfversion,
            insunits=insunits,
            insunits_name=INSUNITS_NAMES.get(insunits, f"código {insunits}"),
            layouts=[lay.name for lay in doc.layouts],
            layers=sorted(layer.dxf.name for layer in doc.layers),
            blocks=sorted(b.name for b in doc.blocks if not b.name.startswith("*")),
            xrefs=xrefs,
            entity_counts=dict(counts),
        )
        inv.unsupported_counts = {
            t: n for t, n in counts.items() if SUPPORT.get(t) is None
        }
        inv.layout_entity_counts = {lay.name: len(lay) for lay in doc.layouts}
        paper = {name: n for name, n in inv.layout_entity_counts.items() if name != "Model"}
        # Pranchas com conteúdo próprio além de carimbo/viewports: a análise lê só o Model.
        heavy = {name: n for name, n in paper.items() if n > 200}
        if heavy:
            inv.warnings.append(
                "Pranchas com geometria própria (não analisada, só o Model): "
                + ", ".join(f"{k} ({v})" for k, v in heavy.items())
            )
        inv.proxy_object_count = sum(1 for o in doc.objects if o.dxftype() == "ACAD_PROXY_OBJECT")
        if inv.proxy_object_count or counts.get("ACAD_PROXY_ENTITY"):
            inv.warnings.append(
                f"Objetos proxy de aplicativo externo: {inv.proxy_object_count} objetos, "
                f"{counts.get('ACAD_PROXY_ENTITY', 0)} entidades — conteúdo não interpretado"
            )
        if not inv.units_declared:
            inv.warnings.append("Unidade não declarada ($INSUNITS=0): confirmação obrigatória")
        else:
            inv.warnings.append(
                f"Unidade declarada ({inv.insunits_name}) é só indício: confirmar antes de medir"
            )
        if xrefs:
            inv.warnings.append(f"{len(xrefs)} XRef(s): enviar em pacote com manifesto")
        return inv

    def entities(self, doc: Drawing, layout: str = "Model") -> Iterator[ExtractedEntity]:
        """Percorre entidades expandindo blocos, preservando caminho de instâncias.

        Duas inserções do mesmo bloco geram identidades distintas.
        """
        space = doc.modelspace() if layout == "Model" else doc.paperspace(layout)
        budget = [self.max_expanded]
        for e in space:
            yield from self._walk(e, layout, (), Matrix44(), None, 0, budget)

    def _walk(
        self,
        e: DXFGraphic,
        layout: str,
        path: tuple[str, ...],
        m: Matrix44,
        block_name: str | None,
        depth: int,
        budget: list[int],
    ) -> Iterator[ExtractedEntity]:
        budget[0] -= 1
        if budget[0] < 0:
            raise DxfReadError("limite de entidades expandidas excedido")
        etype = e.dxftype()
        handle = e.dxf.handle or "?"
        here = (*path, f"entity:{handle}")
        quality = SUPPORT.get(etype, ExtractionQuality.UNSUPPORTED)

        if isinstance(e, Insert):
            if depth >= MAX_BLOCK_DEPTH:
                raise DxfReadError(f"profundidade de blocos excedida em {handle}")
            ins_m = e.matrix44() @ m
            name = e.dxf.name
            yield self._make(e, layout, here, ins_m, name, quality)
            for attrib in e.attribs:
                yield self._make(attrib, layout, (*here, f"attrib:{attrib.dxf.handle}"),
                                 m, name, ExtractionQuality.SUPPORTED)
            block = e.block()
            if block is None:
                return
            child_path = (*path, f"block:{name}@{handle}")
            for child in block:
                if child.dxftype() == "ATTDEF":
                    continue
                yield from self._walk(child, layout, child_path, ins_m, name, depth + 1, budget)
            return

        yield self._make(e, layout, here, m, block_name, quality)

    def _make(
        self,
        e: DXFGraphic,
        layout: str,
        path: tuple[str, ...],
        m: Matrix44,
        block_name: str | None,
        quality: ExtractionQuality,
    ) -> ExtractedEntity:
        pts: tuple[tuple[float, float], ...] = ()
        text = None
        etype = e.dxftype()
        try:
            if etype == "LINE":
                raw = [e.dxf.start, e.dxf.end]
                pts = tuple((v.x, v.y) for v in m.transform_vertices(raw))
            elif etype == "LWPOLYLINE":
                raw = [(x, y, 0) for x, y, *_ in e.get_points("xy")]
                pts = tuple((v.x, v.y) for v in m.transform_vertices(raw))
            elif etype in {"TEXT", "ATTRIB"}:
                text = e.dxf.text
            elif etype == "MTEXT":
                text = e.plain_text()
        except (AttributeError, ValueError):
            quality = ExtractionQuality.INVENTORY_ONLY
        return ExtractedEntity(
            handle=e.dxf.handle or "?",
            entity_type=etype,
            layer=e.dxf.get("layer", "0"),
            layout=layout,
            instance_path=path,
            block_name=block_name,
            world_transform=[list(r) for r in m.rows()],
            quality=quality,
            points=pts,
            text=text,
        )
