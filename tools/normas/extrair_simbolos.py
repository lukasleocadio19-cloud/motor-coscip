"""Desenhos oficiais das NTs (NT 1-03, Anexo A; NT 2-05, Anexo B) extraídos dos PDFs e vetorizados.

Os símbolos e as placas das NTs são **imagens raster** embutidas no PDF (placas de ~275 px,
símbolos de ~110 px), sem perda. Este script:

1. confere o SHA-256 do PDF contra o manifesto (``normative/manifests/base.yaml``);
2. extrai as imagens originais (não o JPG da página) e as associa ao código da placa (NT 2-05)
   ou à ordem e ao nome da linha da tabela (NT 1-03);
3. vetoriza cada uma (``tools.normas.vetorizar``): a placa em regiões de cor chapada sobre um
   fundo; o símbolo de projeto em regiões de tinta (preto), que herdam a cor da camada;
4. grava ``apps/mcp/coscip_mcp/simbolos_nt.json``, que o catálogo do MCP usa no lugar das
   aproximações desenhadas à mão.

Não baixa nada: recebe os PDFs oficiais já baixados (URLs no manifesto); o SHA-256 é conferido.

    python -m tools.normas.extrair_simbolos --pdf-1-03 NT1-03.pdf --pdf-2-05 NT2-05.pdf
        [--revisao pasta]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import numpy as np
import pymupdf
import yaml

from tools.normas.manifesto import MANIFESTO
from tools.normas.vetorizar import Poligono, vetorizar_campo

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "apps" / "mcp" / "coscip_mcp" / "simbolos_nt.json"
CODIGO = re.compile(r"^[PAMSE]-?\d{1,2}(?:-[DE])?$")
MINIMO_PX = 20  # imagens menores são enfeite de página
MARCA_DAGUA_PX = 700  # a marca-d'água do CBMERJ tem 787 px


@dataclass
class Item:
    chave: str  # código (NT 2-05) ou "p<pagina>#<ordem>" (NT 1-03)
    pagina: int
    xref: int
    rgb: np.ndarray  # (h, w, 3) float
    rotulo: str = ""  # nome lido na linha da tabela (NT 1-03)


def _fonte(documento: str) -> dict[str, Any]:
    dados = yaml.safe_load(MANIFESTO.read_text(encoding="utf-8"))
    return next(f for f in dados["fontes"] if f["documento"] == documento)


def abrir_pdf(caminho: Path, documento: str) -> pymupdf.Document:
    fonte = _fonte(documento)
    digest = hashlib.sha256(caminho.read_bytes()).hexdigest()
    if digest != fonte["sha256_pdf"]:
        raise SystemExit(f"{documento}: SHA-256 {digest[:12]}… ≠ o do manifesto "
                         f"{fonte['sha256_pdf'][:12]}… (edição mudou?)")
    return pymupdf.open(caminho)


def _imagem(doc: pymupdf.Document, xref: int) -> np.ndarray:
    pm = pymupdf.Pixmap(doc, xref)
    if pm.n >= 4 and not pm.alpha:
        pm = pymupdf.Pixmap(pymupdf.csRGB, pm)
    arr = np.frombuffer(pm.samples, np.uint8).reshape(pm.h, pm.w, pm.n)[..., :3]
    return arr.astype(float)


def _normaliza_codigo(w: str) -> str:
    m = re.match(r"^([PAMSE])-?(\d{1,2})(-[DE])?$", w)
    assert m
    return f"{m.group(1)}-{m.group(2)}{m.group(3) or ''}"


def itens_nt205(doc: pymupdf.Document) -> list[Item]:
    """Placas por código; várias imagens no mesmo código viram ``S-17``, ``S-17#2``..."""
    itens: list[Item] = []
    for n in range(1, len(doc) + 1):
        pag = doc[n - 1]
        codigos = [(_normaliza_codigo(w[4]), (w[1] + w[3]) / 2) for w in pag.get_text("words")
                   if w[0] < 90 and CODIGO.match(w[4])]
        if not codigos:
            continue
        por_codigo: dict[str, list[tuple[float, int]]] = {}
        for im in pag.get_image_info(xrefs=True):
            if min(im["width"], im["height"]) < MINIMO_PX or im["width"] > MARCA_DAGUA_PX:
                continue
            yc = (im["bbox"][1] + im["bbox"][3]) / 2
            cod = min(codigos, key=lambda c: abs(c[1] - yc))[0]
            por_codigo.setdefault(cod, []).append((yc, im["xref"]))
        for cod, lista in por_codigo.items():
            for k, (_, xref) in enumerate(sorted(lista)):
                itens.append(Item(cod if k == 0 else f"{cod}#{k + 1}", n, xref,
                                  _imagem(doc, xref)))
    return itens


