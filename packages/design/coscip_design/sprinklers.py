"""Dimensionamento do sistema de chuveiros automáticos (sprinklers), NT 2-03 parte 1.

A NT 2-03 fixa **o que o CBMERJ exige** do sistema: onde ele abrange e onde se dispensa, a
reserva técnica (RTI = Q × t, com o tempo da Tabela 1 do Anexo B), válvula de governo e alarme,
shaft, hidrante de recalque e materiais. **Não fixa** densidade, área de operação, área por bico,
espaçamento nem o método hidráulico: manda seguir a ABNT NBR 10897 (ou a NFPA 13, se a NBR não
tratar do assunto, item 5.1.1). Esses valores não estão na base do motor; entram aqui como
**premissa do projetista**, com valores de referência da NFPA 13:2019 que o memorial marca para
conferência na norma adotada. Cada passo que sai da NT cita o item, conferido no texto.

A parte geométrica (malha de bicos, ramais, perdas por trecho) fica em ``rede_sprinklers``.
"""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from coscip_design.memorial import Memorial
from coscip_design.params import Parametros
from coscip_design.rede_sprinklers import Criterios, Rede, Zona, projetar

Classe = Literal["LEVE", "ORDINARIO_1", "ORDINARIO_2", "EXTRAORDINARIO_1", "EXTRAORDINARIO_2"]
TipoAmbiente = Literal["COMUM", "SANITARIO", "VESTIARIO", "SUBESTACAO", "CAMARA_FRIA",
                       "VARANDA_ABERTA", "ENTREFORRO", "CPD", "CASA_MAQUINAS", "RADIOLOGIA"]
CATEGORIA_RTI = {"LEVE": "LEVE", "ORDINARIO_1": "ORDINARIO", "ORDINARIO_2": "ORDINARIO",
                 "EXTRAORDINARIO_1": "EXTRAORDINARIO", "EXTRAORDINARIO_2": "EXTRAORDINARIO"}
ORDEM_RISCO = list(CATEGORIA_RTI)
FONTE_REFERENCIA = ("NFPA 13:2019 (curvas densidade × área e espaçamento de bico padrão) como "
                    "valor de referência; NÃO está na base do motor")
# densidade (L/min/m² = mm/min), área de operação (m²), área máxima por bico (m²), espaçamento
# máximo (m). Conversão da NFPA 13: 0,10/0,15/0,20/0,30/0,40 gpm/ft²; 1500 e 2500 ft²; 225, 130
# e 100 ft²; 15 e 12 ft.
REFERENCIA: dict[str, dict[str, float]] = {
    "LEVE": {"densidade": 4.1, "area_operacao": 139.0, "area_bico": 20.9, "espacamento": 4.6},
    "ORDINARIO_1": {"densidade": 6.1, "area_operacao": 139.0, "area_bico": 12.1,
                    "espacamento": 4.6},
    "ORDINARIO_2": {"densidade": 8.1, "area_operacao": 139.0, "area_bico": 12.1,
                    "espacamento": 4.6},
    "EXTRAORDINARIO_1": {"densidade": 12.2, "area_operacao": 232.0, "area_bico": 9.3,
                         "espacamento": 3.7},
    "EXTRAORDINARIO_2": {"densidade": 16.3, "area_operacao": 232.0, "area_bico": 9.3,
                         "espacamento": 3.7},
}


class Ambiente(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=60)
    area_m2: float = Field(gt=0, le=100000)
    tipo: TipoAmbiente = "COMUM"
    temperatura_c: float | None = Field(default=None, description="câmara frigorífica")
    compartimentado_30min: bool = Field(
        default=False, description="compartimentação equivalente a 30 min de TRRF (5.2.5)")
    substituir_por_detector: bool = Field(
        default=False, description="o projetista opta por detectores no lugar dos bicos (5.2.5)")
    termo_de_compromisso: bool = Field(
        default=False, description="Termo de Compromisso do Anexo A apresentado (varanda, "
                                    "entreforro)")


