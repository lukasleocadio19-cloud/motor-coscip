"""Desenho dos equipamentos em vista para os detalhes de instalação (frente G2, 13/11/2026).

O nível de desenho segue os detalhes de uma prancha protocolada no CBMERJ (extintor com cúpula,
válvula, manômetro, alavanca, mangueira e frisos do cilindro; suportes de parede e de piso;
parede em alvenaria com os tijolos em corte; porta com batente, dobradiças e maçaneta; placa com
o pictograma oficial; placa suspensa por tirantes; bloco autônomo com as lâmpadas). Nada aqui é
medida de norma: as proporções são de representação. As medidas normativas (alturas, dimensões
mínimas) vêm de ``detalhes.py``, que posiciona estes desenhos.

Todas as funções recebem o desenho local ``d`` de ``detalhes._D`` (u para a direita, z para
cima, metros reais) e devolvem pontos de referência para chamadas e balões.
"""

from __future__ import annotations

import math
from typing import Any

from coscip_mcp import simbologia

# dimensões aproximadas de representação (Ø, altura até a alavanca), em m — confirmar com o
# fabricante; a norma não as fixa
DIMENSOES_EXTINTOR = (
    (("AP", "ÁGUA", "AGUA"), (0.18, 0.72)),
    (("CO2", "CO₂", "CARBÔNICO", "CARBONICO"), (0.15, 0.70)),
    (("12 KG", "12KG"), (0.20, 0.66)),
    (("8 KG", "8KG"), (0.17, 0.60)),
    (("4 KG", "4KG", "4,5"), (0.14, 0.48)),
    (("6 KG", "6KG"), (0.16, 0.54)),
)


def dimensoes_extintor(agente: str) -> tuple[float, float]:
    a = agente.upper()
    for chaves, dim in DIMENSOES_EXTINTOR:
        if any(c in a for c in chaves):
            return dim
    return (0.16, 0.54)


def _arco(cx: float, cz: float, rx: float, rz: float, a0: float, a1: float,
          n: int = 16) -> list[tuple[float, float]]:
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cz + rz * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


# --- extintor ----------------------------------------------------------------------------------


