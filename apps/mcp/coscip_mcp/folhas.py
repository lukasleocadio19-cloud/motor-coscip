"""Folhas de projeto em paper space e exportação em PDF (frente D3, §9 da arquitetura).

Uma ``folha`` é um layout do DXF (A0 a A4, em mm) com moldura (margens da NBR 10068), marcas de
dobra, o carimbo no formato do CBMERJ (canto inferior direito, 175 x 283 mm em A0 a A2), quadro
de áreas, notas, tabela de revisões, a janela da legenda e uma janela de visualização
(*viewport*) por vista, cada uma numa escala. O
desenho continua no model space, em metros: a vista só escolhe a região e a escala
(``altura da vista em metros = altura no papel em mm × escala / 1000``).

O carimbo segue o de uma prancha aprovada no CBMERJ (título do PSCIP e destinação, CONTEÚDO, Nº DA
PRANCHA, PROPRIETÁRIO, ENDEREÇO, ESCALA/DATA/ÁREA/REVISÃO, as três assinaturas e o espaço de
APROVAÇÃO CORPO DE BOMBEIROS) e leva os dados que o AAST nº 01/2025 (item 3.2) exige em todas as
pranchas: nomes e registros do responsável técnico e do responsável pela arquitetura, cadastro no
CBMERJ e empresa quando houver. O carimbo, as notas e as revisões só levam o que o usuário
informou: nada é inventado; o resumo lista os campos do AAST que ficaram em branco. A folha
sai sempre com o aviso de rascunho sem valor normativo.

``exportar_pdf`` gera o PDF a partir dos layouts (cada vista é renderizada na escala e recortada
na sua janela). Exige o PyMuPDF (extra ``pdf``).
"""

from __future__ import annotations

import math
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

from ezdxf.enums import TextEntityAlignment
from pydantic import BaseModel, ConfigDict, Field

from coscip_mcp import apresentacao

FORMATOS: dict[str, tuple[float, float]] = {  # paisagem: largura x altura, em mm
    "A0": (1189.0, 841.0), "A1": (841.0, 594.0), "A2": (594.0, 420.0),
    "A3": (420.0, 297.0), "A4": (297.0, 210.0)}
# Margens da NBR 10068: 25 mm à esquerda (encadernação); 10 mm nas demais em A0 e A1, 7 mm em
# A2, A3 e A4. Largura da legenda (carimbo): 175 mm em A0 e A1, 178 mm em A2, A3 e A4.
MARGEM_ESQ = 25.0
_MARGEM = {"A0": 10.0, "A1": 10.0, "A2": 7.0, "A3": 7.0, "A4": 7.0}
_CARIMBO_W = {"A0": 175.0, "A1": 175.0, "A2": 178.0, "A3": 178.0, "A4": 178.0}
DOBRA_X, DOBRA_Y = 185.0, 297.0  # marcas de dobra (NBR 13142): faixas de 185 x 297 mm
MARGEM = 10.0  # compatibilidade: margem das versões anteriores
FOLGA = 6.0
GAP = 8.0
FAIXA_TITULO = 12.0  # altura reservada abaixo de cada vista (título e escala)
LINHA = 4.6  # altura de linha das tabelas
AVISO = "RASCUNHO GERADO PELO MOTOR COSCIP - SEM VALOR NORMATIVO"
MM = 72 / 25.4

TITULO_CARIMBO = "PROJETO DE SEGURANÇA CONTRA INCÊNDIO E PÂNICO"
ASSINATURAS = ("PROPRIETÁRIO", "O AUTOR DO LEV. ARQUITETÔNICO",
               "O AUTOR DO PROJETO DE SEGURANÇA")


@dataclass(frozen=True)
class _Carimbo:
    """Alturas das faixas do carimbo (mm, de cima para baixo) e dos textos.

    O completo (A0 a A2) tem as medidas do carimbo de uma prancha aprovada no CBMERJ (planta
    de referência do usuário, 2026): 175 x 283 mm; o compacto (A3 e A4) mantém as faixas com
    alturas menores."""

    titulo: float
    conteudo: float
    proprietario: float
    endereco: float
    dados: float
    assinaturas: float
    aprovacao: float
    base: float
    h_titulo: float = 3.78
    h_rotulo: float = 2.5
    h_valor: float = 3.6
    h_numero: float = 14.78
    w_numero: float = 40.5  # largura da célula "Nº DA PRANCHA"
    linha_assinatura: float = 12.0  # distância do topo de cada faixa de assinatura à linha

    @property
    def altura(self) -> float:
        return (self.titulo + self.conteudo + self.proprietario + self.endereco + self.dados
                + self.assinaturas + self.aprovacao + self.base)


_COMPLETO = _Carimbo(21.8, 27.0, 13.5, 13.4, 10.0, 78.9, 81.0, 37.4, h_numero=13.0)
_COMPACTO = _Carimbo(14.0, 18.0, 10.0, 10.0, 9.0, 51.0, 30.0, 10.0, h_titulo=3.0,
                     h_rotulo=2.0, h_valor=2.8, h_numero=10.0, w_numero=32.0,
                     linha_assinatura=6.5)
