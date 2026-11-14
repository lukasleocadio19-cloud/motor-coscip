from pathlib import Path

SAIDAS_EXEMPLO = Path(__file__).resolve().parents[1] / "saidas"
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pymupdf as fitz  # noqa: E402

from render_dxf import render_window  # noqa: E402

OUT = str(Path(__file__).resolve().parents[1] / "saidas" / "restaurante-400m2-projeto-incendio.pdf")
MM = 72 / 25.4
TOTAL = 3

PD, LAJE, PLAT, DOOR, WB, WT = 3.60, 3.80, 4.40, 2.10, 0.90, 2.10
DUCT, CAP, ABRI, ABRI_IN = 5.40, 5.62, 2.40, 2.20
BLACK = (0, 0, 0)
GRAY = (0.45, 0.45, 0.45)
LGRAY = (0.9, 0.9, 0.9)
RED = (0.85, 0.1, 0.1)
GREEN = (0.0, 0.6, 0.25)
ORANGE = (0.95, 0.6, 0.0)
BLUE = (0.78, 0.88, 0.96)
MAG = (0.75, 0.0, 0.5)


def tlen(t, size, font="helv"):
    return fitz.get_text_length(t, fontname=font, fontsize=size)


class Sheet:
    def __init__(self, doc, num, title, scale_txt):
        self.page = doc.new_page(width=420 * MM, height=297 * MM)
        p = self.page
        sh = p.new_shape()
        sh.draw_rect(fitz.Rect(10 * MM, 10 * MM, 410 * MM, 287 * MM))
        sh.finish(width=1.2, color=BLACK)
        sh.draw_rect(fitz.Rect(10 * MM, 268 * MM, 410 * MM, 287 * MM))
        sh.finish(width=0.7, color=BLACK)
        for x in (190, 310, 352):
            sh.draw_line(fitz.Point(x * MM, 268 * MM), fitz.Point(x * MM, 287 * MM))
        sh.finish(width=0.5, color=BLACK)
        sh.commit()
        self.text(12, 273, "RESTAURANTE (F-8) - ATC 400,00 m2 - 1 PAVIMENTO", 8.5, "hebo")
        self.text(12, 277.5, "Projeto de seguranca contra incendio e panico (COSCIP/CBMERJ) - RASCUNHO", 6.5)
        self.text(12, 281, "PROJETO FICTICIO - sem valor normativo - nao protocolar - sem responsavel tecnico", 6.5, color=RED)
        self.text(12, 284.6, "Dados de ocupacao, alturas e tipo de construcao sao premissas. Gerado em 09/11/2026 pelo motor COSCIP.", 5.5, color=GRAY)
        self.text(192, 273, "PRANCHA", 5.5, color=GRAY)
        self.text(192, 280, title, 9, "hebo")
        self.text(312, 273, "ESCALA", 5.5, color=GRAY)
        self.text(312, 280, scale_txt, 9, "hebo")
        self.text(354, 273, "FOLHA", 5.5, color=GRAY)
        self.text(354, 280, f"{num:02d}/{TOTAL:02d}", 11, "hebo")

    def text(self, x, y, t, size=6, font="helv", color=BLACK, rot=0):
        self.page.insert_text(fitz.Point(x * MM, y * MM), t, fontsize=size, fontname=font, color=color, rotate=rot)

    def ctext(self, x, y, t, size=6, font="helv", color=BLACK):
        self.text(x - tlen(t, size, font) / MM / 2, y, t, size, font, color)

    def box(self, x0, y0, x1, y1, t, size=6.5, font="helv", color=BLACK):
        r = fitz.Rect(x0 * MM, y0 * MM, x1 * MM, y1 * MM)
        s = size
        while s > 4:
            ok = self.page.insert_textbox(r, t, fontsize=s, fontname=font, color=color, align=0)
            if ok >= 0:
                return s
            s -= 0.3
            # insert_textbox ja desenhou parcialmente? ele retorna <0 sem desenhar
        self.page.insert_textbox(r, t, fontsize=4, fontname=font, color=color)
        return 4

    def rect(self, x0, y0, x1, y1, fill=None, w=0.5, color=BLACK):
        sh = self.page.new_shape()
        sh.draw_rect(fitz.Rect(x0 * MM, y0 * MM, x1 * MM, y1 * MM))
        sh.finish(width=w, color=color, fill=fill)
        sh.commit()

    def line(self, x0, y0, x1, y1, w=0.5, color=BLACK, dash=None):
        sh = self.page.new_shape()
        sh.draw_line(fitz.Point(x0 * MM, y0 * MM), fitz.Point(x1 * MM, y1 * MM))
        sh.finish(width=w, color=color, dashes=dash)
        sh.commit()