def extintor(d, uc: float, zb: float, diam: float, altura: float, *,  # noqa: ANN001
             mangueira: str = "pendente", cam: str = "DETALHE_INC") -> dict[str, Any]:
    """Extintor portátil em vista, com a base em ``zb`` e o topo da alavanca em
    ``zb + altura``. ``mangueira``: "pendente" (presa ao corpo, montado na parede) ou "laco"
    (laçada sobre a válvula, como no suporte de piso). Devolve pontos para chamadas."""
    D, H = diam, altura
    r = D / 2
    z_anel = zb + 0.035 * H
    z_ombro = zb + 0.74 * H
    hd = min(0.09 * H, 0.42 * D)
    z_cupula = z_ombro + hd
    z_pesc = z_cupula + 0.035 * H
    z_valv = z_pesc + 0.07 * H
    z_topo = zb + H
    # corpo e cúpula
    contorno = [(uc - r, z_anel), (uc - r, z_ombro), *_arco(uc, z_ombro, r, hd, 180, 0)[1:-1],
                (uc + r, z_ombro), (uc + r, z_anel)]
    d.poli(contorno, cam)
    d.caixa(uc - r - 0.004, zb, uc + r + 0.004, z_anel, cam)  # anel da base
    # adesivo de identificação e frisos do cilindro (dão o volume, como na referência)
    a0, a1 = uc - 0.30 * D, uc + 0.30 * D
    za0, za1 = zb + 0.30 * H, zb + 0.60 * H
    d.caixa(a0, za0, a1, za1, cam)
    for t in range(20, 170, 15):
        u = uc + r * math.cos(math.radians(t))
        if a0 - 1e-6 <= u <= a1 + 1e-6:
            d.linha(u, z_anel, u, za0, cam)
            d.linha(u, za1, u, z_ombro, cam)
        else:
            d.linha(u, z_anel, u, z_ombro, cam)
    # pescoço, corpo da válvula, alavanca e gatilho
    d.caixa(uc - 0.11 * D, z_cupula - 0.004, uc + 0.11 * D, z_pesc, cam)
    d.caixa(uc - 0.16 * D, z_pesc, uc + 0.16 * D, z_valv, cam)
    d.poli([(uc - 0.10 * D, z_valv), (uc + 0.05 * D, z_topo), (uc + 0.62 * D, z_topo - 0.012 * H),
            (uc + 0.64 * D, z_topo - 0.030 * H), (uc + 0.10 * D, z_valv)], cam)  # alavanca
    d.poli([(uc + 0.12 * D, z_valv - 0.02 * H), (uc + 0.60 * D, z_valv - 0.035 * H),
            (uc + 0.62 * D, z_valv - 0.055 * H), (uc + 0.14 * D, z_valv - 0.045 * H)], cam)
    d.linha(uc, z_valv, uc, z_valv + 0.05 * H, cam)  # pino de segurança
    # manômetro com escala
    rm = 0.13 * D
    mu, mz = uc - 0.30 * D, z_pesc + 0.035 * H
    d.circulo(mu, mz, rm, cam)
    for a in range(200, -21, -30):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        d.linha(mu + 0.7 * rm * c, mz + 0.7 * rm * s, mu + 0.95 * rm * c, mz + 0.95 * rm * s, cam)
    d.linha(mu, mz, mu + 0.6 * rm * math.cos(math.radians(60)),
            mz + 0.6 * rm * math.sin(math.radians(60)), cam)
    # mangueira e difusor
    lm = 0.022
    if mangueira == "laco":
        sai = (uc + 0.16 * D, z_valv - 0.03 * H)
        # laço para o lado, por cima da válvula, como na prancha de referência
        pts = [sai, (uc + 0.30 * D, z_valv + 0.06 * H), (uc + 0.05 * D, z_valv + 0.16 * H)]
        pts += _arco(uc - 0.75 * D, z_valv + 0.12 * H, 0.85 * D, 0.14 * H, 75, 270, 22)
        pts += [(uc - 0.30 * D, z_valv - 0.02 * H + 0.0)]
        d.tubo(pts, lm, cam)
        bico = pts[-1]
        d.peca(bico, (1.0, 0.0), 0.05, lm + 0.012, cam)
    else:
        sai = (uc + 0.16 * D, z_valv - 0.035 * H)
        pts = [sai, (uc + r + 0.03, z_valv - 0.08 * H), (uc + r + 0.03, zb + 0.22 * H)]
        d.tubo(pts, lm, cam)
        d.peca(pts[-1], (0.0, -1.0), 0.06, lm + 0.012, cam)
        d.caixa(uc + r - 0.004, zb + 0.40 * H, uc + r + 0.05, zb + 0.43 * H, cam)  # presilha
    return {"corpo": (uc + r, (z_anel + z_ombro) / 2), "adesivo": (a1, (za0 + za1) / 2),
            "alavanca": (uc + 0.62 * D, z_topo - 0.012 * H), "topo": z_topo,
            "pescoco": (uc - 0.11 * D, (z_cupula + z_pesc) / 2), "base": zb,
            "manometro": (mu - rm, mz)}


def suporte_parede(d, u_parede: float, z: float, alcance: float,  # noqa: ANN001
                   cam: str = "DETALHE") -> dict[str, Any]:
    """Suporte em L preso à parede por dois parafusos com bucha; o gancho em ``z``."""
    d.caixa(u_parede, z - 0.07, u_parede + 0.006, z + 0.03, cam)
    d.poli([(u_parede + 0.006, z), (u_parede + alcance, z), (u_parede + alcance, z + 0.015)], cam)
    parafusos = []
    for zp in (z - 0.045, z + 0.012):
        d.caixa(u_parede - 0.045, zp - 0.006, u_parede, zp + 0.006, cam)  # bucha
        d.linha(u_parede - 0.040, zp, u_parede + 0.012, zp, cam)  # parafuso
        d.circulo(u_parede + 0.012, zp, 0.006, cam)  # cabeça redonda
        parafusos.append((u_parede - 0.02, zp))
    return {"suporte": (u_parede + alcance * 0.6, z), "parafuso": parafusos[1],
            "bucha": parafusos[0]}