DPI_CELULA = 600  # resolução da célula renderizada (a imagem embutida tem ~110 px por ~60 pt)


def _regua_horizontal(pag: pymupdf.Page) -> list[tuple[float, float, float]]:
    """(y, x0, x1) das linhas horizontais longas desenhadas em vetor (bordas da tabela)."""
    out: set[tuple[float, float, float]] = set()
    for dr in pag.get_drawings():
        for it in dr["items"]:
            if it[0] == "l" and abs(it[1].y - it[2].y) < 0.3 and abs(it[1].x - it[2].x) > 100:
                out.add((round(it[1].y, 1), round(min(it[1].x, it[2].x)),
                         round(max(it[1].x, it[2].x))))
            elif it[0] == "re" and it[1].height < 1.5 and it[1].width > 100:
                out.add((round(it[1].y0, 1), round(it[1].x0), round(it[1].x1)))
    return sorted(out)


def _celula(pag: pymupdf.Page, clip: pymupdf.Rect) -> np.ndarray:
    """Renderiza só o desenho da célula (sem a marca-d'água do CBMERJ), em cinza 0..255."""
    pm = pag.get_pixmap(dpi=DPI_CELULA, clip=clip, colorspace=pymupdf.csGRAY, alpha=False)
    return np.frombuffer(pm.samples, np.uint8).reshape(pm.h, pm.w).astype(float)


def itens_nt103(doc: pymupdf.Document) -> list[Item]:
    """Símbolos de projeto por linha da tabela: o nome (coluna da esquerda) e o desenho da célula
    (coluna da direita) renderizado em alta resolução. Renderizar a célula, em vez de pegar a
    imagem embutida, junta o que o anexo mistura: imagem mais traços vetoriais (hidrante
    urbano), e desenhos que são só vetor (parede, hidrante subterrâneo)."""
    itens: list[Item] = []
    for n in range(1, len(doc) + 1):
        pag = doc[n - 1]
        regua = [r for r in _regua_horizontal(pag) if r[1] > 250]  # coluna do símbolo
        if len(regua) < 2:
            continue
        x0, x1 = min(r[1] for r in regua), max(r[2] for r in regua)
        ys = sorted({r[0] for r in regua})
        for im in pag.get_image_info(xrefs=True):  # sem a marca-d'água ao renderizar
            if im["width"] > MARCA_DAGUA_PX:
                pag.delete_image(im["xref"])
        palavras = [w for w in pag.get_text("words") if 130 < w[0] and w[2] < x0 + 2]
        for k, (ya, yb) in enumerate(zip(ys, ys[1:], strict=False)):
            if yb - ya < 20:
                continue
            nome = " ".join(w[4] for w in sorted(
                (w for w in palavras if ya < (w[1] + w[3]) / 2 < yb),
                key=lambda w: (round(w[1] / 4), w[0])))
            clip = pymupdf.Rect(x0 + 2.5, ya + 2.5, x1 - 2.5, yb - 2.5)
            cinza = _celula(pag, clip)
            itens.append(Item(f"p{n}#{k + 1}", n, 0, np.stack([cinza] * 3, axis=2), nome))
    return itens


# --- vetorização ---------------------------------------------------------------------------------