_CARIMBO = {"A0": _COMPLETO, "A1": _COMPLETO, "A2": _COMPLETO, "A3": _COMPACTO,
            "A4": _COMPACTO}

Janela4 = Annotated[list[float], Field(min_length=4, max_length=4)]


class FolhaError(ValueError):
    """Erro de uso: a mensagem diz o que corrigir."""


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Vista(_M):
    titulo: str = Field(min_length=1, max_length=80)
    janela: Janela4 | None = Field(default=None, description="[x0, y0, x1, y1] em metros; "
                                   "sem ela, o desenho inteiro com folga")
    escala: int | None = Field(default=None, ge=10, le=1000,
                               description="denominador; sem ele, a escala da planta")


class Selo(_M):
    """Carimbo da prancha. Os campos que o AAST nº 01/2025 do CBMERJ (item 3.2) torna
    obrigatórios em todas as pranchas: responsável legal (``proprietario``), nome completo e
    registro (com o conselho) do responsável técnico (``responsavel_tecnico``,
    ``registro_profissional``) e do responsável pela arquitetura (``autor_levantamento``,
    ``registro_levantamento``), o cadastro no CBMERJ quando houver (``cadastro_cbmerj``) e a
    empresa com o registro quando o RT assina por ela (``empresa``, ``registro_empresa``)."""

    destinacao: str = Field(default="", max_length=80,
                            description="ex. RESIDENCIAL MULTIFAMILIAR: 'DESTINADO À "
                            "EDIFICAÇÃO ...' no título do carimbo")
    obra: str = Field(default="", max_length=160,
                      description="usado no título quando não há destinacao")
    conteudo: list[str] = Field(default_factory=list, max_length=3,
                                description="linhas do CONTEÚDO; sem elas, o título da folha")
    endereco: str = Field(default="", max_length=200)
    proprietario: str = Field(default="", max_length=160,
                              description="responsável legal (pessoa física ou jurídica)")
    autor_projeto: str = Field(default="", max_length=160,
                               description="autor do projeto de segurança (sem RT informado)")
    responsavel_tecnico: str = Field(default="", max_length=160,
                                     description="nome completo do autor do projeto de "
                                     "segurança (responsável técnico)")
    registro_profissional: str = Field(default="", max_length=80,
                                       description="conselho e número, ex. CREA-RJ 0000000")
    cadastro_cbmerj: str = Field(default="", max_length=40)
    empresa: str = Field(default="", max_length=120)
    registro_empresa: str = Field(default="", max_length=60)
    autor_levantamento: str = Field(default="", max_length=160,
                                    description="responsável pela arquitetura (Lev. Arq., "
                                    "PRPA ou PREO)")
    registro_levantamento: str = Field(default="", max_length=80)
    area: str = Field(default="", max_length=30, description="ex. 8.066,00 m²; sem ela, a ATC")
    escala: str = Field(default="", max_length=20,
                        description="sem ela: a escala única das vistas ou INDICADA")
    data: str = Field(default="", max_length=20)
    revisao: str = Field(default="00", max_length=8)


class Quadro(_M):
    """Quadro de texto na coluna do carimbo (ex. o cálculo da largura das saídas, que as
    pranchas de referência trazem ao lado da planta). Cada linha é um item, sem quebra manual."""

    titulo: str = Field(min_length=1, max_length=80)
    linhas: list[str] = Field(min_length=1, max_length=25)


class Revisao(_M):
    rev: str = Field(max_length=8)
    data: str = Field(default="", max_length=20)
    descricao: str = Field(max_length=120)


class Folha(_M):
    """Prancha em paper space: ver o módulo."""

    tipo: Literal["folha"]
    nome: str = Field(pattern=r"^[A-Za-z0-9 _\-]{1,31}$", description="nome do layout no CAD")
    formato: Literal["A0", "A1", "A2", "A3", "A4"] = "A1"
    prancha: str = Field(default="1/1", max_length=10, description="número da folha, ex. 2/3")
    titulo: str = Field(default="", max_length=120, description="título da prancha no carimbo")
    selo: Selo = Field(default_factory=Selo)
    vistas: list[Vista] = Field(min_length=1, max_length=12)
    legenda: Vista | None = Field(default=None, description="tabelas de legenda (operação "
                                  "legenda) no alto da coluna do carimbo; sem janela, a região "
                                  "das tabelas desenhadas")
    notas: list[str] = Field(default_factory=list, max_length=30)
    quadros: list[Quadro] = Field(default_factory=list, max_length=4,
                                  description="quadros de texto na coluna, depois das notas")
    quadro_de_areas: bool = True
    atc_m2: float | None = Field(default=None, gt=0, description="área total construída")
    revisoes: list[Revisao] = Field(default_factory=list, max_length=12)


