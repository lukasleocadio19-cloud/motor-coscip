"""Restaurante de 400 m2 com a D5: cortes A-A e B-B e fachadas sul e norte DERIVADOS da planta
(modelo da edificação) numa terceira prancha A1. Parte de restaurante-400m2-d4.dxf; não altera
os arquivos anteriores. Projeto FICTÍCIO; alturas (pé-direito 3,20 m, laje 0,20 m, platibanda
0,60 m) são premissas do exemplo."""
from pathlib import Path

from coscip_mcp.autoria import Authoring
from coscip_mcp.folhas import Folha

BASE = Path(__file__).resolve().parents[1] / "saidas"
old = Authoring.load(BASE / "restaurante-400m2-d4.dxf")
coifa = next(o for o in old.ops if type(o).__name__ == "Mobiliario" and o.id.upper() == "COIFA")

EDIF = {"tipo": "edificacao", "pe_direito_m": 3.2, "laje_m": 0.2, "platibanda_m": 0.6,
        "volumes": [{"nome": "Duto de exaustão", "retangulo": [coifa.x - 0.3, coifa.y - 0.3,
                                                              coifa.x + 0.3, coifa.y + 0.3],
                     "base_m": 2.6, "topo_m": 5.0}]}
VISTAS = [
    {"tipo": "secao", "nome": "A", "a": [-1.5, 7.6], "b": [29.0, 7.6], "x": 75, "y": 0,
     "marca_na_planta": False},
    {"tipo": "secao", "nome": "B", "a": [9.8, -2.6], "b": [9.8, 20.0], "sentido": "direita",
     "x": 75, "y": 10, "marca_na_planta": False},
    {"tipo": "fachada", "lado": "sul", "x": 75, "y": 20},
    {"tipo": "fachada", "lado": "norte", "x": 75, "y": 30},
]
folha1 = next(op for op in old.ops if isinstance(op, Folha))
folha3 = {"tipo": "folha", "nome": "PRANCHA 03", "formato": "A1", "prancha": "3/3",
          "titulo": "CORTES E FACHADAS", "quadro_de_areas": False,
          "selo": folha1.model_dump(exclude_none=True)["selo"],
          "vistas": [{"titulo": "Cortes e fachadas", "janela": [72, -4, 104, 38], "escala": 100}],
          "notas": ["Cortes e fachadas gerados da mesma geometria da planta; alturas e "
                    "peitoris são premissas do exemplo (projeto fictício).",
                    "Sem remoção de linhas ocultas."]}
ops = [op.model_dump(exclude_none=True) for op in old.ops]
for o in ops:
    if o["tipo"] == "folha" and o["nome"] == "PRANCHA 01":
        o["prancha"] = "1/3"
    if o["tipo"] == "folha" and o["nome"] == "PRANCHA 02":
        o["prancha"] = "2/3"
novo = Authoring(BASE / "restaurante-400m2-d5.dxf", [], old.title, escala=100)
novo.add([EDIF, *ops, *VISTAS, folha3])
r = novo.build()
print({k: r[k] for k in ("vistas",)})
from coscip_mcp.folhas import exportar_pdf  # noqa: E402
print(exportar_pdf(BASE / "restaurante-400m2-d5.dxf", BASE / "restaurante-400m2-d5.pdf", None))
