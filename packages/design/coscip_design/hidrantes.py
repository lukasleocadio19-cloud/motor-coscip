"""Dimensionamento do sistema de hidrantes e mangotinhos (NT 2-02).

Segue a planilha-modelo do Anexo B da NT 2-02: perda de carga por trecho (Hazen-Williams, com
comprimentos equivalentes), altura manométrica de sucção e de recalque, pressão na mangueira e
pressão de trabalho → altura manométrica total; mais reserva técnica de incêndio, velocidades e
potência estimada da bomba.

O que a NT não fixa entra como premissa do projetista e sai listado: constante da fórmula de
Hazen-Williams (no texto ingerido a fórmula é uma imagem), coeficiente C da mangueira,
comprimentos equivalentes das peças e rendimento da bomba.
"""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from coscip_design.memorial import Memorial
from coscip_design.params import Parametros

RiscoHid = Literal["PEQUENO_MANGOTINHO", "PEQUENO", "MEDIO_1", "MEDIO_2", "GRANDE"]
Material = Literal["FERRO_FUNDIDO", "ACO_PRETO", "GALVANIZADO", "COBRE"]
HW_K = 10.65  # forma SI de Hazen-Williams: J = 10,65 · Q^1,85 / (C^1,85 · D^4,87), Q m³/s, D m
REDE = ("MEDIO_2", "GRANDE")


class Trecho(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=60)
    comprimento_m: float = Field(ge=0, description="tubo reto do trecho")
    comprimento_equivalente_m: float = Field(
        default=0.0, ge=0, description="soma dos comprimentos equivalentes das peças do trecho")
    diametro_interno_mm: float = Field(gt=10, le=400)
    vazao: Literal["SISTEMA", "HIDRANTE"] = Field(
        default="SISTEMA", description="SISTEMA: vazão total; HIDRANTE: ramal de um só hidrante")
    colar: bool = Field(default=False, description="trecho do colar hidráulico da bomba")


class EntradaHidrantes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risco: RiscoHid
    numero_de_hidrantes: int = Field(ge=1, le=500)
    material: Material = "ACO_PRETO"
    succao: list[Trecho] = Field(default_factory=list)
    recalque: list[Trecho] = Field(default_factory=list)
    desnivel_m: float = Field(
        default=0.0, ge=-300, le=300,
        description="cota do hidrante mais desfavorável menos o nível mínimo da água do "
                    "reservatório (positivo: a bomba eleva; negativo: reservatório acima)")
    mangueira_m: float = Field(default=30.0, gt=0, le=60)
    c_mangueira: float = Field(default=140.0, ge=80, le=160)
    rendimento_bomba: float = Field(default=0.5, gt=0.1, le=0.9)


def hazen_williams(q_lpm: float, c: float, d_mm: float) -> float:
    """Perda de carga unitária J (m/m) para Q em L/min e D interno em mm."""
    q = q_lpm / 60000.0
    d = d_mm / 1000.0
    return HW_K * q ** 1.85 / (c ** 1.85 * d ** 4.87)


def velocidade(q_lpm: float, d_mm: float) -> float:
    return (q_lpm / 60000.0) / (math.pi * (d_mm / 1000.0) ** 2 / 4)


