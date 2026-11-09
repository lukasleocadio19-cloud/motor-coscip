"""Saídas de emergência (NT 2-08): população, unidades de passagem e larguras."""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from coscip_design.memorial import Memorial
from coscip_design.params import ParamError, Parametros


class PavimentoSai(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=60)
    area_m2: float | None = Field(default=None, gt=0,
                                  description="área que abriga a população (ver 5.2.3 e 5.2.4)")
    dormitorios: int | None = Field(default=None, ge=0)
    area_alojamento_m2: float | None = Field(default=None, ge=0)
    leitos: int | None = Field(default=None, ge=0)
    area_ambulatorio_m2: float | None = Field(default=None, ge=0)
    vagas: int | None = Field(default=None, ge=0)
    populacao_informada: int | None = Field(
        default=None, ge=0, description="lotação fixada em projeto (prevalece se for maior)")
    descarga: bool = Field(default=False, description="pavimento de descarga (saída ao exterior)")


class EntradaSaidas(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ocupacao: str = Field(min_length=2, max_length=10, description="divisão, ex. D-2")
    pavimentos: list[PavimentoSai] = Field(min_length=1)
    numero_de_pavimentos: int | None = Field(default=None, ge=1)


def _populacao(row: dict[str, Any], pav: PavimentoSai) -> tuple[float, str, dict[str, Any]]:
    kind = row["por"]

    def need(value: Any, name: str) -> Any:
        if value is None:
            raise ParamError(f"{pav.nome}: informe {name} (população por {kind.replace('_', ' ')})")
        return value

    if kind == "dormitorio":
        d = need(pav.dormitorios, "dormitorios")
        return row["pessoas"] * d, "P = 2 × dormitórios", {"dormitorios": d}
    if kind == "dormitorio_e_alojamento":
        d = need(pav.dormitorios, "dormitorios")
        a = pav.area_alojamento_m2 or 0.0
        return (row["pessoas"] * d + a / row["m2_por_pessoa"],
                "P = 2 × dormitórios + área de alojamento / 4",
                {"dormitorios": d, "area_alojamento_m2": a})
    if kind == "leitos_e_ambulatorio":
        beds = need(pav.leitos, "leitos")
        a = pav.area_ambulatorio_m2 or 0.0
        return (row["pessoas_por_leito"] * beds + a / row["m2_por_pessoa"],
                "P = 1,5 × leitos + área de ambulatório / 7", {"leitos": beds,
                                                               "area_ambulatorio_m2": a})
    if kind == "vagas":
        v = need(pav.vagas, "vagas")
        return v / row["vagas_por_pessoa"], "P = vagas / 40", {"vagas": v}
    a = need(pav.area_m2, "area_m2")
    k = row["m2_por_pessoa"]
    return a / k, f"P = área / {k:g}", {"area_m2": a, "m2_por_pessoa": k}


def dimensionar(params: Parametros, entrada: dict[str, Any]) -> Memorial:
    e = EntradaSaidas.model_validate(entrada)
    div = e.ocupacao.strip().upper()
    grupo = div.split("-")[0]
    m = Memorial("saidas", "Saídas de emergência (NT 2-08)", {"ocupacao": div})
    row = params.populacao_de(div)
    m.citacoes[f"{params.populacao_fonte}, p. {row['pagina']}"] = (
        f"População e capacidade da unidade de passagem — linha '{row['linha'][0]}'")
    c_acesso, c_escada, c_porta = row["c"]
    p_up = params.get("sai.unidade_passagem_m")
    p_formula = params.get("sai.formula")
    p_larg = params.get("sai.largura_minima_m")
    p_porta = params.get("sai.porta_vao_m")
    up = p_up.valor
    larg_min = p_larg.valor.get(div, p_larg.valor["geral"])

    quadro = []
    maior = 0
    for pav in e.pavimentos:
        bruto, formula, valores = _populacao(row, pav)
        pop = math.ceil(bruto - 1e-9)
        if pav.populacao_informada is not None and pav.populacao_informada > pop:
            valores["populacao_informada"] = pav.populacao_informada
            pop = pav.populacao_informada
        m.passo(f"{pav.nome}: população", pop, unidade="pessoas", formula=formula, **valores)
        n_acesso = max(1, math.ceil(pop / c_acesso))
        n_porta = max(1, math.ceil(pop / c_porta))
        largura = max(n_acesso * up, larg_min)
        m.passo(f"{pav.nome}: acessos e descarga", round(largura, 2), unidade="m",
                formula="N = teto(P / C); largura = máx(N × 0,55; largura mínima)",
                base=[p_formula, p_up, p_larg], P=pop, C=c_acesso, N=n_acesso,
                largura_minima_m=larg_min)
        portas = _portas(n_porta, p_porta.valor)
        m.passo(f"{pav.nome}: portas das rotas de saída", portas["descricao"],
                formula="N = teto(P / C); vão conforme N", base=[p_porta], P=pop, C=c_porta,
                N=n_porta)
        quadro.append({"pavimento": pav.nome, "populacao": pop,
                       "unidades_de_passagem_acesso": n_acesso,
                       "largura_minima_acessos_m": round(largura, 2),
                       "unidades_de_passagem_portas": n_porta, "portas": portas["descricao"]})
        if not pav.descarga:
            maior = max(maior, pop)
        if grupo == "F" and pop > params.get("sai.barra_antipanico_pessoas").valor:
            m.usa(params.get("sai.barra_antipanico_pessoas"))
            m.pendencias.append(f"{pav.nome}: lotação acima de 200 pessoas no grupo F → barra "
                                "antipânico nas portas de saída (5.3.4.9).")

    m.resultados["quadro_por_pavimento"] = quadro
    n_pav = e.numero_de_pavimentos or len(e.pavimentos)
    if n_pav > 1:
        base_pop = maior or max(q["populacao"] for q in quadro)
        n_esc = max(1, math.ceil(base_pop / c_escada))
        larg_esc = max(n_esc * up, larg_min)
        m.passo("Escadas e rampas (pelo pavimento de maior população)", round(larg_esc, 2),
                unidade="m", formula="N = teto(P / C); largura = máx(N × 0,55; largura mínima)",
                base=[p_formula, p_up, p_larg], P=base_pop, C=c_escada, N=n_esc,
                nota="capacidade válida para lanços retos e saída descendente; lanços "
                     "ascendentes e rampas têm redução (Anexo A, observação B)")
        m.resultados["escadas"] = {"populacao_de_calculo": base_pop,
                                   "unidades_de_passagem": n_esc,
                                   "largura_minima_m": round(larg_esc, 2)}
        p_two = params.get("sai.duas_escadas_pavimentos")
        if n_pav >= p_two.valor["pavimentos"] and div not in p_two.valor["excecoes"]:
            m.usa(p_two)
            m.resultados["escadas"]["minimo_de_escadas"] = 2
        m.pendencias.append("Tipo de escada (não enclausurada, à prova de fumaça, pressurizada) "
                            "pelo Anexo B da NT 2-08, conforme divisão, nº de pavimentos e altura: "
                            "consultar_norma('NT 2-08', 'Anexo B'). Não calculado aqui.")
    if n_pav <= 2:
        m.pendencias.append("NT 2-08, 5.1 c: edificação de até 2 pavimentos isenta de escada "
                            "enclausurada pode ter largura mínima de 0,80 m (não vale para C-3, "
                            "F-1 a F-7, F-9 a F-11, H-2 e H-3). Aqui foi mantido 1,20 m: conferir "
                            "se a redução se aplica.")
    if grupo == "F":
        m.resultados["minimo_de_saidas"] = m.usa(params.get("sai.grupo_f_saidas"))
    if row.get("consultar_norma_especifica"):
        m.pendencias.append("O Anexo A marca '+' nesta divisão: consultar também a norma "
                            "específica da ocupação.")
    m.premissas.append("Áreas informadas já seguem 5.2.3 e 5.2.4 da NT 2-08 (o que entra e o "
                       "que se exclui da área do pavimento) — responsabilidade de quem informou.")
    m.verificar_na_planta += [
        "Distância máxima a percorrer até a saída (Anexo C da NT 2-08): analisar_planta mede o "
        "percurso; sem leiaute definido vale a distância direta com limite 30 % menor (5.3.3.3).",
        "Largura medida na parte mais estreita; portas abrindo no sentido da saída quando o "
        "ambiente passa de 100 pessoas (5.3.4.1).",
        "Sinalização de saída (NT 2-05) e iluminação de emergência nas rotas (NT 2-06)."]
    return m


def _portas(n: int, vaos: dict[int, float]) -> dict[str, Any]:
    """Vão mínimo para N unidades de passagem; acima de 4, mais de uma porta."""
    if n in vaos:
        folhas = " em duas folhas" if n >= 3 else ""
        return {"descricao": f"1 porta com vão ≥ {vaos[n]:.2f} m{folhas} (N = {n})".replace(
            ".", ",")}
    qtd = math.ceil(n / 4)
    por = math.ceil(n / qtd)
    return {"descricao": (f"{qtd} portas, cada uma com vão ≥ {vaos[por]:.2f} m "
                          f"(N = {n}; {por} unidades por porta)").replace(".", ",")}