Extensao = tuple[float, float, float, float]  # x0, y0, x1, y1


def _texto(lay, s: str, x: float, y: float, h: float, *, cor: int = 7,  # noqa: ANN001
           centro: bool = False, direita: bool = False, base_centro: bool = False,
           estilo: str = apresentacao.ESTILO_TEXTO, camada: str = "FOLHA") -> None:
    t = lay.add_text(s, dxfattribs={"layer": camada, "height": h, "color": cor, "style": estilo})
    align = (TextEntityAlignment.MIDDLE_CENTER if centro
             else TextEntityAlignment.BOTTOM_CENTER if base_centro
             else TextEntityAlignment.BOTTOM_RIGHT if direita else TextEntityAlignment.LEFT)
    t.set_placement((x, y), align=align)


def _linha(lay, x0: float, y0: float, x1: float, y1: float, peso: int = 35) -> None:  # noqa: ANN001
    lay.add_line((x0, y0), (x1, y1), dxfattribs={"layer": "FOLHA", "lineweight": peso})


def _retangulo(lay, x0: float, y0: float, x1: float, y1: float, peso: int = 35) -> None:  # noqa: ANN001
    lay.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True,
                       dxfattribs={"layer": "FOLHA", "lineweight": peso})


def _quebrar(s: str, largura_mm: float, h: float, fator: float = 0.64) -> list[str]:
    """Quebra ``s`` em linhas que cabem na largura (Arial: ~0,64 da altura por caractere em
    texto misto; ~0,75 em caixa alta)."""
    cpl = max(8, int(largura_mm / (h * fator)))
    return textwrap.wrap(s, cpl) or [""]


def _caber(s: str, largura_mm: float, h: float) -> float:
    """Altura de texto que faz ``s`` caber em ``largura_mm`` (no máximo ``h``)."""
    return min(h, largura_mm / max(1, len(s) * 0.75))  # caixa alta, Arial


def _escala_texto(escalas: list[int]) -> str:
    return " / ".join(f"1:{e}" for e in sorted(set(escalas), reverse=False))


def _janela_padrao(ext: Extensao | None, folga: float = 1.5) -> Janela4:
    if ext is None:
        raise FolhaError("a planta está vazia: desenhe algo antes de montar a folha")
    return [ext[0] - folga, ext[1] - folga, ext[2] + folga, ext[3] + folga]


def campos_aast_em_branco(s: Selo) -> list[str]:
    """Campos do carimbo exigidos pelo AAST 01/2025 (item 3.2) que ficaram em branco."""
    faltam = []
    for campo, valor in (("proprietario (responsável legal)", s.proprietario),
                         ("responsavel_tecnico", s.responsavel_tecnico or s.autor_projeto),
                         ("registro_profissional (conselho e número)", s.registro_profissional),
                         ("autor_levantamento (responsável pela arquitetura)",
                          s.autor_levantamento),
                         ("registro_levantamento", s.registro_levantamento)):
        if not valor.strip():
            faltam.append(campo)
    if s.empresa and not s.registro_empresa:
        faltam.append("registro_empresa (o RT assina pela empresa)")
    return faltam


def _marcas_de_dobra(lay, W: float, H: float, m: float) -> None:  # noqa: ANN001
    """Marcas de dobra na margem (NBR 13142): a cada 185 mm a partir da direita e a cada
    297 mm a partir de baixo."""
    x = W - DOBRA_X
    while x > MARGEM_ESQ + 1:
        _linha(lay, x, 0.0, x, m, 13)
        _linha(lay, x, H - m, x, H, 13)
        x -= DOBRA_X
    y = DOBRA_Y
    while y < H - 1:
        _linha(lay, 0.0, y, MARGEM_ESQ, y, 13)
        _linha(lay, W - m, y, W, y, 13)
        y += DOBRA_Y


def _vista(v: Vista, ext: Extensao | None, escala_planta: int) -> tuple[float, float, int,
                                                                        Janela4]:
    esc = v.escala or escala_planta
    jan = v.janela or _janela_padrao(ext)
    if not (jan[2] > jan[0] and jan[3] > jan[1]):
        raise FolhaError(f"vista {v.titulo!r}: janela precisa de x1 > x0 e y1 > y0")
    k = 1000.0 / esc
    return (jan[2] - jan[0]) * k, (jan[3] - jan[1]) * k, esc, jan


def _viewport(lay, cx: float, topo: float, w: float, h: float, jan: Janela4) -> None:  # noqa: ANN001
    vp = lay.add_viewport(center=(cx + w / 2, topo - h / 2), size=(w, h),
                          view_center_point=((jan[0] + jan[2]) / 2, (jan[1] + jan[3]) / 2),
                          view_height=(jan[3] - jan[1]))
    vp.dxf.layer = "VIEWPORT"