def _paleta(rgb: np.ndarray, minimo: float = 0.012, fusao: float = 45.0) -> list[np.ndarray]:
    """Cores chapadas da imagem (maiores que ``minimo`` da área), da mais para a menos usada."""
    q = (rgb.reshape(-1, 3) // 8 * 8 + 4).astype(int)
    cores, cont = np.unique(q, axis=0, return_counts=True)
    paleta: list[np.ndarray] = []
    for i in np.argsort(-cont):
        if cont[i] < minimo * q.shape[0]:
            break
        c = cores[i].astype(float)
        if all(np.linalg.norm(c - p) > fusao for p in paleta):
            paleta.append(c)
    return paleta


def _regioes_placa(rgb: np.ndarray) -> list[dict[str, Any]]:
    """Fundo = cor mais usada (retângulo inteiro); as outras viram polígonos por cima."""
    paleta = _paleta(rgb)
    regioes: list[dict[str, Any]] = []
    if min(paleta[0]) >= 225:  # fundo branco (placas de alerta): fica transparente
        cores = paleta[1:]
    else:
        regioes.append({"cor": [int(v) for v in paleta[0]], "base": True})
        cores = paleta[1:]
    for c in cores:
        outras = [p for p in paleta if p is not c]
        raio = min(np.linalg.norm(c - p) for p in outras)
        campo = np.clip(1.0 - np.linalg.norm(rgb - c, axis=2) / raio, 0.0, 1.0)
        regioes.append({"cor": [int(v) for v in c], "poligonos": vetorizar_campo(
            campo, nivel=0.5, ampliacao=3, tolerancia_px=0.35)})
    return regioes


def _regioes_tinta(rgb: np.ndarray) -> list[dict[str, Any]]:
    """Região de tinta: escuro sobre papel branco (255); traços finos em cinza também contam."""
    campo = np.clip((255.0 - rgb.mean(axis=2)) / 255.0, 0.0, 1.0)
    return [{"cor": None, "poligonos": vetorizar_campo(campo, nivel=0.3, ampliacao=1,
                                                       suavizar=0.6, tolerancia_px=0.7)}]


def _normalizar(regioes: list[dict[str, Any]], largura_px: int, altura_px: int,
                por_caixa: bool) -> dict[str, Any]:
    """Coordenadas do símbolo: centro na origem, y para cima, maior dimensão = 1."""
    todos = [p for r in regioes for pol in r.get("poligonos", []) for p in pol[0]]
    if por_caixa and todos:
        xs, ys = [p[0] for p in todos], [p[1] for p in todos]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    else:
        x0, x1, y0, y1 = 0.0, float(largura_px), 0.0, float(altura_px)
    escala = 1.0 / max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    def anel(a: list[tuple[float, float]]) -> list[float]:
        out: list[float] = []
        for x, y in a:
            out += [round((x - cx) * escala, 4), round(-(y - cy) * escala, 4)]
        return out

    saida = []
    for r in regioes:
        if r.get("base"):
            saida.append({"cor": r["cor"], "base": True})
            continue
        pols: list[Poligono] = r["poligonos"]
        saida.append({"cor": r["cor"],
                      "poligonos": [{"ext": anel(e), "furos": [anel(f) for f in fs]}
                                    for e, fs in pols]})
    return {"proporcao": [round((x1 - x0) * escala, 4), round((y1 - y0) * escala, 4)],
            "regioes": saida}


def vetorizar_placa(item: Item) -> dict[str, Any]:
    h, w = item.rgb.shape[:2]
    return _normalizar(_regioes_placa(item.rgb), w, h, por_caixa=False)


def vetorizar_simbolo(item: Item) -> dict[str, Any]:
    h, w = item.rgb.shape[:2]
    return _normalizar(_regioes_tinta(item.rgb), w, h, por_caixa=True)


# --- associação aos ids do catálogo ------------------------------------------------------------


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]+", " ", s).strip()


def _parecenca(nome: str, linha: str) -> float:
    a, b = _norm(nome), _norm(linha)
    if not b:
        return 0.0
    if a == b:
        return 1.0
    return 0.97 if a in b else SequenceMatcher(None, a, b).ratio()


def associar_nt103(itens: list[Item]) -> tuple[dict[str, Item], list[str]]:
    """Imagens da NT 1-03 aos ids do catálogo, pelo nome da linha (e pela ordem nos empates).

    Nem todo símbolo do anexo é imagem (paredes e elevador são desenhos vetoriais) e alguns
    passam de uma página para a outra: a associação é global, por parecença de nome. O que não
    casar fica com o desenho antigo do catálogo e é listado nos avisos.
    """
    from scipy.optimize import linear_sum_assignment

    sys.path.insert(0, str(RAIZ / "apps" / "mcp"))
    from coscip_mcp import simbologia

    entradas = [e for e in simbologia.CATALOGO.values() if e.fonte == simbologia.P1_03]
    custo = np.full((len(entradas), len(itens)), 1.0)
    for i, e in enumerate(entradas):
        for j, it in enumerate(itens):
            sim = _parecenca(e.nome, it.rotulo)
            # nomes iguais em páginas e linhas diferentes (portátil x sobre rodas): a ordem decide
            custo[i, j] = (1.0 - sim) + 0.002 * abs(i - j) + (0.0 if e.pagina == it.pagina
                                                              else 0.01)
    linhas, colunas = linear_sum_assignment(custo)
    out: dict[str, Item] = {}
    avisos: list[str] = []
    for i, j in zip(linhas, colunas, strict=True):
        e, it = entradas[i], itens[j]
        if _parecenca(e.nome, it.rotulo) < 0.75:
            continue
        out[e.id] = it
    usados = {it.chave for it in out.values()}
    for e in entradas:
        if e.id not in out:
            avisos.append(f"sem imagem no PDF (fica o desenho antigo): {e.id} ({e.nome})")
    for it in itens:
        if it.chave not in usados:
            avisos.append(f"imagem sem entrada no catálogo: {it.chave} {it.rotulo!r}")
    return out, avisos


