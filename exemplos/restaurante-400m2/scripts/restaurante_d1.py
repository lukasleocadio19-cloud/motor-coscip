"""Regera o restaurante de 400 m2 com o padrão de apresentação da frente D1 (janelas reais,
etiquetas de vão, cotas em cadeia e marcas de corte), a partir das operações da planta anterior.
Não altera a planta original: grava restaurante-400m2-d1.dxf ao lado."""
from pathlib import Path

from coscip_mcp.autoria import Authoring, Cota, Texto

BASE = Path(__file__).resolve().parents[1] / "saidas"
old = Authoring.load(BASE / "restaurante-400m2.dxf")

TEXTOS_ANTIGOS = {"J1", "J2", "J3", "A", "A'", "B", "B'"}
ops = []
for op in old.ops:
    if isinstance(op, Cota):
        continue  # substituídas pelas cotas em cadeia
    if isinstance(op, Texto) and (op.texto in TEXTOS_ANTIGOS or op.texto.startswith("ESQUADRIAS")):
        continue
    ops.append(op)

novo = Authoring(BASE / "restaurante-400m2-d1.dxf", ops, old.title, escala=100)
novo.add([
    # janelas: J1 e J2 na parede oeste, J3 na sul
    {"tipo": "janela", "x": 0.1, "y": 2.9, "largura_m": 3.0, "altura_m": 1.2, "peitoril_m": 0.9,
     "angulo_graus": 90},
    {"tipo": "janela", "x": 0.1, "y": 7.6, "largura_m": 2.0, "altura_m": 1.2, "peitoril_m": 0.9,
     "angulo_graus": 90},
    {"tipo": "janela", "x": 13.75, "y": 0.1, "largura_m": 3.5, "altura_m": 1.2, "peitoril_m": 0.9,
     "angulo_graus": 0, "lado_etiqueta": "direita"},
    # cotas em cadeia: fachada sul e lado leste
    {"tipo": "cota_cadeia", "pontos": [[0, 0], [3, 0], [5, 0], [9, 0], [11, 0], [12, 0],
                                        [15.5, 0], [25, 0]], "afastamento_m": -1.2},
    {"tipo": "cota_cadeia", "pontos": [[25, 0], [25, 11.1], [25, 16]], "afastamento_m": -1.0},
    # cortes A-A (olhando para o norte) e B-B (olhando para o leste)
    {"tipo": "marca_corte", "nome": "A", "a": [-1.5, 7.6], "b": [29.0, 7.6], "sentido": "esquerda"},
    {"tipo": "marca_corte", "nome": "B", "a": [9.8, -2.6], "b": [9.8, 20.0], "sentido": "direita"},
])
print(novo.build())
