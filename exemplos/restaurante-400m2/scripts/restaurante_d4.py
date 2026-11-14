"""Restaurante de 400 m2 com a D4 (Quadro Resumo automático) e duas pranchas A1: a 01 (planta e
detalhes, como na D3) e a 02 (Quadro Resumo). Parte das operações de restaurante-400m2-d2d3.dxf;
não altera os arquivos anteriores. Projeto FICTÍCIO."""
import tempfile
from pathlib import Path

from coscip_mcp import folhas
from coscip_mcp.autoria import Authoring
from coscip_mcp.folhas import Folha

BASE = Path(__file__).resolve().parents[1] / "saidas"
old = Authoring.load(BASE / "restaurante-400m2-d2d3.dxf")

QUADRO = {
    "tipo": "quadro_resumo", "x": 50.0, "y": 45.0,
    "pavimentos": [{"nome": "Térreo", "atc_m2": 400.0}],
    "identificacao": {
        "endereco": "Endereço fictício", "proprietario": "Proprietário fictício",
        "responsavel_tecnico": "", "decreto_adotado": "Decreto nº 42/2018",
        "numero_de_pavimentos": "1", "ocupacao_do_subsolo": "Não há",
        "lotacao_prevista": "351 pessoas (NT 2-08, Anexo A)"},
    "classificacao": {"grupo": "F", "ocupacao": "Local de reunião de público", "divisao": "F-8",
                      "descricao": "Local para refeição", "risco": "MÉDIO 1 (NT 1-04)"},
    "medidas_de_seguranca": ["Tabela 2 do Anexo III", "Extintores", "Saídas de emergência",
                             "Iluminação de emergência", "Sinalização de segurança",
                             "Controle de materiais de acabamento"],
    "riscos_especiais": ["Gás liquefeito de petróleo (central externa, NT 3-02)",
                         "Cozinha profissional (NT 3-01), a confirmar"],
    "saidas": {"lotacao": "351", "grupo_e_divisao": "F-8", "pavimento": "Térreo",
               "saida_unica": False, "tipo_de_escada": "Sem escada",
               "capacidade_da_unidade_de_passagem": "100",
               "unidades_de_passagem_projetadas": "8 (portas do salão: 3 + 3 + 2)"},
    "declarado": {"extintores": 5, "saidas": 2, "glp_kg": 180, "atc_m2": 400.0},
}

base = [op for op in old.ops if not isinstance(op, Folha)]
folha1 = next(op for op in old.ops if isinstance(op, Folha)).model_dump(exclude_none=True)
folha1["prancha"] = "1/2"

# 1ª passada: só para saber a altura do quadro e enquadrar a prancha 02
tmp = Authoring(Path(tempfile.mkdtemp()) / "p.dxf", [], old.title, escala=100)
tmp.add([op.model_dump(exclude_none=True) for op in base] + [QUADRO])
altura = tmp.build()["quadro_resumo"]["altura_m"]

folha2 = {
    "tipo": "folha", "nome": "PRANCHA 02", "formato": "A1", "prancha": "2/2",
    "titulo": "QUADRO RESUMO", "quadro_de_areas": False,
    "selo": folha1["selo"],
    "vistas": [{"titulo": "Quadro resumo", "janela": [49.5, 45 - altura - 1.0, 62.5, 46.0],
                "escala": 100}],
    "notas": ["Dados de identificação, classificação, medidas e saídas informados no "
              "projeto de exemplo; quantidades de extintores, placas, iluminação, GLP e áreas "
              "contadas do desenho.",
              "A conferência entre o desenho e os valores declarados está no retorno do motor "
              "(quadro_resumo.conferencia)."],
}

novo = Authoring(BASE / "restaurante-400m2-d4.dxf", [], old.title, escala=100)
novo.add([op.model_dump(exclude_none=True) for op in base] + [QUADRO, folha1, folha2])
r = novo.build()
print({k: r[k] for k in ("escala_de_impressao",)})
q = r["quadro_resumo"]
print("altura do quadro (m):", q["altura_m"], "| contagens:", q["contagens"])
for c in q["conferencia"]:
    print(" -", c["situacao"].upper().ljust(18), c["item"], "| desenho", c["desenho"],
          "| declarado", c["declarado"])
print(folhas.exportar_pdf(BASE / "restaurante-400m2-d4.dxf",
                          BASE / "restaurante-400m2-d4.pdf", None))