class ZonaEntrada(BaseModel):
    """Zona da planta onde a malha de bicos e a hidráulica são calculadas."""

    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=40)
    retangulo: list[float] | None = Field(default=None, min_length=4, max_length=4)
    poligono: list[list[float]] | None = None
    alimentacao: list[float] = Field(min_length=2, max_length=2,
                                     description="[x, y] onde a prumada chega à zona")
    z_ramal_m: float = Field(default=3.0, gt=0.5, le=30)
    z_base_m: float = Field(default=0.0, ge=-10, le=50)
    orientacao: Literal["auto", "x", "y"] = "auto"

    @model_validator(mode="after")
    def _forma(self) -> ZonaEntrada:
        if (self.retangulo is None) == (self.poligono is None):
            raise ValueError("zona: informe retangulo OU poligono")
        return self

    def zona(self) -> Zona:
        if self.retangulo is not None:
            x0, y0, x1, y1 = self.retangulo
            pts = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
        else:
            pts = tuple((p[0], p[1]) for p in self.poligono or [])
        return Zona(self.nome, pts, (self.alimentacao[0], self.alimentacao[1]), self.z_ramal_m,
                    self.z_base_m, self.orientacao)


class EntradaSprinklers(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classe: Classe
    norma_adotada: Literal["NBR_10897", "NFPA_13"] = "NBR_10897"
    ambientes: list[Ambiente] = Field(default_factory=list, max_length=500)
    zonas: list[ZonaEntrada] = Field(default_factory=list, max_length=40)
    resposta: Literal["PADRAO", "RAPIDA"] = "PADRAO"
    tubo: Literal["ACO", "COBRE", "CPVC"] = "ACO"
    # critérios da norma adotada (None: valor de referência da NFPA 13, como premissa)
    densidade_mm_min: float | None = Field(default=None, gt=0, le=60)
    area_operacao_m2: float | None = Field(default=None, gt=0, le=2000)
    area_max_bico_m2: float | None = Field(default=None, gt=0, le=40)
    espacamento_max_m: float | None = Field(default=None, gt=0, le=8)
    fator_k: float = Field(default=80.0, gt=10, le=400, description="L/min/bar^½")
    pressao_minima_bar: float = Field(default=0.5, gt=0, le=5)
    velocidade_max_ms: float = Field(default=5.0, gt=0.5, le=12)
    conexoes_pct: float = Field(default=20.0, ge=0, le=100)
    perda_vga_bar: float = Field(default=0.3, ge=0, le=3)
    c_hazen_williams: float = Field(default=120.0, ge=80, le=160)
    # edificação
    grupo_divisao: str | None = Field(default=None, description="ex. F-8")
    pavimentos_protegidos: int = Field(default=1, ge=1, le=100)
    prumada_atravessa_pavimentos: bool = False
    reservatorio_acima_do_teto: bool | None = None
    pavimentos_computaveis: int | None = Field(default=None, ge=1, le=200)
    # reserva
    hidrantes_conjugados: bool = False
    rti_hidrantes_l: float = Field(default=0.0, ge=0, le=1_000_000)
    volume_reservatorio_l: float | None = Field(default=None, gt=0, le=10_000_000)
    reservatorio_unico: bool = True


def criterios_de(e: EntradaSprinklers) -> Criterios:
    ref = REFERENCIA[e.classe]
    return Criterios(
        densidade_mm_min=e.densidade_mm_min or ref["densidade"],
        area_operacao_m2=e.area_operacao_m2 or ref["area_operacao"],
        area_max_bico_m2=e.area_max_bico_m2 or ref["area_bico"],
        espacamento_max_m=e.espacamento_max_m or ref["espacamento"],
        k=e.fator_k, pressao_min_bar=e.pressao_minima_bar, c_hw=e.c_hazen_williams,
        v_max_ms=e.velocidade_max_ms, conexoes_pct=e.conexoes_pct,
        perda_vga_bar=e.perda_vga_bar)


def _milhar(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


def decidir(a: Ambiente, params: Parametros, m: Memorial) -> tuple[str, str]:
    """Decisão para o ambiente: (PROTEGER | DISPENSADO | DETECTORES, motivo com o item da NT)."""
    t = a.tipo
    if t == "SANITARIO":
        m.usa(params.get("spk.dispensa_sanitarios"))
        return "DISPENSADO", "banheiro, lavatório ou lavabo (NT 2-03, 5.2.3)"
    if t == "VESTIARIO":
        m.usa(params.get("spk.dispensa_sanitarios"))
        return "PROTEGER", "vestiário: a dispensa de banheiros não vale (5.2.3)"
    if t == "SUBESTACAO":
        lim = params.get("spk.dispensa_sanitarios").valor["area_max_eletrica_m2"]
        m.usa(params.get("spk.dispensa_sanitarios"))
        if a.area_m2 <= lim:
            return "DISPENSADO", f"subestação, sala de medidores ou de PC de energia até {lim} m²"
        return _detector(a, params, m, params.get("spk.detector_alternativa").valor[
            "subestacao_area_max_m2"], "subestação acima de 20 m²")
    if t == "CASA_MAQUINAS":
        return _detector(a, params, m, params.get("spk.detector_alternativa").valor[
            "subestacao_area_max_m2"], "casa de máquinas de elevador ou de incêndio sem motor "
                                       "à explosão")
    if t == "CPD":
        return _detector(a, params, m, params.get("spk.detector_alternativa").valor[
            "cpd_area_max_m2"], "centro de processamento de dados")
    if t == "RADIOLOGIA":
        return _detector(a, params, m, None, "sala de equipamento de radiologia")
    if t == "CAMARA_FRIA":
        p = params.get("spk.dispensa_camara_fria")
        m.usa(p)
        v = p.valor
        if a.temperatura_c is not None and a.temperatura_c < v["temperatura_max_c"] \
                and a.area_m2 <= v["area_max_m2"]:
            return "DISPENSADO", (f"câmara frigorífica a {a.temperatura_c:g} °C e "
                                  f"{a.area_m2:g} m² (5.2.3.1)")
        return "PROTEGER", (f"câmara frigorífica fora da dispensa (precisa de temperatura "
                            f"abaixo de "
                            f"{v['temperatura_max_c']} °C e até {v['area_max_m2']} m²; "
                            "temperatura informada: "
                            f"{'não informada' if a.temperatura_c is None else a.temperatura_c})")
    if t == "VARANDA_ABERTA":
        m.usa(params.get("spk.dispensa_varanda"))
        return "DISPENSADO", "varanda permanentemente aberta (5.2.4), com Termo de Compromisso"
    if t == "ENTREFORRO":
        m.usa(params.get("spk.entreforro"))
        if a.termo_de_compromisso:
            return "DISPENSADO", "entreforro com Termo de Compromisso (Anexo A, Quadro 2; 5.2.6.1)"
        return "PROTEGER", "entreforro sujeito aos bicos (5.2.6)"
    m.usa(params.get("spk.abrangencia"))
    return "PROTEGER", "o sistema abrange toda a área da edificação (5.2.1)"


def _detector(a: Ambiente, params: Parametros, m: Memorial, limite: float | None,
              rotulo: str) -> tuple[str, str]:
    p = params.get("spk.detector_alternativa")
    m.usa(p)
    ok = a.compartimentado_30min and (limite is None or a.area_m2 <= limite)
    if ok and a.substituir_por_detector:
        return "DETECTORES", (f"{rotulo}: detectores no lugar dos bicos, a critério do projetista, "
                              "com compartimentação de 30 min de TRRF (5.2.5)")
    if ok:
        return "PROTEGER", (f"{rotulo}: poderia ter detectores (5.2.5) mas o projetista não optou "
                            "por eles")
    return "PROTEGER", (f"{rotulo}: não cumpre as condições da alternativa por detectores "
                        f"(compartimentação de 30 min de TRRF"
                        f"{'' if limite is None else f' e área até {limite:g} m²'})")


def dimensionar(params: Parametros, entrada: dict[str, Any]) -> Memorial:
    e = EntradaSprinklers.model_validate(entrada)
    crit = criterios_de(e)
    m = Memorial("sprinklers", "Chuveiros automáticos / sprinklers (NT 2-03 parte 1)",
                 {"classe_de_risco": e.classe, "norma_adotada": e.norma_adotada.replace("_", " "),
                  "resposta": e.resposta, "tubo": e.tubo,
                  "grupo_divisao": e.grupo_divisao})
    ref = REFERENCIA[e.classe]
    usados = {"densidade": e.densidade_mm_min, "area_operacao": e.area_operacao_m2,
              "area_bico": e.area_max_bico_m2, "espacamento": e.espacamento_max_m}
    de_referencia = [k for k, v in usados.items() if v is None]
    m.passo("Critérios de projeto (norma adotada)", {
        "densidade_mm_min": crit.densidade_mm_min, "area_de_operacao_m2": crit.area_operacao_m2,
        "area_maxima_por_bico_m2": crit.area_max_bico_m2,
        "espacamento_maximo_m": crit.espacamento_max_m},
        nota="a NT 2-03, 5.1.1, manda seguir a ABNT NBR 10897 (ou a NFPA 13 se a NBR não tratar "
             "do assunto) para classificação do risco, área de operação e demais parâmetros")
    if de_referencia:
        m.premissas.append(
            f"{', '.join(de_referencia)}: valores de referência da {FONTE_REFERENCIA}, para a "
            f"classe {e.classe} (densidade {ref['densidade']} mm/min, área de operação "
            f"{ref['area_operacao']:g} m², até {ref['area_bico']} m² por bico e "
            f"{ref['espacamento']} m entre bicos). Conferir na norma adotada "
            f"({e.norma_adotada.replace('_', ' ')}) antes de usar.")
    m.premissas.append(
        f"Fator K = {e.fator_k:g} L/min/bar^½ (NT 2-03, 4.8, só define o fator), pressão mínima no "
        f"bico {e.pressao_minima_bar:g} bar, C de Hazen-Williams {e.c_hazen_williams:g}, "
        f"velocidade máxima {e.velocidade_max_ms:g} m/s, conexões {e.conexoes_pct:g} % do tubo "
        f"reto e perda da VGA {e.perda_vga_bar:g} bar: premissas do projetista (a NT não fixa).")

    # --- onde se instala e onde se dispensa -----------------------------------------------------
    linhas = []
    protegida = 0.0
    n_min = 0
    for a in e.ambientes:
        decisao, motivo = decidir(a, params, m)
        n = math.ceil(a.area_m2 / crit.area_max_bico_m2 - 1e-9) if decisao == "PROTEGER" else 0
        protegida += a.area_m2 if decisao == "PROTEGER" else 0.0
        n_min += n
        linhas.append({"ambiente": a.nome, "area_m2": a.area_m2, "decisao": decisao,
                       "motivo": motivo, "bicos_minimos": n})
        if a.tipo == "VARANDA_ABERTA":
            m.pendencias.append(f"{a.nome}: apresentar em planta o Termo de Compromisso do "
                                "Anexo A, Quadro 1 (acabamento incombustível e sem fechamento "
                                "das aberturas), NT 2-03, 5.2.4.2.")
        if a.tipo == "ENTREFORRO" and not a.termo_de_compromisso:
            m.pendencias.append(f"{a.nome}: sem bicos no entreforro só com o Termo de "
                                "Compromisso do Anexo A, Quadro 2 (5.2.6.1); aplicam-se as "
                                "isenções da NBR 10897.")
        if a.tipo == "CAMARA_FRIA" and a.temperatura_c is not None:
            m.pendencias.append(f"{a.nome}: havendo mais de uma câmara dispensada, cumprir a "
                                "compartimentação da NT 2-18 (5.2.3.1.1).")
        if a.tipo in ("CPD", "CASA_MAQUINAS", "SUBESTACAO", "RADIOLOGIA") \
                and decisao == "DETECTORES":
            m.pendencias.append(f"{a.nome}: detectores ligados ao alarme do prédio ou ao do "
                                "sistema de bicos (5.2.5) e compartimentação de 30 min de TRRF.")
    if e.ambientes:
        m.passo("Ambientes e dispensas", linhas, base=[params.get("spk.abrangencia")],
                nota="decisão por ambiente conforme o tipo informado pelo projetista")
    m.passo("Área protegida", round(protegida, 2), unidade="m²",
            formula="soma das áreas dos ambientes que levam bicos")
    if n_min:
        m.passo("Número mínimo de bicos", n_min, unidade="un",
                formula="Σ ⌈área do ambiente ÷ área máxima por bico⌉",
                nota="mínimo teórico por área: o número real vem da malha (espaçamento, paredes "
                     "e obstruções) e é maior")

    # --- vazão e área de operação ---------------------------------------------------------------
    n_op = max(1, math.ceil(crit.area_operacao_m2 / crit.area_max_bico_m2 - 1e-9))
    q_bico = crit.densidade_mm_min * crit.area_max_bico_m2
    p_bico = max(crit.pressao_min_bar, (q_bico / crit.k) ** 2)
    m.passo("Vazão mínima em cada bico da área de operação", round(q_bico, 2), unidade="L/min",
            formula="q = densidade × área por bico", densidade=crit.densidade_mm_min,
            area_por_bico_m2=crit.area_max_bico_m2)
    m.passo("Pressão no bico remoto", round(p_bico, 3), unidade="bar",
            formula="P = (q ÷ K)², não menor que a pressão mínima", q_lpm=round(q_bico, 2),
            K=crit.k, pressao_minima_bar=crit.pressao_min_bar)
    q_min = n_op * q_bico
    m.passo("Vazão mínima do sistema (sem perdas)", round(q_min, 1), unidade="L/min",
            formula="Q = bicos da área de operação × q", bicos_na_area=n_op)

    # --- hidráulica das zonas -----------------------------------------------------------------
    redes: list[Rede] = [projetar(z.zona(), crit) for z in e.zonas]
    q_sist = q_min
    pior: Rede | None = None
    if redes:
        pior = max(redes, key=lambda r: r.resumo.get("vazao_total_lpm", 0.0))
        q_sist = max(q_min, pior.resumo.get("vazao_total_lpm", 0.0))
        for r in redes:
            m.passo(f"Rede da zona {r.zona.nome}", r.resumo, nota="cálculo hidráulico da área de "
                    "operação remota (bicos em cascata, Hazen-Williams); simplificado")
            m.pendencias += [f"Zona {r.zona.nome}: {av}" for av in r.avisos]
        m.premissas.append(
            "A hidráulica é a de uma zona retangular ou poligonal alimentada por uma subgeral, "
            "com tubo de aço classe 40 e diâmetros escolhidos por velocidade e perda unitária. Não "
            "trata de obstruções, vigas, desníveis internos nem de vários ramais ligados por "
            "laços: o projeto executivo usa o programa de cálculo do projetista.")
    else:
        m.pendencias.append("Nenhuma zona informada: a vazão acima não inclui as perdas de carga "
                            "nas tubulações. Informe 'zonas' (polígono e ponto de alimentação) "
                            "para o cálculo hidráulico e a pressão na base da prumada.")

    # --- reserva técnica de incêndio -------------------------------------------------------------
    p_t = params.get("spk.rti_duracao_min")
    categoria = CATEGORIA_RTI[e.classe]
    t_min = p_t.valor[categoria]
    rti_spk = q_sist * t_min
    m.passo("Reserva técnica de incêndio dos sprinklers (RTI)", round(rti_spk), unidade="L",
            formula="RTI = Q × t", base=[p_t], Q_lpm=round(q_sist, 1), t_min=t_min,
            categoria=categoria,
            nota="com mais de uma classificação de risco, vale a vazão e o tempo do maior risco "
                 "(5.4.2)")
    m.usa(params.get("spk.rti_maior_risco"))
    rti_total = rti_spk
    if e.hidrantes_conjugados:
        p_h = params.get("spk.rti_soma_hidrantes")
        rti_total = rti_spk + e.rti_hidrantes_l
        m.passo("RTI total com hidrantes ou mangotinhos", round(rti_total), unidade="L",
                formula="RTI total = RTI dos sprinklers + RTI da NT 2-02", base=[p_h],
                rti_sprinklers_l=round(rti_spk), rti_hidrantes_l=e.rti_hidrantes_l,
                nota="as vazões e pressões da NT 2-02 também precisam ser garantidas (5.4.3)")
        if e.rti_hidrantes_l == 0:
            m.pendencias.append("Hidrantes conjugados sem a RTI informada: use o resultado de "
                                "dimensionar_hidrantes (rti_l) em 'rti_hidrantes_l'.")
    if e.volume_reservatorio_l:
        p_70 = params.get("spk.rti_reservatorio_unico")
        fracao = 100 * rti_total / e.volume_reservatorio_l
        m.usa(p_70)
        if e.reservatorio_unico and fracao > p_70.valor:
            m.pendencias.append(
                f"A RTI ({_milhar(rti_total)} L) é {fracao:.0f} % do reservatório único "
                f"({_milhar(e.volume_reservatorio_l)} L), acima de {p_70.valor} %: apresentar o "
                "cálculo do abastecimento predial diário pelo Código de Obras do município "
                "(5.4.4).")
        elif not e.reservatorio_unico:
            m.pendencias.append("Reservatórios distintos: indicar posição e volume de ambos no "
                                "projeto e, se for o caso, o cálculo do abastecimento predial "
                                "(5.4.5).")
    if pior is not None:
        pb = pior.resumo["pressao_na_base_da_prumada_mca"]
        m.passo("Pressão exigida na base da prumada (zona mais desfavorável)", pb, unidade="mca",
                formula="soma das perdas até a prumada + altura estática + perda da VGA",
                zona=pior.zona.nome, vazao_lpm=pior.resumo["vazao_total_lpm"])
        m.pendencias.append("Bomba de incêndio e conjunto de pressurização: escolher pela curva "
                            "do fabricante no ponto (Q, pressão) acima, somando o desnível da "
                            "água e as perdas da sucção; conjugado com hidrantes, atender aos "
                            "dois sistemas (NT 2-04).")

    # --- tubulação, controle, shaft e recalque ------------------------------------------------
    p_tubos = params.get("spk.tubos_acima_do_solo")
    m.usa(p_tubos)
    if e.tubo == "CPVC" and not (e.classe == "LEVE" and e.resposta == "RAPIDA"):
        m.pendencias.append("CPVC só é aceito no Risco Leve e com bicos exclusivamente de "
                            "resposta rápida (FR): trocar o material ou a resposta (5.3.1).")
    m.passo("Material da tubulação", e.tubo, base=[p_tubos],
            nota="tubos não enterrados: aço, cobre ou CPVC (CPVC só com Risco Leve e bicos FR)")
    p_vga = params.get("spk.vga")
    m.usa(p_vga)
    excecoes = p_vga.valor["controle_secundario_excecoes"]
    grupo = (e.grupo_divisao or "").upper()
    sem_secundario = bool(grupo) and (grupo.split("-")[0] in excecoes or grupo in excecoes)
    if e.pavimentos_protegidos > 1:
        if sem_secundario:
            controle = ("válvula de governo e alarme (VGA) em cada coluna de alimentação; o "
                        f"grupo {grupo} não admite comando secundário por pavimento (5.5.1)")
        else:
            controle = ("VGA por coluna de alimentação; admite-se comando secundário (floor "
                        "control valve) na saída da prumada de cada pavimento, respeitados os "
                        "limites de área da NBR 10897 por coluna (5.5.1)")
    else:
        controle = ("uma válvula de governo e alarme (VGA) na coluna de alimentação (definição "
                    "4.14; obrigatória quando o nível mínimo da RTI fica abaixo do teto mais "
                    "alto, 5.5.5)")
    if e.reservatorio_acima_do_teto is True:
        controle += ("; com o nível mínimo da RTI acima do teto do pavimento mais alto e a área "
                     "dentro do limite da NBR 10897, a VGA pode ser trocada por retenção na "
                     "expedição da bomba e chave de fluxo (5.5.4)")
    elif e.reservatorio_acima_do_teto is False:
        controle += "; reservatório abaixo do teto mais alto: VGA obrigatória (5.5.5)"
    m.passo("Dispositivos de bloqueio, controle e alarme", controle, base=[p_vga])
    m.pendencias.append("Alarme de fluxo: o gongo hidráulico pode ser trocado por alarme elétrico "
                        "supervisionado ligado ao alarme do prédio (5.5.6).")
    if e.prumada_atravessa_pavimentos:
        p_s = params.get("spk.shaft")
        v = p_s.valor
        isento = grupo in ("A-2", "A-5", "A-6") and (e.pavimentos_computaveis or 99) <= 5
        m.passo("Prisma vertical (shaft) das prumadas", "dispensado (5.6.1, isenção das divisões "
                "A-2, A-5 e A-6 com até 5 pavimentos computáveis, na condição do item)" if isento
                else "exigido", base=[p_s],
                largura_min_cm=v["largura_min_cm"], profundidade_min_cm=v["profundidade_min_cm"],
                trrf_min_h=v["trrf_min_h"],
                caixa_de_inspecao_cm=f"{v['porta_min_cm'][0]} x {v['porta_min_cm'][1]}",
                inscricao=v["inscricao"],
                nota="no shaft: tubos de hidrantes e de sprinklers, dreno e eletrodutos; ele "
                     "deve figurar nas plantas arquitetônicas (5.6.5)")
    p_r = params.get("spk.recalque")
    m.passo("Hidrante de recalque dos sprinklers", f"{p_r.valor['saidas']} saídas Storz de "
            f"2½\" ({p_r.valor['storz_mm']} mm), sinalizado \"SPRINKLER\" (Anexo C)", base=[p_r],
            nota="recalque único para hidrantes e sprinklers: \"HIDRANTE/SPRINKLER\"; vários "
                 "sistemas: inscrição adicional (Bloco 1/Bloco 2...)")

    m.resultados.update({
        "classe_de_risco": e.classe, "area_protegida_m2": round(protegida, 2),
        "bicos_minimos_por_area": n_min, "bicos_na_area_de_operacao": n_op,
        "vazao_do_sistema_lpm": round(q_sist, 1), "rti_sprinklers_l": round(rti_spk),
        "rti_total_l": round(rti_total), "duracao_min": t_min,
        "ambientes": linhas,
        "zonas": [r.as_dict() for r in redes],
        "simbolos": ["BICO_SPRINKLER_PENDENTE", "VALVULA_GOVERNO_ALARME_VGA",
                     "REGISTRO_RECALQUE_SPRINKLER"],
        "criterios": {"densidade_mm_min": crit.densidade_mm_min,
                      "area_operacao_m2": crit.area_operacao_m2,
                      "area_max_bico_m2": crit.area_max_bico_m2,
                      "espacamento_max_m": crit.espacamento_max_m, "k": crit.k},
    })
    m.pendencias.append("Obstruções à descarga dos bicos, distância ao teto e ao deflector, "
                        "proteção sob vigas e dutos: ABNT NBR 10897 (NT 2-03, 5.1.2).")
    m.verificar_na_planta += [
        "Cada ambiente que leva bicos tem malha respeitando o espaçamento e a área por bico; "
        "bicos fora dos ambientes dispensados.",
        "VGA, prumada e hidrante de recalque indicados e sinalizados (NT 2-05 E-10; Anexo C da "
        "NT 2-03)."]
    return m