def montar(doc, folha: Folha, ext: Extensao | None, ambientes: list[dict[str, Any]],  # noqa: ANN001
           escala_planta: int, legenda_ext: Extensao | None = None) -> dict[str, Any]:
    """Cria o layout da folha no ``doc`` e devolve um resumo do que foi montado.
    ``legenda_ext`` é a região das tabelas de legenda: a janela padrão da legenda."""
    W, H = FORMATOS[folha.formato]
    if folha.nome in doc.layout_names():
        raise FolhaError(f"já existe um layout chamado {folha.nome!r}; use outro nome")
    for nome in ("FOLHA", "VIEWPORT"):
        apresentacao.criar_camada(doc, nome)
    lay = doc.layouts.new(folha.nome)
    lay.page_setup(size=(W, H), margins=(0, 0, 0, 0), units="mm")
    m = _MARGEM[folha.formato]
    cw, cb = _CARIMBO_W[folha.formato], _CARIMBO[folha.formato]
    x0, x1, y0, y1 = MARGEM_ESQ, W - m, m, H - m
    xc = x1 - cw  # início da coluna da direita (carimbo e quadros)
    ys = y0 + cb.altura  # topo do carimbo

    _retangulo(lay, x0, y0, x1, y1, 50)
    _linha(lay, xc, y0, xc, y1, 50)
    if folha.formato != "A4":
        _marcas_de_dobra(lay, W, H, m)

    # --- vistas ---------------------------------------------------------------------------
    area_x0, area_x1 = x0 + FOLGA, xc - FOLGA
    area_y0, area_y1 = y0 + FOLGA, y1 - FOLGA
    cx, topo, linha_h = area_x0, area_y1, 0.0
    vistas_out: list[dict[str, Any]] = []
    escalas: list[int] = []
    for v in folha.vistas:
        w, h, esc, jan = _vista(v, ext, escala_planta)
        livre_w, livre_h = area_x1 - area_x0, area_y1 - area_y0 - FAIXA_TITULO
        if w > livre_w + 1e-6 or h > livre_h + 1e-6:
            need = math.ceil(max((jan[2] - jan[0]) * 1000 / livre_w,
                                 (jan[3] - jan[1]) * 1000 / livre_h))
            sug = next((e for e in apresentacao.ESCALAS if e >= need), need)
            raise FolhaError(
                f"vista {v.titulo!r} na escala 1:{esc} mede {w:.0f} x {h:.0f} mm e a área livre "
                f"da {folha.formato} é {livre_w:.0f} x {livre_h:.0f} mm: use 1:{sug} ou um "
                "formato maior")
        if cx + w > area_x1 + 1e-6:  # próxima linha
            cx, topo = area_x0, topo - linha_h - GAP
            linha_h = 0.0
        if topo - h - FAIXA_TITULO < area_y0 - 1e-6:
            raise FolhaError(f"as vistas não cabem na {folha.formato}: reduza a escala de "
                             f"alguma, tire uma vista ou use um formato maior (faltou espaço "
                             f"para {v.titulo!r})")
        _viewport(lay, cx, topo, w, h, jan)
        _titulo_vista(lay, len(vistas_out) + 1, v.titulo.upper(), f"ESCALA 1:{esc}", cx,
                      topo - h)
        vistas_out.append({"titulo": v.titulo, "escala": f"1:{esc}",
                           "janela_m": [round(j, 3) for j in jan],
                           "tamanho_mm": [round(w, 1), round(h, 1)]})
        escalas.append(esc)
        cx += w + GAP
        linha_h = max(linha_h, h + FAIXA_TITULO)

    # --- coluna da direita: legenda, quadro de áreas, notas e revisões ---------------------
    yy = y1
    h_txt = 2.5
    larg = cw - 2 * FOLGA
    legenda_out: dict[str, Any] | None = None
    if folha.legenda is not None:
        v = folha.legenda
        if v.janela is None and legenda_ext is None:
            raise FolhaError("a folha pede a legenda, mas a planta não tem a operação legenda: "
                             "desenhe-a ou informe a janela")
        if v.janela is None and legenda_ext is not None:
            f = 1.0 * (v.escala or escala_planta) / 1000.0  # 1 mm de folga no papel
            v = v.model_copy(update={"janela": [legenda_ext[0] - f, legenda_ext[1] - f,
                                               legenda_ext[2] + f, legenda_ext[3] + f]})
        w, h, esc, jan = _vista(v, ext, escala_planta)
        livre_h = yy - ys - 2 * FOLGA
        if w > larg + 1e-6 or h > livre_h + 1e-6:
            need = math.ceil(max((jan[2] - jan[0]) * 1000 / larg,
                                 (jan[3] - jan[1]) * 1000 / livre_h))
            sug = next((e for e in apresentacao.ESCALAS if e >= need), need)
            raise FolhaError(f"a legenda na escala 1:{esc} mede {w:.0f} x {h:.0f} mm e a coluna "
                             f"do carimbo tem {larg:.0f} x {livre_h:.0f} mm livres: use "
                             f"1:{sug} ou uma janela menor")
        _viewport(lay, xc + (cw - w) / 2, yy - FOLGA, w, h, jan)
        legenda_out = {"escala": f"1:{esc}", "janela_m": [round(j, 3) for j in jan],
                       "tamanho_mm": [round(w, 1), round(h, 1)]}
        yy -= h + 2 * FOLGA
        _linha(lay, xc, yy, x1, yy, 35)

    def titulo_tabela(txt: str) -> None:
        nonlocal yy
        _retangulo(lay, xc, yy - 6.0, x1, yy, 35)
        _texto(lay, txt, xc + FOLGA, yy - 4.2, 3.0)
        yy -= 6.0

    soma = round(sum(a["area_m2"] for a in ambientes), 2)
    if folha.quadro_de_areas and ambientes:
        titulo_tabela("QUADRO DE ÁREAS")
        linhas = [(a["nome"], a["area_m2"]) for a in ambientes]
        extra = 1 + (1 if folha.atc_m2 else 0)
        reserva = (24.0 if folha.notas else 0.0) + (
            len(folha.revisoes) * LINHA + 14.0 if folha.revisoes else 0.0)
        livre = yy - ys - FOLGA - reserva
        passo = min(LINHA, livre / max(1, len(linhas) + extra))
        if passo < 3.0:
            raise FolhaError("o quadro de áreas não cabe na coluna: tire ambientes ou use um "
                             "formato maior")
        for nome, area in linhas:
            _texto(lay, nome[:int(larg / (h_txt * 0.55)) - 9].upper(), xc + FOLGA,
                   yy - passo * 0.72, h_txt)
            _texto(lay, f"{area:.2f} m²".replace(".", ","), x1 - FOLGA, yy - passo * 0.72, h_txt,
                   direita=True)
            yy -= passo
        _linha(lay, xc, yy, x1, yy, 18)
        _texto(lay, "ÁREA ÚTIL TOTAL", xc + FOLGA, yy - passo * 0.72, h_txt)
        _texto(lay, f"{soma:.2f} m²".replace(".", ","), x1 - FOLGA, yy - passo * 0.72, h_txt,
               direita=True)
        yy -= passo
        if folha.atc_m2:
            _texto(lay, "ÁREA CONSTRUÍDA (ATC)", xc + FOLGA, yy - passo * 0.72, h_txt)
            _texto(lay, f"{folha.atc_m2:.2f} m²".replace(".", ","), x1 - FOLGA,
                   yy - passo * 0.72, h_txt, direita=True)
            yy -= passo
        yy -= GAP / 2

    if folha.notas:
        titulo_tabela("NOTAS")
        linhas_n: list[str] = []
        for i, nota in enumerate(folha.notas, 1):
            linhas_n += _quebrar(f"{i}. {nota}", larg, h_txt)
        reserva = (len(folha.revisoes) * LINHA + 14) if folha.revisoes else 0
        cabem = int((yy - ys - FOLGA - reserva) / 3.6)
        if len(linhas_n) > cabem:
            raise FolhaError(f"as notas ocupam {len(linhas_n)} linhas e só cabem {max(cabem, 0)} "
                             f"na coluna da {folha.formato}: encurte as notas ou use um formato "
                             "maior")
        for ln in linhas_n:
            _texto(lay, ln, xc + FOLGA, yy - 3.0, h_txt)
            yy -= 3.6
        yy -= GAP / 2

    for q in folha.quadros:
        titulo_tabela(q.titulo.upper())
        linhas_q: list[str] = []
        for ln in q.linhas:
            linhas_q += _quebrar(f"• {ln}", larg, h_txt)
        reserva = (len(folha.revisoes) * LINHA + 14) if folha.revisoes else 0
        cabem = int((yy - ys - FOLGA - reserva) / 3.6)
        if len(linhas_q) > cabem:
            raise FolhaError(f"o quadro {q.titulo!r} ocupa {len(linhas_q)} linhas e só cabem "
                             f"{max(cabem, 0)} na coluna da {folha.formato}: encurte-o ou use um "
                             "formato maior")
        for ln in linhas_q:
            _texto(lay, ln, xc + FOLGA, yy - 3.0, h_txt)
            yy -= 3.6
        _linha(lay, xc, yy - 1.0, x1, yy - 1.0, 18)
        yy -= GAP / 2

    if folha.revisoes:
        n = len(folha.revisoes)
        topo_rev = ys + FOLGA + LINHA * (n + 1)
        if yy < topo_rev:
            raise FolhaError("a tabela de revisões não cabe na coluna: use um formato maior")
        yr = topo_rev
        _retangulo(lay, xc, yr - LINHA, x1, yr, 35)
        for rx, rt in ((xc + FOLGA, "REV"), (xc + 16, "DATA"), (xc + 38, "DESCRIÇÃO")):
            _texto(lay, rt, rx, yr - LINHA + 1.4, 2.2)
        yr -= LINHA
        for r in folha.revisoes:
            _texto(lay, r.rev, xc + FOLGA, yr - LINHA + 1.4, h_txt)
            _texto(lay, r.data, xc + 16, yr - LINHA + 1.4, h_txt)
            _texto(lay, r.descricao[:int((x1 - xc - 40) / (h_txt * 0.55))], xc + 38,
                   yr - LINHA + 1.4, h_txt)
            _linha(lay, xc, yr - LINHA, x1, yr - LINHA, 13)
            yr -= LINHA

    esc_txt = folha.selo.escala or ((f"1:{escalas[0]}" if len(set(escalas)) == 1
                                     else "INDICADA") if escalas else "")
    _carimbo(lay, folha, cb, xc, x1, y0, ys, esc_txt)
    s = folha.selo

    return {"folha": folha.nome, "formato": folha.formato, "papel_mm": [W, H],
            "vistas": vistas_out, **({"legenda": legenda_out} if legenda_out else {}),
            "ambientes_no_quadro": len(ambientes) if folha.quadro_de_areas else 0,
            "notas": len(folha.notas), "quadros": len(folha.quadros),
            "revisoes": len(folha.revisoes),
            "carimbo": {"modelo": "CBMERJ (PSCIP), " + ("completo 175 x 283 mm"
                                                        if cb is _COMPLETO else
                                                        f"compacto {cw:.0f} x "
                                                        f"{cb.altura:.0f} mm"),
                        "campos_aast_01_2025_em_branco": campos_aast_em_branco(s)}}


