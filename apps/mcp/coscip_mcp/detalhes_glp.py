"""Detalhes de GLP (frente G3, 13/11/2026): central de recipientes transportáveis, regulador
de 1º estágio (prumada da rede) e regulador de 2º estágio.

As medidas e exigências vêm de parâmetros ``det.glp.*`` com citação conferida na NT 3-02
(5.2.1, 5.2.5, 5.3.2, 5.3.4, 5.3.5, 5.4.2, 5.4.5, Tabelas 1 e 3, 6.1, 6.2). Diâmetros das
conexões e o tipo dos reguladores são do projeto da rede (NBR 15526 / 15358, que a NT 3-02
adota em 6.1) e entram como dado informado; sem eles, as chamadas dizem "conforme projeto".
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from coscip_mcp import apresentacao
from coscip_mcp import equipamentos as eq
from coscip_mcp import equipamentos_glp as gq

if TYPE_CHECKING:
    from coscip_mcp.detalhes import _D, Detalhe


def _api():  # noqa: ANN202
    from coscip_mcp import detalhes

    return detalhes


def _bitola(s: str) -> str:
    return f" {s}" if s else ""


# --- central de GLP --------------------------------------------------------------------------


def central(d: _D, op: Detalhe) -> dict[str, Any]:
    api = _api()
    _p, _ref, _m, Err = api._p, api._ref, api._m, api.DetalheError  # noqa: N806
    tipo = op.recipiente
    if tipo not in gq.RECIPIENTES:
        raise Err(f"central de GLP: recipiente {tipo!r} fora de {sorted(gq.RECIPIENTES)}")
    if not op.recipientes:
        raise Err("central de GLP: informe recipientes (quantidade de recipientes na central)")
    D, H, kg = gq.RECIPIENTES[tipo]
    n = op.recipientes
    total = kg * n
    ab, vent = _p("det.glp.abrigo"), _p("det.glp.abrigo_ventilacao")
    lin = _p("det.glp.linha_unica") if kg > 45 else _p("det.glp.duas_linhas")
    placa, local, ralos = _p("det.glp.placa"), _p("det.glp.local"), _p("det.glp.ralos_m")
    dist, cor = _p("det.glp.extintor_distancia_m"), _p("det.glp.cor_tubo")
    ext = _p("det.glp.extintores_ate_270" if total <= 270 else
             "det.glp.extintores_ate_1800" if total <= 1800 else "det.glp.extintores_acima_1800")
    linhas_rec = 1 if kg > 45 or n <= 4 else 2
    por_linha = math.ceil(n / linhas_rec)
    passo = D + 0.10
    larg_min = por_linha * passo + 0.20
    prof_min = linhas_rec * passo + 0.20
    if op.abrigo_m is not None:
        larg, prof = op.abrigo_m
        if larg + 1e-6 < larg_min or prof + 1e-6 < prof_min:
            raise Err(f"central de GLP: {n} x {tipo} pedem abrigo interno de pelo menos "
                      f"{_m(larg_min)} x {_m(prof_min)} m na disposição da NT 3-02")
    else:
        larg, prof = larg_min, prof_min
    hu = max(float(ab.valor["altura_util_m"]), H + 0.45)
    e = 0.15  # parede
    teto = 0.10
    piso = float(ab.valor["piso_m"])
    area = larg * prof
    vent_min = max(float(vent.valor["fracao_planta"]) * area,
                   float(vent.valor["inferior_m2"]) + float(vent.valor["superior_m2"]))
    trrf = total > float(ab.valor["limite_alvenaria_kg"])
    k = d.k
    dn = 0.027  # tubulação de 3/4" (representação)
    # --- corte (vista frontal pelo lado aberto) ----------------------------------------------
    eq.laje_concreto(d, 0, larg + 2 * e, hu, hu + teto)
    eq.laje_concreto(d, 0, e, 0, hu)
    eq.laje_concreto(d, larg + e, larg + 2 * e, 0, hu)
    eq.laje_concreto(d, -0.10, larg + 2 * e + 0.10, -piso, 0)
    d.piso(-0.40, larg + 2 * e + 0.90, -piso)
    zcol = min(hu - 0.15, H + 0.30)
    u_ini = e + 0.12
    valvulas = []
    for i in range(por_linha):
        uc = e + 0.10 + passo * i + passo / 2
        c = gq.cilindro(d, uc, 0.0, tipo)
        valvulas.append(c["valvula"])
    u_fim = larg + e + 0.02
    d.tubo([(u_ini, zcol), (u_fim, zcol)], dn, gq.CAM)  # coletor
    tp = gq.tampao(d, u_ini, zcol, dn)
    for vv in valvulas:
        gq.pigtail(d, vv, (vv[0] + passo * 0.25, zcol - dn / 2))
    vr = gq.valvula_retencao(d, u_fim - 0.08, zcol)
    d.tubo([(u_fim, zcol), (larg + 2 * e + 0.18, zcol), (larg + 2 * e + 0.18, -0.35)], dn,
           gq.CAM)  # saída pela parede, para o consumo
    d.texto("PARA O CONSUMO", larg + 2 * e + 0.24, -0.25, 1.8)
    d.cota_v_pts((larg + 2 * e + 0.62, 0.0), (larg + e, hu), 0.62 + e)
    d.chamada_s((larg / 2 + e, hu + teto * 0.5), larg + 2 * e + 0.30, hu + teto + 0.18,
                [("COBERTURA COM TRRF 120 min" if trrf else "COBERTURA EM CONCRETO")])
    d.balao((u_ini + 0.20, zcol + dn / 2), u_ini + 0.20, hu - 0.07, 3)
    v2 = valvulas[1] if len(valvulas) > 1 else valvulas[0]
    d.balao((v2[0] + 0.02, v2[1] + 0.08), v2[0] + passo * 0.5, hu - 0.07, 2)
    d.balao(vr, u_fim - 0.08, hu - 0.07, 4)
    d.balao(tp, e + 0.04, zcol - 0.20, 5)
    ult = valvulas[-1][0] + D / 2
    d.balao((ult, 0.45 * H), larg + 2 * e + 0.36, 0.45 * H, 1)
    d.subtitulo("CORTE", e, -0.30)
    # --- planta ------------------------------------------------------------------------------
    p0 = larg + 2 * e + 1.90
    v0 = 0.0  # v (profundidade) cresce para cima no desenho da planta
    eq.concreto(d, p0, p0 + larg + 2 * e, v0 + prof, v0 + prof + e)  # fundo
    eq.concreto(d, p0, p0 + e, v0, v0 + prof)
    eq.concreto(d, p0 + larg + e, p0 + larg + 2 * e, v0, v0 + prof)
    for j in range(linhas_rec):
        for i in range(por_linha):
            if j * por_linha + i >= n:
                break
            gq.cilindro_planta(d, p0 + e + 0.10 + passo * i + passo / 2,
                               v0 + prof - 0.10 - passo * j - passo / 2, tipo)
    # portas de abrir para fora (duas folhas, com veneziana)
    fl = larg / 2
    for s, base in ((1, p0 + e), (-1, p0 + e + larg)):
        d.linha(base, v0, base + s * 0.0, v0 - fl, "DETALHE")
        pts = [(base + s * fl * math.cos(math.radians(a)), v0 - fl * math.sin(math.radians(a)))
               for a in range(0, 91, 10)]
        d.poli(pts, "DETALHE_AUX", tracejado=True)
    d.linha(p0 + e, v0, p0 + e + larg, v0, "DETALHE_AUX", tracejado=True)
    d.cota_h(p0 + e, p0 + e + larg, v0 + prof + e, 0.15)
    d.cota_v_pts((p0 + larg + 2 * e, v0), (p0 + larg + 2 * e, v0 + prof), 0.18)
    d.balao((p0 + e + larg * 0.25, v0 - fl * 0.7), p0 - 0.25, v0 - fl * 0.5, 6)
    d.subtitulo("PLANTA", p0 + e, v0 - fl - 0.30)
    # --- placa da central (ampliada) ----------------------------------------------------------
    pv = placa.valor
    w_p, h_p = pv["largura_mm"] / 1000, pv["altura_mm"] / 1000
    f = 5.0  # ampliação para leitura
    u_pl = p0 + larg + 2 * e + 0.80
    z_pl = hu - h_p * f
    d.texto(f"PLACA DA CENTRAL (AMPLIADA {round(f)}x)", u_pl, hu + 0.36, 2.0)
    W, Hh = w_p * f, h_p * f
    d.caixa(u_pl, z_pl, u_pl + W, z_pl + Hh, "DETALHE_TEXTO")
    d.caixa(u_pl + 0.03, z_pl + 0.03, u_pl + W - 0.03, z_pl + Hh - 0.03, "DETALHE_TEXTO")
    faixa = z_pl + Hh * 0.62
    d.caixa(u_pl + 0.12, faixa + 0.02, u_pl + W - 0.12, z_pl + Hh - 0.06, "DETALHE_INC",
            solido=1)
    hl = apresentacao.altura_texto(d.esc)
    mm_titulo = (z_pl + Hh - 0.06 - faixa - 0.02) * 0.62 / hl * apresentacao.TEXTO_MM
    d.texto(pv["dizeres"][0], u_pl + W / 2, (faixa + 0.02 + z_pl + Hh - 0.06) / 2, mm_titulo,
            alinhar="centro", cor=7)
    # dizeres à esquerda, pictograma de proibido fumar (P-1) à direita, sem se tocarem
    lp = (faixa - z_pl) * 0.80
    larg_txt = W * 0.62
    alt_txt = min((faixa - z_pl) * 0.24,
                  larg_txt / max(d.largura_texto(s, 1.0) for s in pv["dizeres"][1:]))
    mm_corpo = alt_txt / hl * apresentacao.TEXTO_MM
    d.texto(pv["dizeres"][1], u_pl + W * 0.05, faixa - (faixa - z_pl) * 0.30, mm_corpo)
    d.texto(pv["dizeres"][2], u_pl + W * 0.05, faixa - (faixa - z_pl) * 0.68, mm_corpo)
    eq.placa_nt(d, "P-1", u_pl + W - 0.06 - lp / 2, z_pl + 0.07, lp, "DETALHE_INC")
    d.cota_h(u_pl, u_pl + W, z_pl + Hh, 0.12)
    d.cota_v(u_pl + W, z_pl, z_pl + Hh, 0.12)
    d.texto(f"MEDIDAS MÍNIMAS {pv['largura_mm']} x {pv['altura_mm']} mm; COTAS NA AMPLIAÇÃO",
            u_pl, z_pl - 0.14, 1.8)
    itens = [(1, f"{n} RECIPIENTE(S) {tipo} ({total} kg), "
                 f"{'LINHA ÚNICA' if linhas_rec == 1 else 'ATÉ DUAS LINHAS'}"),
             (2, "PIGTAIL (MANGUEIRA DE ALTA PRESSÃO) POR RECIPIENTE"),
             (3, f"COLETOR — TUBULAÇÃO APARENTE NA COR {cor.valor['vapor']} (FASE VAPOR)"),
             (4, "VÁLVULA DE RETENÇÃO NA SAÍDA DO COLETOR"),
             (5, "TAMPÃO NA EXTREMIDADE DO COLETOR"),
             (6, "PORTAS INCOMBUSTÍVEIS ABRINDO PARA FORA, COM VENEZIANA EM TODA A EXTENSÃO")]
    d.tabela_itens(u_pl, z_pl - 0.32, itens)
    exig = ext.valor
    ext_txt = f"{exig['portateis']} EXTINTOR(ES) 20-B:C OU PQS 6 kg" + (
        f" E {exig['sobre_rodas']} SOBRE RODAS 80-B:C OU PQS 50 kg" if exig["sobre_rodas"]
        else "")
    linhas = [
        f"CENTRAL NO TÉRREO, FORA DA PROJEÇÃO DA EDIFICAÇÃO, EM LOCAL VENTILADO ({_ref(local)}); "
        f"RECIPIENTES A NO MÍNIMO {_m(float(ralos.valor))} m DE RALOS, CANALETAS E CAIXAS "
        f"({_ref(ralos)}).",
        (f"CAPACIDADE {total} kg (> {ab.valor['limite_alvenaria_kg']} kg): PAREDES E COBERTURA "
         f"COM TRRF DE NO MÍNIMO {ab.valor['trrf_min']} min" if trrf else
         f"CAPACIDADE {total} kg (ATÉ {ab.valor['limite_alvenaria_kg']} kg): PAREDES E "
         "COBERTURA EM ALVENARIA OU CONCRETO")
        + f"; PISO EM CONCRETO COM NO MÍNIMO {_m(piso)} m; ALTURA INTERNA ÚTIL MÍNIMA "
        f"{_m(float(ab.valor['altura_util_m']))} m ({_ref(ab)}).",
        f"LADO MAIOR ABERTO COM PORTAS INCOMBUSTÍVEIS ABRINDO PARA FORA; VENTILAÇÃO PERMANENTE "
        f"DE NO MÍNIMO {_m(vent_min)} m² (MAIOR ENTRE 10% DA PLANTA E 0,32 + 0,32 m²) "
        f"({_ref(vent)}).",
        f"RECIPIENTES LADO A LADO, {'EM LINHA ÚNICA' if kg > 45 else 'EM ATÉ DUAS LINHAS'} "
        f"({_ref(lin)}).",
        f"PLACA COM NO MÍNIMO {pv['largura_mm']} x {pv['altura_mm']} mm, LETRA DE NO MÍNIMO "
        f"{pv['letra_mm']} mm, PERIGO / GÁS INFLAMÁVEL / PROIBIDO FUMAR, FOTOLUMINESCENTE, "
        f"VISÍVEL DE QUALQUER ACESSO ({_ref(placa)}).",
        f"PROTEÇÃO: {ext_txt}, A NO MÁXIMO {dist.valor} m DA CENTRAL ({_ref(ext)}; {_ref(dist)}).",
        f"TUBULAÇÃO APARENTE DE GLP: FASE VAPOR {cor.valor['vapor']}, FASE LÍQUIDA "
        f"{cor.valor['liquida']} ({_ref(cor)}).",
        f"RECIPIENTES REPRESENTADOS COM Ø {_m(D)} x {_m(H)} m (TAMANHO APROXIMADO); "
        "VÁLVULA DE RETENÇÃO E PIGTAILS CONFORME O PROJETO DA CENTRAL.",
    ]
    medidas = [{"valor": f"{_m(float(ab.valor['altura_util_m']))} m; piso {_m(piso)} m",
                "o_que": ab.titulo, "fonte": ab.citacao},
               {"valor": f"{_m(vent_min)} m²", "o_que": vent.titulo, "fonte": vent.citacao},
               {"valor": f"{pv['largura_mm']} x {pv['altura_mm']} mm", "o_que": placa.titulo,
                "fonte": placa.citacao},
               {"valor": ext_txt, "o_que": ext.titulo, "fonte": ext.citacao}]
    informado = [f"{n} x {tipo} ({total} kg)",
                 f"abrigo interno {_m(larg)} x {_m(prof)} m"
                 + ("" if op.abrigo_m else " (mínimo para a disposição)")]
    return {"linhas": linhas, "medidas": medidas, "informado": informado,
            "altura": hu + teto + 0.45 + 0 * k}


# --- regulador de 1º estágio (prumada) --------------------------------------------------------


def regulador_1(d: _D, op: Detalhe) -> dict[str, Any]:
    api = _api()
    _p, _ref = api._p, api._ref  # noqa: N806
    reg, nbr, cor = _p("det.glp.registro_geral"), _p("det.glp.rede_nbr"), _p("det.glp.cor_tubo")
    br, bg = _bitola(op.bitola_rede), _bitola(op.bitola_regulador)
    u = 1.20
    D1, D2 = 0.027, 0.021  # representação: rede maior que o regulador
    z = 2.30
    pecas: list[tuple[str, tuple[float, float], str]] = []  # (texto, alvo, lado)

    def desce(dz: float) -> tuple[float, float]:
        nonlocal z
        z0, z1 = z - dz, z
        z = z0
        return z0, z1

    d.tubo([(u, z + 0.25), (u, z)], D1, gq.CAM)
    z0, z1 = desce(0.16)
    pecas.append((f"REGISTRO GERAL DE CORTE{br}", gq.registro_esfera(d, u, z0, z1, D1), "dir"))
    d.tubo([(u, z), (u, z - 0.22)], D1, gq.CAM)
    z -= 0.22
    z0, z1 = desce(0.04)
    gq.niple(d, u, z0, z1, D1)
    pecas.append((f"NIPLE{br}", (u - D1 / 2, (z0 + z1) / 2), "esq"))
    z0, z1 = desce(0.16)
    der = gq.te(d, u, z0, z1, D1)
    pecas.append((f"TÊ DE REDUÇÃO{br}", (u - D1 / 2 - 0.015, (z0 + z1) / 2), "esq"))
    d.caixa(der[0], der[1] - 0.012, der[0] + 0.04, der[1] + 0.012, gq.CAM)
    gq.manometro(d, der[0] + 0.085, der[1], 0.045)
    pecas.append(("MANÔMETRO", (der[0] + 0.13, der[1]), "dir"))
    z0, z1 = desce(0.04)
    gq.niple(d, u, z0, z1, D1)
    z0, z1 = desce(0.15)
    pecas.append((f"VÁLVULA DE ESPERA{br}", gq.registro_esfera(d, u, z0, z1, D1), "dir"))
    z0, z1 = desce(0.04)
    gq.niple(d, u, z0, z1, D1)
    z -= 0.03
    pecas.append((f"UNIÃO{br}", gq.uniao(d, u, z, D1), "dir"))
    z -= 0.03
    z0, z1 = desce(0.06)
    pecas.append((f"LUVA DE REDUÇÃO{br}{' X' + bg if bg else ''}",
                  gq.luva_reducao(d, u, z0, z1, D2, D1), "dir"))
    z0, z1 = desce(0.04)
    gq.niple(d, u, z0, z1, D2)
    z -= 0.06
    r1 = gq.regulador_1(d, u, z)
    pecas.append(("REGULADOR DE 1º ESTÁGIO COM MANÔMETRO", r1["corpo"], "esq"))
    z -= 0.06
    z0, z1 = desce(0.04)
    gq.niple(d, u, z0, z1, D2)
    z0, z1 = desce(0.06)
    gq.luva_reducao(d, u, z0, z1, D1, D2)
    z0, z1 = desce(0.04)
    gq.niple(d, u, z0, z1, D1)
    z0, z1 = desce(0.15)
    pecas.append((f"VÁLVULA DE ESPERA{br}", gq.registro_esfera(d, u, z0, z1, D1), "dir"))
    z0, z1 = desce(0.04)
    gq.niple(d, u, z0, z1, D1)
    z -= 0.03
    gq.uniao(d, u, z, D1)
    z -= 0.03
    d.tubo([(u, z), (u, z - 0.25)], D1, gq.CAM)
    z_base = z - 0.25
    # cantoneiras do nicho/abrigo de manobra (tracejado), como na referência
    x0, x1, y0, y1 = u - 0.75, u + 0.75, z_base, 2.55 + 0.25
    for cx, cy, sx, sy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.poli([(cx + sx * 0.18, cy), (cx, cy), (cx, cy + sy * 0.18)], "DETALHE_AUX")
    # chamadas: à esquerda e à direita, na altura de cada peça
    for texto, alvo, lado in pecas:
        if lado == "dir":
            d.chamada_s(alvo, u + 0.30, alvo[1], [texto])
        else:
            w = d.largura_texto(texto, d.hp) + 1.0 * d.k
            d.linha(alvo[0], alvo[1], u - 0.30, alvo[1], "DETALHE_AUX")
            d.linha(u - 0.30 - w, alvo[1], u - 0.30, alvo[1], "DETALHE_AUX")
            d.texto(texto, u - 0.30 - w + 0.5 * d.k, alvo[1] + 0.9 * d.hp,
                    apresentacao.TEXTO_PEQUENO_MM)
    d.subtitulo("REGULADOR DE 1º ESTÁGIO", u - 0.45, z_base - 0.20)
    linhas = [
        f"REGISTRO GERAL DE CORTE O MAIS PRÓXIMO POSSÍVEL DO LIMITE DA PROPRIEDADE, EM ÁREA COMUM "
        f"E FORA DA PROJEÇÃO DA EDIFICAÇÃO ({_ref(reg)}).",
        f"REDE DE DISTRIBUIÇÃO INTERNA CONFORME A {nbr.valor['residencial']} (RESIDENCIAL) OU A "
        f"{nbr.valor['nao_residencial']} (NÃO RESIDENCIAL) ({_ref(nbr)}).",
        f"TUBULAÇÃO APARENTE NA COR {cor.valor['vapor']} (FASE VAPOR) ({_ref(cor)}).",
        "DIÂMETROS, CLASSE DAS CONEXÕES E PRESSÕES CONFORME O PROJETO DA REDE"
        + ("" if br else " (NÃO INFORMADOS)") + ".",
    ]
    medidas = [{"valor": "registro geral de corte", "o_que": reg.titulo, "fonte": reg.citacao}]
    informado = ([f"bitola da rede{br}"] if br else []) + \
        ([f"bitola do regulador{bg}"] if bg else [])
    return {"linhas": linhas, "medidas": medidas, "informado": informado, "altura": 2.80}


# --- regulador de 2º estágio ------------------------------------------------------------------


def regulador_2(d: _D, op: Detalhe) -> dict[str, Any]:
    api = _api()
    _p, _ref = api._p, api._ref  # noqa: N806
    nbr, cor = _p("det.glp.rede_nbr"), _p("det.glp.cor_tubo")
    bg = _bitola(op.bitola_regulador)
    # caixa na parede
    u0, z0, w, h = 0.30, 0.30, 0.62, 0.92
    d.caixa(u0, z0, u0 + w, z0 + h, "DETALHE")
    d.caixa(u0 + 0.03, z0 + 0.03, u0 + w - 0.03, z0 + h - 0.03, "DETALHE")
    uc = u0 + w * 0.45
    zr = z0 + 0.36
    r2 = gq.regulador_2(d, uc, zr)
    # mangueira flexível em laço até o ponto de consumo
    s = r2["saida"]
    pts = [s, (s[0], s[1] + 0.08)]
    pts += eq._arco(s[0] - 0.12, s[1] + 0.22, 0.12, 0.14, -60, 230, 18)  # noqa: SLF001
    pts += [(s[0] - 0.12, s[1] + 0.08), (u0 + w - 0.06, s[1] + 0.08)]
    d.tubo(pts, 0.016, gq.CAM)
    d.caixa(u0 + w - 0.06, s[1] + 0.06, u0 + w - 0.04, s[1] + 0.10, gq.CAM)
    # conexões de entrada, por baixo
    zb = r2["baixo"][1]
    gq.niple(d, uc, zb - 0.04, zb, 0.016)
    gq.luva_reducao(d, uc, zb - 0.07, zb - 0.04, 0.021, 0.016)
    gq.niple(d, uc, zb - 0.11, zb - 0.07, 0.021)
    d.caixa(uc - 0.014, zb - 0.15, uc + 0.014, zb - 0.11, gq.CAM)  # joelho
    d.circulo(uc, zb - 0.15, 0.014, gq.CAM)
    ut = u0 + w + 0.25
    d.chamada_s((s[0] - 0.22, s[1] + 0.26), ut, s[1] + 0.32, ["MANGUEIRA FLEXÍVEL"])
    d.chamada_s(r2["registro"], ut, r2["registro"][1] + 0.05, ["REGISTRO DO REGULADOR"])
    d.chamada_s(r2["corpo"], ut, zr - 0.08, ["REGULADOR DE 2º ESTÁGIO", "COM REGISTRO"])
    d.chamada_s((uc + 0.008, zb - 0.02), ut, zb - 0.10, [f"NIPLE{bg}"])
    d.chamada_s((uc + 0.012, zb - 0.055), ut, zb - 0.20, [f"LUVA DE REDUÇÃO{bg}"])
    d.chamada_s((uc + 0.014, zb - 0.13), ut, zb - 0.30, ["JOELHO"])
    d.subtitulo("REGULADOR DE 2º ESTÁGIO", u0, -0.10)
    d.texto("INSTALADO NA PAREDE, JUNTO AO PONTO DE CONSUMO", u0, -0.20, 1.8)
    linhas = [
        f"REDE DE DISTRIBUIÇÃO INTERNA CONFORME A {nbr.valor['residencial']} (RESIDENCIAL) OU A "
        f"{nbr.valor['nao_residencial']} (NÃO RESIDENCIAL) ({_ref(nbr)}).",
        f"TUBULAÇÃO APARENTE NA COR {cor.valor['vapor']} (FASE VAPOR) ({_ref(cor)}).",
        "REGULADOR, MANGUEIRA E CONEXÕES CONFORME O PROJETO DA REDE E O FABRICANTE"
        + ("" if bg else " (DIÂMETROS NÃO INFORMADOS)") + ".",
    ]
    medidas = [{"valor": nbr.valor["nao_residencial"], "o_que": nbr.titulo,
                "fonte": nbr.citacao}]
    informado = [f"bitola do regulador{bg}"] if bg else []
    return {"linhas": linhas, "medidas": medidas, "informado": informado, "altura": 1.45}


__all__ = ["central", "regulador_1", "regulador_2"]
