"""Detalhes de instalação das medidas de segurança (frente G, 13/11/2026).

Cada detalhe é desenhado em tamanho real (metros) numa região própria do model space, com textos
e cotas na escala do detalhe (1:20 a 1:50), e traz as notas com a origem de cada número. As
medidas normativas saem de ``normative/projeto/parametros.yaml`` (ids ``det.*``), cuja citação é
conferida no texto da NT ao carregar: se não conferir, o detalhe é recusado. O que a norma da base
não fixa (altura do bloco autônomo e do abrigo, fluxo luminoso, dimensão da placa) é informado
pelo usuário e sai como dado informado.

Modelos:

- ``extintor``: vistas frontal e lateral (alça, parte inferior, suporte, placa E-5 no nível
  superior) e, nas indústrias e depósitos, a área de piso pintada (NT 2-01, 5.2.1 e 6.12).
- ``abrigo_mangueira``: elevação com porta de vidro e inscrição INCÊNDIO, corte com registro
  globo angular, junta storz e redução, mangueira e esguicho, placa E-7 e a área de piso de
  1 x 1 m na rede preventiva (NT 2-02, 5.3 e Tabela 1).
- ``recalque_passeio``: corte e planta da caixa no passeio (dimensões pelo risco, profundidade,
  rebordo, saída a 45°, registro, storz e tampão; duplo a partir de 400 L/min) (NT 2-02, 5.2).
- ``recalque_fachada``: elevação e corte do abrigo na fachada (altura de 1 a 1,2 m, saída a 45°
  voltada para a rua) (NT 2-02, 5.2.2 e 5.2.3).
- ``bloco_autonomo``: vistas lateral e frontal com a altura informada e a autonomia da NT 2-06.
- ``sinalizacao_saida``: placa sobre a porta, placa na parede (nível superior) e sinalização
  de nível inferior (NT 2-05, 4.5, 4.7 e Anexo B).
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any, Literal

from ezdxf.enums import TextEntityAlignment
from pydantic import BaseModel, ConfigDict, Field

from coscip_mcp import apresentacao
from coscip_mcp import equipamentos as eq

Modelo = Literal["extintor", "abrigo_mangueira", "recalque_passeio", "recalque_fachada",
                 "bloco_autonomo", "sinalizacao_saida", "central_glp", "regulador_1_estagio",
                 "regulador_2_estagio"]
Risco = Literal["PEQUENO", "MEDIO_1", "MEDIO_2", "GRANDE"]
REDE = ("MEDIO_2", "GRANDE")

CAMADAS = ("DETALHE", "DETALHE_AUX", "DETALHE_INC", "DETALHE_ILUM", "DETALHE_SINAL",
           "DETALHE_COTA", "DETALHE_TEXTO", "DETALHE_HACH", "DETALHE_GLP")

TITULOS = {
    "extintor": "DETALHE - INSTALAÇÃO DO EXTINTOR",
    "abrigo_mangueira": "DETALHE - ABRIGO DE MANGUEIRAS",
    "recalque_passeio": "DETALHE - HIDRANTE DE RECALQUE NO PASSEIO",
    "recalque_fachada": "DETALHE - HIDRANTE DE RECALQUE NA FACHADA",
    "bloco_autonomo": "DETALHE - BLOCO AUTÔNOMO DE ILUMINAÇÃO",
    "sinalizacao_saida": "DETALHE - INSTALAÇÃO DA SINALIZAÇÃO",
    "central_glp": "DETALHE - CENTRAL DE GLP",
    "regulador_1_estagio": "DETALHE - REGULADOR DE 1º ESTÁGIO",
    "regulador_2_estagio": "DETALHE - REGULADOR DE 2º ESTÁGIO",
}
ESCALA_PADRAO = {"extintor": 15, "abrigo_mangueira": 20, "recalque_passeio": 10,
                 "recalque_fachada": 20, "bloco_autonomo": 20, "sinalizacao_saida": 25,
                 "central_glp": 25, "regulador_1_estagio": 10, "regulador_2_estagio": 10}


class DetalheError(ValueError):
    """Erro de uso: a mensagem diz o que corrigir."""


class Detalhe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["detalhe"]
    modelo: Modelo
    x: float = Field(description="canto inferior esquerdo do detalhe no model space (m)")
    y: float
    escala: int | None = Field(default=None, ge=10, le=100,
                               description="escala de impressão do detalhe (texto e cotas)")
    titulo: str = Field(default="", max_length=80, description="sem ele, o título do modelo")
    risco: Risco | None = Field(default=None, description="classificação de risco dos hidrantes "
                                "(abrigo e recalque): define dimensões e diâmetros")
    vazao_lpm: float | None = Field(default=None, gt=0, le=20000,
                                    description="vazão do sistema: recalque duplo se >= 400")
    agente: str = Field(default="PQS ABC 6 kg", max_length=40,
                        description="extintor: tipo e capacidade escritos no detalhe")
    placa_mm: str = Field(default="", pattern=r"^(|\d{2,4}x\d{2,4})$",
                          description="dimensão da placa desenhada, L x H em mm (a das chamadas "
                          "da planta, NT 2-05 Tabela 7)")
    montagem: Literal["parede", "piso", "ambos"] = Field(
        default="ambos", description="extintor: na parede (suporte), no piso (suporte de piso) "
        "ou as duas vistas")
    extintor_m: tuple[float, float] | None = Field(
        default=None, description="extintor: Ø e altura até a alavanca (m) do modelo adotado; "
        "sem ele, tamanho aproximado de catálogo pelo agente")
    recipiente: str = Field(default="P-13", max_length=6,
                            description="central de GLP: P-13, P-20, P-45, P-90 ou P-190")
    recipientes: int | None = Field(default=None, ge=1, le=40,
                                    description="central de GLP: quantidade de recipientes")
    abrigo_m: tuple[float, float] | None = Field(
        default=None, description="central de GLP: largura e profundidade internas do abrigo; "
        "sem elas, o mínimo para a disposição dos recipientes")
    bitola_rede: str = Field(default="", max_length=12, description='GLP: ex. 3/4"')
    bitola_regulador: str = Field(default="", max_length=12, description='GLP: ex. 1/2"')
    piso_demarcado: bool = Field(default=False, description="extintor: área de piso pintada "
                                 "(indústrias, depósitos, galpões, oficinas — NT 2-01, 6.12)")
    base_m: float | None = Field(default=None, gt=0, le=3.0,
                                 description="abrigo de mangueiras: altura da base do abrigo "
                                 "ao piso, informada")
    altura_m: float | None = Field(default=None, gt=0, le=8.0,
                                   description="bloco autônomo: altura da base ao piso; recalque "
                                   "na fachada: altura da saída (1,0 a 1,2 m)")
    pe_direito_m: float | None = Field(default=None, gt=1.5, le=20.0)
    fluxo_lm: int | None = Field(default=None, gt=0, le=100000)
    divisao: str = Field(default="", max_length=6, description="bloco autônomo: divisão da "
                         "ocupação (H-2 e H-3 têm autonomia maior)")


@lru_cache(maxsize=1)
def _params():  # noqa: ANN202
    from coscip_design import load_params

    from coscip_mcp import norms

    return load_params(norms.load_base().sources)


def _p(pid: str):  # noqa: ANN202
    from coscip_design import ParamError

    try:
        return _params().get(pid)
    except ParamError as exc:
        raise DetalheError(f"detalhe recusado: {exc}") from exc


def _ref(p) -> str:  # noqa: ANN001
    return f"{p.documento}, {p.item}"


def _m(v: float) -> str:
    return f"{v:.2f}".replace(".", ",")


class _D:
    """Desenho local: u para a direita, z para cima, a partir de (x, y), em metros reais."""

    def __init__(self, doc, msp, x: float, y: float, escala: int) -> None:  # noqa: ANN001
        self.doc, self.msp, self.x, self.y, self.esc = doc, msp, x, y, escala
        for c in CAMADAS:
            apresentacao.criar_camada(doc, c)
        apresentacao._estilo_cota(doc, escala)  # noqa: SLF001
        self.h = apresentacao.altura_texto(escala)  # 2,5 mm
        self.hp = apresentacao.altura_texto(escala, apresentacao.TEXTO_PEQUENO_MM)
        self.k = escala / 1000.0  # 1 mm de papel em metros
        self.caixas: list[tuple[float, float, float, float]] = []
        self.zmin, self.umax = math.inf, 0.0

    def _visto(self, pts) -> None:  # noqa: ANN001
        for u, z in pts:
            self.zmin = min(self.zmin, z)
            self.umax = max(self.umax, u)

    def P(self, u: float, z: float) -> tuple[float, float]:
        return (self.x + u, self.y + z)

    def linha(self, u0: float, z0: float, u1: float, z1: float, cam: str = "DETALHE",
              tracejado: bool = False) -> None:
        a: dict[str, Any] = {"layer": cam}
        if tracejado:
            a["linetype"] = "DASHED"
        self._visto([(u0, z0), (u1, z1)])
        self.msp.add_line(self.P(u0, z0), self.P(u1, z1), dxfattribs=a)

    def poli(self, pts: list[tuple[float, float]], cam: str = "DETALHE", fechar: bool = False,
             tracejado: bool = False) -> None:
        a: dict[str, Any] = {"layer": cam}
        if tracejado:
            a["linetype"] = "DASHED"
        self._visto(pts)
        self.msp.add_lwpolyline([self.P(u, z) for u, z in pts], close=fechar, dxfattribs=a)

    def caixa(self, u0: float, z0: float, u1: float, z1: float, cam: str = "DETALHE", *,
              solido: int | None = None, padrao: str | None = None, escala_hach: float = 1.0,
              tracejado: bool = False) -> None:
        pts = [(u0, z0), (u1, z0), (u1, z1), (u0, z1)]
        self.poli(pts, cam, fechar=True, tracejado=tracejado)
        if solido is not None or padrao:
            h = self.msp.add_hatch(color=solido if solido is not None else 8,
                                   dxfattribs={"layer": "DETALHE_HACH"})
            if solido is not None:
                h.set_solid_fill(color=solido)
            else:
                h.set_pattern_fill(padrao, color=8, scale=escala_hach * self.k * 4)
            h.paths.add_polyline_path([self.P(u, z) for u, z in pts], is_closed=True)

    def tubo(self, pts: list[tuple[float, float]], diam: float, cam: str = "DETALHE_INC") -> None:
        """Tubo pelo eixo, com o diâmetro em verdadeira grandeza (contorno das duas geratrizes)."""
        from shapely.geometry import LineString

        g = LineString(pts).buffer(diam / 2, cap_style="flat", join_style="mitre")
        self.poli(list(g.exterior.coords), cam, fechar=True)

    def peca(self, c: tuple[float, float], direcao: tuple[float, float], comp: float,
             larg: float, cam: str = "DETALHE_INC") -> list[tuple[float, float]]:
        """Retângulo que começa em ``c`` e avança ``comp`` na ``direcao`` (unitária)."""
        dx, dy = direcao
        nx, ny = -dy, dx
        pts = [(c[0] + nx * larg / 2, c[1] + ny * larg / 2),
               (c[0] + dx * comp + nx * larg / 2, c[1] + dy * comp + ny * larg / 2),
               (c[0] + dx * comp - nx * larg / 2, c[1] + dy * comp - ny * larg / 2),
               (c[0] - nx * larg / 2, c[1] - ny * larg / 2)]
        self.poli(pts, cam, fechar=True)
        return pts

    def circulo(self, u: float, z: float, r: float, cam: str = "DETALHE") -> None:
        self._visto([(u - r, z - r), (u + r, z + r)])
        self.msp.add_circle(self.P(u, z), r, dxfattribs={"layer": cam})

    def texto(self, s: str, u: float, z: float, mm: float = apresentacao.TEXTO_MM, *,
              alinhar: str = "esq", cam: str = "DETALHE_TEXTO", cor: int | None = None,
              rot: float = 0.0) -> tuple[float, float, float, float]:
        h = apresentacao.altura_texto(self.esc, mm)
        a: dict[str, Any] = {"layer": cam, "height": h, "rotation": rot,
                             "style": apresentacao.ESTILO_TEXTO}
        if cor is not None:
            a["color"] = cor
        t = self.msp.add_text(s, dxfattribs=a)
        al = {"esq": TextEntityAlignment.MIDDLE_LEFT, "centro": TextEntityAlignment.MIDDLE_CENTER,
              "dir": TextEntityAlignment.MIDDLE_RIGHT}[alinhar]
        t.set_placement(self.P(u, z), align=al)
        w = self.largura_texto(s, h)
        u0 = {"esq": u, "centro": u - w / 2, "dir": u - w}[alinhar]
        caixa = (u0, z - h / 2, u0 + w, z + h / 2)
        self.caixas.append(caixa)
        self._visto([(caixa[0], caixa[1]), (caixa[2], caixa[3])])
        return caixa

    @staticmethod
    def largura_texto(s: str, h: float) -> float:
        """Largura real do texto na fonte do estilo (Arial), em m."""
        from ezdxf.fonts import fonts

        try:
            return fonts.make_font("arial.ttf", h).text_width(s)
        except Exception:  # noqa: BLE001 — sem a fonte, estimativa conservadora
            return len(s) * h * 0.72

    def cota_v(self, u: float, z0: float, z1: float, desloc: float) -> None:
        d = self.msp.add_linear_dim(base=self.P(u + desloc, (z0 + z1) / 2), p1=self.P(u, z0),
                                    p2=self.P(u, z1), angle=90,
                                    dimstyle=apresentacao.dimstyle_nome(self.esc),
                                    dxfattribs={"layer": "DETALHE_COTA"})
        d.render()

    def cota_v_pts(self, p1: tuple[float, float], p2: tuple[float, float],
                   desloc: float) -> None:
        """Cota vertical entre dois pontos quaisquer; a linha de cota fica em p2.u + desloc."""
        base_u = p2[0] + desloc
        d = self.msp.add_linear_dim(base=self.P(base_u, (p1[1] + p2[1]) / 2), p1=self.P(*p1),
                                    p2=self.P(*p2), angle=90,
                                    dimstyle=apresentacao.dimstyle_nome(self.esc),
                                    dxfattribs={"layer": "DETALHE_COTA"})
        d.render()
        self._visto([(base_u, p1[1]), (base_u, p2[1])])

    def chamada_s(self, alvo: tuple[float, float], u: float, z: float,
                  linhas: list[str]) -> None:
        """Chamada como nas pranchas de referência: linha do alvo até o início de um traço
        horizontal, com o texto apoiado sobre o traço (várias linhas empilhadas)."""
        h = self.hp
        w = max(self.largura_texto(s, h) for s in linhas) + 1.0 * self.k
        self.linha(alvo[0], alvo[1], u, z, "DETALHE_AUX")
        self.linha(u, z, u + w, z, "DETALHE_AUX")
        self.circulo(alvo[0], alvo[1], 0.4 * self.k, "DETALHE_AUX")
        for i, s in enumerate(reversed(linhas)):
            self.texto(s, u + 0.5 * self.k, z + (0.9 + 1.45 * i) * h,
                       apresentacao.TEXTO_PEQUENO_MM)

    def balao(self, alvo: tuple[float, float], u: float, z: float, n: int) -> None:
        """Balão numerado (círculo com o número) ligado ao alvo: o item vai na tabela."""
        r = 2.6 * self.k
        du, dz = u - alvo[0], z - alvo[1]
        dist = math.hypot(du, dz) or 1.0
        self.linha(alvo[0], alvo[1], u - du / dist * r, z - dz / dist * r, "DETALHE_AUX")
        self.circulo(u, z, r, "DETALHE_TEXTO")
        self.texto(str(n), u, z, 2.5, alinhar="centro")

    def tabela_itens(self, u0: float, z_topo: float, itens: list[tuple[int, str]]) -> float:
        """Tabela Nº | DESCRIÇÃO dos balões; devolve o z da base."""
        k, h = self.k, self.hp
        lin = 5.5 * k
        w1 = 10 * k
        textos = ["DESCRIÇÃO", *(s for _, s in itens)]
        w2 = max(self.largura_texto(s, h) for s in textos) + 4 * k
        n = len(itens) + 1
        zb = z_topo - n * lin
        self.poli([(u0, zb), (u0 + w1 + w2, zb), (u0 + w1 + w2, z_topo), (u0, z_topo)],
                  "DETALHE_TEXTO", fechar=True)
        self.linha(u0 + w1, zb, u0 + w1, z_topo, "DETALHE_TEXTO")
        for i in range(1, n):
            self.linha(u0, z_topo - i * lin, u0 + w1 + w2, z_topo - i * lin, "DETALHE_TEXTO")
        self.texto("Nº", u0 + w1 / 2, z_topo - lin / 2, apresentacao.TEXTO_PEQUENO_MM,
                   alinhar="centro")
        self.texto("DESCRIÇÃO", u0 + w1 + w2 / 2, z_topo - lin / 2,
                   apresentacao.TEXTO_PEQUENO_MM, alinhar="centro")
        for i, (num, s) in enumerate(itens, 1):
            zc = z_topo - (i + 0.5) * lin
            self.texto(str(num), u0 + w1 / 2, zc, apresentacao.TEXTO_PEQUENO_MM,
                       alinhar="centro")
            self.texto(s, u0 + w1 + 2 * k, zc, apresentacao.TEXTO_PEQUENO_MM)
        return zb

    def chave(self, u: float, z0: float, z1: float, linhas: list[str]) -> None:
        """Chave (}) e as linhas de especificação à direita, centradas na altura."""
        k = self.k
        zm = (z0 + z1) / 2
        self.poli([(u, z1), (u + 1.2 * k, z1 - 1.2 * k), (u + 1.2 * k, zm + 1.2 * k),
                   (u + 2.4 * k, zm), (u + 1.2 * k, zm - 1.2 * k), (u + 1.2 * k, z0 + 1.2 * k),
                   (u, z0)], "DETALHE_TEXTO")
        passo = 1.6 * self.hp
        z = zm + passo * (len(linhas) - 1) / 2
        for s in linhas:
            self.texto(s, u + 4 * k, z, apresentacao.TEXTO_PEQUENO_MM)
            z -= passo

    def cota_h(self, u0: float, u1: float, z: float, desloc: float) -> None:
        d = self.msp.add_linear_dim(base=self.P((u0 + u1) / 2, z + desloc), p1=self.P(u0, z),
                                    p2=self.P(u1, z), angle=0,
                                    dimstyle=apresentacao.dimstyle_nome(self.esc),
                                    dxfattribs={"layer": "DETALHE_COTA"})
        d.render()

    def chamada(self, alvo: tuple[float, float], u_txt: float, z_txt: float, s: str) -> None:
        """Linha de chamada do alvo até o texto (à direita), com um ponto no alvo."""
        self.linha(alvo[0], alvo[1], u_txt - 1.5 * self.k, z_txt, "DETALHE_AUX")
        self.linha(u_txt - 1.5 * self.k, z_txt, u_txt - 0.5 * self.k, z_txt, "DETALHE_AUX")
        self.circulo(alvo[0], alvo[1], 0.5 * self.k, "DETALHE_AUX")
        self.texto(s, u_txt, z_txt, apresentacao.TEXTO_PEQUENO_MM)

    def piso(self, u0: float, u1: float, z: float = 0.0) -> None:
        self.linha(u0, z, u1, z, "DETALHE")
        self.caixa(u0, z - 2.5 * self.k, u1, z, "DETALHE_AUX", padrao="AR-CONC",
                   escala_hach=0.08)

    def parede_corte(self, u0: float, u1: float, z0: float, z1: float) -> None:
        self.caixa(u0, z0, u1, z1, "DETALHE", padrao="ANSI31", escala_hach=1.0)

    def subtitulo(self, s: str, u: float, z: float) -> None:
        self.texto(s, u, z, 2.5)
        w = len(s) * self.h * 0.62
        self.linha(u, z - 0.9 * self.h, u + w, z - 0.9 * self.h, "DETALHE_AUX")

    def notas(self, linhas: list[str], u: float, z_topo: float) -> float:
        """Notas numeradas, de cima para baixo; devolve o z da última linha."""
        z = z_topo
        self.texto("NOTAS:", u, z, 2.5)
        for i, ln in enumerate(linhas, 1):
            z -= (1.9 if i == 1 else 1.7) * self.hp
            self.texto(f"{i}. {ln}", u, z, apresentacao.TEXTO_PEQUENO_MM)
        return z

    def placa(self, u: float, z_base: float, w: float, h: float, cor: int, codigo: str,
              cam: str = "DETALHE_SINAL") -> None:
        if codigo.startswith("E"):
            cam = "DETALHE_INC"
        self.caixa(u - w / 2, z_base, u + w / 2, z_base + h, cam, solido=cor)
        self.texto(codigo, u + w / 2 + 1.2 * self.k, z_base + h / 2,
                   apresentacao.TEXTO_PEQUENO_MM, cam=cam)


def _placa_dims(op: Detalhe, padrao_mm: tuple[int, int]) -> tuple[float, float, bool]:
    if op.placa_mm:
        w, h = (int(v) / 1000 for v in op.placa_mm.split("x"))
        return w, h, True
    return padrao_mm[0] / 1000, padrao_mm[1] / 1000, False


def _nota_placa(informada: bool, padrao: str) -> list[str]:
    if informada:
        return []
    return [f"PLACA DESENHADA COM {padrao} mm: ADOTAR A DIMENSÃO DAS CHAMADAS DA PLANTA "
            "(NT 2-05, TABELA 7)."]


def _placa_ampliada(d: _D, codigo: str, u0: float, z_base: float, largura: float,
                    forma, dim_txt: str) -> None:  # noqa: ANN001
    """Placa com o pictograma oficial em tamanho ampliado e a chave de especificação."""
    d.texto(f"PLACA {codigo} (AMPLIADA, SEM ESCALA)", u0, z_base + largura * 0.95 + 6 * d.k,
            2.0)
    w, h = eq.placa_nt(d, codigo, u0 + largura / 2, z_base, largura)
    v = forma.valor
    linhas = [f"SÍMBOLO: {v['forma']}", f"CÓDIGO: {codigo}", f"FUNDO: {v['fundo']}",
              f"PICTOGRAMA: {v['pictograma']}"]
    if v.get("letra_min_mm"):
        linhas.append(f"LETRA: ACIMA DE {v['letra_min_mm']} mm")
    linhas += [f"DIMENSÃO: {dim_txt}", f"{forma.documento.upper()}, {forma.item.upper()}"]
    d.chave(u0 + w + 3 * d.k, z_base, z_base + h, linhas)


# --- extintor ------------------------------------------------------------------------------


def _extintor(d: _D, op: Detalhe) -> dict[str, Any]:
    alca, base, sup = _p("det.ext.alca_max_m"), _p("det.ext.base_min_m"), _p("det.ext.suporte")
    nsup, e5, e5f = (_p("det.placa.nivel_superior_min_m"), _p("det.placa.e5_nivel"),
                     _p("det.placa.e5_forma"))
    D, H = op.extintor_m or eq.dimensoes_extintor(op.agente)
    za = float(alca.valor)  # alça no limite: o detalhe mostra o máximo admitido
    zmin = float(base.valor)
    zb = za - H
    if zb < zmin - 1e-9:
        raise DetalheError(f"extintor com {_m(H)} m de altura não cabe com a alça a {_m(za)} m e "
                           f"a parte inferior a {_m(zmin)} m do piso ({_ref(alca)}): confira a "
                           "altura informada")
    pw, ph, informada = _placa_dims(op, (200, 200))
    zp = float(nsup.valor)
    k = d.k
    montagem = op.montagem
    itens = [(1, f"EXTINTOR {op.agente.upper()}")]
    u = 0.0
    if montagem in ("parede", "ambos"):
        eq.parede_alvenaria(d, 0.0, 0.15, 0.0, zp + ph + 0.40)
        d.caixa(0.15, zp, 0.158, zp + ph, "DETALHE_INC", solido=1)  # placa vista de lado
        uc = 0.15 + 0.03 + D / 2
        ex = eq.extintor(d, uc, zb, D, H, mangueira="pendente")
        sp = eq.suporte_parede(d, 0.15, ex["pescoco"][1], (uc - 0.11 * D) - 0.15)
        d.piso(-0.10, 1.85)
        uc_txt = 0.66
        d.chamada_s((0.158, zp + ph * 0.6), uc_txt, zp + ph + 0.10, ["PLACA E-5"])
        d.chamada_s(sp["suporte"], uc_txt, (za + zp) / 2 - 0.03, ["SUPORTE DE FIXAÇÃO"])
        d.chamada_s(sp["parafuso"], uc_txt, za - 0.17, ["PARAFUSO E BUCHA"])
        d.chamada_s(ex["adesivo"], uc_txt, ex["adesivo"][1] - 0.16,
                    ["ADESIVO DE", "IDENTIFICAÇÃO"])
        d.chamada_s((0.08, 0.62), uc_txt, 0.40, ["PAREDE EM", "ALVENARIA"])
        d.balao(ex["corpo"], uc + D / 2 + 0.16, zb + 0.13 * H, 1)
        ud = 1.42
        d.cota_v_pts((ud, 0.0), (ex["alavanca"][0], za), ud - ex["alavanca"][0])
        d.cota_v_pts((ud + 0.16, 0.0), (0.158, zp), ud + 0.16 - 0.158)
        d.cota_v_pts((ud - 0.16, 0.0), (uc + D / 2, zb), ud - 0.16 - uc - D / 2)
        d.subtitulo("NA PAREDE", 0.35, -0.20)
        u = 1.95
    if montagem in ("piso", "ambos"):
        ucp = u + 0.55
        sp2 = eq.suporte_piso(d, ucp, D)
        ex2 = eq.extintor(d, ucp, sp2["apoio"], D, H, mangueira="laco")
        d.piso(u - 0.10, u + 1.25)
        d.balao(ex2["corpo"], ucp + D / 2 + 0.22, ex2["corpo"][1], 1)
        d.balao(sp2["anel"], ucp + D / 2 + 0.22, sp2["anel"][1], 2)
        d.subtitulo("NO PISO", ucp - 0.15, -0.20)
        itens.append((2, "SUPORTE PARA EXTINTOR NO PISO"))
        u += 1.45
    # placa ampliada, tabela de itens
    lado = 0.60
    _placa_ampliada(d, "E-5", u + 0.10, zp - 0.10, lado, e5f,
                    f"{round(pw * 1000)} x {round(ph * 1000)} mm")
    d.tabela_itens(u + 0.10, zp - 0.45, itens)
    linhas = [
        f"ALÇA DE MANUSEIO A NO MÁXIMO {_m(za)} m DO PISO ACABADO ({_ref(alca)} b).",
        f"PARTE INFERIOR A NO MÍNIMO {_m(zmin)} m DO PISO; O EXTINTOR NÃO FICA EM CONTATO COM "
        f"O PISO: NO PISO, SOBRE SUPORTE ({_ref(base)} b e c).",
        f"SUPORTE RESISTENTE A {sup.valor} VEZES A MASSA TOTAL DO EXTINTOR ({_ref(sup)} a).",
        f"PLACA E-5 NO NÍVEL {str(e5.valor).upper()}: BASE A NO MÍNIMO {_m(zp)} m DO PISO "
        f"({_ref(nsup)}; {_ref(e5)}).",
        f"EXTINTOR REPRESENTADO COM Ø {_m(D)} x {_m(H)} m (TAMANHO APROXIMADO: CONFIRMAR COM O "
        "FABRICANTE).",
    ]
    medidas = [{"valor": f"{_m(za)} m", "o_que": alca.titulo, "fonte": alca.citacao},
               {"valor": f"{_m(zmin)} m", "o_que": base.titulo, "fonte": base.citacao},
               {"valor": f"{_m(zp)} m", "o_que": nsup.titulo, "fonte": nsup.citacao}]
    if op.piso_demarcado:
        pd = _p("det.ext.piso_demarcado")
        lado_p, borda = pd.valor["lado_m"], pd.valor["borda_m"]
        u2 = d.umax + 0.5
        tot = lado_p + 2 * borda
        d.subtitulo("PLANTA - PISO SOB O EXTINTOR", u2, zp + ph + 0.15)
        d.caixa(u2, 0.3, u2 + tot, 0.3 + tot, "DETALHE_SINAL", solido=2)
        d.caixa(u2 + borda, 0.3 + borda, u2 + borda + lado_p, 0.3 + borda + lado_p,
                "DETALHE_INC", solido=1)
        d.cota_h(u2 + borda, u2 + borda + lado_p, 0.3 + borda, -(borda + 0.12))
        d.cota_h(u2, u2 + borda, 0.3 + tot, 0.12)
        d.texto("VERMELHO", u2 + tot / 2, 0.3 + tot / 2, apresentacao.TEXTO_PEQUENO_MM,
                alinhar="centro", cor=7)
        d.chamada_s((u2 + tot - borda / 2, 0.3 + tot - borda / 2), u2 + tot + 0.15,
                    0.3 + tot + 0.08, ["BORDA AMARELA"])
        linhas.append(f"ÁREA DE PISO SOB O EXTINTOR: {_m(lado_p)} x {_m(lado_p)} m EM VERMELHO "
                      f"COM BORDA AMARELA DE {_m(borda)} m ({_ref(pd)}).")
        medidas.append({"valor": f"{_m(lado_p)} x {_m(lado_p)} m + {_m(borda)} m",
                        "o_que": pd.titulo, "fonte": pd.citacao})
    informado = [f"agente e capacidade: {op.agente}",
                 f"extintor representado com Ø {_m(D)} x {_m(H)} m"
                 + ("" if op.extintor_m else " (tamanho aproximado de catálogo)")]
    linhas += _nota_placa(informada, "200x200")
    if informada:
        informado.append(f"placa {op.placa_mm} mm")
    return {"linhas": linhas, "medidas": medidas, "informado": informado,
            "altura": max(zp + ph + 0.45, za + 0.3) + 0 * k}


# --- abrigo de mangueiras -----------------------------------------------------------------


def _abrigo(d: _D, op: Detalhe) -> dict[str, Any]:
    if op.risco is None:
        raise DetalheError("detalhe abrigo_mangueira: informe o risco (PEQUENO, MEDIO_1, "
                           "MEDIO_2 ou GRANDE) da Tabela 1 da NT 2-02")
    if op.base_m is None:
        raise DetalheError("detalhe abrigo_mangueira: informe base_m (altura da base do abrigo "
                           "ao piso); a NT 2-02 não a fixa")
    rede = op.risco in REDE
    dims = _p("det.abrigo.rede_cm" if rede else "det.abrigo.canalizacao_cm")
    reg = _p("det.abrigo.registro_rede" if rede else "det.abrigo.registro_canalizacao")
    porta, pint = _p("det.abrigo.porta"), _p("det.abrigo.pintura")
    sis = _p(f"hid.sistema.{op.risco}")
    nsup, e7, e7f = (_p("det.placa.nivel_superior_min_m"), _p("det.placa.e7_nivel"),
                     _p("det.placa.e7_forma"))
    H, W, P = (v / 100 for v in dims.valor)
    zb = op.base_m
    pw, ph, informada = _placa_dims(op, (200, 200))
    zp = max(float(nsup.valor), zb + H + 0.10)
    topo = zp + ph + 0.35
    dn = reg.valor["registro_mm"] / 1000
    # elevação --------------------------------------------------------------------------------
    U = 1.50
    u0 = 0.35
    d.piso(0, U)
    d.caixa(u0 - 0.02, zb - 0.02, u0 + W + 0.02, zb + H + 0.02, "DETALHE_INC")  # aro
    d.caixa(u0, zb, u0 + W, zb + H, "DETALHE_INC")
    mold = porta.valor["moldura_cm"] / 100
    d.caixa(u0 + mold, zb + mold, u0 + W - mold, zb + H - mold, "DETALHE_INC")
    d.texto("INCÊNDIO", u0 + W / 2, zb + H - mold / 2, 1.8, alinhar="centro", cam="DETALHE_INC")
    eq.mangueira_aduchada(d, u0 + W / 2, zb + H * 0.47, W - 2 * mold - 0.06, H * 0.42)
    rg = eq.registro_globo_angular(d, u0 + mold + 0.06, zb + H - mold - 0.17, 0.8)
    stz = eq.storz(d, (u0 + mold + 0.09, zb + H - mold - 0.18), (0.7071, -0.7071), dn * 0.6)
    esg = eq.esguicho(d, u0 + mold + 0.03, zb + mold + 0.05, min(0.26, W - 2 * mold - 0.06))
    d.linha(u0 + W - mold - 0.02, zb + H * 0.45, u0 + W - mold - 0.02, zb + H * 0.55,
            "DETALHE_INC")  # trinco
    eq.placa_nt(d, "E-7", u0 + W / 2, zp, pw, "DETALHE_INC")
    ub = u0 + W + 0.20
    d.balao((u0 + W + 0.02, zb + H * 0.85), ub, zb + H * 0.85, 1)
    d.balao(rg["volante"], ub, zb + H + 0.08, 2)
    d.balao(stz, ub - 0.02, zb + H * 0.66, 3)
    d.balao((u0 + W / 2 + (W - 2 * mold - 0.06) / 2, zb + H * 0.47), ub, zb + H * 0.47, 4)
    d.balao(esg, ub, zb + mold + 0.02, 5)
    d.balao((u0 + W / 2 + pw / 2, zp + ph * 0.5), ub, zp + ph * 0.5, 6)
    d.cota_h(u0, u0 + W, zb, -0.12)
    d.cota_v_pts((0.12, 0.0), (u0, zb), 0.12 - u0)
    d.cota_v_pts((0.22, zb), (u0, zb + H), 0.22 - u0)
    d.cota_v_pts((0.02, 0.0), (u0 + W / 2 - pw / 2, zp), 0.02 - (u0 + W / 2 - pw / 2))
    d.subtitulo("ELEVAÇÃO", u0, -0.20)
    # corte -----------------------------------------------------------------------------------
    c0 = U + 0.50
    eq.parede_alvenaria(d, c0, c0 + 0.15, 0, topo - 0.10)
    d.piso(c0 - 0.05, c0 + 1.35)
    ua = c0 + 0.15
    d.caixa(ua, zb, ua + P, zb + H, "DETALHE_INC")
    d.linha(ua + P - 0.012, zb + 0.03, ua + P - 0.012, zb + H - 0.03, "DETALHE_INC")  # vidro
    zr = zb + H - mold - 0.17
    d.tubo([(c0 + 0.08, -0.05), (c0 + 0.08, zr - 0.06), (ua + 0.04, zr - 0.06)], dn)
    eq.registro_globo_angular(d, ua + 0.06, zr, 0.8)
    eq.storz(d, (ua + 0.09, zr - 0.01), (0.7071, -0.7071), dn * 0.6)
    d.caixa(ua + 0.02, zb + 0.05, ua + P - 0.03, zb + H * 0.70, "DETALHE_INC")  # mangueira
    for kk in range(1, 5):
        zz = zb + 0.05 + (H * 0.70 - 0.05) * kk / 5
        d.linha(ua + 0.02, zz, ua + P - 0.03, zz, "DETALHE_INC")
    d.caixa(ua, zp, ua + 0.008, zp + ph, "DETALHE_INC", solido=1)
    if rede:
        pv = _p("det.abrigo.piso_vermelho_m")
        lado = float(pv.valor)
        d.caixa(ua, -2.5 * d.k, ua + lado, 0, "DETALHE_INC", solido=1)
        d.cota_h(ua, ua + lado, 0, -0.22)
    d.subtitulo("CORTE", ua, -0.32 if rede else -0.20)
    itens = [(1, f"ABRIGO {round(H * 100)} x {round(W * 100)} x {round(P * 100)} cm, PORTA DE "
                 f"VIDRO {porta.valor['vidro_mm']} mm COM INSCRIÇÃO INCÊNDIO"),
             (2, f"REGISTRO GLOBO ANGULAR Ø{reg.valor['registro_mm']} mm"),
             (3, f"JUNTA STORZ {reg.valor['storz_mm']} mm E REDUÇÃO {reg.valor['reducao_mm']} mm"),
             (4, f"MANGUEIRA Ø{sis.valor['mangueira_mm']} mm "
                 f"{sis.valor['mangueira_tipo'].upper()}, ATÉ {sis.valor['mangueira_max_m']} m"),
             (5, f"ESGUICHO REGULÁVEL Ø{sis.valor['esguicho_mm']} mm"),
             (6, "PLACA E-7 (ABRIGO DE MANGUEIRA E HIDRANTE)")]
    ut = c0 + 1.55
    _placa_ampliada(d, "E-7", ut, zp - 0.05, 0.55, e7f,
                    f"{round(pw * 1000)} x {round(ph * 1000)} mm")
    d.tabela_itens(ut, zp - 0.35, itens)
    linhas = [
        f"ABRIGO COM NO MÍNIMO {round(H * 100)} cm DE ALTURA, {round(W * 100)} cm DE LARGURA E "
        f"{round(P * 100)} cm DE PROFUNDIDADE, EXCLUSIVO PARA OS EQUIPAMENTOS ({_ref(dims)}).",
        f"PORTA DE VIDRO COM {porta.valor['vidro_mm']} mm NO MÍNIMO E INSCRIÇÃO INCÊNDIO EM "
        f"VERMELHO, TRAÇO DE {porta.valor['traco_cm']} cm, MOLDURA DE "
        f"{porta.valor['moldura_cm']} cm ({_ref(porta)}).",
        f"REGISTRO GLOBO ANGULAR DE {reg.valor['registro_mm']} mm, JUNTA STORZ DE "
        f"{reg.valor['storz_mm']} mm E REDUÇÃO PARA {reg.valor['reducao_mm']} mm "
        f"({_ref(reg)}).",
        f"MANGUEIRA DE {sis.valor['mangueira_mm']} mm, ATÉ {sis.valor['mangueira_max_m']} m, "
        f"ESGUICHO REGULÁVEL DE {sis.valor['esguicho_mm']} mm ({_ref(sis)}).",
        f"ABRIGO PINTADO PREFERENCIALMENTE DE VERMELHO, COM VENTILAÇÃO PERMANENTE E TRINCO OU "
        f"FECHADURA COM A CHAVE JUNTO AO ABRIGO ({_ref(pint)}).",
        f"PLACA E-7 NO NÍVEL {str(e7.valor).upper()}: BASE A NO MÍNIMO "
        f"{_m(float(nsup.valor))} m DO PISO ({_ref(nsup)}; {_ref(e7)}).",
    ]
    medidas = [{"valor": f"{round(H * 100)} x {round(W * 100)} x {round(P * 100)} cm",
                "o_que": dims.titulo, "fonte": dims.citacao},
               {"valor": f"Ø{reg.valor['registro_mm']} mm", "o_que": reg.titulo,
                "fonte": reg.citacao}]
    if rede:
        pv = _p("det.abrigo.piso_vermelho_m")
        linhas.append(f"PISO SOB O ABRIGO: {_m(float(pv.valor))} x {_m(float(pv.valor))} m "
                      f"PINTADO DE VERMELHO, SEM OCUPAÇÃO ({_ref(pv)}).")
        medidas.append({"valor": "1,00 x 1,00 m", "o_que": pv.titulo, "fonte": pv.citacao})
    linhas += _nota_placa(informada, "200x200")
    informado = [f"base do abrigo a {_m(zb)} m do piso", f"risco {op.risco}"]
    return {"linhas": linhas, "medidas": medidas, "informado": informado, "altura": topo}


# --- hidrante de recalque -------------------------------------------------------------------


def _duplo(op: Detalhe) -> tuple[bool, Any]:
    dp = _p("det.rec.duplo")
    return (op.vazao_lpm is not None and op.vazao_lpm >= dp.valor["vazao_lpm"]), dp


def _recalque_passeio(d: _D, op: Detalhe) -> dict[str, Any]:
    if op.risco is None:
        raise DetalheError("detalhe recalque_passeio: informe o risco (PEQUENO, MEDIO_1, MEDIO_2 "
                           "ou GRANDE): define a caixa mínima (NT 2-02, 5.2.5)")
    cx, sd = _p("det.rec.passeio_caixa_m"), _p("det.rec.passeio_saida")
    val, proib, sret = (_p("det.rec.valvula"), _p("det.rec.local_proibido"),
                        _p("det.rec.sem_retencao"))
    a_m, b_m = cx.valor[op.risco]
    prof = float(cx.valor["profundidade_max_m"])
    rebordo = float(sd.valor["profundidade_max_m"])
    duplo, dp = _duplo(op)
    topo = 0.45
    U = 1.30
    larg = max(a_m, b_m)
    u0 = (U - larg) / 2
    # passeio, solo e caixa
    d.linha(0, 0, u0 - 0.05, 0)
    d.linha(u0 + larg + 0.05, 0, U, 0)
    d.caixa(0, -0.08, u0 - 0.05, 0, "DETALHE_AUX", padrao="AR-CONC", escala_hach=0.08)
    d.caixa(u0 + larg + 0.05, -0.08, U, 0, "DETALHE_AUX", padrao="AR-CONC", escala_hach=0.08)
    d.parede_corte(u0 - 0.05, u0, -prof - 0.05, 0)
    d.parede_corte(u0 + larg, u0 + larg + 0.05, -prof - 0.05, 0)
    d.parede_corte(u0 - 0.05, u0 + larg + 0.05, -prof - 0.05, -prof)
    d.caixa(u0 - 0.03, 0, u0 + larg + 0.03, 0.012, "DETALHE_INC")  # tampa metálica
    d.caixa(u0 + larg * 0.85, 0.012, u0 + larg * 0.95, 0.02, "DETALHE_INC")  # puxador
    # tubulação, registro de gaveta, curva a 45°, junta storz e tampão no limite do rebordo
    s45 = math.sqrt(0.5)
    diam = cx.valor["registro_mm"] / 1000
    uc = u0 + larg * 0.35
    alt_storz = (0.045 + 0.012 + (diam + 0.03) / 2) * s45
    zo = -rebordo - alt_storz
    ze = zo - 0.10
    ue = uc + (zo - ze)
    zr = -prof + 0.10
    d.tubo([(uc, -prof - 0.35), (uc, zr - 0.05)], diam)
    rgv = eq.registro_gaveta(d, uc, zr, diam)
    d.tubo([(uc, zr + 0.05), (uc, ze), (ue, zo)], diam)
    fim = eq.storz(d, (ue, zo), (s45, s45), diam)
    zt = fim[1] + (0.012 + (diam + 0.03) / 2) * s45
    d.cota_v(u0 - 0.05, -prof, 0, -0.14)
    d.cota_v_pts((u0 + 0.12, zt), (u0 + 0.12, 0.0), 0.0)
    ub = U + 0.20
    d.balao((u0 + larg * 0.6, 0.012), ub, 0.25, 1)
    d.balao((fim[0], fim[1]), ub, 0.05, 2)
    d.balao(rgv["volante"], ub, -0.15, 3)
    d.balao((u0 + larg + 0.05, -prof * 0.6), ub, -0.35, 4)
    d.balao((uc + diam / 2, -prof - 0.28), ub, -0.55, 5)
    d.subtitulo("CORTE", 0.0, topo)
    # planta da caixa
    p0 = ub + 0.40
    d.subtitulo("PLANTA DA CAIXA", p0, topo)
    pz = -prof - 0.05
    d.caixa(p0, pz, p0 + b_m, pz + a_m, "DETALHE_INC")
    d.texto("INCÊNDIO", p0 + b_m / 2, pz + a_m * 0.72, 2.5, alinhar="centro", cam="DETALHE_INC")
    d.cota_h(p0, p0 + b_m, pz, -0.10)
    d.cota_v(p0 + b_m, pz, pz + a_m, 0.10)
    for f in ((0.3, 0.7) if duplo else (0.5,)):
        d.circulo(p0 + b_m * f, pz + a_m * 0.30, 0.045, "DETALHE_INC")
        d.circulo(p0 + b_m * f, pz + a_m * 0.30, 0.028, "DETALHE_INC")
    itens = [(1, "TAMPA METÁLICA COM INSCRIÇÃO INCÊNDIO"),
             (2, f"JUNTA STORZ {cx.valor['registro_mm']} mm COM TAMPÃO, SAÍDA A "
                 f"{sd.valor['angulo_graus']}° PARA CIMA"),
             (3, f"REGISTRO DE GAVETA Ø{cx.valor['registro_mm']} mm (2 1/2\")"),
             (4, f"CAIXA {_m(a_m)} x {_m(b_m)} m, PROFUNDIDADE MÁXIMA {_m(prof)} m"),
             (5, "TUBULAÇÃO DO SISTEMA"
                 + (f" Ø{dp.valor['tubo_mm']} mm (RECALQUE DUPLO)" if duplo else ""))]
    d.tabela_itens(p0 + b_m + 0.45, topo - 0.05, itens)
    linhas = [
        f"CAIXA METÁLICA COM TAMPA E INSCRIÇÃO INCÊNDIO, NO MÍNIMO {_m(a_m)} x {_m(b_m)} m, "
        f"PROFUNDIDADE MÁXIMA {_m(prof)} m; REGISTRO DE GAVETA DE {cx.valor['registro_mm']} mm "
        f"COM JUNTA STORZ E TAMPÃO ({_ref(cx)}).",
        f"REBORDO DO HIDRANTE NO MÁXIMO {_m(rebordo)} m ABAIXO DA BORDA DA CAIXA, SAÍDA VOLTADA "
        f"PARA CIMA A {sd.valor['angulo_graus']}° ({_ref(cx)}; {_ref(sd)}).",
        f"VÁLVULA DE GAVETA OU ESFERA, COM FLUXO NOS DOIS SENTIDOS ({_ref(val)}); SEM "
        f"VÁLVULA DE RETENÇÃO ({_ref(sret)}).",
        f"PROIBIDO EM LOCAL DE PASSAGEM OU ESTACIONAMENTO DE VEÍCULOS ({_ref(proib)}).",
    ]
    if duplo:
        linhas.append(f"VAZÃO DE {round(op.vazao_lpm)} L/min (>= {dp.valor['vazao_lpm']}): "
                      f"HIDRANTE DE RECALQUE DUPLO, TUBULAÇÃO DE NO MÍNIMO "
                      f"{dp.valor['tubo_mm']} mm ({_ref(dp)}).")
    medidas = [{"valor": f"{_m(a_m)} x {_m(b_m)} m; prof. máx. {_m(prof)} m",
                "o_que": cx.titulo, "fonte": cx.citacao},
               {"valor": f"{_m(rebordo)} m; {sd.valor['angulo_graus']}°", "o_que": sd.titulo,
                "fonte": sd.citacao}]
    informado = [f"risco {op.risco}"] + ([f"vazão {op.vazao_lpm} L/min"] if op.vazao_lpm
                                         else [])
    return {"linhas": linhas, "medidas": medidas, "informado": informado, "altura": topo + 0.1,
            "duplo": duplo}


def _recalque_fachada(d: _D, op: Detalhe) -> dict[str, Any]:
    if op.risco is None:
        raise DetalheError("detalhe recalque_fachada: informe o risco: define o abrigo mínimo "
                           "(NT 2-02, 5.2.3)")
    alt, ab = _p("det.rec.fachada_altura_m"), _p("det.rec.fachada_abrigo_m")
    val, sret = _p("det.rec.valvula"), _p("det.rec.sem_retencao")
    zmin, zmax = float(alt.valor["min"]), float(alt.valor["max"])
    z = op.altura_m if op.altura_m is not None else zmin
    if not zmin - 1e-9 <= z <= zmax + 1e-9:
        raise DetalheError(f"recalque na fachada: altura {z} m fora de {_m(zmin)} a {_m(zmax)} m "
                           f"({_ref(alt)})")
    a_m, b_m = ab.valor[op.risco]
    duplo, dp = _duplo(op)
    topo = z + a_m / 2 + 0.70
    diam = 0.063
    # elevação --------------------------------------------------------------------------------
    U = 1.40
    u0 = (U - b_m) / 2
    d.piso(0, U)
    d.caixa(u0 - 0.02, z - a_m / 2 - 0.02, u0 + b_m + 0.02, z + a_m / 2 + 0.02, "DETALHE_INC")
    d.caixa(u0, z - a_m / 2, u0 + b_m, z + a_m / 2, "DETALHE_INC")
    d.texto("INCÊNDIO", u0 + b_m / 2, z + a_m / 2 - 0.05, 1.8, alinhar="centro",
            cam="DETALHE_INC")
    for us in ([u0 + b_m / 2] if not duplo else [u0 + b_m * 0.3, u0 + b_m * 0.7]):
        d.circulo(us, z - 0.03, 0.05, "DETALHE_INC")
        d.circulo(us, z - 0.03, 0.032, "DETALHE_INC")
        d.circulo(us, z - 0.03, 0.012, "DETALHE_INC")
    d.cota_v_pts((0.20, 0.0), (u0 + b_m / 2, z - 0.03), 0.20 - (u0 + b_m / 2))
    d.cota_h(u0, u0 + b_m, z - a_m / 2, -0.10)
    d.cota_v(u0 + b_m, z - a_m / 2, z + a_m / 2, 0.10)
    d.subtitulo("ELEVAÇÃO", u0, -0.20)
    # corte -----------------------------------------------------------------------------------
    c0 = U + 0.60
    uf = c0 + 0.45  # face externa (rua à esquerda); parede de 0,25 m
    zi, zs = z - a_m / 2, z + a_m / 2
    eq.parede_alvenaria(d, uf, uf + 0.25, 0, zi)
    eq.parede_alvenaria(d, uf, uf + 0.25, zs, topo - 0.30)
    d.caixa(uf + 0.20, zi, uf + 0.25, zs, "DETALHE", padrao="ANSI31", escala_hach=1.0)
    d.caixa(uf, zi, uf + 0.20, zs, "DETALHE_INC")
    d.piso(c0, c0 + 1.30)
    s45 = math.sqrt(0.5)
    zc = z - 0.03
    d.tubo([(uf + 0.85, zc + 0.08), (uf + 0.14, zc + 0.08), (uf + 0.07, zc + 0.01)], diam)
    rgv = eq.registro_gaveta(d, uf + 0.55, zc + 0.08, diam)
    fim = eq.storz(d, (uf + 0.07, zc + 0.01), (-s45, -s45), diam)
    d.texto("RUA", c0 + 0.12, 0.25, 1.8)
    d.texto("INTERIOR", uf + 0.55, 0.25, 1.8)
    ub = uf + 1.05
    d.balao((uf + 0.19, zs - 0.03), ub, zs + 0.15, 1)
    d.balao(fim, ub, zc - 0.10, 2)
    d.balao(rgv["volante"], ub, zc + 0.08, 3)
    d.subtitulo("CORTE", uf, -0.20)
    itens = [(1, f"ABRIGO {_m(a_m)} x {_m(b_m)} m COM INSCRIÇÃO INCÊNDIO"),
             (2, f"JUNTA STORZ COM TAMPÃO, SAÍDA A {alt.valor['angulo_graus']}° PARA A RUA"),
             (3, "REGISTRO DE GAVETA OU ESFERA (FLUXO NOS DOIS SENTIDOS)")]
    d.tabela_itens(ub + 0.30, topo - 0.10, itens)
    linhas = [
        f"SAÍDA DO HIDRANTE A {_m(zmin)} A {_m(zmax)} m DO PISO, A {alt.valor['angulo_graus']}° "
        f"E VOLTADA PARA A RUA, NA FACHADA DE MELHOR ACESSO DAS VIATURAS ({_ref(alt)}).",
        f"ABRIGO DE NO MÍNIMO {_m(a_m)} x {_m(b_m)} m COM INSCRIÇÃO INCÊNDIO, A NO MÁXIMO "
        f"{ab.valor['distancia_max_alinhamento_m']} m DO ALINHAMENTO DA VIA ({_ref(ab)}).",
        f"VÁLVULA DE GAVETA OU ESFERA, COM FLUXO NOS DOIS SENTIDOS ({_ref(val)}); SEM "
        f"VÁLVULA DE RETENÇÃO ({_ref(sret)}).",
    ]
    if duplo:
        linhas.append(f"VAZÃO DE {round(op.vazao_lpm)} L/min: HIDRANTE DUPLO, TUBULAÇÃO DE NO "
                      f"MÍNIMO {dp.valor['tubo_mm']} mm ({_ref(dp)}).")
    informado = [f"saída a {_m(z)} m" + (" (mínimo da faixa: altura não informada)"
                                         if op.altura_m is None else ""), f"risco {op.risco}"]
    medidas = [{"valor": f"{_m(zmin)} a {_m(zmax)} m; {alt.valor['angulo_graus']}°",
                "o_que": alt.titulo, "fonte": alt.citacao},
               {"valor": f"{_m(a_m)} x {_m(b_m)} m", "o_que": ab.titulo, "fonte": ab.citacao}]
    return {"linhas": linhas, "medidas": medidas, "informado": informado, "altura": topo,
            "duplo": duplo}


# --- bloco autônomo -------------------------------------------------------------------------


def _bloco(d: _D, op: Detalhe) -> dict[str, Any]:
    if op.altura_m is None:
        raise DetalheError("detalhe bloco_autonomo: informe altura_m (altura de instalação, "
                           "da NBR 10898 adotada pela NT 2-06 — não está na base do motor)")
    aut, nbr, esc_ = _p("det.ilum.autonomia_min"), _p("det.ilum.nbr"), _p("det.ilum.escadas")
    div = op.divisao.strip().upper()
    minutos = aut.valor.get(div, aut.valor["geral"])
    z = op.altura_m
    pd = op.pe_direito_m
    bh = 0.11
    if pd is not None and z + bh > pd:
        raise DetalheError("bloco autônomo acima do forro: altura_m + 0,11 > pe_direito_m")
    teto = pd if pd is not None else z + 0.45
    topo = teto + 0.30
    # vista lateral ---------------------------------------------------------------------------
    U = 1.9
    eq.parede_alvenaria(d, 0, 0.15, 0, teto)
    if pd is not None:
        eq.laje_concreto(d, 0, U, pd, pd + 0.12)
        eq.forro(d, 0.15, U, pd)
        d.cota_v_pts((U - 0.05, 0.0), (U - 0.05, pd), 0.10)
    d.piso(0, U)
    bl = eq.bloco_lateral(d, 0.15, z)
    for ang in (35, 60):  # facho de luz, só ilustrativo
        alc = min(z * math.tan(math.radians(ang)), U - 0.40)
        d.linha(bl["farol"][0], bl["farol"][1], bl["farol"][0] + alc,
                bl["farol"][1] - alc / math.tan(math.radians(ang)), "DETALHE_ILUM",
                tracejado=True)
    d.cota_v_pts((0.40, 0.0), (0.15 + 0.07, z), 0.40 - 0.22)
    d.balao((0.15 + 0.07, z + bh), 0.62, z + bh + 0.16, 1)
    d.subtitulo("VISTA LATERAL", 0.30, -0.20)
    # vista frontal ---------------------------------------------------------------------------
    f0 = U + 0.60
    d.piso(f0, f0 + 1.0)
    uc = f0 + 0.5
    eq.bloco_frente(d, uc, z)
    if pd is not None:
        eq.forro(d, f0, f0 + 1.0, pd)
    d.balao((uc + 0.16, z + bh / 2), uc + 0.42, z + bh / 2, 1)
    d.subtitulo("VISTA FRONTAL", f0 + 0.2, -0.20)
    lm = f"{op.fluxo_lm} lm" if op.fluxo_lm else "FLUXO CONFORME PROJETO"
    d.tabela_itens(f0 + 1.25, topo - 0.10,
                   [(1, f"BLOCO AUTÔNOMO DE ILUMINAÇÃO DE EMERGÊNCIA, {lm}, AUTONOMIA "
                        f"MÍNIMA {minutos} min")])
    linhas = [
        f"AUTONOMIA MÍNIMA DE {minutos} min ({_ref(aut)})"
        + (f"; DIVISÃO {div}." if div else "."),
        f"INSTALAÇÃO, NÍVEL DE ILUMINAMENTO E DISTÂNCIA ENTRE PONTOS PELA {nbr.valor}, "
        f"ADOTADA PELA NT ({_ref(nbr)}).",
        f"NAS ESCADAS: UM PONTO NO NÍVEL DO PAVIMENTO E OUTRO NO PATAMAR INTERMEDIÁRIO, SEM "
        f"PONTO DE SOMBRA ({_ref(esc_)}).",
        f"ALTURA DE INSTALAÇÃO {_m(z)} m (INFORMADA); FACHO DE LUZ ILUSTRATIVO.",
    ]
    informado = [f"altura {_m(z)} m"] + ([f"pé-direito {_m(pd)} m"] if pd else []) + \
        ([f"fluxo {op.fluxo_lm} lm"] if op.fluxo_lm else [])
    medidas = [{"valor": f"{minutos} min", "o_que": aut.titulo, "fonte": aut.citacao}]
    return {"linhas": linhas, "medidas": medidas, "informado": informado, "altura": topo}


# --- sinalização de saída -------------------------------------------------------------------


def _sinalizacao(d: _D, op: Detalhe) -> dict[str, Any]:
    nsup, ninf, s12, s12f = (_p("det.placa.nivel_superior_min_m"),
                             _p("det.placa.nivel_inferior_max_m"), _p("det.placa.s12_nivel"),
                             _p("det.placa.s12_forma"))
    zs, zi = float(nsup.valor), float(ninf.valor)
    pw, _ph, informada = _placa_dims(op, (252, 126))
    porta_h, porta_w = 2.10, 0.90  # porta representada (a da planta manda)
    pd = op.pe_direito_m or 3.00
    topo = pd + 0.40
    # 1. acima da porta -----------------------------------------------------------------------
    eq.porta(d, 0.55, porta_w, porta_h)
    _w, h1 = eq.placa_nt(d, "S-12", 0.55 + porta_w / 2, porta_h + 0.08, pw)
    d.piso(0, 2.0)
    d.cota_v_pts((0.25, 0.0), (0.55 + porta_w / 2 - pw / 2, porta_h + 0.08),
                 0.25 - (0.55 + porta_w / 2 - pw / 2))
    d.subtitulo("ACIMA DA PORTA", 0.55, -0.40)
    # 2. na parede ----------------------------------------------------------------------------
    u2 = 2.5
    d.piso(u2, u2 + 1.7)
    eq.placa_nt(d, "S-1", u2 + 1.0, zs, pw)
    d.cota_v_pts((u2 + 0.30, 0.0), (u2 + 1.0 - pw / 2, zs), 0.30 - (1.0 - pw / 2))
    d.subtitulo("NA PAREDE", u2 + 0.4, -0.40)
    # 3. suspensa no teto ---------------------------------------------------------------------
    u3 = 4.7
    eq.laje_concreto(d, u3, u3 + 1.8, pd + 0.15, pd + 0.27)
    eq.forro(d, u3, u3 + 1.8, pd)
    zb3 = max(zs, pd - 0.55)
    eq.placa_suspensa(d, "S-1", u3 + 1.0, pd - 0.025, zb3, pw)
    d.piso(u3, u3 + 1.8)
    d.cota_v_pts((u3 + 0.30, 0.0), (u3 + 1.0 - pw / 2, zb3), 0.30 - (1.0 - pw / 2))
    d.subtitulo("SUSPENSA NO TETO", u3 + 0.4, -0.40)
    # 4. nível inferior -----------------------------------------------------------------------
    u4 = 7.0
    d.piso(u4, u4 + 1.6)
    _w4, h4 = eq.placa_nt(d, "S-1", u4 + 1.0, zi - pw * 0.5413, pw)
    d.cota_v_pts((u4 + 0.30, 0.0), (u4 + 1.0 - pw / 2, zi), 0.30 - (1.0 - pw / 2))
    d.subtitulo("NÍVEL INFERIOR", u4 + 0.4, -0.40)
    _placa_ampliada(d, "S-12", u4 + 2.0, 1.0, 1.0, s12f,
                    f"{round(pw * 1000)} x {round(pw * 0.5413 * 1000)} mm")
    linhas = [
        f"NÍVEL SUPERIOR: BASE DA PLACA A NO MÍNIMO {_m(zs)} m DO PISO ACABADO OU NO TETO "
        f"({_ref(nsup)}).",
        f"PLACA S-12 SOBRE A PORTA DE SAÍDA, NO NÍVEL {str(s12.valor).upper()} ({_ref(s12)}).",
        f"NÍVEL INFERIOR: NO PISO OU A NO MÁXIMO {_m(zi)} m ({_ref(ninf)}).",
        "PORTA REPRESENTADA COM 0,90 x 2,10 m E PÉ-DIREITO "
        f"{_m(pd)} m: VALEM AS MEDIDAS DA PLANTA.",
    ]
    linhas += _nota_placa(informada, "252x126")
    medidas = [{"valor": f"{_m(zs)} m", "o_que": nsup.titulo, "fonte": nsup.citacao},
               {"valor": f"{_m(zi)} m", "o_que": ninf.titulo, "fonte": ninf.citacao}]
    informado = [f"pé-direito {_m(pd)} m"] if op.pe_direito_m else []
    return {"linhas": linhas, "medidas": medidas, "informado": informado, "altura": topo}


_DESENHO = {"extintor": _extintor, "abrigo_mangueira": _abrigo,
            "recalque_passeio": _recalque_passeio, "recalque_fachada": _recalque_fachada,
            "bloco_autonomo": _bloco, "sinalizacao_saida": _sinalizacao,
            "central_glp": lambda d, op: _glp().central(d, op),
            "regulador_1_estagio": lambda d, op: _glp().regulador_1(d, op),
            "regulador_2_estagio": lambda d, op: _glp().regulador_2(d, op)}


def _glp():  # noqa: ANN202
    from coscip_mcp import detalhes_glp

    return detalhes_glp


def desenhar(doc, msp, op: Detalhe) -> dict[str, Any]:  # noqa: ANN001
    esc = op.escala or ESCALA_PADRAO[op.modelo]
    d = _D(doc, msp, op.x, op.y, esc)
    r = _DESENHO[op.modelo](d, op)
    # título acima e notas abaixo do desenho
    titulo = (op.titulo or TITULOS[op.modelo]).upper()
    zt = r["altura"] + 15 * d.k
    d.texto(titulo, 0.0, zt, apresentacao.TEXTO_TITULO_MM)
    d.texto(f"ESCALA 1:{esc}", 0.0, zt - 5.5 * d.k, 2.0, cor=8)
    z_base = (d.zmin if math.isfinite(d.zmin) else 0.0) - 8 * d.k
    largura = d.umax + 0.2
    z_fim = d.notas(r["linhas"], 0.0, z_base)
    out = {"modelo": op.modelo, "escala": f"1:{esc}", "titulo": titulo,
           "regiao_m": [round(op.x, 3), round(op.y + z_fim - 0.1, 3),
                        round(op.x + max(largura, d.umax + 0.1), 3),
                        round(op.y + zt + 0.1, 3)],
           "medidas_normativas": r["medidas"], "dados_informados": r["informado"]}
    if "duplo" in r:
        out["recalque_duplo"] = r["duplo"]
    return out


__all__ = ["Detalhe", "DetalheError", "desenhar"]
