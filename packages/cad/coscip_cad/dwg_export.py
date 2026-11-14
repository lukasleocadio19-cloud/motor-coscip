"""DXF → DWG pelo ODA File Converter, com conferência de ida e volta (frente D7, §9).

O motor desenha em DXF; o projeto que o CBMERJ recebe é DWG. Este módulo converte uma **cópia**
do DXF para DWG e confere o resultado reconvertendo o DWG para DXF e comparando os dois
desenhos: camadas e suas propriedades, entidades por camada e tipo, blocos, estilos, layouts,
*viewports*, textos e extensão do desenho. O DXF original nunca é alterado.

A conferência diz o que a conversão **preservou**; não diz que o desenho está certo nem que o
AutoCAD o abrirá sem aviso (isso só o AutoCAD confirma). Diferenças sem consequência para o
desenho (nomes de blocos anônimos, ordem) não contam.

Licença: a mesma da ADR 0006. O conversor gratuito restringe não membros da ODA a uso não
comercial; o SDK de teste expira, e então a conversão falha com a mensagem do conversor.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import time
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from coscip_cad import dwg as dwg_mod
from coscip_cad.dwg import DwgConversionError, Runner

TOLERANCIA_M = 1e-3  # diferença aceita na extensão do desenho
_ANONIMOS = ("*",)  # blocos anônimos (*D1, *U2...) são renumerados pelo conversor
_PADRAO_ESTILOS = {"standard", "annotative", "bylayer", "byblock", "continuous"}


@dataclass
class DwgExport:
    dxf_path: str
    dxf_sha256: str
    dwg_path: str
    dwg_sha256: str
    dwg_version: str | None
    tool: str
    tool_path: str
    tool_version: str | None
    seconds: float
    conferencia: dict[str, Any] = field(default_factory=dict)
    note: str = dwg_mod.LICENSE_NOTE

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# --- conferência -------------------------------------------------------------------------------


def _sem_padrao(nomes: Iterable[str]) -> set[str]:
    return {n.casefold() for n in nomes if n.casefold() not in _PADRAO_ESTILOS}


def _texto(e) -> str | None:  # noqa: ANN001
    t = e.dxftype()
    if t == "TEXT":
        return e.dxf.text
    if t == "MTEXT":
        return e.plain_text()
    if t in ("ATTRIB", "ATTDEF"):
        return e.dxf.text
    return None


def _ler_layout(layout) -> dict[str, Any]:  # noqa: ANN001
    por_tipo: Counter[tuple[str, str]] = Counter()
    textos: Counter[str] = Counter()
    for e in layout:
        if e.dxftype() == "VIEWPORT" and e.dxf.id == 1:
            continue  # a viewport do layout inteiro: o conversor a muda de camada
        por_tipo[(e.dxf.layer, e.dxftype())] += 1
        t = _texto(e)
        if t:
            textos[t.strip()] += 1
        if e.dxftype() == "INSERT":
            for a in e.attribs:
                if a.dxf.text:
                    textos[a.dxf.text.strip()] += 1
    return {"entidades": por_tipo, "textos": textos}


def _viewports(layout) -> list[float]:  # noqa: ANN001
    """Escala (altura vista / altura no papel) de cada viewport útil; a de id 1 é o layout todo."""
    out = []
    for v in layout.viewports():
        if v.dxf.id == 1:
            continue
        papel = v.dxf.height or 0.0
        out.append(round((v.dxf.view_height or 0.0) / papel, 3) if papel else 0.0)
    return sorted(out)


def _extensao(doc) -> tuple[float, float, float, float] | None:  # noqa: ANN001
    from ezdxf import bbox

    e = bbox.extents(doc.modelspace())
    if not e.has_data:
        return None
    return (e.extmin.x, e.extmin.y, e.extmax.x, e.extmax.y)


def _camadas(doc) -> dict[str, tuple]:  # noqa: ANN001
    return {la.dxf.name.casefold(): (abs(la.color), la.dxf.lineweight, la.dxf.linetype.casefold(),
                                     bool(la.is_off()), bool(la.is_frozen()),
                                     la.dxf.get("plot", 1))
            for la in doc.layers}


def _dif_contagem(rotulo: str, a: Counter, b: Counter, limite: int = 8) -> list[str]:
    out = []
    for chave in sorted(set(a) | set(b), key=str):
        if a[chave] != b[chave]:
            out.append(f"{rotulo} {chave}: {a[chave]} no original, {b[chave]} no DWG reaberto")
    return out[:limite] + ([f"{rotulo}: mais {len(out) - limite} diferenças"]
                           if len(out) > limite else [])


def comparar_desenhos(original, reaberto) -> dict[str, Any]:  # noqa: ANN001
    """Compara dois ``ezdxf.Drawing`` e devolve ``{confere, diferencas, metricas}``.

    ``diferencas`` é a lista do que mudou (vazia quando confere); ``metricas`` traz os números
    comparados, para o relatório.
    """
    dif: list[str] = []
    ca, cb = _camadas(original), _camadas(reaberto)
    for nome in sorted(set(ca) - set(cb)):
        dif.append(f"camada {nome!r} sumiu")
    for nome in sorted(set(ca) & set(cb)):
        if ca[nome] != cb[nome]:
            dif.append(f"camada {nome!r}: propriedades {ca[nome]} -> {cb[nome]}")
    ba = {b.name.casefold() for b in original.blocks if not b.name.startswith(_ANONIMOS)}
    bb = {b.name.casefold() for b in reaberto.blocks if not b.name.startswith(_ANONIMOS)}
    for nome in sorted(ba - bb):
        dif.append(f"bloco {nome!r} sumiu")
    for rotulo, tabela in (("estilo de cota", "dimstyles"), ("estilo de texto", "styles"),
                           ("tipo de linha", "linetypes")):
        faltam = _sem_padrao(e.dxf.name for e in getattr(original, tabela)) \
            - _sem_padrao(e.dxf.name for e in getattr(reaberto, tabela))
        dif += [f"{rotulo} {n!r} sumiu" for n in sorted(faltam)]
    la = {n.casefold() for n in original.layouts.names()}
    lb = {n.casefold() for n in reaberto.layouts.names()}
    dif += [f"layout {n!r} sumiu" for n in sorted(la - lb)]

    total_a = total_b = 0
    textos_a: Counter[str] = Counter()
    textos_b: Counter[str] = Counter()
    entidades_a: Counter[tuple[str, str]] = Counter()
    entidades_b: Counter[tuple[str, str]] = Counter()
    viewports: dict[str, tuple[int, int]] = {}
    for nome in original.layouts.names():
        lay_b = _achar_layout(reaberto, nome)
        if lay_b is None:
            continue
        lay_a = original.layouts.get(nome)
        da, db = _ler_layout(lay_a), _ler_layout(lay_b)
        prefixo = "model" if nome.casefold() == "model" else f"layout {nome}"
        dif += _dif_contagem(f"{prefixo}: entidades", da["entidades"], db["entidades"])
        dif += _dif_contagem(f"{prefixo}: texto", da["textos"], db["textos"], 5)
        for chave, n in da["entidades"].items():
            entidades_a[chave] += n
            total_a += n
        for chave, n in db["entidades"].items():
            entidades_b[chave] += n
            total_b += n
        textos_a.update(da["textos"])
        textos_b.update(db["textos"])
        if nome.casefold() != "model":
            va, vb = _viewports(lay_a), _viewports(lay_b)
            viewports[nome] = (len(va), len(vb))
            if len(va) != len(vb):
                dif.append(f"layout {nome!r}: {len(va)} viewports no original, {len(vb)} no DWG")
            elif va != vb:
                dif.append(f"layout {nome!r}: escalas das viewports mudaram {va} -> {vb}")

    ea, eb = _extensao(original), _extensao(reaberto)
    if ea and eb and any(abs(x - y) > TOLERANCIA_M for x, y in zip(ea, eb, strict=True)):
        dif.append(f"extensão do desenho mudou: {tuple(round(v, 3) for v in ea)} -> "
                   f"{tuple(round(v, 3) for v in eb)}")
    if original.header.get("$INSUNITS") != reaberto.header.get("$INSUNITS"):
        dif.append(f"$INSUNITS mudou: {original.header.get('$INSUNITS')} -> "
                   f"{reaberto.header.get('$INSUNITS')}")
    return {
        "confere": not dif, "diferencas": dif,
        "metricas": {"camadas": len(ca), "camadas_no_dwg": len(cb),
                     "blocos": len(ba), "blocos_no_dwg": len(bb),
                     "entidades": total_a, "entidades_no_dwg": total_b,
                     "textos": sum(textos_a.values()), "textos_no_dwg": sum(textos_b.values()),
                     "layouts": len(la), "viewports_por_layout": viewports,
                     "extensao_m": ea, "extensao_no_dwg_m": eb},
    }


def _achar_layout(doc, nome: str):  # noqa: ANN001
    for n in doc.layouts.names():
        if n.casefold() == nome.casefold():
            return doc.layouts.get(n)
    return None


# --- exportação ---------------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def exportar_dwg(dxf: Path, destino: Path, *, tool: Path | None = None,
                 runner: Runner | None = None, sobrescrever: bool = False,
                 conferir: bool = True) -> DwgExport:
    """Converte o DXF para DWG e, por padrão, confere a ida e volta.

    O DWG só é entregue depois de gravado por inteiro; se a conferência divergir o arquivo
    continua entregue, e ``conferencia.confere`` diz o que mudou (decidir é do usuário).
    """
    import ezdxf

    dxf, destino = Path(dxf), Path(destino)
    if not dxf.is_file():
        raise DwgConversionError(f"arquivo não encontrado: {dxf}")
    if destino.suffix.lower() != ".dwg":
        raise DwgConversionError("o destino precisa terminar em .dwg")
    if destino.exists() and not sobrescrever:
        raise DwgConversionError(f"{destino} já existe; use sobrescrever ou escolha outro nome")
    tool = tool or dwg_mod.find_oda()
    if tool is None:
        raise DwgConversionError(
            "ODA File Converter não encontrado. Instale-o (opendesign.com → ODA File "
            f"Converter, aceitando a licença) ou informe o executável em {dwg_mod.ODA_ENV}. "
            + dwg_mod.LICENSE_NOTE)
    executar = runner or dwg_mod._oda_runner
    t0 = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="coscip_dxf2dwg_") as tmp:
        # nome simples na cópia: o conversor trabalha por pasta e não gosta de acentos
        copia = Path(tmp) / "entrada" / "origem.dxf"
        copia.parent.mkdir()
        shutil.copyfile(dxf, copia)
        saida = Path(tmp) / "saida.dwg"
        executar(tool, copia, saida)
        if not saida.exists() or saida.stat().st_size == 0:
            raise DwgConversionError("o conversor não produziu o DWG")
        versao = dwg_mod.dwg_header_version(saida)
        if versao is None:
            raise DwgConversionError("o arquivo produzido não tem cabeçalho de DWG (AC10xx)")
        conferencia: dict[str, Any] = {}
        if conferir:
            volta = Path(tmp) / "volta" / "origem.dwg"
            volta.parent.mkdir()
            shutil.copyfile(saida, volta)
            reaberto_dxf = Path(tmp) / "reaberto.dxf"
            executar(tool, volta, reaberto_dxf)
            if not reaberto_dxf.exists() or reaberto_dxf.stat().st_size == 0:
                raise DwgConversionError("a conferência falhou: o DWG gerado não reabriu")
            conferencia = comparar_desenhos(ezdxf.readfile(dxf), ezdxf.readfile(reaberto_dxf))
        destino.parent.mkdir(parents=True, exist_ok=True)
        parcial = destino.with_name(destino.name + ".tmp")
        shutil.copyfile(saida, parcial)
        parcial.replace(destino)  # só aparece o DWG inteiro
    return DwgExport(
        dxf_path=str(dxf), dxf_sha256=_sha256(dxf), dwg_path=str(destino),
        dwg_sha256=_sha256(destino), dwg_version=versao, tool="ODA File Converter",
        tool_path=str(tool), tool_version=dwg_mod._tool_version(tool),
        seconds=round(time.monotonic() - t0, 2), conferencia=conferencia)


__all__ = ["DwgExport", "comparar_desenhos", "exportar_dwg"]