def suporte_piso(d, uc: float, diam: float, cam: str = "DETALHE_INC") -> dict[str, Any]:
    """Suporte de piso: anel que recebe o extintor e três pés; o extintor apoia em 0,08 m."""
    r = diam / 2 + 0.02
    d.caixa(uc - r, 0.06, uc + r, 0.105, cam)
    d.linha(uc - r, 0.075, uc + r, 0.075, cam)
    d.linha(uc - r, 0.09, uc + r, 0.09, cam)
    d.linha(uc - r + 0.01, 0.06, uc - r - 0.03, 0.0, cam)
    d.linha(uc + r - 0.01, 0.06, uc + r + 0.03, 0.0, cam)
    d.linha(uc, 0.06, uc, 0.0, cam)
    return {"anel": (uc + r, 0.083), "apoio": 0.08}


# --- construção -------------------------------------------------------------------------------


def parede_alvenaria(d, u0: float, u1: float, z0: float, z1: float,  # noqa: ANN001
                     cam: str = "DETALHE") -> None:
    """Parede de alvenaria em corte: contorno, fiadas de 0,20 m e juntas desencontradas."""
    d.poli([(u0, z0), (u1, z0), (u1, z1), (u0, z1)], cam, fechar=True)
    t = u1 - u0
    z, i = z0, 0
    while z < z1 - 1e-6:
        zt = min(z + 0.20, z1)
        if zt < z1 - 1e-6:
            d.linha(u0, zt, u1, zt, cam)
        uj = u0 + t * (0.35 if i % 2 else 0.68)
        d.linha(uj, z, uj, zt, cam)
        z, i = zt, i + 1


def concreto(d, u0: float, u1: float, z0: float, z1: float) -> None:  # noqa: ANN001
    """Concreto em corte: contorno e a textura de pedriscos (triângulos e pontos), desenhada
    como linhas para aparecer em qualquer visualizador (a hachura AR-CONC some no PDF)."""
    d.caixa(u0, z0, u1, z1, "DETALHE")
    k = d.k
    passo = 3.2 * k
    s = 0.7 * k
    i = 0
    z = z0 + passo / 2
    while z < z1 - s:
        u = u0 + passo * (0.3 + 0.5 * ((i * 7) % 3) / 2)
        j = 0
        while u < u1 - s:
            if (i + j) % 3 == 0:
                d.poli([(u, z), (u + s, z), (u + s / 2, z + s * 0.9)], "DETALHE_HACH",
                       fechar=True)
            else:
                d.linha(u, z, u + 0.15 * k, z, "DETALHE_HACH")
            u += passo * (0.8 + 0.4 * ((i + j * 5) % 4) / 3)
            j += 1
        z += passo * 0.75
        i += 1


def laje_concreto(d, u0: float, u1: float, z0: float, z1: float) -> None:  # noqa: ANN001
    concreto(d, u0, u1, z0, z1)


def forro(d, u0: float, u1: float, z: float, esp: float = 0.025) -> None:  # noqa: ANN001
    d.caixa(u0, z - esp, u1, z, "DETALHE", padrao="ANSI31", escala_hach=0.12)


def porta(d, u0: float, largura: float, altura: float,  # noqa: ANN001
          cam: str = "DETALHE") -> dict[str, Any]:
    """Porta em vista: batente, folha com almofada, três dobradiças e maçaneta de alavanca."""
    b = 0.06
    d.poli([(u0 - b, 0), (u0 - b, altura + b), (u0 + largura + b, altura + b),
            (u0 + largura + b, 0)], cam)
    d.poli([(u0, 0), (u0, altura), (u0 + largura, altura), (u0 + largura, 0)], cam)
    d.caixa(u0 + 0.03, 0.03, u0 + largura - 0.03, altura - 0.03, "DETALHE_AUX")
    for f in (0.15, 0.50, 0.85):
        zc = altura * f
        d.caixa(u0 - 0.012, zc - 0.05, u0 + 0.012, zc + 0.05, cam)
        d.linha(u0 - 0.012, zc, u0 + 0.012, zc, cam)
    mu, mz = u0 + largura - 0.09, 1.05
    d.circulo(mu, mz, 0.03, cam)
    d.caixa(mu - 0.12, mz - 0.008, mu, mz + 0.008, cam)
    return {"verga": altura, "batente": altura + b}


# --- placas ----------------------------------------------------------------------------------

_PALAVRA = {"E": "EQUIP", "S": "SAIDA", "P": "PROIB", "A": "ALERTA", "M": "MENS"}