class V:
    """Vista em metros (x para a direita, h para cima) desenhada na folha a 'k' mm por metro."""

    def __init__(self, sh, ox, gy, k=8.0):
        self.s, self.ox, self.gy, self.k = sh, ox, gy, k

    def X(self, x):
        return self.ox + x * self.k

    def Y(self, h):
        return self.gy - h * self.k

    def line(self, x0, h0, x1, h1, w=0.5, color=BLACK, dash=None):
        self.s.line(self.X(x0), self.Y(h0), self.X(x1), self.Y(h1), w, color, dash)

    def rect(self, x0, h0, x1, h1, fill=None, w=0.5, color=BLACK):
        self.s.rect(self.X(x0), self.Y(h1), self.X(x1), self.Y(h0), fill, w, color)

    def poly(self, pts, fill=None, w=0.5, color=BLACK):
        sh = self.s.page.new_shape()
        sh.draw_polyline([fitz.Point(self.X(x) * MM, self.Y(h) * MM) for x, h in pts])
        sh.finish(width=w, color=color, fill=fill, closePath=True)
        sh.commit()

    def hatch(self, x0, h0, x1, h1, gap=0.16, fill=LGRAY):
        self.rect(x0, h0, x1, h1, fill=fill, w=0.5)
        c = x0 + h0 + gap
        while c < x1 + h1:
            xa, xb = max(x0, c - h1), min(x1, c - h0)
            if xa < xb:
                self.line(xa, c - xa, xb, c - xb, w=0.15, color=GRAY)
            c += gap

    def t(self, x, h, txt, size=5.5, font="helv", color=BLACK, center=False, rot=0):
        if center:
            self.s.text(self.X(x) - tlen(txt, size, font) / MM / 2, self.Y(h), txt, size, font, color)
        else:
            self.s.text(self.X(x), self.Y(h), txt, size, font, color, rot)

    def dim_h(self, x0, x1, h, txt, size=5.5):
        self.line(x0, h, x1, h, w=0.3)
        for x in (x0, x1):
            self.line(x, h - 0.12, x, h + 0.12, w=0.3)
            self.line(x - 0.08, h - 0.08, x + 0.08, h + 0.08, w=0.5)
        self.t((x0 + x1) / 2, h + 0.18, txt, size, center=True)

    def dim_v(self, x, h0, h1, txt, size=5.5):
        self.line(x, h0, x, h1, w=0.3)
        for h in (h0, h1):
            self.line(x - 0.12, h, x + 0.12, h, w=0.3)
            self.line(x - 0.08, h - 0.08, x + 0.08, h + 0.08, w=0.5)
        self.t(x - 0.2, (h0 + h1) / 2, txt, size, rot=90)

    def ground(self, x0, x1):
        self.line(x0, 0, x1, 0, w=1.1)
        h = 0.0
        x = x0
        while x < x1:
            self.line(x, 0, x - 0.25, -0.25, w=0.15, color=GRAY)
            x += 0.4

    def wall(self, x0, x1, top, openings=()):
        cur = 0.0
        for a, b in sorted(openings):
            if a > cur:
                self.hatch(x0, cur, x1, a)
            cur = b
        if top > cur:
            self.hatch(x0, cur, x1, top)

    def ie(self, x, h=2.5):
        self.rect(x - 0.15, h, x + 0.15, h + 0.13, fill=(1, 0.85, 0.5), w=0.4, color=ORANGE)
        self.line(x, h + 0.13, x, PD, w=0.3, color=ORANGE)

    def ext(self, x, h0=0.95, label=""):
        self.rect(x - 0.15, h0, x + 0.15, h0 + 0.55, fill=(1, 0.8, 0.8), w=0.6, color=RED)
        self.rect(x - 0.07, h0 + 0.55, x + 0.07, h0 + 0.68, fill=RED, w=0.3, color=RED)
        self.rect(x - 0.2, h0 + 0.85, x + 0.2, h0 + 1.25, fill=(1, 0.9, 0.9), w=0.5, color=RED)
        if label:
            self.t(x, h0 + 1.38, label, 4.5, center=True, color=RED)

    def sign(self, x, h, txt, color=GREEN, w=0.5):
        self.rect(x - w / 2, h, x + w / 2, h + 0.4, fill=(0.8, 0.95, 0.85) if color == GREEN else (1, 0.85, 0.85), w=0.5, color=color)
        self.t(x, h + 0.14, txt, 3.8, center=True, color=color)


def arrow_tri(sh, pts, color):
    s = sh.page.new_shape()
    s.draw_polyline([fitz.Point(x * MM, y * MM) for x, y in pts])
    s.finish(width=0.3, color=color, fill=color, closePath=True)
    s.commit()


