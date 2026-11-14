"""Restaurante de 400 m2 com a D2 (chamadas de placa, mobiliário e equipamentos da biblioteca) e a
D3 (folha A1 em paper space + PDF). Parte das operações de restaurante-400m2-d1.dxf; não altera
os arquivos anteriores. Projeto FICTÍCIO: selo sem nomes reais."""
from pathlib import Path

from coscip_mcp import folhas
from coscip_mcp.autoria import Authoring, Parede, Simbolo, Texto

BASE = Path(__file__).resolve().parents[1] / "saidas"
old = Authoring.load(BASE / "restaurante-400m2-d1.dxf")

PLACAS = {"E-5", "S-12", "PICTO_P-1", "PICTO_A-2", "PICTO_A-3"}
ops = []
for op in old.ops:
    if isinstance(op, Parede) and op.estilo == "divisoria":
        continue  # contornos de equipamento da cozinha: viram blocos da biblioteca
    if isinstance(op, Texto) and (op.texto.isdigit() or op.x >= 29.5
                                  or op.texto.startswith("EXT. CLASSE K")):
        continue  # numeração dos equipamentos e legenda de texto da cozinha
    if isinstance(op, Simbolo) and op.id:
        if op.id.upper() == "VASO_PRESSAO":
            continue  # botijões: viram blocos P-45
        if op.id.upper() in PLACAS:
            continue  # placas: viram chamadas
    ops.append(op)

novo = Authoring(BASE / "restaurante-400m2-d2d3.dxf", ops, old.title, escala=100)