# --- principal ----------------------------------------------------------------------------------


def gerar(pdf_103: Path, pdf_205: Path, revisao: Path | None = None) -> dict[str, Any]:
    d103, d205 = abrir_pdf(pdf_103, "NT 1-03"), abrir_pdf(pdf_205, "NT 2-05")
    placas_it = itens_nt205(d205)
    simbolos, avisos = associar_nt103(itens_nt103(d103))
    dados: dict[str, Any] = {
        "versao": 1,
        "aviso": "Desenhos extraídos dos PDFs oficiais do CBMERJ e vetorizados por "
                 "tools/normas/extrair_simbolos.py; rascunho sem valor normativo.",
        "fontes": {"NT 1-03": {"sha256_pdf": _fonte("NT 1-03")["sha256_pdf"],
                               "edicao": _fonte("NT 1-03")["edicao"]},
                   "NT 2-05": {"sha256_pdf": _fonte("NT 2-05")["sha256_pdf"],
                               "edicao": _fonte("NT 2-05")["edicao"]}},
        "placas": {}, "simbolos": {}, "avisos": avisos,
    }
    for it in placas_it:
        v = vetorizar_placa(it)
        dados["placas"][it.chave] = {"pagina": it.pagina, "xref": it.xref, **v}
        if revisao:
            _folha(revisao, f"placa-{it.chave}", it, v)
    for id_, it in simbolos.items():
        v = vetorizar_simbolo(it)
        dados["simbolos"][id_] = {"pagina": it.pagina, "xref": it.xref, "linha": it.rotulo, **v}
        if revisao:
            _folha(revisao, f"simbolo-{id_}", it, v)
    return dados


def _folha(pasta: Path, nome: str, it: Item, v: dict[str, Any]) -> None:
    """Imagem lado a lado (original | vetorizada) para conferência visual."""
    from PIL import Image, ImageDraw

    pasta.mkdir(parents=True, exist_ok=True)
    h, w = it.rgb.shape[:2]
    k = 2 if max(w, h) < 400 else 400 / max(w, h)
    pw, ph = int(w * k), int(h * k)
    tela = Image.new("RGB", (pw * 2 + 10, ph), (255, 255, 255))
    tela.paste(Image.fromarray(it.rgb.astype(np.uint8)).resize((pw, ph)), (0, 0))
    dr = ImageDraw.Draw(tela)
    px_, py_ = v["proporcao"]
    esc = min(pw / px_, ph / py_)  # coordenadas normalizadas (maior dimensão = 1) -> painel
    ox, oy = pw + 10 + pw / 2, ph / 2
    for r in v["regioes"]:
        cor = tuple(r["cor"]) if r["cor"] else (0, 0, 0)
        if r.get("base"):
            dr.rectangle([pw + 10, 0, pw * 2 + 10, ph], fill=cor)
            continue
        for pol in r["poligonos"]:
            dr.polygon([(ox + pol["ext"][i] * esc, oy - pol["ext"][i + 1] * esc)
                        for i in range(0, len(pol["ext"]), 2)], fill=cor)
            for f in pol["furos"]:  # furo: devolve a cor de baixo (fundo da placa ou papel)
                fundo = next((tuple(x["cor"]) for x in v["regioes"] if x.get("base")),
                             (255, 255, 255))
                dr.polygon([(ox + f[i] * esc, oy - f[i + 1] * esc) for i in range(0, len(f), 2)],
                           fill=fundo)
    tela.save(pasta / f"{re.sub(r'[^A-Za-z0-9#_-]+', '_', nome)}.png")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pdf-1-03", type=Path, required=True)
    ap.add_argument("--pdf-2-05", type=Path, required=True)
    ap.add_argument("--saida", type=Path, default=SAIDA)
    ap.add_argument("--revisao", type=Path, help="pasta para as imagens de conferência")
    a = ap.parse_args(argv)
    dados = gerar(a.pdf_1_03, a.pdf_2_05, a.revisao)
    a.saida.write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")),
                       encoding="utf-8")
    print(f"gravado: {a.saida} ({a.saida.stat().st_size // 1024} KB): "
          f"{len(dados['placas'])} placas, {len(dados['simbolos'])} símbolos")
    for av in dados["avisos"]:
        print("AVISO", av)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