def _nome_bloco(codigo: str) -> str:
    """Nome que o leitor de símbolos NÃO reconhece como placa (o detalhe não é equipamento)."""
    c = codigo.upper().replace("#", "V")
    letra, resto = c[0], c[1:].replace("-", "")
    return f"DETV_PICT_{_PALAVRA.get(letra, 'X')}{resto}"


def placa_nt(d, codigo: str, uc: float, z_base: float, largura: float,  # noqa: ANN001
             cam: str = "DETALHE_SINAL") -> tuple[float, float]:
    """Placa com o pictograma oficial da NT 2-05 (vetorizado), largura em m, proporção da NT.
    Sem o desenho oficial, retângulo na cor do grupo. Devolve (largura, altura)."""
    item = simbologia._NT.get("placas", {}).get(codigo)  # noqa: SLF001
    if item is None:
        cor = {"E": 1, "S": 3}.get(codigo[:1].upper(), 30)
        d.caixa(uc - largura / 2, z_base, uc + largura / 2, z_base + largura * 0.5, cam,
                solido=cor)
        return largura, largura * 0.5
    px, py = item["proporcao"]
    esc = largura / px
    alt = py * esc
    nome = _nome_bloco(codigo)
    if nome not in d.doc.blocks:
        simbologia.emit(d.doc.blocks.new(nome), simbologia.glyph_nt(item))
    d.msp.add_blockref(nome, d.P(uc, z_base + alt / 2),
                       dxfattribs={"layer": cam, "xscale": esc, "yscale": esc})
    d._visto([(uc - largura / 2, z_base), (uc + largura / 2, z_base + alt)])  # noqa: SLF001
    return largura, alt


def placa_suspensa(d, codigo: str, uc: float, z_teto: float, z_base: float,  # noqa: ANN001
                   largura: float) -> tuple[float, float]:
    """Placa pendurada no teto por dois tirantes, com a chapa de fixação."""
    w, h = placa_nt(d, codigo, uc, z_base, largura)
    d.caixa(uc - w * 0.45, z_teto - 0.008, uc + w * 0.45, z_teto, "DETALHE")
    for s in (-1, 1):
        u = uc + s * w * 0.32
        d.linha(u - 0.006, z_base + h, u - 0.006, z_teto - 0.008, "DETALHE")
        d.linha(u + 0.006, z_base + h, u + 0.006, z_teto - 0.008, "DETALHE")
    return w, h


# --- iluminação ------------------------------------------------------------------------------


def bloco_frente(d, uc: float, z: float, w: float = 0.32, h: float = 0.11,  # noqa: ANN001
                 cam: str = "DETALHE_ILUM") -> dict[str, Any]:
    """Bloco autônomo de dois faróis em vista frontal: caixa, faróis com aletas e LED."""
    d.caixa(uc - w / 2, z, uc + w / 2, z + h, cam)
    d.caixa(uc - w / 2 + 0.01, z + 0.01, uc + w / 2 - 0.01, z + h - 0.01, "DETALHE_AUX")
    for s in (-1, 1):
        fc = uc + s * w * 0.28
        d.caixa(fc - 0.045, z + 0.02, fc + 0.045, z + h - 0.02, cam)
        for k in range(1, 4):
            zz = z + 0.02 + (h - 0.04) * k / 4
            d.linha(fc - 0.04, zz, fc + 0.04, zz, cam)
    d.circulo(uc, z + h * 0.3, 0.008, cam)  # LED de carga
    return {"caixa": (uc + w / 2, z + h / 2)}


def bloco_lateral(d, u_parede: float, z: float, p: float = 0.07, h: float = 0.11,  # noqa: ANN001
                  cam: str = "DETALHE_ILUM") -> dict[str, Any]:
    d.caixa(u_parede, z, u_parede + p, z + h, cam)
    d.poli([(u_parede + p, z + h * 0.25), (u_parede + p + 0.03, z + h * 0.15),
            (u_parede + p + 0.03, z + h * 0.65), (u_parede + p, z + h * 0.55)], cam,
           fechar=True)  # farol inclinado
    for zp in (z + 0.025, z + h - 0.025):
        d.linha(u_parede - 0.035, zp, u_parede + 0.01, zp, "DETALHE")
    return {"farol": (u_parede + p + 0.03, z + h * 0.4)}


