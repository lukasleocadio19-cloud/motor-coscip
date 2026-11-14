import json
import os
from pathlib import Path

from coscip_mcp.workspace import Workspace

DXF = str(Path(__file__).resolve().parents[1] / "saidas" / "restaurante-400m2.dxf")
OUT = Path(__file__).resolve().parents[1] / "saidas"
MEMORIAL = Path(str(Path(__file__).resolve().parents[1] / "saidas" / "restaurante-400m2-memorial.md"))

ws = Workspace()
r = ws.create(DXF, "Restaurante 400 m2 - Projeto de incendio (rascunho)", True)
pid = r["planta_id"]
print("planta", pid, "operacoes", r.get("criada", {}).get("operacoes"))

ws.confirm_unit(pid, [
    {"ponto_a": [0, 0], "ponto_b": [25, 0], "medida_real_m": 25},
    {"ponto_a": [0, 0], "ponto_b": [0, 16], "medida_real_m": 16},
], "Planta sintetica criada pelo motor em metros ($INSUNITS = 6); fachada de 25,00 m e lateral de 16,00 m sao as dimensoes de projeto adotadas por Claude, nao medidas confirmadas pelo usuario.")
ws.define_floors(pid, [{"nome": "TÉRREO", "janela": [-3, -6, 29, 21]}])

