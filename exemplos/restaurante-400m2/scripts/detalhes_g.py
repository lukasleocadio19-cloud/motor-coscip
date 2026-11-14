"""Frente G (13/11/2026): detalhes de instalação das medidas de segurança.

1. restaurante-400m2-g.*: o restaurante F-8 fictício (parte do -f) ganha a PRANCHA 05 com os
   detalhes que se aplicam a ele: extintor, bloco autônomo e sinalização de saída.
2. detalhes-exemplo.*: uma prancha A0 com os seis modelos (inclusive abrigo de mangueiras e
   hidrantes de recalque, que o restaurante não tem), para conferência visual.

Projeto FICTÍCIO: alturas de bloco e abrigo, risco e vazão dos hidrantes são premissas do
exemplo; as medidas das NTs saem do parametros.yaml do motor com a citação conferida."""
from pathlib import Path

from coscip_mcp.autoria import Authoring
from coscip_mcp.folhas import exportar_pdf

BASE = Path(__file__).resolve().parents[1] / "saidas"


def vistas_dos(r, nomes):
    out = []
    for d in r["detalhes"]:
        if d["modelo"] in nomes:
            x0, y0, x1, y1 = d["regiao_m"]
            out.append({"titulo": nomes[d["modelo"]], "janela": [x0 - 0.2, y0 - 0.2, x1 + 0.2,
                                                                 y1 + 0.2],
                        "escala": int(d["escala"].split(":")[1])})
    return out


# --- 1. restaurante ------------------------------------------------------------------------
old = Authoring.load(BASE / "restaurante-400m2-f.dxf")
ops = [op.model_dump(exclude_none=True) for op in old.ops]
selo = next(o for o in ops if o["tipo"] == "folha")["selo"]
for o in ops:
    if o["tipo"] == "folha":
        n = o["prancha"].split("/")[0]
        o["prancha"] = f"{n}/6"
DET = [
    {"tipo": "detalhe", "modelo": "extintor", "x": 200, "y": 0, "placa_mm": "200x200"},
    {"tipo": "detalhe", "modelo": "bloco_autonomo", "x": 200, "y": 7, "altura_m": 2.2,
     "pe_direito_m": 3.2, "fluxo_lm": 300, "divisao": "F-8"},
    {"tipo": "detalhe", "modelo": "sinalizacao_saida", "x": 200, "y": 15, "placa_mm": "252x126"},
    # GLP: a central do exemplo é de 4 x P-45 (premissa do exercício de 09/11/2026)
    {"tipo": "detalhe", "modelo": "central_glp", "x": 230, "y": 0, "recipiente": "P-45",
     "recipientes": 4},
    {"tipo": "detalhe", "modelo": "regulador_1_estagio", "x": 230, "y": 8,
     "bitola_rede": '3/4"', "bitola_regulador": '1/2"'},
    {"tipo": "detalhe", "modelo": "regulador_2_estagio", "x": 236, "y": 8,
     "bitola_regulador": '1/2"'},
]
novo = Authoring(BASE / "restaurante-400m2-g.dxf", [], old.title, escala=100)
novo.add([*ops, *DET])
r = novo.build()
NOMES = {"extintor": "Detalhe 1 - extintor", "bloco_autonomo": "Detalhe 2 - bloco autônomo",
         "sinalizacao_saida": "Detalhe 3 - sinalização"}
GLP = {"central_glp": "Detalhe 4 - central de GLP",
       "regulador_1_estagio": "Detalhe 5 - regulador de 1º estágio",
       "regulador_2_estagio": "Detalhe 6 - regulador de 2º estágio"}
FOLHA6 = {"tipo": "folha", "nome": "PRANCHA 06", "formato": "A0", "prancha": "6/6",
          "titulo": "DETALHES DE GLP", "quadro_de_areas": False, "selo": selo,
          "vistas": [], "notas": ["Central de 4 x P-45 (premissa do exemplo); diâmetros da "
                                   "rede são premissas (projeto fictício)."]}
FOLHA5 = {"tipo": "folha", "nome": "PRANCHA 05", "formato": "A0", "prancha": "5/6",
          "titulo": "DETALHES DE INSTALAÇÃO", "quadro_de_areas": False, "selo": selo,
          "vistas": vistas_dos(r, NOMES),
          "notas": ["Detalhes cotados com as medidas das NTs citadas em cada nota; alturas do "
                    "bloco autônomo e pé-direito são premissas do exemplo (projeto fictício)."]}
FOLHA6["vistas"] = vistas_dos(r, GLP)
novo.add([FOLHA5, FOLHA6])
r = novo.build()
print([(d["modelo"], d["regiao_m"]) for d in r["detalhes"]])
print(r["folhas"][-1]["vistas"])
print(exportar_pdf(BASE / "restaurante-400m2-g.dxf", BASE / "restaurante-400m2-g.pdf", None))

# --- 2. prancha de exemplo com os seis modelos ---------------------------------------------
TODOS = [
    {"tipo": "sala", "nome": "Área de exemplo", "retangulo": [0, 0, 4, 3]},
    {"tipo": "detalhe", "modelo": "extintor", "x": 0, "y": 10, "piso_demarcado": True},
    {"tipo": "detalhe", "modelo": "abrigo_mangueira", "x": 0, "y": 18, "risco": "MEDIO_2",
     "base_m": 0.9},
    {"tipo": "detalhe", "modelo": "recalque_passeio", "x": 0, "y": 26, "risco": "MEDIO_2",
     "vazao_lpm": 400},
    {"tipo": "detalhe", "modelo": "recalque_fachada", "x": 14, "y": 10, "risco": "MEDIO_2",
     "altura_m": 1.1, "vazao_lpm": 400},
    {"tipo": "detalhe", "modelo": "bloco_autonomo", "x": 14, "y": 18, "altura_m": 2.2,
     "pe_direito_m": 3.0, "fluxo_lm": 300, "divisao": "H-2"},
    {"tipo": "detalhe", "modelo": "sinalizacao_saida", "x": 14, "y": 26},
]
ex = Authoring(BASE / "detalhes-exemplo.dxf", [], "detalhes de exemplo", escala=100)
ex.add(TODOS)
r2 = ex.build()
N2 = {"extintor": "Extintor", "abrigo_mangueira": "Abrigo de mangueiras",
      "recalque_passeio": "Recalque no passeio", "recalque_fachada": "Recalque na fachada",
      "bloco_autonomo": "Bloco autônomo", "sinalizacao_saida": "Sinalização"}
ex.add([{"tipo": "folha", "nome": "DETALHES", "formato": "A0", "prancha": "1/1",
         "titulo": "DETALHES DE INSTALAÇÃO - EXEMPLO", "quadro_de_areas": False,
         "selo": {"obra": "Exemplo fictício", "proprietario": "Fictício",
                  "autor_projeto": "Motor COSCIP", "data": "13/11/2026"},
         "vistas": vistas_dos(r2, N2),
         "notas": ["Exemplo fictício: risco, vazão e alturas informadas são premissas."]}])
r2 = ex.build()
print(r2["folhas"][-1]["vistas"])
print(exportar_pdf(BASE / "detalhes-exemplo.dxf", BASE / "detalhes-exemplo.pdf", None))
