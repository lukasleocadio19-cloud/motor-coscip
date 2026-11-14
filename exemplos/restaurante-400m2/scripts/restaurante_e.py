"""Restaurante de 400 m2 com sprinklers (frente E): malha de bicos no salão e na cozinha, rede,
cálculo hidráulico, isométrico do salão (prancha 04) e memorial NT 2-03. Parte de
restaurante-400m2-d5.dxf; não altera os arquivos anteriores. Projeto FICTÍCIO; a classe de risco
(Ordinário 1) e os critérios são premissas do exemplo, a conferir na NBR 10897 / NFPA 13."""
from pathlib import Path

from coscip_cad.dwg_export import exportar_dwg
from coscip_mcp.autoria import Authoring, Sala
from coscip_mcp.folhas import Folha, exportar_pdf
from coscip_mcp.workspace import Workspace

BASE = Path(__file__).resolve().parents[1] / "saidas"
old = Authoring.load(BASE / "restaurante-400m2-d5.dxf")
salas = {o.nome: o for o in old.ops if isinstance(o, Sala)}
salao = next(n for n in salas if n.startswith("SAL"))
cozinha = next(n for n in salas if n.startswith("COZINHA"))

SPK = [
    {"tipo": "sprinklers", "nome": "Salão", "classe": "ORDINARIO_1", "sala": salao,
     "alimentacao": [17.9, 4.0], "z_ramal_m": 3.2},
    {"tipo": "sprinklers", "nome": "Cozinha", "classe": "ORDINARIO_1", "sala": cozinha,
     "alimentacao": [12.7, 13.5], "z_ramal_m": 3.2},
    {"tipo": "isometrico", "sprinklers": "Salão", "x": 135, "y": 8,
     "titulo": "ISOMÉTRICO DA REDE DE SPRINKLERS - SALÃO"},
    {"tipo": "isometrico", "sprinklers": "Cozinha", "x": 135, "y": 32,
     "titulo": "ISOMÉTRICO DA REDE DE SPRINKLERS - COZINHA"},
]
folha_ref = next(o for o in old.ops if isinstance(o, Folha))
folha4 = {"tipo": "folha", "nome": "PRANCHA 04", "formato": "A1", "prancha": "4/4",
          "titulo": "SPRINKLERS - ISOMÉTRICOS E CÁLCULO",
          "quadro_de_areas": False, "selo": folha_ref.model_dump(exclude_none=True)["selo"],
          "vistas": [{"titulo": "Isométricos", "janela": [110, 0, 181, 50], "escala": 100}],
          "notas": ["Rede calculada pelo motor: bicos em cascata (K·√P) e Hazen-Williams, "
                    "tubo de aço classe 40; critérios da classe Ordinário 1 por premissa "
                    "(NFPA 13), a conferir na norma adotada.",
                    "Uma prumada por zona neste exemplo; o projeto executivo usa o programa de "
                    "cálculo do projetista (obstruções, vigas, laços)."]}
ops = [op.model_dump(exclude_none=True) for op in old.ops]
for o in ops:
    if o["tipo"] == "folha":
        o["prancha"] = o["prancha"].split("/")[0] + "/4"
novo = Authoring(BASE / "restaurante-400m2-e.dxf", [], old.title, escala=100)
novo.add([*ops, *SPK, folha4])
r = novo.build()
for z in r["sprinklers"]:
    print(z["nome"], z["bicos"], "bicos;", z["bicos_em_operacao"], "em operação;",
          z["vazao_total_lpm"], "L/min;", z["pressao_na_base_da_prumada_mca"], "mca;", z["avisos"])

# memorial NT 2-03 com as duas zonas (os ambientes do restaurante)
ws = Workspace()
memo = ws.design("sprinklers", {
    "classe": "ORDINARIO_1", "norma_adotada": "NBR_10897", "grupo_divisao": "F-8",
    "pavimentos_protegidos": 1, "hidrantes_conjugados": False,
    "ambientes": [
        {"nome": salao, "area_m2": 179.28}, {"nome": cozinha, "area_m2": 57.04},
        {"nome": "ESTOQUE SECO", "area_m2": 18.4}, {"nome": "RECEBIMENTO / CÂMARA FRIA",
                                                     "area_m2": 35.8},
        {"nome": "WC MASCULINO", "area_m2": 19.7, "tipo": "SANITARIO"},
        {"nome": "WC FEMININO", "area_m2": 19.7, "tipo": "SANITARIO"},
        {"nome": "WC PCD", "area_m2": 10.1, "tipo": "SANITARIO"},
        {"nome": "DML", "area_m2": 10.1, "tipo": "SANITARIO"},
        {"nome": "CIRCULAÇÃO", "area_m2": 19.4}],
    "zonas": [{"nome": "Salão", "retangulo": [0.2, 0.2, 16.8, 11.0], "alimentacao": [17.9, 4.0],
               "z_ramal_m": 3.2},
              {"nome": "Cozinha", "retangulo": [0.2, 11.2, 12.6, 15.8],
               "alimentacao": [12.7, 13.5], "z_ramal_m": 3.2}]})
md = BASE / "restaurante-400m2-sprinklers-memorial.md"
from coscip_design.memorial import AVISO  # noqa: E402

md.write_text("# Memorial dos sprinklers - restaurante fictício de 400 m²\n\n> " + AVISO + "\n\n"
              + ws.memorials[-1].markdown(), encoding="utf-8")
print("memorial:", md)
print(exportar_pdf(BASE / "restaurante-400m2-e.dxf", BASE / "restaurante-400m2-e.pdf", None))
d = exportar_dwg(BASE / "restaurante-400m2-e.dxf", BASE / "restaurante-400m2-e.dwg",
                 sobrescrever=True)
print("DWG:", d.dwg_path, d.conferencia.get("confere"), d.conferencia.get("diferencas"))