# ------------------------------------------------------------------ PRANCHA 1
def prancha1(doc):
    sh = Sheet(doc, 1, "PLANTA BAIXA - TERREO", "1:100")
    WIN = [-3, -4.2, 28.5, 21]
    PX0, PY0 = 13, 12
    pdf = render_window(WIN, 10, exclude_text=("PLANTA BAIXA", "RESTAURANTE (F-8)"),
                        exclude_pred=lambda e: e.dxftype() == "DIMENSION")
    src = fitz.open(stream=pdf, filetype="pdf")
    w, h = (WIN[2] - WIN[0]) * 10, (WIN[3] - WIN[1]) * 10
    sh.page.show_pdf_page(fitz.Rect(PX0 * MM, PY0 * MM, (PX0 + w) * MM, (PY0 + h) * MM), src, 0)

    def mx(x):
        return PX0 + (x - WIN[0]) * 10

    def my(y):
        return PY0 + (WIN[3] - y) * 10

    # cotas
    y = -3.3
    sh.line(mx(0), my(y), mx(25), my(y), 0.4)
    for x in (0, 25):
        sh.line(mx(x), my(y) - 1.2, mx(x), my(y) + 1.2, 0.4)
        sh.line(mx(x) - 0.8, my(y) + 0.8, mx(x) + 0.8, my(y) - 0.8, 0.8)
    sh.ctext(mx(12.5), my(y) - 1.0, "25,00", 7)
    x = 27.4
    sh.line(mx(x), my(0), mx(x), my(16), 0.4)
    for yy in (0, 16):
        sh.line(mx(x) - 1.2, my(yy), mx(x) + 1.2, my(yy), 0.4)
        sh.line(mx(x) - 0.8, my(yy) + 0.8, mx(x) + 0.8, my(yy) - 0.8, 0.8)
    sh.text(mx(x) - 1.2, my(8) + 5, "16,00", 7, rot=90)
    # linhas de corte
    sh.line(mx(-1.2), my(7.6), mx(26.0), my(7.6), 0.5, MAG, "[8 2 1 2] 0")
    sh.line(mx(9.8), my(-2.3), mx(9.8), my(20.0), 0.5, MAG, "[8 2 1 2] 0")
    for x0 in (-1.2, 26.0):
        arrow_tri(sh, [(mx(x0) - 1.3, my(7.6)), (mx(x0) + 1.3, my(7.6)), (mx(x0), my(7.6) - 3)], MAG)
    for y0 in (-2.3, 20.0):
        arrow_tri(sh, [(mx(9.8), my(y0) - 1.3), (mx(9.8), my(y0) + 1.3), (mx(9.8) + 3, my(y0))], MAG)
    # norte
    cx, cy = 322, 30
    sh.page.draw_circle(fitz.Point(cx * MM, cy * MM), 7 * MM, color=BLACK, width=0.6)
    arrow_tri(sh, [(cx, cy - 6), (cx - 2.2, cy + 3), (cx + 2.2, cy + 3)], BLACK)
    sh.ctext(cx, cy + 11, "N", 8, "hebo")
    # coluna de notas
    x0, x1 = 334, 408
    sh.rect(x0, 12, x1, 262, w=0.5)
    sh.text(x0 + 2, 17, "DADOS E RESULTADOS", 7.5, "hebo")
    notas = (
        "OCUPACAO: F-8 local para refeicao (premissa: 'restaurante'). Risco MEDIO 1 (NT 1-04).\n"
        "ATC 400,00 m2; 1 pavimento; altura 4,40 m (premissa); construcao tipo BETA (premissa).\n\n"
        "EXIGIDO (Anexo III, Tab. 2): extintores; sinalizacao; iluminacao de emergencia; saidas de emergencia; controle de materiais de acabamento. Hidrante e alarme: nao marcados na tabela.\n\n"
        "SAIDAS (NT 2-08): populacao 351 pessoas (350,48 m2 = 400 menos sanitarios, 5.2.4); N = 4 unidades de passagem, largura minima 2,20 m; minimo 2 saidas. Salao: P1 2,00 + P2 2,00 + P3 1,20 = 5,20 m, portas abrindo para fora com barra antipanico (lotacao > 200). Servico: P4 cozinha 1,00 m e P5 recebimento 1,20 m.\n\n"
        "EXTINTORES (NT 2-01): 3 pela area (150 m2 por unidade) + 2 instalacoes especiais = 5 calculados; 7 desenhados (E1-E5 PQS ABC, K na cozinha, E6 central de GLP).\n\n"
        "ILUMINACAO (NT 2-06): 21 pontos, autonomia 60 min.\n\n"
        "MOTOR COSCIP (unidade confirmada por 2 medidas de projeto): maior percurso ate extintor 12,8 m (+/- 0,6) para limite de 15 m; ate a saida 16,5 m (+/- 0,6) para limite de 30 m (Anexo C, BETA, 2 saidas, leiaute definido); distancia direta 13,3 m. Verificacao do percurso ate a saida depende de o usuario confirmar as saidas.\n\n"
        "COZINHA E GLP: ver pranchas 02 e 03 e o memorial (NT 3-01 e NT 3-02).\n\n"
        "NAO CONSTA DA PLANTA: projeto de exaustao (NBR 14518), espacamento da iluminacao (NBR 10898), implantacao do lote e distancia ao passeio."
    )
    sh.box(x0 + 2, 20, x1 - 2, 258, notas, 6.2)
    doc.set_metadata({"title": "Restaurante F-8 400 m2 - projeto de incendio (rascunho ficticio)"})


