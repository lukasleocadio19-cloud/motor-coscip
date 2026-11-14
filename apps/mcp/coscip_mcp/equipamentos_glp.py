"""Componentes de GLP desenhados para os detalhes (frente G3, 13/11/2026).

Mesmo nível de desenho dos detalhes de uma prancha protocolada usada como referência pelo
usuário: recipientes com colarinho e base, coletor com pigtails, válvula de retenção e tampão,
conexões roscadas (niple, união, luva de redução, tê), registro de esfera com alavanca,
manômetro com escala e reguladores de 1º e 2º estágio. Proporções de representação; medidas
de norma vêm de ``detalhes_glp.py``.
"""

from __future__ import annotations

import math
from typing import Any

# (Ø, altura) aproximados de catálogo, em m — representação; confirmar com o distribuidor
RECIPIENTES = {"P-13": (0.36, 0.47, 13), "P-20": (0.31, 0.70, 20), "P-45": (0.37, 1.25, 45),
               "P-90": (0.47, 1.30, 90), "P-190": (0.60, 1.45, 190)}
CAM = "DETALHE_GLP"


def cilindro(d, uc: float, zb: float, tipo: str, cam: str = CAM) -> dict[str, Any]:  # noqa: ANN001
    """Recipiente transportável em vista: pé, corpo com ombros chanfrados, colarinho e válvula."""
    D, H, _kg = RECIPIENTES[tipo]
    r = D / 2
    pe = 0.07 * H
    d.caixa(uc - r * 0.78, zb, uc + r * 0.78, zb + pe, cam)  # pé
    z0, z1 = zb + pe, zb + 0.84 * H
    ch = min(0.10 * H, 0.35 * r)
    d.poli([(uc - r, z0), (uc - r, z1), (uc - r + ch, z1 + ch), (uc + r - ch, z1 + ch),
            (uc + r, z1), (uc + r, z0)], cam, fechar=True)
    zc = z1 + ch
    d.poli([(uc - r * 0.62, zc), (uc - r * 0.62, zb + H), (uc + r * 0.62, zb + H),
            (uc + r * 0.62, zc)], cam)  # colarinho (alça)
    d.caixa(uc - 0.03, zc, uc + 0.03, zc + 0.05, cam)  # válvula
    d.texto(tipo, uc, (z0 + z1) / 2, 1.8, alinhar="centro", cam=cam)
    return {"valvula": (uc, zc + 0.05), "corpo": (uc + r, (z0 + z1) / 2), "topo": zb + H}


def cilindro_planta(d, uc: float, vc: float, tipo: str, cam: str = CAM) -> None:  # noqa: ANN001
    D = RECIPIENTES[tipo][0]
    d.circulo(uc, vc, D / 2, cam)
    d.circulo(uc, vc, D / 2 * 0.62, cam)
    d.circulo(uc, vc, 0.03, cam)


def pigtail(d, a: tuple[float, float], b: tuple[float, float], cam: str = CAM) -> None:  # noqa: ANN001
    """Mangueira de alta pressão (pigtail) em arco, da válvula do recipiente ao coletor."""
    (ua, za), (ub, zb) = a, b
    # sobe da válvula, faz uma curva suave para o lado e entra por baixo do coletor
    pts = [a, (ua, za + 0.05)]
    n = 10
    for i in range(1, n + 1):
        t = i / n
        u = ua + (ub - ua) * (3 * t * t - 2 * t * t * t) - 0.05 * math.sin(math.pi * t)
        z = za + 0.05 + (zb - 0.04 - za - 0.05) * t
        pts.append((u, z))
    pts.append(b)
    d.tubo(pts, 0.018, cam)


def valvula_retencao(d, u: float, z: float, cam: str = CAM) -> tuple[float, float]:  # noqa: ANN001
    d.circulo(u, z, 0.035, cam)
    d.poli([(u - 0.02, z - 0.015), (u + 0.02, z), (u - 0.02, z + 0.015)], cam, fechar=True)
    return (u, z + 0.035)


def tampao(d, u: float, z: float, diam: float, cam: str = CAM) -> tuple[float, float]:  # noqa: ANN001
    d.caixa(u - 0.05, z - diam / 2 - 0.012, u, z + diam / 2 + 0.012, cam)
    return (u - 0.025, z + diam / 2 + 0.012)


# --- conexões em prumada (eixo vertical em u) -------------------------------------------------


def niple(d, u: float, z0: float, z1: float, diam: float, cam: str = CAM) -> None:  # noqa: ANN001
    d.caixa(u - diam / 2, z0, u + diam / 2, z1, cam)
    n = max(2, int((z1 - z0) / 0.012))
    for i in range(1, n):
        zz = z0 + (z1 - z0) * i / n
        d.linha(u - diam / 2, zz - 0.004, u + diam / 2, zz + 0.004, cam)


def uniao(d, u: float, z: float, diam: float, cam: str = CAM) -> tuple[float, float]:  # noqa: ANN001
    w = diam * 2.6
    d.poli([(u - w / 2, z - 0.015), (u - w / 2 + 0.02, z - 0.03), (u + w / 2 - 0.02, z - 0.03),
            (u + w / 2, z - 0.015), (u + w / 2, z + 0.015), (u + w / 2 - 0.02, z + 0.03),
            (u - w / 2 + 0.02, z + 0.03), (u - w / 2, z + 0.015)], cam, fechar=True)
    d.linha(u - w / 2, z, u + w / 2, z, cam)
    for s in (-1, 1):
        d.linha(u + s * w / 6, z - 0.03, u + s * w / 6, z + 0.03, cam)
    return (u + w / 2, z)