ctx = {
    "occupancy": "F-8", "building_area_m2": 400, "building_floors": 1,
    "building_height_m": 4.4, "construction_type": "BETA", "layout_defined": True,
    "multiple_exits": True, "single_occupancy": True, "sprinklers_or_detection": False,
    "requires_hydrants": False, "requires_alarm": False, "requires_lighting": True,
}
res = ws.analyze(pid, ctx, None)
(OUT / "analise3.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
pv = res["pavimentos"][0]
print("area_util", pv["area_util_m2"], "+-", pv["incerteza_area_m2"])
print("simbolos", pv["simbolos"])
for k in ("extinguisher", "exit"):
    m = pv["maior_percurso_m"][k]
    print(k, m["valor"], "+-", m["incerteza"], "ponto", m["ponto"], "nao alcancada", m["area_nao_alcancada_m2"])
print("direta", pv["maior_distancia_direta_saida_m"])
for p in res["pendencias"]:
    print("-", p["tipo"], "|", p["titulo"])
print(res["resumo"])

# memorial
ws.design("saidas", {"ocupacao": "F-8", "numero_de_pavimentos": 1,
                     "pavimentos": [{"nome": "Térreo", "area_m2": 350.48, "descarga": True}]})
ws.design("extintores", {"risco": "MEDIO", "pavimentos": [
    {"nome": "Térreo", "area_m2": 400,
     "instalacoes_especiais": ["Central de GLP", "Quadro geral de energia elétrica"]}]})
ws.design("iluminacao", {"ocupacao": "F-8"})
if MEMORIAL.exists():
    os.remove(MEMORIAL)
ws.save_memorial(str(MEMORIAL), "Restaurante F-8 400 m2 - memorial de calculo (rascunho, projeto ficticio)", {
    "ocupacao": "F-8 (local para refeição) - suposta a partir de 'restaurante'",
    "area_total_construida_m2": 400, "pavimentos": 1,
    "altura_m": "4,40 até o topo da platibanda (premissa); pé-direito 3,60",
    "tipo_de_construcao": "BETA (premissa)",
    "area_para_populacao_m2": "350,48 (400 - sanitarios 49,52; NT 2-08 5.2.4)",
})

extra = """

## Cozinha profissional (NT 3-01) — projeto fictício, premissas do projetista

**Equipamentos de cocção (Tabela 1 da NT 3-01, p. 5, fonte ABNT NBR 14518):** fogão 6 bocas (moderado), chapa de grelhados (severo),
fritadeira (moderado) e forno combinado (moderado), todos a GLP e sob a mesma coifa. Como há equipamento moderado e severo sob o
mesmo captor, o sistema de exaustão é **Tipo I** (5.5.1; observação da Tabela 1: o mais crítico define).
**Edificação de economia única** (uma razão social; 5.6.1).

**Aplicabilidade (2.1 e 2.2, p. 3):** a NT só se aplica quando falta compartimentação, isto é, quando o duto (a) atravessa paredes, pisos
ou tetos e se comunica com outros ambientes ou (b) fica a menos de 1 m de aberturas da fachada. **Premissa do desenho:** um único duto vertical,
aparente, que sobe de dentro da cozinha direto à cobertura, sem passar por forro ou ambiente de outra finalidade, e sai pelo menos 1,0 m acima da laje, longe de
janelas (a janela mais próxima, J1, está a mais de 9 m). Nessa condição a cozinha é compartimentada (4.5) e a NT 3-01 não se aplica. **Isso precisa ser
confirmado pelo responsável técnico com o projeto de exaustão (NBR 14518, fora da base do motor).**

**Se o duto cruzar outro ambiente (Tipo I, economia única, Tabela 2, p. 5):** damper corta-fogo de acionamento eletromecânico (5.9.7 e 5.9.8: fechamento imediato,
estanque, resistência ≥ 60 min), selagem das travessias, proteção passiva do duto, extintor portátil e **dispensa de sistema fixo de extinção**. Em qualquer caso:
rede de dutos aparente, sem forro (5.9.1); aço carbono ≥ 1,37 mm ou inox ≥ 1,09 mm (5.9.3); trecho externo ≥ 1 m de qualquer abertura (5.9.4);
o duto não pode passar em compartimento com medidor ou botijão de gás (5.9.2 — a central de GLP é externa).

**Extintores da cozinha (5.9.9 da NT 3-01 e NT 2-01 6.2):** um de pó ABC junto à porta de acesso ao salão e **um extintor classe K** junto à linha de cocção
(a 4 m do fogão e dentro de 10 m de todos os equipamentos; Tabela 5 da NT 2-01: distância máxima 10 m). O dimensionamento da classe K é **a critério do
profissional autor do projeto** (NT 2-01 6.2.2): capacidade e agente (agente químico úmido) ficam como pendência.

## Central de GLP (NT 3-02, 2ª ed. 2023, alterada em 2025) — projeto fictício

| Item | Adotado | Base |
|---|---|---|
| Recipientes | 4 × P-45, trocáveis, em uma linha | 4.20; 5.3.4 e 5.3.5 |
| Massa / volume total | 180 kg / 0,432 m³ (4 × 0,108 m³) | 4.4; Anexo A, Tabela 2 (até 2,0 m³) |
| Localização | térreo, fora da projeção da edificação, ventilada, junto à fachada norte | 5.2.1 |
| Abrigo | 180 kg > 90 kg: paredes e cobertura com **TRRF ≥ 120 min** | 5.3.2 b |
| Dimensões internas | 2,00 × 1,60 m, altura útil ≥ 1,80 m, piso de concreto ≥ 0,05 m | 5.3.2 c, d |
| Abertura | lado maior (norte) totalmente aberto, com portas incombustíveis para fora; ventilação ≥ 10 % da planta (0,32 m²) | 5.3.2 e, f |
| Afastamento da edificação | 0 m (central ≤ 2,0 m³) | Anexo A, Tabela 2 |
| Aberturas e fontes de ignição | 1,5 m (trocáveis); com abrigo TRRF 120 interposto, pode cair à metade | Anexo A, Tabela 1 e obs. j |
| Ralos e caixas de gordura | ≥ 1,0 m (a caixa de gordura prevista está a mais de 8 m) | 5.2.5 |
| Passeio público | 3 m (ou metade, com abrigo TRRF 120) — **depende da implantação do lote, não definida** | Anexo A, Tabela 2 e obs. d |
| Extintores | capacidade total ≤ 270 kg: 1 × 20-B:C ou 1 × PQS 6 kg, a ≤ 10 m, sinalizado (E-5); previsto a cerca de 2 m | 5.4.1, 5.4.2, Tabela 3 |
| Hidrante da central | não exigido: a edificação não tem sistema de hidrantes | 5.4.3 |
| Resfriamento fixo e SPDA | não exigidos (< 10 m³; SPDA dispensado na central) | 5.4.4; 5.4.8 |
| Placa | PERIGO / GÁS INFLAMÁVEL / PROIBIDO FUMAR, 190 × 95 mm, fotoluminescente; desenhadas as placas P-1, A-2 e A-3 | 5.4.5 |
| Registro geral de corte | junto à central, fora da projeção da edificação | 6.2 |
| Outros materiais na central | proibidos | 5.1.7 |

**Pendências da central de GLP:** documento de responsabilidade técnica da execução da central, do ensaio de estanqueidade e das estruturas com TRRF 120 (5.3.9); ensaio de
estanqueidade da rede interna pela ABNT NBR 15358 e laudo (6.4); nota no Quadro Resumo informando abastecimento por central de GLP e representação em planta, corte e planta de
situação com quantidade, massa e volume dos recipientes e forma de abastecimento — trocável (8.2). A rede interna não é analisada pelo CBMERJ (8.4). Confirmar a distância ao limite do lote e a norma NBR 13523 (fora da base).

## Esquadrias e fachadas

A observação 4 da Tabela 2 do Anexo III refere-se a edificações sem janelas. O projeto prevê J1 e J2 (oeste) e J3 (sul), todas de 1,20 m de altura com peitoril de 0,90 m.
Como o motor não desenha janelas, elas aparecem como texto na planta e em desenho nas fachadas; confirmar a observação 4 com o analista.
"""
with MEMORIAL.open("a", encoding="utf-8") as f:
    f.write(extra)
print("memorial ok", MEMORIAL.stat().st_size)