novo.add([
    # --- cozinha: equipamentos e coifa
    {"tipo": "mobiliario", "id": "FOGAO", "x": 7.3, "y": 15.25},
    {"tipo": "mobiliario", "id": "CHAPA", "x": 8.7, "y": 15.25},
    {"tipo": "mobiliario", "id": "FRITADEIRA", "x": 9.85, "y": 15.25},
    {"tipo": "mobiliario", "id": "FORNO", "x": 10.95, "y": 15.25},
    {"tipo": "mobiliario", "id": "COIFA", "x": 8.9, "y": 15.2, "largura_m": 5.0,
     "profundidade_m": 1.15},
    {"tipo": "mobiliario", "id": "BALCAO", "x": 8.8, "y": 13.15, "largura_m": 3.2,
     "profundidade_m": 0.7},
    {"tipo": "mobiliario", "id": "REFRIGERADOR", "x": 12.05, "y": 12.15, "largura_m": 0.9,
     "profundidade_m": 1.3},
    {"tipo": "mobiliario", "id": "BALCAO", "x": 0.8, "y": 12.9, "largura_m": 2.6,
     "profundidade_m": 0.8, "rotacao_graus": 90},
    {"tipo": "mobiliario", "id": "PIA", "x": 2.0, "y": 11.9},
    # --- central de GLP: 4 x P-45
    *({"tipo": "mobiliario", "id": "BOTIJAO_P45", "x": x, "y": 16.4}
      for x in (9.5, 9.95, 10.4, 10.85)),
    # --- salão: 12 mesas de 4 lugares
    *({"tipo": "mobiliario", "id": "MESA_4_LUGARES", "x": x, "y": y}
      for y in (4.0, 6.8, 9.4) for x in (3.5, 7.0, 10.5, 14.0)),
    # --- sanitários
    *({"tipo": "mobiliario", "id": "VASO_SANITARIO", "x": x, "y": 3.2}
      for x in (20.2, 21.6, 23.0)),
    *({"tipo": "mobiliario", "id": "LAVATORIO", "x": x, "y": 0.6, "rotacao_graus": 180}
      for x in (20.2, 21.6, 23.0)),
    *({"tipo": "mobiliario", "id": "VASO_SANITARIO", "x": x, "y": 6.8}
      for x in (20.2, 21.6, 23.0)),
    *({"tipo": "mobiliario", "id": "LAVATORIO", "x": x, "y": 4.2, "rotacao_graus": 180}
      for x in (20.2, 21.6, 23.0)),
    {"tipo": "mobiliario", "id": "VASO_SANITARIO", "x": 20.4, "y": 10.6},
    {"tipo": "mobiliario", "id": "LAVATORIO", "x": 19.6, "y": 8.3, "rotacao_graus": 90},
    # --- placas em planta de projeto (dimensões: exemplos da Tabela 7 da NT 2-05, a conferir
    #     pela distância de visualização real)
    {"tipo": "texto", "texto": "EXT. CLASSE K", "x": 4.4, "y": 14.35, "altura_m": 0.15},
    *({"tipo": "chamada", "codigo": "S-12", "x": x, "y": y, "dimensao": "600x300"}
      for x, y in ((4.0, 1.9), (10.0, 1.9), (1.9, 5.6))),
    {"tipo": "chamada", "codigo": "S-12", "x": 3.0, "y": 14.2, "dimensao": "300x150"},
    {"tipo": "chamada", "codigo": "S-12", "x": 24.0, "y": 14.8, "dimensao": "300x150"},
    *({"tipo": "chamada", "codigo": "E-5", "x": x, "y": y, "dimensao": "150x150",
       "alvo": [ax, ay]}
      for x, y, ax, ay in ((7.0, 1.9, 7.0, 0.6), (1.5, 9.1, 0.6, 9.8), (15.3, 7.0, 16.4, 8.0),
                           (8.0, 12.6, 8.0, 11.5), (24.0, 11.3, 24.4, 12.6),
                           (6.1, 13.4, 6.1, 14.55), (8.4, 17.9, 8.4, 17.2))),
    {"tipo": "chamada", "codigo": "P-1", "x": 9.6, "y": 18.4, "dimensao": "150x150"},
    {"tipo": "chamada", "codigo": "A-2", "x": 10.4, "y": 18.4, "dimensao": "150x150"},
    {"tipo": "chamada", "codigo": "A-3", "x": 11.2, "y": 18.4, "dimensao": "150x150"},
    # --- folha A1
    {"tipo": "folha", "nome": "PRANCHA 01", "formato": "A1", "prancha": "1/1",
     "titulo": "PLANTA BAIXA - TÉRREO E DETALHES",
     "selo": {"obra": "RESTAURANTE (F-8) - ATC 400,00 m² - EXEMPLO FICTÍCIO",
              "endereco": "Endereço fictício",
              "proprietario": "Proprietário fictício",
              "autor_projeto": "Projeto fictício gerado pelo motor COSCIP",
              "data": "10/11/2026", "revisao": "00"},
     "atc_m2": 400.0,
     "vistas": [
         {"titulo": "Planta baixa - térreo", "janela": [-3.5, -3.0, 29.5, 21.0], "escala": 100},
         {"titulo": "Detalhe - cozinha", "janela": [0.0, 10.5, 13.0, 16.5], "escala": 50},
         {"titulo": "Detalhe - central de GLP", "janela": [8.2, 15.5, 12.4, 19.5],
          "escala": 25}],
     "notas": [
         "Cotas em metros; etiquetas de porta e janela em centímetros (largura x altura / "
         "peitoril).",
         "Projeto fictício de exemplo: premissas de ocupação, alturas e tipo de construção não "
         "foram confirmadas.",
         "Placas de sinalização (NT 2-05): dimensões das chamadas tiradas dos exemplos da "
         "Tabela 7; conferir pela distância de visualização.",
         "Cozinha: duto de exaustão único e aparente, sem travessia de outros ambientes (NT "
         "3-01, itens 2.1 e 2.2) - a confirmar com o projeto de exaustão.",
         "Central de GLP: 4 recipientes P-45 em abrigo com paredes e cobertura TRRF 120 min, "
         "lado norte aberto (NT 3-02)."],
     "revisoes": [{"rev": "00", "data": "10/11/2026", "descricao": "Emissão inicial (exemplo)"}]},
])
print(novo.build())
pdf = folhas.exportar_pdf(BASE / "restaurante-400m2-d2d3.dxf",
                          BASE / "restaurante-400m2-d2d3.pdf")
print(pdf)