def _titulo_vista(lay, n: int, titulo: str, escala: str, x: float,  # noqa: ANN001
                  y_base: float) -> None:
    """Título da vista como nas pranchas de referência: círculo com o número da vista,
    título sublinhado à direita e a escala, menor e em cinza, sob o traço."""
    r = 3.2
    cx, cy = x + r, y_base - 4.0 - r
    lay.add_circle((cx, cy), r, dxfattribs={"layer": "FOLHA", "lineweight": 25})
    _texto(lay, str(n), cx, cy, 3.0, centro=True)
    tx = cx + r + 1.5
    _texto(lay, titulo, tx, cy + 0.9, 3.5)
    larg = max(len(titulo) * 3.5 * 0.72, len(escala) * 2.2 * 0.72) + 2.0
    _linha(lay, cx + r, cy, tx + larg, cy, 25)
    _texto(lay, escala, tx, cy - 3.4, 2.2, cor=8)


def _carimbo(lay, folha: Folha, cb: _Carimbo, xa: float, xb: float,  # noqa: ANN001
             y0: float, ys: float, esc_txt: str) -> None:
    """Carimbo no canto inferior direito, no formato do CBMERJ (ver ``_Carimbo``), com os
    campos do AAST 01/2025, item 3.2. Só leva o que foi informado."""
    s = folha.selo
    w = xb - xa
    hr, hv = cb.h_rotulo, cb.h_valor
    y = ys
    _linha(lay, xa, ys, xb, ys, 50)

    # 1) título
    linha2 = (f"DESTINADO À EDIFICAÇÃO {s.destinacao.upper()}" if s.destinacao
              else s.obra.upper())
    ht = _caber(max(TITULO_CARIMBO, linha2, key=len), w - 6.0, cb.h_titulo)
    _texto(lay, TITULO_CARIMBO, (xa + xb) / 2, y - cb.titulo * 0.39, ht, base_centro=True)
    if linha2:
        _texto(lay, linha2, (xa + xb) / 2, y - cb.titulo * 0.72, ht, base_centro=True)
    y -= cb.titulo
    _linha(lay, xa, y, xb, y)

    # 2) conteúdo | nº da prancha
    xn = xb - cb.w_numero
    _linha(lay, xn, y, xn, y - cb.conteudo)
    _texto(lay, "CONTEÚDO:", xa + 0.6, y - hr * 1.3, hr)
    _texto(lay, "Nº DA PRANCHA:", xn + 0.5, y - hr * 1.0, hr * 0.8)
    linhas = [c.upper() for c in (s.conteudo or [folha.titulo or folha.nome]) if c.strip()]
    quebradas: list[str] = []
    for ln in linhas:
        quebradas += _quebrar(ln, xn - xa - 16.0, hv, 0.75)
    passo = min(hv * 1.9, (cb.conteudo - hr * 2.2) / max(1, len(quebradas)))
    for i, ln in enumerate(quebradas[:4]):
        _texto(lay, ln, xa + 13.7 * cb.titulo / 21.8, y - hr * 2.0 - hv - i * passo,
               min(hv, passo / 1.5))
    num, _, tot = folha.prancha.partition("/")
    num = num.strip().zfill(2) if num.strip().isdigit() else num.strip()
    _texto(lay, num, xb - 9.4 * cb.w_numero / 40.5, y - cb.conteudo + cb.conteudo * 0.17,
           cb.h_numero, direita=True)
    if tot.strip():
        _texto(lay, f"DE {tot.strip().zfill(2)}", xn + 1.5, y - cb.conteudo + 1.8, hr * 0.8)
    y -= cb.conteudo
    _linha(lay, xa, y, xb, y)

    # 3) proprietário e 4) endereço
    for rotulo, valor, alt in (("PROPRIETÁRIO:", s.proprietario, cb.proprietario),
                               ("ENDEREÇO:", s.endereco, cb.endereco)):
        _texto(lay, rotulo, xa + 1.1, y - hr * 1.3, hr * 1.06)
        if valor:
            _texto(lay, valor.upper(), xa + 4.0, y - alt + alt * 0.27,
                   _caber(valor, w - 6.0, hv))
        y -= alt
        _linha(lay, xa, y, xb, y)

    # 5) escala | data | área | revisão
    area = s.area or (f"{folha.atc_m2:,.2f} m²".replace(",", "X").replace(".", ",")
                      .replace("X", ".") if folha.atc_m2 else "")
    xs = [xa + w * f for f in (0.0, 0.25, 0.5, 0.75, 1.0)]
    for i, (rot, val) in enumerate((("ESCALA:", esc_txt), ("DATA:", s.data), ("ÁREA:", area),
                                    ("REVISÃO:", s.revisao))):
        if i:
            _linha(lay, xs[i], y, xs[i], y - cb.dados)
        _texto(lay, rot, xs[i] + 0.4, y - hr * 1.35, hr * 0.9)
        if val:
            # o valor não pode subir até o rótulo (ESCALA: x INDICADA encostavam)
            teto = cb.dados - hr * 1.35 - 0.45 * hr * 0.9 - 0.8 - cb.dados * 0.18
            _texto(lay, val, (xs[i] + xs[i + 1]) / 2, y - cb.dados + cb.dados * 0.18,
                   min(_caber(val, w / 4 - 3.0, hv * 0.97), max(teto, 1.5)), base_centro=True)
    y -= cb.dados
    _linha(lay, xa, y, xb, y)

    # 6) assinaturas: linha, função e, abaixo, nome e registro (AAST 01/2025, 3.2)
    nome_rt = s.responsavel_tecnico or s.autor_projeto
    rt_reg = " - ".join(t for t in (s.registro_profissional,
                                    f"CBMERJ {s.cadastro_cbmerj}" if s.cadastro_cbmerj
                                    else "") if t)
    empresa = " - ".join(t for t in (s.empresa, s.registro_empresa) if t)
    blocos = ((ASSINATURAS[0], [s.proprietario]),
              (ASSINATURAS[1], [s.autor_levantamento, s.registro_levantamento]),
              (ASSINATURAS[2], [nome_rt, rt_reg, f"EMPRESA: {empresa}" if empresa else ""]))
    hb = cb.assinaturas / 3
    la, lb = xa + w * 0.14, xb - w * 0.118
    for i, (funcao, dados) in enumerate(blocos):
        yl = y - i * hb - cb.linha_assinatura
        _linha(lay, la, yl, lb, yl, 25)
        _texto(lay, funcao, la, yl - hr * 1.3, hr * 0.9)
        dados_ok = [d for d in dados if d]
        passo = min(hr * 1.45, (hb - cb.linha_assinatura - hr * 1.8) / max(1, len(dados_ok)))
        for j, d in enumerate(dados_ok):
            _texto(lay, d.upper() if j == 0 else d, la, yl - hr * 1.3 - (j + 1) * passo,
                   _caber(d, lb - la, min(hr * 0.95, passo * 0.8)))
    y -= cb.assinaturas
    _linha(lay, xa, y, xb, y)

    # 7) aprovação do Corpo de Bombeiros (em branco) e 8) faixa livre
    _texto(lay, "APROVAÇÃO CORPO DE BOMBEIROS:", xa + 0.8, y - hr * 1.6, hr * 0.95)
    y -= cb.aprovacao
    _linha(lay, xa, y, xb, y)
    # 8) faixa livre de baixo: o aviso de rascunho do motor (fora da margem, onde ficam as
    #    marcas de dobra)
    aviso = (AVISO + " - REQUER CONFERÊNCIA DO RESPONSÁVEL TÉCNICO" if s.responsavel_tecnico
             else AVISO + " - SEM RESPONSÁVEL TÉCNICO")
    ha = min(2.5, cb.base / 4)
    linhas_aviso = _quebrar(aviso, w - 4.0, ha, 0.78)
    for i, ln in enumerate(linhas_aviso):
        _texto(lay, ln, xa + 2.0, y - ha * 1.6 - i * ha * 1.5, ha, cor=1)