# ------------------------------------------------------------------ PRANCHA 2
def corte_aa(sh, ox, gy):
    v = V(sh, ox, gy)
    v.t(-1.8, 5.9, "CORTE A-A (olhando para o norte)", 8, "hebo")
    v.ground(-1.6, 26.4)
    v.hatch(0, -0.12, 25, 0, gap=0.2)
    v.wall(0, 0.2, PLAT, [(WB, WT)])
    v.rect(0, WB, 0.2, WT, fill=BLUE, w=0.6)
    v.wall(24.8, 25.0, PLAT)
    for a, b in ((16.8, 17.0), (18.8, 19.0), (21.8, 22.0)):
        v.wall(a, b, PD)
    v.hatch(0, PD, 25, LAJE, gap=0.2)
    v.hatch(-0.1, PLAT - 0.0, 0.0, PLAT, gap=0.2) if False else None
    for x in (2.5, 7, 11.5, 15, 17.9, 20.4):
        v.ie(x)
    v.ext(16.55, label="E3")
    v.t(0.3, 1.5, "J2", 4.5, color=BLACK)
    v.t(8.5, 1.8, "SALAO DE REFEICOES", 7, "hebo", center=True)
    v.t(8.5, 1.4, "A = 179,28 m2  -  pe-direito 3,60 m", 5.5, center=True)
    v.t(17.9, 1.8, "CIRC.", 4.5, center=True)
    v.t(20.4, 1.8, "WC PCD", 5, center=True)
    v.t(23.4, 1.8, "DML", 5, center=True)
    v.t(8.5, 3.15, "IE = iluminacao de emergencia (ponto a 2,50 m)", 4.5, center=True, color=ORANGE)
    # cotas
    v.dim_v(-0.7, 0, PD, "3,60")
    v.dim_v(-1.3, 0, PLAT, "4,40")
    v.dim_h(0.2, 16.8, -0.7, "16,60")
    v.dim_h(17.0, 18.8, -0.7, "1,80")
    v.dim_h(19.0, 21.8, -0.7, "2,80")
    v.dim_h(22.0, 24.8, -0.7, "2,80")
    v.dim_h(0, 25, -1.4, "25,00")
    for h, txt in ((0, "+0,00"), (PD, "+3,60 (forro)"), (LAJE, "+3,80 (laje)"), (PLAT, "+4,40 (platibanda)")):
        v.line(25.0, h, 25.5, h, w=0.3)
        v.t(25.6, h - 0.05, txt, 4.8)
    v.t(0.0, -2.0, "Esc. 1:125 - cota de piso +0,00 - esquematico, sem estrutura", 4.8, color=GRAY)


def corte_bb(sh, ox, gy):
    v = V(sh, ox, gy)
    v.t(-1.8, 6.25, "CORTE B-B (olhando para o leste)", 8, "hebo")
    v.ground(-1.6, 19.6)
    v.hatch(0, -0.12, 16.0, 0, gap=0.2)
    v.wall(0, 0.2, PLAT, [(0, DOOR)])
    v.rect(0.04, 0, 0.16, DOOR, fill=BLUE, w=0.6)
    v.wall(11.0, 11.2, PD)
    v.wall(15.8, 16.0, PLAT)
    v.hatch(0, PD, 16.0, LAJE, gap=0.2)
    for u in (2.5, 8.5, 13.5):
        v.ie(u)
    v.t(5.6, 1.9, "SALAO DE REFEICOES", 7, "hebo", center=True)
    v.t(5.6, 1.45, "A = 179,28 m2", 5.5, center=True)
    v.t(13.5, 1.9, "COZINHA", 7, "hebo", center=True)
    v.t(13.5, 1.45, "A = 57,04 m2", 5.5, center=True)
    v.t(0.55, 2.3, "P2 2,00 x 2,10 - abre p/ fora - barra antipanico", 4.3)
    v.sign(0.55, 2.7, "S-12")
    # equipamentos cortados
    v.hatch(12.8, 0, 13.5, 0.9, gap=0.14, fill=(0.82, 0.87, 0.92))
    v.t(13.15, 1.0, "5", 5, center=True)
    v.hatch(14.8, 0, 15.7, 0.9, gap=0.14, fill=(0.82, 0.87, 0.92))
    v.t(15.25, 1.0, "3", 5, center=True)
    v.poly([(14.6, 2.0), (15.75, 2.0), (15.45, 2.7), (14.95, 2.7)], fill=(0.93, 0.93, 0.95), w=0.6)
    v.t(15.17, 2.2, "COIFA", 4.2, center=True)
    v.rect(14.95, 2.7, 15.45, DUCT, fill=(0.96, 0.96, 0.96), w=0.7)
    v.hatch(14.9, PD, 15.5, LAJE, gap=0.08, fill=(0.7, 0.7, 0.7))
    v.poly([(14.75, DUCT), (15.65, DUCT), (15.2, CAP)], fill=(0.85, 0.85, 0.85), w=0.6)
    v.t(4.0, 5.45, "DUTO DE EXAUSTAO: aco carbono >= 1,37 mm, aparente, unico, sobe direto a cobertura", 4.8, "hebo")
    v.t(4.0, 5.2, "e sai 1,60 m acima da laje (+5,40); nao cruza outro ambiente (NT 3-01, 2.1 e 2.2)", 4.5)
    v.line(11.9, 5.3, 14.7, 5.0, w=0.3, color=GRAY)
    v.t(15.75, 5.55, "+5,40", 4.8)
    # central de GLP
    v.hatch(16.0, -0.06, 17.8, 0, gap=0.2)
    v.hatch(16.0, ABRI_IN, 17.8, ABRI, gap=0.14)
    v.rect(16.0, 0, 17.6, ABRI_IN, w=0.4, color=GRAY)
    v.line(17.6, 0, 17.6, ABRI_IN, w=0.6, dash="[3 2] 0")
    v.hatch(16.21, 0, 16.59, 1.25, gap=0.12, fill=(0.7, 0.75, 0.8))
    v.rect(16.3, 1.25, 16.5, 1.38, fill=GRAY, w=0.4)
    v.t(16.4, 0.45, "P-45", 4.2, center=True)
    for hh, txt, fnt in ((-2.05, "CENTRAL DE GLP (abrigo a direita): 4 x P-45 = 180 kg; abrigo TRRF 120 min (5.3.2 b); altura util 2,20 m;", "hebo"),
                         (-2.3, "piso de concreto >= 5 cm; lado norte aberto com portas incombustiveis p/ fora; ventilacao 10% da planta (0,32 m2)", "helv")):
        v.t(17.8 - tlen(txt, 4.4, fnt) / MM / v.k, hh, txt, 4.4, fnt)
    # cotas
    v.dim_v(-0.7, 0, PD, "3,60")
    v.dim_v(-1.3, 0, PLAT, "4,40")
    v.dim_h(0.2, 11.0, -0.7, "10,80")
    v.dim_h(11.2, 15.8, -0.7, "4,60")
    v.dim_h(16.0, 17.6, -0.7 - 0.0, "1,60") if False else None
    v.dim_h(0, 17.6, -1.4, "17,60 (ate a abertura do abrigo)")
    v.t(0.0, -2.6, "Esc. 1:125 - esquematico; pe-direito 3,60 m; laje 0,20 m", 4.8, color=GRAY)


