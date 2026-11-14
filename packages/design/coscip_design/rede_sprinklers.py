"""Malha de chuveiros automáticos e hidráulica da área remota de uma zona (frente E).

Dada uma zona (polígono da planta), os critérios de projeto e o ponto de alimentação, este módulo:

1. distribui os bicos numa malha que respeita o espaçamento máximo, a área máxima por bico e a
   distância máxima à parede;
2. monta a rede: ramais (linhas de bicos), subgeral (que alimenta os ramais pela extremidade mais
   próxima da alimentação), tubulação geral até a prumada e a prumada até a válvula de governo
   e alarme (VGA);
3. calcula a hidráulica da **área de operação remota** com o método dos bicos em cascata
   (K·√P em cada bico, Hazen-Williams em cada trecho), escolhendo o diâmetro de cada trecho pela
   velocidade máxima, e devolve vazão total e pressão necessária na base da prumada.

O que NÃO está na NT 2-03 (densidade, área de operação, área por bico, espaçamento, K, pressão
mínima, velocidade, perdas das conexões e da VGA) vem em :class:`Criterios`, preenchido por quem
chama a partir da norma adotada (ABNT NBR 10897 ou NFPA 13) ou por premissa listada no memorial.
É um cálculo simplificado de uma zona retangular ou poligonal; não substitui o programa de
cálculo hidráulico completo do projetista (obstruções, vigas, desníveis, vários ramais ligados).
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from shapely.geometry import Point, Polygon, box

from coscip_design.hidrantes import hazen_williams

BAR_POR_M = 0.0980665  # 1 mca em bar
# DN nominal e diâmetro interno (mm) do tubo de aço, classe 40
DN_SERIE: tuple[tuple[int, float], ...] = (
    (25, 26.6), (32, 35.1), (40, 40.9), (50, 52.5), (65, 62.7), (80, 77.9), (100, 102.3),
    (150, 154.1), (200, 202.7))
Ponto3 = tuple[float, float, float]


@dataclass(frozen=True)
class Criterios:
    """Critérios hidráulicos e de malha (da norma adotada ou premissa do projetista)."""

    densidade_mm_min: float  # L/min por m² de área de operação
    area_operacao_m2: float
    area_max_bico_m2: float
    espacamento_max_m: float
    espacamento_min_m: float = 1.8
    k: float = 80.0  # L/min/bar^½ (fator K)
    pressao_min_bar: float = 0.5
    c_hw: float = 120.0
    v_max_ms: float = 5.0
    perda_unitaria_max_bar_m: float = 0.05  # limite que mantém a pressão pouco variável
    conexoes_pct: float = 20.0  # comprimento equivalente das conexões, % do tubo reto
    perda_vga_bar: float = 0.3
    dn_min_ramal: int = 25


@dataclass(frozen=True)
class Zona:
    nome: str
    poligono: tuple[tuple[float, float], ...]
    alimentacao: tuple[float, float]  # onde a prumada chega à zona, na planta
    z_ramal_m: float = 3.0  # cota das tubulações (m acima do piso)
    z_base_m: float = 0.0  # cota da VGA / base da prumada
    orientacao: str = "auto"  # "x", "y" ou "auto" (ramais ao longo do lado maior)


@dataclass
class Bico:
    id: str  # B1, B2... (nunca S/E/A/P/M + número: o leitor leria como placa)
    x: float
    y: float
    z: float
    ramal: int
    ordem: int  # posição no ramal, da subgeral para a ponta
    opera: bool = False
    vazao_lpm: float = 0.0
    pressao_bar: float = 0.0


@dataclass
class Tubo:
    id: str  # T1, T2...
    tipo: str  # ramal | subgeral | geral | prumada
    p0: Ponto3
    p1: Ponto3
    de: str
    para: str
    dn: int = 0
    di_mm: float = 0.0
    vazao_lpm: float = 0.0
    perda_bar: float = 0.0
    velocidade_ms: float = 0.0

    @property
    def comprimento_m(self) -> float:
        return math.dist(self.p0, self.p1)


@dataclass
class Rede:
    zona: Zona
    criterios: Criterios
    bicos: list[Bico] = field(default_factory=list)
    tubos: list[Tubo] = field(default_factory=list)
    resumo: dict[str, Any] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {**self.resumo, "avisos": self.avisos}


def escolher_dn(vazao_lpm: float, c: Criterios, dn_min: int = 25) -> tuple[int, float]:
    """Menor DN da série (a partir de ``dn_min``) que respeita a velocidade máxima e a perda de
    carga unitária máxima (com o acréscimo das conexões)."""
    for dn, di in DN_SERIE:
        if dn < dn_min:
            continue
        unitaria = hazen_williams(vazao_lpm, c.c_hw, di) * BAR_POR_M * (1 + c.conexoes_pct / 100)
        if velocidade(vazao_lpm, di) <= c.v_max_ms and unitaria <= c.perda_unitaria_max_bar_m:
            return dn, di
    return DN_SERIE[-1]


def velocidade(q_lpm: float, di_mm: float) -> float:
    return (q_lpm / 60000.0) / (math.pi * (di_mm / 1000.0) ** 2 / 4)


def perda_bar(q_lpm: float, di_mm: float, comp_m: float, c: float, conexoes_pct: float) -> float:
    """Perda de carga (bar) no trecho, com o acréscimo percentual das conexões."""
    if q_lpm <= 0 or comp_m <= 0:
        return 0.0
    return hazen_williams(q_lpm, c, di_mm) * BAR_POR_M * comp_m * (1 + conexoes_pct / 100.0)


# --- malha --------------------------------------------------------------------------------------


def _contagens(la: float, lb: float, c: Criterios) -> tuple[int, int]:
    na = max(1, math.ceil(la / c.espacamento_max_m - 1e-9))
    nb = max(1, math.ceil(lb / c.espacamento_max_m - 1e-9))
    while (la / na) * (lb / nb) > c.area_max_bico_m2 + 1e-9:
        if la / na >= lb / nb:
            na += 1
        else:
            nb += 1
    return na, nb


def malha(zona: Zona, c: Criterios) -> tuple[list[tuple[int, int, float, float]], str,
                                             dict[str, float]]:
    """Bicos da malha como (ramal, ordem, x, y), a orientação dos ramais e os espaçamentos."""
    poly = Polygon(zona.poligono)
    minx, miny, maxx, maxy = poly.bounds
    w, h = maxx - minx, maxy - miny
    ori = zona.orientacao if zona.orientacao in ("x", "y") else ("x" if w >= h else "y")
    la, lb = (w, h) if ori == "x" else (h, w)  # a: ao longo do ramal; b: entre ramais
    na, nb = _contagens(la, lb, c)
    sa, sb = la / na, lb / nb
    a0, b0 = (minx, miny) if ori == "x" else (miny, minx)
    pontos: list[tuple[int, int, float, float]] = []
    for j in range(nb):
        for i in range(na):
            a, b = a0 + (i + 0.5) * sa, b0 + (j + 0.5) * sb
            x, y = (a, b) if ori == "x" else (b, a)
            dx, dy = (sa, sb) if ori == "x" else (sb, sa)
            celula = box(x - dx / 2, y - dy / 2, x + dx / 2, y + dy / 2)
            if poly.contains(Point(x, y)) or poly.intersection(celula).area >= 0.15 * celula.area:
                pontos.append((j, i, x, y))
    return pontos, ori, {"entre_bicos_m": sa, "entre_ramais_m": sb, "area_por_bico_m2": sa * sb}


def pior_distancia(poly: Polygon, bicos: list[Bico]) -> float:
    """Maior distância de um ponto da zona ao bico mais próximo (amostra de 0,5 m)."""
    if not bicos:
        return math.inf
    minx, miny, maxx, maxy = poly.bounds
    pior = 0.0
    y = miny + 0.25
    while y < maxy:
        x = minx + 0.25
        while x < maxx:
            if poly.contains(Point(x, y)):
                pior = max(pior, min(math.hypot(b.x - x, b.y - y) for b in bicos))
            x += 0.5
        y += 0.5
    return pior


# --- projeto ------------------------------------------------------------------------------------


def projetar(zona: Zona, c: Criterios) -> Rede:
    """Malha, rede e hidráulica da área remota de ``zona``."""
    rede = Rede(zona, c)
    poly = Polygon(zona.poligono)
    pontos, ori, esp = malha(zona, c)
    if not pontos:
        rede.avisos.append("a zona não recebeu nenhum bico: polígono pequeno ou inválido")
        return rede
    sa, sb = esp["entre_bicos_m"], esp["entre_ramais_m"]
    if min(sa, sb) < c.espacamento_min_m - 1e-9:
        rede.avisos.append(f"espaçamento de {min(sa, sb):.2f} m abaixo do mínimo de "
                           f"{c.espacamento_min_m:g} m entre bicos: revisar a malha com a norma")

    # a: coordenada ao longo do ramal; b: coordenada entre ramais
    def a_de(x: float, y: float) -> float:
        return x if ori == "x" else y

    def b_de(x: float, y: float) -> float:
        return y if ori == "x" else x

    def xy(a: float, b: float) -> tuple[float, float]:
        return (a, b) if ori == "x" else (b, a)

    z = zona.z_ramal_m
    ax, ay = zona.alimentacao
    por_ramal: dict[int, list[tuple[float, float]]] = {}
    for j, _, x, y in pontos:
        por_ramal.setdefault(j, []).append((x, y))
    a_min = min(a_de(x, y) for _, _, x, y in pontos)
    a_max = max(a_de(x, y) for _, _, x, y in pontos)
    pelo_minimo = abs(a_de(ax, ay) - a_min) <= abs(a_de(ax, ay) - a_max)
    a_sub = (a_min - sa / 2 + 0.3) if pelo_minimo else (a_max + sa / 2 - 0.3)
    b_ramal = {j: sum(b_de(x, y) for x, y in lst) / len(lst) for j, lst in por_ramal.items()}
    b_alim = b_de(ax, ay)
    ordem_sub = sorted(por_ramal, key=lambda j: abs(b_ramal[j] - b_alim))  # perto -> longe

    # --- bicos e tubos ----------------------------------------------------------------------------
    n_bico = n_tubo = 0
    cadeias: dict[int, list[Bico]] = {}
    for j in ordem_sub:
        lst = sorted(por_ramal[j], key=lambda p: abs(a_de(*p) - a_sub))  # da subgeral para a ponta
        cadeias[j] = []
        for ordem, (x, y) in enumerate(lst):
            n_bico += 1
            px, py = xy(a_de(x, y), b_ramal[j])
            b = Bico(f"B{n_bico}", px, py, z, j, ordem)
            cadeias[j].append(b)
            rede.bicos.append(b)
    no_sub: dict[int, Ponto3] = {j: (*xy(a_sub, b_ramal[j]), z) for j in ordem_sub}

    def tubo(tipo: str, p0: Ponto3, p1: Ponto3, de: str, para: str) -> Tubo:
        nonlocal n_tubo
        n_tubo += 1
        t = Tubo(f"T{n_tubo}", tipo, p0, p1, de, para)
        rede.tubos.append(t)
        return t

    ramal_tubos: dict[int, list[Tubo]] = {}
    for j in ordem_sub:
        ant, nome = no_sub[j], f"J{j + 1}"
        ramal_tubos[j] = []
        for b in cadeias[j]:
            ramal_tubos[j].append(tubo("ramal", ant, (b.x, b.y, b.z), nome, b.id))
            ant, nome = (b.x, b.y, b.z), b.id
    sub_tubos = [tubo("subgeral", no_sub[j0], no_sub[j1], f"J{j0 + 1}", f"J{j1 + 1}")
                 for j0, j1 in zip(ordem_sub, ordem_sub[1:], strict=False)]
    topo: Ponto3 = (ax, ay, z)
    canto: Ponto3 = (*xy(a_sub, b_alim), z)
    entrada = no_sub[ordem_sub[0]]
    geral: list[Tubo] = []
    if math.dist(topo[:2], canto[:2]) > 1e-6:
        geral.append(tubo("geral", topo, canto, "PR", "G1"))
    if math.dist(canto[:2], entrada[:2]) > 1e-6:
        geral.append(tubo("geral", canto, entrada, geral[-1].para if geral else "PR",
                          f"J{ordem_sub[0] + 1}"))
    prumada = tubo("prumada", (ax, ay, zona.z_base_m), topo, "VGA", "PR")

    # --- área de operação remota --------------------------------------------------------------
    q_req = c.densidade_mm_min * esp["area_por_bico_m2"]  # L/min no bico remoto
    n_op = max(1, math.ceil(c.area_operacao_m2 / esp["area_por_bico_m2"] - 1e-9))
    por_ramal_op = max(1, min(max(len(v) for v in cadeias.values()),
                              math.ceil(1.2 * math.sqrt(c.area_operacao_m2) / sa)))
    ramais_op: list[int] = []  # do mais distante da alimentação para perto
    operando = 0
    for j in reversed(ordem_sub):
        if operando >= n_op:
            break
        tomar = min(por_ramal_op, len(cadeias[j]), n_op - operando)
        for b in cadeias[j][len(cadeias[j]) - tomar:]:
            b.opera = True
        operando += tomar
        ramais_op.append(j)

    p_tip_min = max(c.pressao_min_bar, (q_req / c.k) ** 2)
    perda: Callable[[float, Tubo], float] = lambda q, t: perda_bar(  # noqa: E731
        q, t.di_mm, t.comprimento_m, c.c_hw, c.conexoes_pct)

    def corre_ramal(j: int, p_tip: float) -> tuple[float, float]:
        """Do bico da ponta até o nó da subgeral: (vazão do ramal, pressão no nó)."""
        ts, bs = ramal_tubos[j], cadeias[j]
        p = p_tip
        soma = 0.0
        for k in range(len(bs) - 1, -1, -1):
            b = bs[k]
            if b.opera:
                b.pressao_bar = p
                b.vazao_lpm = c.k * math.sqrt(p)
                soma += b.vazao_lpm
            else:
                b.pressao_bar = b.vazao_lpm = 0.0
            ts[k].vazao_lpm = soma
            ts[k].perda_bar = perda(soma, ts[k])
            p += ts[k].perda_bar
        return soma, p

    def ramal_para_pressao(j: int, p_alvo: float) -> tuple[float, float]:
        """Acha a pressão na ponta que dá ``p_alvo`` no nó (bisseção; a perda cresce com ela)."""
        lo, hi = 0.0, max(p_alvo, p_tip_min) + 1.0
        for _ in range(60):
            meio = (lo + hi) / 2
            if corre_ramal(j, meio)[1] > p_alvo:
                hi = meio
            else:
                lo = meio
        return corre_ramal(j, lo)

    def calcula() -> tuple[float, float]:
        """Cascata do ramal mais distante até a base da prumada: (vazão total, pressão na base)."""
        q0, p_no = corre_ramal(ramais_op[0], p_tip_min)
        q_tot = q0
        atual = ramais_op[0]
        for j in ramais_op[1:]:
            seg = sub_tubos[ordem_sub.index(j)]  # entre j e o ramal seguinte (mais distante)
            seg.vazao_lpm = q_tot
            seg.perda_bar = perda(q_tot, seg)
            p_no += seg.perda_bar
            q_j, _ = ramal_para_pressao(j, p_no)
            q_tot += q_j
            atual = j
        for k in range(ordem_sub.index(atual)):  # do ramal operante mais próximo até a entrada
            sub_tubos[k].vazao_lpm = q_tot
            sub_tubos[k].perda_bar = perda(q_tot, sub_tubos[k])
            p_no += sub_tubos[k].perda_bar
        for t in (*geral, prumada):
            t.vazao_lpm = q_tot
            t.perda_bar = perda(q_tot, t)
            p_no += t.perda_bar
        return q_tot, p_no

    # escolhe os DN pela vazão e refaz até estabilizar (os DN mudam as perdas e as vazões)
    for t in rede.tubos:
        t.dn, t.di_mm = DN_SERIE[0] if t.tipo != "ramal" else _dn(c.dn_min_ramal)
    q_total, p_final = calcula()
    for _ in range(8):
        mudou = False
        for t in rede.tubos:
            if t.vazao_lpm <= 0:
                continue
            dn, di = escolher_dn(t.vazao_lpm, c, c.dn_min_ramal if t.tipo == "ramal" else 25)
            if dn != t.dn:
                t.dn, t.di_mm, mudou = dn, di, True
        q_total, p_final = calcula()
        if not mudou:
            break
    for t in rede.tubos:
        if t.vazao_lpm <= 0:  # sem vazão na área remota: DN mínimo (confirmar pelo projetista)
            t.dn, t.di_mm = _dn(c.dn_min_ramal) if t.tipo == "ramal" else DN_SERIE[0]
        t.velocidade_ms = velocidade(t.vazao_lpm, t.di_mm) if t.vazao_lpm > 0 else 0.0

    estatica = (zona.z_ramal_m - zona.z_base_m) * BAR_POR_M
    p_base = p_final + estatica + c.perda_vga_bar
    dist = pior_distancia(poly, rede.bicos)
    limite = math.sqrt(2) / 2 * c.espacamento_max_m
    if dist > limite + 1e-6:
        rede.avisos.append(f"há ponto da zona a {dist:.2f} m do bico mais próximo (limite "
                           f"{limite:.2f} m): reforçar a malha nos cantos")
    for t in rede.tubos:
        if t.vazao_lpm > 0 and t.velocidade_ms > c.v_max_ms + 1e-6:
            rede.avisos.append(f"{t.id} ({t.tipo}): velocidade {t.velocidade_ms:.1f} m/s acima "
                               f"de {c.v_max_ms:g} m/s no maior DN da série")
    comp_por_dn = Counter()
    for t in rede.tubos:
        comp_por_dn[t.dn] += t.comprimento_m
    perdas = Counter()
    for t in rede.tubos:
        perdas[t.tipo] += t.perda_bar
    rede.resumo = {
        "zona": zona.nome, "orientacao_dos_ramais": ori, "bicos": len(rede.bicos),
        "ramais": len(ordem_sub), "espacamento_entre_bicos_m": round(sa, 3),
        "espacamento_entre_ramais_m": round(sb, 3),
        "area_por_bico_m2": round(esp["area_por_bico_m2"], 3),
        "bicos_em_operacao": sum(1 for b in rede.bicos if b.opera),
        "area_de_operacao_m2": round(sum(1 for b in rede.bicos if b.opera)
                                     * esp["area_por_bico_m2"], 2),
        "vazao_do_bico_remoto_lpm": round(q_req, 2),
        "pressao_do_bico_remoto_bar": round(p_tip_min, 3),
        "vazao_total_lpm": round(q_total, 1),
        "pressao_na_base_da_prumada_bar": round(p_base, 3),
        "pressao_na_base_da_prumada_mca": round(p_base / BAR_POR_M, 2),
        "perdas_bar": {k: round(v, 3) for k, v in perdas.items()}
                      | {"estatica": round(estatica, 3), "vga": c.perda_vga_bar},
        "comprimento_por_dn_m": {f"DN{dn}": round(v, 2) for dn, v in sorted(comp_por_dn.items())
                                 if dn},
        "distancia_maxima_ao_bico_m": round(dist, 2),
    }
    return rede


def _dn(dn: int) -> tuple[int, float]:
    return next((d, di) for d, di in DN_SERIE if d >= dn)