# --- PDF ------------------------------------------------------------------------------------


def _render_pdf(doc, lay, caixa: Extensao, mm_por_m: float) -> bytes:  # noqa: ANN001
    """PDF vetorial só da região ``caixa`` do layout ``lay`` (x0, y0, x1, y1), na escala dada: a
    página do PDF tem exatamente o tamanho da região em mm, com o canto inferior esquerdo da caixa
    no canto inferior esquerdo da página. (``draw_layout`` e não ``draw_entities``: só ele define
    o fundo branco e a cor 7 como preta.)"""
    from ezdxf.addons.drawing import Frontend, RenderContext, layout
    from ezdxf.addons.drawing import pymupdf as ezpdf
    from ezdxf.addons.drawing.config import BackgroundPolicy, Configuration
    from ezdxf.math import BoundingBox2d

    x0, y0, x1, y1 = caixa
    be = ezpdf.PyMuPdfBackend()
    Frontend(RenderContext(doc), be, config=Configuration(
        background_policy=BackgroundPolicy.WHITE)).draw_layout(lay)
    page = layout.Page((x1 - x0) * mm_por_m, (y1 - y0) * mm_por_m, layout.Units.mm)
    settings = layout.Settings(scale=mm_por_m, fit_page=False, crop_at_margins=True,
                               page_alignment=layout.PageAlignment.BOTTOM_LEFT)
    return be.get_pdf_bytes(page, settings=settings,
                            render_box=BoundingBox2d([(x0, y0), (x1, y1)]))