def fachada_base(v, w, label, x_label=-1.0):
    v.t(x_label, 6.25, label, 8, "hebo")
    v.ground(-1.2, w + 1.2)
    v.rect(0, 0, w, PLAT, fill=(0.96, 0.95, 0.92), w=0.8)
    v.rect(-0.08, PLAT, w + 0.08, PLAT + 0.1, fill=(0.7, 0.7, 0.7), w=0.6)
    v.line(0, LAJE, w, LAJE, w=0.2, color=GRAY, dash="[2 2] 0")
    for h, txt in ((0, "+0,00"), (PLAT, "+4,40 platibanda"), (DUCT, "+5,40 duto")):
        v.line(w, h, w + 0.4, h, w=0.3)
        v.t(w + 0.5, h - 0.05, txt, 4.6)


def duct(v, x):
    v.rect(x - 0.25, PLAT + 0.1, x + 0.25, DUCT, fill=(0.93, 0.93, 0.93), w=0.7)
    v.poly([(x - 0.45, DUCT), (x + 0.45, DUCT), (x, CAP)], fill=(0.85, 0.85, 0.85), w=0.6)


def door(v, x0, x1, h=DOOR, tag="", glass=True):
    v.rect(x0, 0, x1, h, fill=BLUE if glass else (0.75, 0.75, 0.75), w=0.8)
    xm = (x0 + x1) / 2
    if x1 - x0 > 1.5:
        v.line(xm, 0, xm, h, w=0.5)
    v.line(x0 + 0.1, 1.0, x0 + 0.1 + (x1 - x0) * 0.35, 1.0, w=0.9, color=GRAY)
    if tag:
        v.t(xm, h + 0.12, tag, 4.6, center=True)


def window(v, x0, x1, tag):
    v.rect(x0, WB, x1, WT, fill=BLUE, w=0.8)
    xm = (x0 + x1) / 2
    v.line(xm, WB, xm, WT, w=0.4)
    v.t(xm, WT + 0.12, tag, 4.6, center=True)


def fach_sul(sh, ox, gy):
    v = V(sh, ox, gy)
    fachada_base(v, 25, "FACHADA SUL (frontal)", -1.8)
    duct(v, 9.8)
    door(v, 3, 5, tag="P1 2,00 x 2,10")
    door(v, 9, 11, tag="P2 2,00 x 2,10")
    v.sign(4, 2.4, "S-12")
    v.sign(10, 2.4, "S-12")
    window(v, 12.0, 15.5, "J3 3,50 x 1,20 (peitoril 0,90)")
    v.t(17.5, 2.6, "WC / circulacao: parede cega", 5, color=GRAY)
    v.dim_h(0, 3, -0.6, "3,00")
    v.dim_h(3, 5, -0.6, "2,00")
    v.dim_h(5, 9, -0.6, "4,00")
    v.dim_h(9, 11, -0.6, "2,00")
    v.dim_h(11, 12, -0.6, "1,00")
    v.dim_h(12, 15.5, -0.6, "3,50")
    v.dim_h(15.5, 25, -0.6, "9,50")
    v.dim_h(0, 25, -1.3, "25,00")