def luva_reducao(d, u: float, z0: float, z1: float, d_baixo: float, d_cima: float,  # noqa: ANN001
                 cam: str = CAM) -> tuple[float, float]:
    d.poli([(u - d_baixo / 2 - 0.006, z0), (u + d_baixo / 2 + 0.006, z0),
            (u + d_cima / 2 + 0.006, z1), (u - d_cima / 2 - 0.006, z1)], cam, fechar=True)
    return (u + d_baixo / 2 + 0.006, (z0 + z1) / 2)


def registro_esfera(d, u: float, z0: float, z1: float, diam: float,  # noqa: ANN001
                    cam: str = CAM) -> tuple[float, float]:
    """Registro de esfera em linha vertical, com alavanca para o lado direito."""
    w = diam + 0.03
    d.caixa(u - w / 2, z0, u + w / 2, z1, cam)
    for s in (-1, 1):
        d.caixa(u + s * (w / 2) - 0.006, z0 + 0.012, u + s * (w / 2) + 0.006, z1 - 0.012, cam)
    zm = (z0 + z1) / 2
    d.caixa(u + w / 2 + 0.006, zm - 0.008, u + w / 2 + 0.025, zm + 0.008, cam)  # haste
    d.poli([(u + w / 2 + 0.025, zm), (u + w / 2 + 0.035, zm), (u + w / 2 + 0.035, zm - 0.12)],
           cam)  # alavanca
    return (u + w / 2 + 0.03, zm)


def te(d, u: float, z0: float, z1: float, diam: float,  # noqa: ANN001
       cam: str = CAM) -> tuple[float, float]:
    """Tê com derivação para a direita; devolve a ponta da derivação."""
    w = diam + 0.03
    d.caixa(u - w / 2, z0, u + w / 2, z1, cam)
    zm = (z0 + z1) / 2
    d.caixa(u + w / 2, zm - diam / 2, u + w / 2 + 0.035, zm + diam / 2, cam)
    return (u + w / 2 + 0.035, zm)


def manometro(d, u: float, z: float, r: float = 0.045, cam: str = CAM) -> None:  # noqa: ANN001
    d.circulo(u, z, r, cam)
    d.circulo(u, z, r * 0.85, cam)
    for a in range(225, -46, -27):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        d.linha(u + 0.70 * r * c, z + 0.70 * r * s, u + 0.85 * r * c, z + 0.85 * r * s, cam)
    d.linha(u, z, u + 0.6 * r * math.cos(math.radians(70)),
            z + 0.6 * r * math.sin(math.radians(70)), cam)


def regulador_1(d, u: float, z: float, cam: str = CAM) -> dict[str, Any]:  # noqa: ANN001
    """Regulador de 1º estágio em vista: corpo circular, tampa com parafuso e manômetro."""
    r = 0.06
    d.circulo(u, z, r, cam)
    d.circulo(u, z, r * 0.78, cam)
    d.poli([(u + 0.015 * math.cos(math.radians(a)), z + 0.015 * math.sin(math.radians(a)))
            for a in range(0, 361, 60)], cam)  # parafuso de ajuste
    d.poli([(u - 0.012, z - r * 0.6), (u + 0.012, z - r * 0.6), (u, z - r * 0.78)], cam,
           fechar=True)  # seta de fluxo
    manometro(d, u + r + 0.05, z, 0.04, cam)
    d.linha(u + r, z, u + r + 0.01, z, cam)
    return {"corpo": (u - r, z), "manometro": (u + r + 0.09, z)}


def regulador_2(d, u: float, z: float, cam: str = CAM) -> dict[str, Any]:  # noqa: ANN001
    """Regulador de 2º estágio com registro: corpo, registro de alavanca e porca de saída."""
    r = 0.075
    d.circulo(u, z, r, cam)
    d.circulo(u, z, 0.016, cam)
    d.linha(u - 0.011, z - 0.011, u + 0.011, z + 0.011, cam)
    zr = z + r + 0.02
    d.caixa(u - 0.045, zr - 0.02, u + 0.025, zr + 0.02, cam)  # registro
    d.poli([(u + 0.025, zr + 0.01), (u + 0.06, zr + 0.01), (u + 0.09, zr - 0.04),
            (u + 0.08, zr - 0.045), (u + 0.025, zr - 0.01)], cam)  # alavanca
    d.caixa(u - 0.012, zr + 0.02, u + 0.012, zr + 0.06, cam)
    d.caixa(u - 0.018, zr + 0.06, u + 0.018, zr + 0.09, cam)  # porca
    return {"corpo": (u + r * 0.7, z - r * 0.3), "registro": (u + 0.025, zr),
            "saida": (u, zr + 0.09), "baixo": (u, z - r)}


__all__ = ["RECIPIENTES", "cilindro", "cilindro_planta", "luva_reducao", "manometro", "niple",
           "pigtail", "registro_esfera", "regulador_1", "regulador_2", "tampao", "te", "uniao",
           "valvula_retencao"]