def exportar_pdf(dxf: Path, destino: Path, folhas: list[str] | None = None) -> dict[str, Any]:
    """Gera o PDF das folhas (layouts com viewport) do DXF. Uma página por folha."""
    try:
        import pymupdf
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise FolhaError("exportar PDF exige o PyMuPDF (pip install pymupdf; extra 'pdf')") from exc
    import ezdxf
    from ezdxf import bbox

    base = ezdxf.readfile(dxf)
    nomes = [n for n in base.layout_names() if n != "Model"]
    if folhas:
        faltam = [n for n in folhas if n not in nomes]
        if faltam:
            raise FolhaError(f"folha(s) inexistente(s): {faltam}; há {nomes}")
        nomes = [n for n in nomes if n in folhas]
    nomes = [n for n in nomes if any(e.dxftype() == "VIEWPORT" and e.dxf.id != 1
                                      for e in base.layouts.get(n))]
    if not nomes:
        raise FolhaError("o DXF não tem folha montada (operação 'folha'): nada a exportar")
    out = pymupdf.open()
    for nome in nomes:
        doc = ezdxf.readfile(dxf)
        lay = doc.layouts.get(nome)
        W, H = float(lay.dxf.paper_width), float(lay.dxf.paper_height)
        vps = [e for e in lay if e.dxftype() == "VIEWPORT"]
        dados = [(vp.dxf.center.x, vp.dxf.center.y, vp.dxf.width, vp.dxf.height,
                  vp.dxf.view_center_point.x, vp.dxf.view_center_point.y, vp.dxf.view_height)
                 for vp in vps if vp.dxf.id != 1]
        for vp in vps:
            lay.delete_entity(vp)
        pagina = out.new_page(width=W * MM, height=H * MM)
        # 1) moldura, selo, quadros e textos da folha (paper space, em mm); o PDF dessa camada
        #    tem fundo branco, por isso vai por baixo e as vistas por cima
        if len(lay):
            src = pymupdf.open(stream=_render_pdf(doc, lay, (0.0, 0.0, W, H), 1.0),
                               filetype="pdf")
            pagina.show_pdf_page(pymupdf.Rect(0, 0, W * MM, H * MM), src, 0)
        # 2) cada vista: o desenho do model space na escala da janela, recortado nela
        for cx, cy, w, h, mx, my, vh in dados:
            k = h / vh  # mm de papel por metro
            mw = w / k
            win = (mx - mw / 2, my - vh / 2, mx + mw / 2, my + vh / 2)
            vdoc = ezdxf.readfile(dxf)  # cópia só desta vista: o model space é podado
            msp = vdoc.modelspace()
            for e in list(msp):
                try:
                    ex = bbox.extents([e])
                except Exception:  # noqa: BLE001 - entidade sem geometria
                    msp.delete_entity(e)
                    continue
                if not ex.has_data or (ex.extmax.x < win[0] or ex.extmin.x > win[2]
                                       or ex.extmax.y < win[1] or ex.extmin.y > win[3]):
                    msp.delete_entity(e)
            if not len(msp):
                continue
            src = pymupdf.open(stream=_render_pdf(vdoc, msp, win, k), filetype="pdf")
            rect = pymupdf.Rect((cx - w / 2) * MM, (H - cy - h / 2) * MM,
                                (cx + w / 2) * MM, (H - cy + h / 2) * MM)
            pagina.show_pdf_page(rect, src, 0)
    out.set_metadata({"title": "Folhas do projeto (rascunho sem valor normativo)",
                      "producer": "motor COSCIP"})
    destino.parent.mkdir(parents=True, exist_ok=True)
    out.save(destino, deflate=True)
    return {"arquivo": str(destino), "paginas": nomes}