def fach_norte(sh, ox, gy):
    v = V(sh, ox, gy)
    fachada_base(v, 25, "FACHADA NORTE (fundos)", -1.8)

    def X(x):
        return 25 - x

    duct(v, X(9.8))
    door(v, X(3.5), X(2.5), tag="P4 1,00 x 2,10 (saida cozinha)", glass=False)
    # abrigo de GLP, lado aberto voltado para o observador
    v.hatch(X(11.4), 0, X(9.0), ABRI, gap=0.14)
    v.rect(X(11.2), 0, X(9.2), ABRI_IN, fill=(1, 1, 1), w=0.6)
    h = 0.12
    while h < ABRI_IN:
        v.line(X(11.2), h, X(9.2), h, w=0.15, color=GRAY)
        h += 0.14
    for x in (9.5, 9.95, 10.4, 10.85):
        v.rect(X(x) - 0.19, 0, X(x) + 0.19, 1.25, fill=(0.7, 0.75, 0.8), w=0.5)
    v.t(X(10.2), 2.6, "CENTRAL DE GLP (abrigo TRRF 120)", 4.8, "hebo", center=True)
    for x, tag in ((9.6, "P-1"), (10.2, "A-2"), (10.8, "A-3")):
        v.sign(X(x), 2.95, tag, color=RED, w=0.45)
    v.ext(X(8.4), label="E6")
    v.t(X(8.4) + 0.4, 0.55, "registro geral", 4.0)
    v.t(X(8.4) + 0.4, 0.35, "de corte", 4.0)
    v.rect(X(0.6) - 0.3, -0.12, X(0.6) + 0.3, 0.05, fill=LGRAY, w=0.5)
    v.t(X(0.6), 0.25, "CX. GORDURA", 4.0, center=True)
    v.dim_h(0, X(11.4), -0.6, "13,60")
    v.dim_h(X(11.4), X(9.0), -0.6, "2,40")
    v.dim_h(X(9.0), X(3.5), -0.6, "5,50")
    v.dim_h(X(3.5), X(2.5), -0.6, "1,00")
    v.dim_h(X(2.5), 25, -0.6, "2,50")
    v.dim_h(0, 25, -1.3, "25,00")


def fach_oeste(sh, ox, gy):
    v = V(sh, ox, gy)
    fachada_base(v, 16, "FACHADA OESTE", -1.0)

    def X(y):
        return 16 - y

    v.rect(X(17.6), 0, X(16.0), ABRI, fill=(0.82, 0.82, 0.82), w=0.4, color=GRAY)
    v.t(X(16.8), 1.0, "GLP", 4.5, center=True, color=GRAY)
    duct(v, X(15.25))
    window(v, X(8.6), X(6.6), "J2 2,00 x 1,20")
    door(v, X(6.2), X(5.0), tag="P3 1,20 x 2,10")
    v.sign(X(5.6), 2.4, "S-12")
    window(v, X(4.4), X(1.4), "J1 3,00 x 1,20")
    v.t(X(13.6), 2.4, "cozinha: parede cega", 5, color=GRAY)
    v.dim_h(0, X(8.6), -0.6, "7,40")
    v.dim_h(X(8.6), X(6.6), -0.6, "2,00")
    v.dim_h(X(6.6), X(6.2), -0.6, "0,40")
    v.dim_h(X(6.2), X(5.0), -0.6, "1,20")
    v.dim_h(X(5.0), X(4.4), -0.6, "0,60")
    v.dim_h(X(4.4), X(1.4), -0.6, "3,00")
    v.dim_h(X(1.4), 16, -0.6, "1,40")
    v.dim_h(0, 16, -1.3, "16,00")


def fach_leste(sh, ox, gy):
    v = V(sh, ox, gy)
    fachada_base(v, 16, "FACHADA LESTE", -1.0)
    v.rect(16.0, 0, 17.6, ABRI, fill=(0.82, 0.82, 0.82), w=0.4, color=GRAY)
    v.t(16.8, 1.0, "GLP", 4.5, center=True, color=GRAY)
    duct(v, 15.25)
    door(v, 12.9, 14.1, glass=False, tag="P5 1,20 x 2,10 (saida servico)")
    v.t(4.0, 2.4, "WC / DML / circulacao: parede cega", 5, color=GRAY)
    v.dim_h(0, 12.9, -0.6, "12,90")
    v.dim_h(12.9, 14.1, -0.6, "1,20")
    v.dim_h(14.1, 16, -0.6, "1,90")
    v.dim_h(0, 16, -1.3, "16,00")