# --- hidrantes -------------------------------------------------------------------------------


def registro_globo_angular(d, u: float, z: float, s: float = 1.0,  # noqa: ANN001
                           cam: str = "DETALHE_INC") -> dict[str, Any]:
    """Registro globo angular: corpo, haste e volante; entrada por baixo, saída a 45°."""
    d.circulo(u, z, 0.035 * s, cam)
    d.caixa(u - 0.012 * s, z + 0.035 * s, u + 0.012 * s, z + 0.09 * s, cam)  # castelo
    d.caixa(u - 0.065 * s, z + 0.09 * s, u + 0.065 * s, z + 0.105 * s, cam)  # volante
    d.linha(u, z + 0.105 * s, u, z + 0.125 * s, cam)
    return {"corpo": (u + 0.035 * s, z), "volante": (u + 0.065 * s, z + 0.098 * s)}


def storz(d, c: tuple[float, float], direcao: tuple[float, float], diam: float,  # noqa: ANN001
          cam: str = "DETALHE_INC") -> tuple[float, float]:
    """Junta storz (com as garras) a partir de ``c``; devolve o ponto final."""
    d.peca(c, direcao, 0.045, diam + 0.03, cam)
    dx, dy = direcao
    nx, ny = -dy, dx
    fim = (c[0] + dx * 0.045, c[1] + dy * 0.045)
    for s in (-1, 1):
        g = (fim[0] + nx * s * (diam / 2 + 0.005), fim[1] + ny * s * (diam / 2 + 0.005))
        d.peca(g, direcao, 0.012, 0.012, cam)
    return fim


def mangueira_aduchada(d, uc: float, zc: float, larg: float, alt: float,  # noqa: ANN001
                       voltas: int = 4, cam: str = "DETALHE_INC") -> None:
    """Mangueira aduchada vista de frente: voltas em 'estádio' concêntricas."""
    for i in range(voltas):
        w = larg / 2 - i * larg * 0.09
        h = alt / 2 - i * alt * 0.09
        if w <= 0.02 or h <= 0.02:
            break
        rr = min(w, h)
        pts = _arco(uc + w - rr, zc, rr, h, -90, 90, 10) + _arco(uc - w + rr, zc, rr, h, 90, 270,
                                                                    10)
        d.poli(pts, cam, fechar=True)


def esguicho(d, u: float, z: float, comp: float = 0.26,  # noqa: ANN001
             cam: str = "DETALHE_INC") -> tuple[float, float]:
    """Esguicho regulável deitado (base em u, ponta para a direita)."""
    d.poli([(u, z - 0.03), (u + comp * 0.35, z - 0.03), (u + comp * 0.40, z - 0.045),
            (u + comp, z - 0.02), (u + comp, z + 0.02), (u + comp * 0.40, z + 0.045),
            (u + comp * 0.35, z + 0.03), (u, z + 0.03)], cam, fechar=True)
    for k in (0.5, 0.65, 0.8):
        d.linha(u + comp * k, z - 0.04 + comp * (k - 0.4) * 0.07,
                u + comp * k, z + 0.04 - comp * (k - 0.4) * 0.07, cam)
    return (u + comp / 2, z)


def registro_gaveta(d, u: float, z: float, diam: float,  # noqa: ANN001
                    cam: str = "DETALHE_INC") -> dict[str, Any]:
    """Registro de gaveta numa tubulação vertical: corpo, castelo para o lado e volante."""
    d.caixa(u - diam / 2 - 0.02, z - 0.05, u + diam / 2 + 0.02, z + 0.05, cam)
    d.caixa(u + diam / 2 + 0.02, z - 0.012, u + diam / 2 + 0.08, z + 0.012, cam)
    d.caixa(u + diam / 2 + 0.08, z - 0.05, u + diam / 2 + 0.095, z + 0.05, cam)
    return {"volante": (u + diam / 2 + 0.095, z)}


__all__ = ["bloco_frente", "bloco_lateral", "dimensoes_extintor", "esguicho", "extintor",
           "forro", "laje_concreto", "mangueira_aduchada", "parede_alvenaria", "placa_nt",
           "placa_suspensa", "porta", "registro_gaveta", "registro_globo_angular", "storz",
           "suporte_parede", "suporte_piso"]
