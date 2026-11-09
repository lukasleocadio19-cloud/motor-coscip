"""Requisitos de projeto da iluminação de emergência (NT 2-06) e do alarme (NT 2-07).

As duas notas remetem o dimensionamento fino às normas ABNT (NBR 10898 e NBR 17240), que não
estão na base do motor. Aqui sai só o que as NTs fixam; o resto fica como pendência explícita.
"""

from __future__ import annotations

from coscip_design.memorial import Memorial
from coscip_design.params import Parametros


def iluminacao(params: Parametros, ocupacao: str) -> Memorial:
    div = ocupacao.strip().upper()
    grupo = div.split("-")[0]
    m = Memorial("iluminacao", "Iluminação de emergência (NT 2-06)", {"ocupacao": div})
    p_loc = params.get("ilu.locais")
    p_aut = params.get("ilu.autonomia_min")
    p_esc = params.get("ilu.escadas")
    chave = "B_C_F_H" if grupo in {"B", "C", "F", "H"} else "A_D_E_G_I_J_L_M"
    m.passo("Onde instalar", p_loc.valor[chave], base=[p_loc])
    m.passo("Autonomia mínima", p_aut.valor.get(div, p_aut.valor["geral"]), unidade="min",
            base=[p_aut])
    m.passo("Escadas", p_esc.valor, base=[p_esc])
    m.resultados = {"simbolo": "PONTO_ILUMINACAO_EMERGENCIA",
                    "autonomia_min": p_aut.valor.get(div, p_aut.valor["geral"]),
                    "locais": p_loc.valor[chave]}
    m.pendencias.append("Espaçamento, nível de iluminamento e tipo de luminária seguem a ABNT "
                        "NBR 10898 (NT 2-06, 5.1.1), que não está na base do motor: definir com "
                        "o responsável técnico.")
    m.verificar_na_planta.append("Pontos ao longo de toda a rota de saída, nas mudanças de "
                                 "direção e nas portas de saída, sem ponto de sombra.")
    return m


def alarme(params: Parametros) -> Memorial:
    m = Memorial("alarme", "Alarme de incêndio (NT 2-07)")
    p_dist = params.get("ala.acionador_distancia_m")
    p_aut = params.get("ala.autonomia")
    m.passo("Distância máxima a percorrer até um acionador manual", p_dist.valor, unidade="m",
            base=[p_dist], nota="em cada pavimento, nos locais de trânsito de pessoas")
    m.passo("Autonomia da fonte secundária", p_aut.valor, base=[p_aut])
    m.resultados = {"simbolos": ["ACIONADOR_MANUAL", "AVISADOR_SONORO_ELETRONICO",
                                 "CENTRAL_ALARME_DETECCAO"],
                    "acionador_distancia_max_m": p_dist.valor}
    m.pendencias.append("Quantidade e posição de avisadores, central e, quando exigida, "
                        "detecção seguem a NT 2-07 e a ABNT NBR 17240: fora deste cálculo.")
    m.verificar_na_planta.append("Percurso até o acionador ≤ 30 m em todos os pontos "
                                 "(analisar_planta mede o pior percurso).")
    return m