def prancha2(doc):
    sh = Sheet(doc, 2, "CORTES E FACHADAS", "1:125")
    rows = (20, 100, 180)  # y (mm) do titulo de cada linha
    gy = [r + 5.9 * 8 + 4 for r in rows]
    corte_aa(sh, 12 + 1.8 * 8, gy[0])
    fach_sul(sh, 12 + 1.8 * 8, gy[1])
    fach_norte(sh, 12 + 1.8 * 8, gy[2])
    ox2 = 248
    corte_bb(sh, ox2 + 1.8 * 8, gy[0])
    fach_oeste(sh, ox2 + 1.0 * 8, gy[1])
    fach_leste(sh, ox2 + 1.0 * 8, gy[2])
    sh.box(246, 247, 408, 265,
           "NOTAS: pe-direito 3,60 m; laje de cobertura 0,20 m (+3,80); platibanda +4,40 m. Alturas, esquadrias e dimensoes do abrigo sao premissas do projeto ficticio, desenhadas de forma esquematica a partir da planta baixa (prancha 01). "
           "Cortes A-A (y = 7,60) e B-B (x = 9,80) marcados na planta. Duto de exaustao: unico, vertical, sem travessia de outros ambientes (NT 3-01, 2.1 e 2.2); projeto de exaustao pela ABNT NBR 14518 fica a cargo do responsavel tecnico. "
           "Portas de saida do salao abrem para fora (NT 2-08, 5.3.4.1).", 5.6)


