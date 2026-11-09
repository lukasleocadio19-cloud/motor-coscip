"""Dimensionamento de extintores (NT 2-01): quantidade por pavimento, tipo e capacidade.

O critério de ÁREA é calculado aqui. O de DISTÂNCIA (percurso real até o extintor, com
paredes e obstáculos) só se verifica na planta: use ``analisar_planta`` depois de posicionar.
"""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from coscip_design.memorial import Memorial
from coscip_design.params import Parametros

Risco = Literal["PEQUENO", "MEDIO", "GRANDE"]


class PavimentoExt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=60)
    area_m2: float = Field(gt=0)
    instalacoes_especiais: list[str] = Field(
        default_factory=list,
        description="casa de máquinas, casa de bombas, subestação, gerador… (NT 2-01, 6.4)")


class EntradaExtintores(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risco: Risco
    pavimentos: list[PavimentoExt] = Field(min_length=1)
    unifamiliar: bool = False


def dimensionar(params: Parametros, entrada: dict[str, Any]) -> Memorial:
    e = EntradaExtintores.model_validate(entrada)
    m = Memorial("extintores", "Extintores de incêndio (NT 2-01)",
                 {"risco": e.risco, "pavimentos": {p.nome: f"{p.area_m2:g} m²"
                                                   for p in e.pavimentos}})
    if e.unifamiliar:
        m.pendencias.append("NT 2-01, item 2: a nota não se aplica a residência unifamiliar; "
                            "nada a dimensionar.")
        m.resultados = {"total_de_extintores": 0}
        return m
    p_area = params.get("ext.area_max_m2")
    p_dist = params.get("ext.distancia_max_m")
    p_min = params.get("ext.minimo_por_edificacao")
    p_unico = params.get("ext.unico_abc_area_m2")
    p_cap = params.get("ext.capacidade_minima_portatil")
    p_esp = params.get("ext.instalacao_especial_distancia_m")
    area_max = p_area.valor[e.risco]
    area_total = sum(p.area_m2 for p in e.pavimentos)
    unico = e.risco == "PEQUENO" and area_total < p_unico.valor

    quadro = []
    total = 0
    for pav in e.pavimentos:
        por_area = math.ceil(pav.area_m2 / area_max)
        minimo = 1 if unico else p_min.valor
        n = max(por_area, minimo)
        m.passo(f"{pav.nome}: unidades extintoras pela área", por_area, unidade="un",
                formula="N = teto(área / área máxima por unidade)",
                base=[p_area], area_m2=pav.area_m2, area_max_m2=area_max)
        m.passo(f"{pav.nome}: mínimo de extintores", minimo, unidade="un",
                base=[p_unico] if unico else [p_min],
                nota=("edificação de risco pequeno com menos de 50 m²: uma unidade de pó ABC"
                      if unico else "um classe A e um classes B e C, ou dois de pó ABC"))
        especiais = len(pav.instalacoes_especiais)
        if especiais:
            m.passo(f"{pav.nome}: extintores das instalações especiais", especiais, unidade="un",
                    base=[p_esp], instalacoes=pav.instalacoes_especiais,
                    nota=f"um por instalação, a no máximo {p_esp.valor} m dela; tipo conforme a "
                         "NT ou a NBR da instalação")
        quadro.append({"pavimento": pav.nome, "area_m2": pav.area_m2, "por_area": por_area,
                       "minimo": minimo, "adotado": n, "instalacoes_especiais": especiais,
                       "total": n + especiais})
        total += n + especiais

    cap = m.usa(p_cap)
    tipo = {"agente": "PQS_ABC", "simbolo": "EXTINTOR_PQS_ABC",
            "capacidade_minima": cap["PQS_ABC"],
            "alternativa": f"um de água ({cap['AGUA']}) + um de CO2 ({cap['CO2']}) ou pó BC "
                           f"({cap['PQS_BC']})"}
    if e.risco == "GRANDE":
        p_4a = params.get("ext.risco_grande_classe_a")
        p_rodas = params.get("ext.sobre_rodas_risco_grande")
        p_cap_r = params.get("ext.capacidade_minima_sobre_rodas")
        tipo["capacidade_minima_classe_a"] = m.usa(p_4a)
        m.usa(p_rodas)
        m.resultados["sobre_rodas"] = {
            "obrigatorio": True, "simbolo": "EXTINTOR_PQS_ABC_SOBRERODAS",
            "capacidade_minima": m.usa(p_cap_r)["PQS_ABC"],
            "regra": "protege no máximo metade da área do risco; o restante por portáteis, "
                     "alternando os dois tipos; não protege pavimentos diferentes"}
        m.pendencias.append("Risco grande: definir quantos extintores sobre rodas e quais "
                            "áreas eles cobrem (acesso livre, sem degraus nem soleiras).")

    m.resultados.update({"total_de_extintores": total, "quadro_por_pavimento": quadro,
                         "tipo_sugerido": tipo,
                         "distancia_maxima_a_percorrer_m": m.usa(p_dist)[e.risco],
                         "altura_maxima_da_alca_m": m.usa(params.get("ext.altura_alca_max_m"))})
    m.verificar_na_planta += [
        f"Distância real a percorrer até o extintor ≤ {p_dist.valor[e.risco]} m em todos os "
        "pontos (analisar_planta mede o pior percurso); se passar, acrescentar extintores.",
        "Extintor junto aos acessos, visível, fora de escadas e sem obstrução (5.2.2).",
        "Placa E-5 em cada extintor (NT 2-05)."]
    m.pendencias.append("Classes D e K (metais pirofóricos, cozinha profissional) e depósitos de "
                        "inflamáveis/GLP seguem notas específicas (NT 2-01 6.2 e 6.3): fora "
                        "deste cálculo.")
    return m
