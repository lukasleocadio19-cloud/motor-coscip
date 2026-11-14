"""Restaurante de 400 m2 com a frente F (13/11/2026), elementos tirados dos projetos de
referência da pasta restaurante-scripts: telhado em duas águas nos cortes e fachadas (chamada
da telha e do forro), figura humana de escala, rótulos PAREDE/PISO CLASSE (NT 2-20), traços de
vidro e letreiro na fachada, quadro de cálculo das saídas na prancha, títulos de vista com
círculo numerado e uma PRANCHA 04 com a planta de situação (lote, ruas, esquina, norte).

Parte de restaurante-400m2-d5.dxf; não altera os arquivos anteriores. Projeto FICTÍCIO: lote,
ruas, inclinação, telha, classes dos materiais e letreiro são premissas do exemplo."""
from pathlib import Path

from coscip_mcp.autoria import Authoring
from coscip_mcp.folhas import exportar_pdf

BASE = Path(__file__).resolve().parents[1] / "saidas"
old = Authoring.load(BASE / "restaurante-400m2-d5.dxf")
ops = [op.model_dump(exclude_none=True) for op in old.ops]

for o in ops:
    if o["tipo"] == "edificacao":
        o["platibanda_m"] = 0.0
        o["forro"] = "FORRO DE GESSO"
        o["cobertura"] = {"tipo": "duas_aguas", "cumeeira": "x", "inclinacao_pct": 15,
                          "beiral_m": 0.6, "telha": "TELHA ONDULADA DE FIBROCIMENTO"}
    elif o["tipo"] == "secao":
        o["classe_parede"] = "I"
    elif o["tipo"] == "fachada" and o["lado"] == "sul":
        o["letreiro"] = "RESTAURANTE"
    elif o["tipo"] == "folha":
        o["prancha"] = {"PRANCHA 01": "1/4", "PRANCHA 02": "2/4", "PRANCHA 03": "3/4"}[o["nome"]]
        if o["nome"] == "PRANCHA 03":
            o["vistas"][0]["janela"] = [72, -4, 106, 38]  # cabe o nível da cumeeira
            o["notas"] =["Cortes e fachadas gerados da mesma geometria da planta; alturas, "
                          "telhado e classes dos materiais são premissas do exemplo (projeto "
                          "fictício)."]
            o["quadros"] = [{"titulo": "Cálculo da largura das saídas (NT 2-08)", "linhas": [
                "Ocupação F-8 (local para refeição): 1 pessoa por m² de área (Anexo A).",
                "Área atendida pela descarga: 350,48 m² -> P = 351 pessoas.",
                "C = 100 pessoas por unidade de passagem (acessos e descarga).",
                "N = 351 / 100 = 3,51 -> 4 unidades de passagem.",
                "Largura mínima = 4 x 0,55 = 2,20 m.",
                "Largura projetada: portas de 1,20 + 1,20 m = 2,40 m (>= 2,20 m)."]}]

# rótulos de classe de piso nos ambientes principais (centro livre de cada sala)
CLASSES = [
    {"tipo": "rotulo_classe", "elemento": "piso", "classe": "I", "x": 1.31, "y": 0.95},
    {"tipo": "rotulo_classe", "elemento": "piso", "classe": "I", "x": 1.31, "y": 14.95},
    {"tipo": "rotulo_classe", "elemento": "piso", "classe": "I", "x": 13.91, "y": 11.95},
]

LX0, LY0 = 120.0, 0.0  # lote 30 x 40 m, de frente para a rua ao sul
SITUACAO = {
    "tipo": "situacao", "escala": 500,
    "lote": [[LX0, LY0], [LX0 + 30, LY0], [LX0 + 30, LY0 + 40], [LX0, LY0 + 40]],
    "edificacoes": [{"poligono": [[LX0 + 2.5, 8], [LX0 + 27.5, 8], [LX0 + 27.5, 24],
                                  [LX0 + 2.5, 24]],
                     "caimentos": [[LX0 + 8, 12, -90], [LX0 + 8, 20, 90],
                                   [LX0 + 22, 12, -90], [LX0 + 22, 20, 90]]}],
    "ruas": [{"nome": "Rua das Flores", "eixo": [[112, -6], [182, -6]], "largura_m": 10},
             {"nome": "Avenida Central", "eixo": [[166, -40], [166, 60]], "largura_m": 14}],
    "raio_esquina_m": 5,
    "distancias": [{"a": [LX0 + 30, -2.5], "b": [159, -2.5], "deslocamento_m": -1.5}],
    "textos": [{"texto": "Alinhamento", "x": LX0 + 15, "y": 1.6},
               {"texto": "Restaurante (projeção)", "x": LX0 + 15, "y": 27.5}],
    "norte_graus": 20, "norte_xy": [LX0 + 15, 62],
}
FOLHA4 = {"tipo": "folha", "nome": "PRANCHA 04", "formato": "A2", "prancha": "4/4",
          "titulo": "PLANTA DE SITUAÇÃO", "quadro_de_areas": False,
          "selo": next(o for o in ops if o["tipo"] == "folha")["selo"],
          "vistas": [{"titulo": "Planta de situação", "janela": [106, -44, 186, 76],
                      "escala": 500}],
          "notas": ["Lote, ruas, distância à esquina e norte são premissas do exemplo "
                    "(projeto fictício)."]}

novo = Authoring(BASE / "restaurante-400m2-f.dxf", [], old.title, escala=100)
novo.add([*ops, *CLASSES, SITUACAO, FOLHA4])
r = novo.build()
print({k: r[k] for k in ("vistas", "situacao")})
print([(f["folha"], f["vistas"]) for f in r["folhas"]])
print(exportar_pdf(BASE / "restaurante-400m2-f.dxf", BASE / "restaurante-400m2-f.pdf", None))