def dimensionar(params: Parametros, entrada: dict[str, Any]) -> Memorial:
    e = EntradaHidrantes.model_validate(entrada)
    m = Memorial("hidrantes", "Hidrantes e mangotinhos (NT 2-02)",
                 {"risco": e.risco, "numero_de_hidrantes": e.numero_de_hidrantes,
                  "material_da_tubulacao": e.material, "desnivel_m": e.desnivel_m})
    p_sis = params.get(f"hid.sistema.{e.risco}")
    sis = m.usa(p_sis)
    q_sis = float(sis["vazao_lpm"])
    simult = int(sis["hidrantes_simultaneos"])
    q_hid = q_sis / simult
    m.passo("Sistema exigido", f"{'rede' if e.risco in REDE else 'canalização'} preventiva"
            if e.risco != "PEQUENO_MANGOTINHO" else "mangotinho", base=[p_sis],
            esguicho_mm=sis["esguicho_mm"], mangueira_mm=sis["mangueira_mm"],
            hidrantes_simultaneos=simult, pressao_de_trabalho_mca=sis["pressao_mca"],
            vazao_lpm=q_sis)
    if simult > 1:
        m.premissas.append(
            f"A vazão da Tabela 1 ({q_sis:g} L/min) foi tomada como vazão do SISTEMA, dividida "
            f"entre os {simult} hidrantes em uso simultâneo ({q_hid:g} L/min em cada um). "
            "Confirmar a leitura da tabela com o responsável técnico.")

    # --- reserva técnica de incêndio ---------------------------------------------------------
    p_base = params.get("hid.rti_base_l")
    p_acr = params.get("hid.rti_acrescimo_l")
    base = p_base.valor[e.risco]
    excedente = max(0, e.numero_de_hidrantes - p_acr.valor["a_partir_de"])
    rti = min(base + excedente * p_acr.valor["por_hidrante_excedente"],
              p_acr.valor["maximo"][e.risco])
    m.passo("Reserva técnica de incêndio (RTI)", rti, unidade="L",
            formula="RTI = base + 500 × (hidrantes − 4), limitada ao máximo do risco",
            base=[p_base, p_acr], base_l=base, hidrantes_excedentes=excedente,
            maximo_l=p_acr.valor["maximo"][e.risco])

    # --- perdas de carga ------------------------------------------------------------------------
    p_c = params.get("hid.hazen_williams_c")
    c = p_c.valor[e.material]
    p_vcolar = params.get("hid.velocidade_max_ms")
    p_vgeral = params.get("hid.velocidade_geral_ms")
    m.premissas.append(
        f"Hazen-Williams na forma SI: J = {HW_K:g}·Q^1,85 / (C^1,85·D^4,87), Q em m³/s e D em m "
        "(a NT 2-02 5.7.6 define as variáveis; a fórmula é imagem no texto ingerido).")

    def perdas(lado: str, trechos: list[Trecho]) -> float:
        total = 0.0
        for t in trechos:
            q = q_sis if t.vazao == "SISTEMA" else q_hid
            j = hazen_williams(q, c, t.diametro_interno_mm)
            hf = j * (t.comprimento_m + t.comprimento_equivalente_m)
            v = velocidade(q, t.diametro_interno_mm)
            limite = p_vgeral.valor
            if t.colar:
                limite = p_vcolar.valor["succao" if lado == "sucção" else "recalque_colar"]
            m.passo(f"Perda de carga — {lado}: {t.nome}", round(hf, 3), unidade="mca",
                    formula="hf = J × (L + Leq)", base=[p_c],
                    Q_lpm=q, C=c, D_mm=t.diametro_interno_mm, J_m_por_m=round(j, 5),
                    L_m=t.comprimento_m, Leq_m=t.comprimento_equivalente_m,
                    velocidade_m_s=round(v, 2))
            if v > limite + 1e-9:
                m.usa(p_vcolar if t.colar else p_vgeral)
                m.pendencias.append(
                    f"{t.nome}: velocidade {v:.2f} m/s acima do máximo de {limite:g} m/s "
                    f"({'colar hidráulico, 5.7.7' if t.colar else '5.7.8'}): aumentar o diâmetro.")
            total += hf
        return total

    hms = perdas("sucção", e.succao)
    hmr = perdas("recalque", e.recalque)
    if not e.recalque:
        m.pendencias.append("Nenhum trecho de recalque informado: a altura manométrica abaixo "
                            "não inclui perdas na tubulação. Informe os trechos até o hidrante "
                            "mais desfavorável (comprimento, peças e diâmetro interno).")
    p_mang = params.get("hid.mangueira_alcance")
    if e.mangueira_m > p_mang.valor["linha_max_m"]:
        m.pendencias.append(f"Linha de mangueiras de {e.mangueira_m:g} m acima do máximo de "
                            f"{p_mang.valor['linha_max_m']} m (5.6.1 b).")
    j_mang = hazen_williams(q_hid, e.c_mangueira, float(sis["mangueira_mm"]))
    h_mang = j_mang * e.mangueira_m
    m.passo("Perda de carga na mangueira", round(h_mang, 3), unidade="mca",
            formula="P mang = J × comprimento da linha", base=[p_mang], Q_lpm=q_hid,
            C=e.c_mangueira, D_mm=sis["mangueira_mm"], L_m=e.mangueira_m)
    m.premissas.append(f"Coeficiente C da mangueira = {e.c_mangueira:g} e diâmetro interno igual "
                       "ao nominal (a NT manda somar a perda na mangueira, 5.1.3, sem fixar C).")
    m.premissas.append("Comprimentos equivalentes das peças informados pelo projetista (a NT não "
                       "traz tabela; a planilha do Anexo B só reserva os campos).")

    p_trab = float(sis["pressao_mca"])
    hmt = hms + hmr + h_mang + p_trab + e.desnivel_m
    m.passo("Altura manométrica total", round(hmt, 2), unidade="mca",
            formula="Hmt = Hms + Hmr + P mang + P trab + desnível", base=[p_sis],
            Hms=round(hms, 3), Hmr=round(hmr, 3), P_mang=round(h_mang, 3), P_trab=p_trab,
            desnivel_m=e.desnivel_m,
            nota="estrutura da planilha-modelo do Anexo B da NT 2-02")
    p_max = params.get("hid.pressao_max_mca")
    bomba: dict[str, Any]
    if hmt <= 0:
        bomba = {"necessaria": False,
                 "motivo": "o desnível do reservatório cobre perdas e pressão de trabalho"}
        m.pendencias.append("Pelo cálculo a gravidade atende o hidrante mais desfavorável; "
                            "conferir os demais hidrantes e a exigência de bombas da NT 2-04.")
    else:
        pot_cv = 1000.0 * (q_sis / 60000.0) * hmt / (75.0 * e.rendimento_bomba)
        m.passo("Potência estimada da bomba", round(pot_cv, 2), unidade="cv",
                formula="P = 1000 × Q × Hmt / (75 × η)", Q_m3_s=round(q_sis / 60000.0, 5),
                Hmt_mca=round(hmt, 2), rendimento=e.rendimento_bomba)
        m.premissas.append(f"Rendimento da bomba η = {e.rendimento_bomba:g}; a potência é "
                           "estimativa: a escolha é pela curva do fabricante no ponto (Q, Hmt).")
        bomba = {"necessaria": True, "vazao_lpm": q_sis, "vazao_m3_h": round(q_sis * 0.06, 2),
                 "altura_manometrica_mca": round(hmt, 2), "potencia_estimada_cv": round(pot_cv, 2)}
        if hmt > p_max.valor:
            m.usa(p_max)
            m.pendencias.append(f"Hmt de {hmt:.1f} mca acima da pressão máxima de "
                                f"{p_max.valor} mca (5.7.4): aumentar diâmetros ou usar válvula "
                                "redutora (5.7.9).")
    m.pendencias.append("Conjunto de pressurização (quantidade e tipo de bombas, partida, "
                        "pressostato) segue a NT 2-04: fora deste cálculo.")

    rede = e.risco in REDE
    recalque = {"tipo": "duplo, tubulação ≥ 75 mm" if q_sis >= params.get(
        "hid.recalque_duplo_lpm").valor else "simples"}
    m.usa(params.get("hid.recalque_duplo_lpm"))
    m.resultados.update({
        "sistema": sis, "vazao_por_hidrante_lpm": q_hid, "rti_l": rti,
        "perdas_mca": {"succao": round(hms, 3), "recalque": round(hmr, 3),
                       "mangueira": round(h_mang, 3)},
        "bomba": bomba, "hidrante_de_recalque": recalque,
        "casa_de_maquinas": m.usa(params.get("hid.cmi_dimensoes_rede" if rede
                                             else "hid.cmi_dimensoes")),
        "abrigo_de_mangueiras": m.usa(params.get("hid.abrigo_dimensoes_rede" if rede
                                                 else "hid.abrigo_dimensoes")),
        "altura_do_registro_m": m.usa(params.get("hid.registro_altura_m"))})
    m.verificar_na_planta += [
        "Qualquer ponto alcançado por uma linha de mangueiras de até 30 m, medida pelo percurso "
        "(analisar_planta mede o pior percurso até o hidrante).",
        "Hidrantes fora de caixas de escada e antecâmaras, próximos aos acessos; placas da "
        "NT 2-05."]
    return m