# ------------------------------------------------------------------ PRANCHA 3
def prancha3(doc):
    sh = Sheet(doc, 3, "LEGENDA, QUADROS E NOTAS", "S/ ESC.")
    # legenda DXF
    sh.text(12, 17, "LEGENDA DOS SIMBOLOS (NT 1-03 e NT 2-05)", 8, "hebo")
    WIN = [33.2, -5.5, 45.0, 16.4]
    SC = 9
    pdf = render_window(WIN, SC, exclude_text=("ESQUADRIAS:",))
    src = fitz.open(stream=pdf, filetype="pdf")
    w, h = (WIN[2] - WIN[0]) * SC, (WIN[3] - WIN[1]) * SC
    sh.page.show_pdf_page(fitz.Rect(12 * MM, 20 * MM, (12 + w) * MM, (20 + h) * MM), src, 0)
    y0 = 17
    sh.text(126, y0, "EQUIPAMENTOS DA COZINHA", 8, "hebo")
    sh.box(126, y0 + 2, 188, y0 + 150,
           "1  Fogao 6 bocas (GLP) - equipamento moderado\n2  Chapa de grelhados (GLP) - severo\n3  Fritadeira 2 cubas (GLP) - moderado\n4  Forno combinado (GLP) - moderado\n"
           "5  Ilha de preparo\n6  Refrigeracao\n7  Pia de panelas\n8  Lava-loucas\n\n"
           "Sob a mesma coifa ha equipamento moderado e severo: exaustao Tipo I (NT 3-01, 5.5.1). Edificacao de economia unica. "
           "Coifa + duto unico, aparente, sobe a cobertura. Extintor classe K junto a linha de coccao (distancia maxima 10 m, NT 2-01 Tab. 5); "
           "a NT 1-03 nao tem simbolo para classe K: na planta ele usa o simbolo do extintor AP, com a anotacao 'EXT. CLASSE K'.", 6.4)

    # quadro de extintores
    x0 = 192
    sh.text(x0, 17, "QUADRO DE EXTINTORES (NT 2-01 e NT 3-02)", 8, "hebo")
    cols = [(x0, 12, "ID"), (x0 + 12, 52, "TIPO / CAPACIDADE"), (x0 + 64, 92, "LOCAL"), (x0 + 156, 34, "POSICAO x ; y (m)")]
    rows = [
        ("E1", "PQS ABC 2-A:20-B:C", "Salao - parede sul entre as portas", "7,00 ; 0,60"),
        ("E2", "PQS ABC 2-A:20-B:C", "Salao - parede oeste, lado norte", "0,60 ; 9,80"),
        ("E3", "PQS ABC 2-A:20-B:C", "Salao - parede leste, junto a circulacao", "16,40 ; 8,00"),
        ("E4", "PQS ABC 2-A:20-B:C", "Cozinha - junto a porta do salao", "8,00 ; 11,50"),
        ("K", "Classe K (a criterio do projetista)", "Cozinha - extremo oeste da linha de coccao", "6,10 ; 14,55"),
        ("E5", "PQS ABC 2-A:20-B:C", "Recebimento - saida de servico e QGBT (<= 5 m)", "24,40 ; 12,60"),
        ("E6", "PQS 6 kg (20-B:C)", "Central de GLP (<= 10 m, NT 3-02 5.4.2)", "8,40 ; 17,20"),
    ]
    ty = 20
    sh.rect(x0, ty, x0 + 190, ty + 6, fill=LGRAY, w=0.5)
    for cx, cw, t in cols:
        sh.text(cx + 1.2, ty + 4.2, t, 5.6, "hebo")
    for i, r in enumerate(rows):
        yy = ty + 6 + i * 6.2
        sh.rect(x0, yy, x0 + 190, yy + 6.2, w=0.35)
        for (cx, cw, _), t in zip(cols, r):
            sh.text(cx + 1.2, yy + 4.2, t, 5.6)
    for cx, cw, _ in cols[1:]:
        sh.line(cx, ty, cx, ty + 6 + len(rows) * 6.2, 0.35)
    yb = ty + 6 + len(rows) * 6.2 + 4
    sh.box(x0, yb, x0 + 190, yb + 26,
           "Calculo (NT 2-01): risco MEDIO; area 400 m2 / 150 m2 por unidade = 3; minimo 2; + 1 por instalacao especial (GLP e quadro eletrico) = 5. "
           "Desenhados 7 (E4 e K acrescentados para a cozinha). Altura maxima da alca 1,60 m; distancia maxima a percorrer 15 m (K: 10 m). "
           "Cada extintor leva placa E-5 (NT 2-05). Medido pelo motor: maior percurso ate um extintor 12,8 m (+/- 0,6).", 6.0)

    # saidas / iluminacao / sinalizacao
    ty2 = yb + 30
    sh.text(x0, ty2, "SAIDAS, ILUMINACAO E SINALIZACAO", 8, "hebo")
    sh.box(x0, ty2 + 2, x0 + 190, ty2 + 56,
           "SAIDAS (NT 2-08): populacao 351 pessoas (area 350,48 m2 = 400 menos sanitarios 49,52 m2, 1 pessoa/m2); N = 4 unidades de passagem; largura minima de acessos 2,20 m; minimo 2 saidas (grupo F). "
           "Salao: P1 2,00 m, P2 2,00 m e P3 1,20 m = 5,20 m, abrindo para fora, com barra antipanico (lotacao > 200, 5.3.4.9). Servico: P4 (cozinha) 1,00 m e P5 (recebimento) 1,20 m. "
           "Limite de percurso 30 m (Anexo C, BETA, 2 saidas, leiaute definido); medido 16,5 m (+/- 0,6).\n\n"
           "ILUMINACAO DE EMERGENCIA (NT 2-06): 21 pontos ao longo das rotas, portas de saida, corredor, sanitarios, cozinha e recebimento; autonomia 60 min. Espacamento e iluminamento pela NBR 10898 (fora da base): a definir.\n\n"
           "SINALIZACAO (NT 2-05): S-12 sobre as 5 saidas; E-5 em cada extintor; P-1, A-2 e A-3 e a placa PERIGO / GAS INFLAMAVEL / PROIBIDO FUMAR na central de GLP.", 6.0)

    # GLP
    ty3 = ty2 + 62
    sh.text(x0, ty3, "CENTRAL DE GLP (NT 3-02)", 8, "hebo")
    sh.box(x0, ty3 + 2, x0 + 190, ty3 + 50,
           "4 x P-45 trocaveis = 180 kg (0,432 m3), em linha unica, no terreo, fora da projecao da edificacao, junto a fachada norte (5.2.1). Abrigo com paredes e cobertura TRRF >= 120 min (acima de 90 kg, 5.3.2 b), piso de concreto >= 5 cm, altura util 2,20 m (>= 1,80), "
           "lado maior aberto com portas incombustiveis para fora e ventilacao >= 0,32 m2 (10% da planta de 3,20 m2). Afastamentos (Anexo A): edificacao 0 m; aberturas e fontes de ignicao 1,5 m (reduzivel a metade com o abrigo); caixa de gordura >= 1,0 m (esta a mais de 8 m); passeio publico 3 m (depende do lote). "
           "Extintor 20-B:C ate 10 m (E6 a cerca de 2 m). Registro geral de corte junto a central (6.2). Sem hidrante exigido, resfriamento ou SPDA.", 6.0)

    # pendencias
    ty4 = ty3 + 54
    sh.text(x0, ty4, "PENDENCIAS E PREMISSAS (revisao do responsavel tecnico)", 8, "hebo", color=RED)
    sh.box(x0, ty4 + 2, x0 + 190, 264,
           "- Ocupacao F-8, 1 pavimento, 400 m2, altura 4,40 m e construcao tipo BETA sao premissas minhas; as saidas nao foram confirmadas pelo usuario.\n"
           "- Cozinha: confirmar que o duto nao cruza outro ambiente; se cruzar, aplicar damper corta-fogo, selagem e protecao passiva (Tabela 2 da NT 3-01; sem sistema fixo na economia unica). Dimensionar o extintor classe K.\n"
           "- GLP: ART da central e do ensaio de estanqueidade (5.3.9, 6.4), nota no Quadro Resumo (8.2), representacao em corte e planta de situacao, distancia ao lote.\n"
           "- Esquadrias J1 a J3 so existem como texto na planta (o motor nao desenha janelas); conferir a observacao 4 da Tabela 2 (edificacoes sem janelas).\n"
           "- Fora da base do motor: NBR 14518 (exaustao), NBR 10898 (iluminacao), NBR 13523 e NBR 15358 (GLP). Controle de materiais de acabamento (NT 2-20) e plano de emergencia nao detalhados.\n"
           "- Barras antipanico aparecem desenhadas mas o motor nao as conta como equipamento.", 5.9)


doc = fitz.open()
prancha1(doc)
prancha2(doc)
prancha3(doc)
doc.save(OUT, deflate=True, garbage=3)
print("salvo", OUT, len(doc), "paginas")
for i, p in enumerate(doc):
    p.get_pixmap(dpi=75).save(rf"{SAIDAS_EXEMPLO}\prancha{i + 1}.png")
