"""Medida de um desenho profissional de referência e comparação com o que o motor produz
(frente D6, docs/arquitetura-projeto.md §9).

O desenho real (DWG de processo) fica **fora do repositório**: dados reais nunca entram aqui. Este
script o abre numa cópia (DWG por conversão ODA), mede **só números e presença de recursos**
(camadas com espessura, estilos de cota por escala, layouts e escalas das viewports, blocos,
janelas, etiquetas de vão, cortes, quadro resumo, selo...) e grava um YAML sem nenhum texto do
projeto. O YAML-gabarito (``docs/validacao/desenho-referencia.yaml``) é o que entra no Git.

O mesmo medidor roda sobre o DXF que o motor gera; ``comparar`` lista os recursos que o
desenho de referência tem e o do motor não (as **lacunas**), e os números lado a lado.

    python -m tools.validacao.desenho_referencia MEDIR  <arquivo.dwg|.dxf> --saida gabarito.yaml
    python -m tools.validacao.desenho_referencia COMPARAR <dxf-do-motor> --gabarito gabarito.yaml
    python -m tools.validacao.desenho_referencia EXEMPLO  <saida.dxf>   # exemplo do motor
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ESCALAS_PADRAO = (20, 25, 50, 75, 100, 125, 150, 200, 250, 300, 500)
_VAO = re.compile(r"^\d{2,3}\s*[xX]\s*\d{2,3}(\s*/\s*\d{1,3})?$")
_ESCALA_NO_NOME = re.compile(r"(\d{2,4})")


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()


def _texto_de(e: Any) -> str:
    try:
        t = e.dxf.text if e.dxftype() == "TEXT" else e.plain_text()
    except Exception:  # noqa: BLE001 - texto malformado
        return ""
    return str(t)


def _escala_padrao(denominador: float) -> int:
    perto = min(ESCALAS_PADRAO, key=lambda e: abs(e - denominador))
    return perto if abs(perto - denominador) / perto <= 0.06 else round(denominador)


def abrir(caminho: Path, cache: Path | None = None):  # noqa: ANN201
    """Abre DXF, ou DWG convertido numa cópia pelo ODA File Converter."""
    from ezdxf import recover

    caminho = Path(caminho)
    if caminho.suffix.lower() == ".dwg":
        from coscip_cad.dwg import dwg_to_dxf

        conv = dwg_to_dxf(caminho, cache or Path.cwd() / ".coscip-dwg-cache")
        caminho = Path(conv.dxf_path)
    doc, _ = recover.readfile(str(caminho))
    return doc


def medir(doc) -> dict[str, Any]:  # noqa: ANN001
    """Números e presença de recursos de um desenho. Nenhum texto do projeto sai daqui."""
    msp = doc.modelspace()
    tipos = Counter(e.dxftype() for e in msp)
    por_camada = Counter(e.dxf.layer for e in msp)
    camadas = list(doc.layers)
    usadas = [c for c in camadas if por_camada.get(c.dxf.name)]

    blocos = [b for b in doc.blocks if not b.name.startswith("*")
              and not b.name.startswith("_") and len(b) > 0]
    insercoes = Counter(e.dxf.name for e in msp.query("INSERT"))
    nomes_blocos = [_norm(b.name) for b in blocos]

    textos_modelo = [_texto_de(e) for e in msp.query("TEXT MTEXT")]
    layouts = []
    textos_folha: list[str] = []
    escalas: set[int] = set()
    viewports = 0
    for nome in doc.layout_names():
        if nome == "Model":
            continue
        lay = doc.layouts.get(nome)
        vps = [v for v in lay.query("VIEWPORT") if v.dxf.id != 1]
        viewports += len(vps)
        for v in vps:
            ph = v.dxf.height
            if ph > 0 and v.dxf.view_height > 0:
                ratio = v.dxf.view_height / ph  # unidades do modelo por mm de papel
                # modelo em metros: 0,1 m/mm = 1:100; em mm: 100 mm/mm = 1:100
                escalas.add(_escala_padrao(ratio * 1000 if ratio < 5 else ratio))
        textos_folha += [_texto_de(e) for e in lay.query("TEXT MTEXT")]
        layouts.append({"viewports": len(vps), "entidades": len(lay)})
    todos = [_norm(t) for t in textos_modelo + textos_folha if t.strip()]

    def tem(*palavras: str) -> int:
        return sum(any(p in t for p in palavras) for t in todos)

    dimstyles = [d.dxf.name for d in doc.dimstyles]
    estilos_cota_escala = sum(1 for n in dimstyles if re.search(r"\d{2,4}", n)
                              and n.upper() not in ("ISO-25",))
    estilos_texto = [s.dxf.name for s in doc.styles]
    tracos = {c.dxf.linetype for c in usadas}
    hatches = list(msp.query("HATCH"))
    janelas = (sum(por_camada[n] for n in por_camada if re.search(r"JANELA|WINDOW", _norm(n)))
               + sum(n for b, n in insercoes.items() if re.search(r"JANELA|WINDOW", _norm(b))))
    etiquetas = sum(bool(_VAO.match(t.strip())) for t in textos_modelo)
    placas = sum(n for b, n in insercoes.items()
                 if re.search(r"PICTO|^[SEAPM]-?\d|PLACA|SINALIZA", _norm(b)))
    chamadas = sum(n for b, n in insercoes.items() if "CHAMAD" in _norm(b))
    selo = sum(tem(p) > 0 for p in ("PRANCHA", "ESCALA", "REVISAO", "RESPONSAVEL", "OBRA",
                                    "PROPRIETARIO", "FOLHA"))

    m = {
        "unidade": {"insunits_declarado": int(doc.header.get("$INSUNITS", 0))},
        "modelo": {"entidades": sum(tipos.values()), "tipos": dict(tipos)},
        "camadas": {"total": len(camadas), "usadas": len(usadas),
                    "com_cor": sum(1 for c in usadas if c.dxf.color not in (7, 0)),
                    "com_espessura": sum(1 for c in usadas if c.dxf.lineweight > 0),
                    "tipos_de_linha": len(tracos)},
        "blocos": {"definicoes": len(blocos), "insercoes": sum(insercoes.values()),
                   "distintos_em_uso": len(insercoes),
                   "chamadas_de_placa": chamadas, "placas_ou_pictogramas": placas},
        "estilos": {"texto": len(estilos_texto), "cota": len(dimstyles),
                    "cota_por_escala": estilos_cota_escala},
        "hachuras": {"total": len(hatches),
                     "padroes": len({h.dxf.pattern_name for h in hatches})},
        "layouts": {"papel": len(layouts), "com_viewports": sum(1 for x in layouts
                                                                if x["viewports"]),
                    "viewports": viewports, "escalas": sorted(escalas)},
        "textos": {"modelo": len(textos_modelo), "folha": len(textos_folha),
                   "etiquetas_de_vao": etiquetas},
        "presencas": {  # quantas linhas de texto citam o termo (só o número sai)
            "janelas": janelas, "marcas_de_corte": tem('CORTE "', "CORTE A", "CORTE B"),
            "cortes": tem("CORTE"), "fachadas": tem("FACHADA"),
            "quadro_resumo": tem("QUADRO RESUMO"),
            "quadro_de_areas": tem("QUADRO DE AREAS"), "notas": tem("NOTAS"),
            "legenda": tem("LEGENDA"), "detalhes": tem("DETALHE"), "isometrico": tem("ISOMETRICO"),
            "situacao": tem("SITUACAO"), "selo_campos": selo,
            "norte": tem("NORTE") + sum(1 for b in nomes_blocos if b == "NORTE")},
    }
    m["recursos"] = recursos(m)
    return m


def recursos(m: dict[str, Any]) -> dict[str, bool]:
    """Cada recurso que um desenho profissional tem, como verdadeiro/falso."""
    p, c, b, e, h, lay, t = (m["presencas"], m["camadas"], m["blocos"], m["estilos"],
                             m["hachuras"], m["layouts"], m["textos"])
    return {
        "folha_em_paper_space": lay["com_viewports"] >= 1,
        "varias_escalas_na_folha": len(lay["escalas"]) >= 2,
        "camadas_com_espessura": c["com_espessura"] >= 5,
        "camadas_coloridas": c["com_cor"] >= 3,
        "estilos_de_cota_por_escala": e["cota_por_escala"] >= 1,
        "cotas_nativas": m["modelo"]["tipos"].get("DIMENSION", 0) >= 3,
        "janelas_em_planta": p["janelas"] >= 1,
        "etiquetas_de_vao": t["etiquetas_de_vao"] >= 3,
        "blocos_distintos_em_uso": b["distintos_em_uso"] >= 5,
        "chamadas_de_placa": b["chamadas_de_placa"] >= 1,
        "hachuras": h["total"] >= 10,
        "marca_de_corte": p["marcas_de_corte"] >= 1 or p["cortes"] >= 1,
        "cortes": p["cortes"] >= 1,
        "fachadas": p["fachadas"] >= 1,
        "quadro_resumo": p["quadro_resumo"] >= 1,
        "quadro_de_areas": p["quadro_de_areas"] >= 1,
        "selo_na_folha": p["selo_campos"] >= 3,
        "notas_de_projeto": p["notas"] >= 1,
        "legenda": p["legenda"] >= 1,
        "detalhes_construtivos": p["detalhes"] >= 1,
        "isometrico": p["isometrico"] >= 1,
        "planta_de_situacao": p["situacao"] >= 1,
        "indicacao_de_norte": p["norte"] >= 1,
        "multileaders_ou_leaders": m["modelo"]["tipos"].get("MULTILEADER", 0)
        + m["modelo"]["tipos"].get("LEADER", 0) >= 1,
    }


def comparar(gabarito: dict[str, Any], motor: dict[str, Any]) -> dict[str, Any]:
    """Lacunas (o gabarito tem e o motor não), o que o motor já cobre e os números lado a lado."""
    rg, rm = gabarito["recursos"], motor["recursos"]
    lacunas = sorted(k for k, v in rg.items() if v and not rm.get(k, False))
    cobre = sorted(k for k, v in rg.items() if v and rm.get(k, False))
    extras = sorted(k for k, v in rm.items() if v and not rg.get(k, False))
    lado = {
        "camadas_usadas": (gabarito["camadas"]["usadas"], motor["camadas"]["usadas"]),
        "blocos_definidos": (gabarito["blocos"]["definicoes"], motor["blocos"]["definicoes"]),
        "viewports": (gabarito["layouts"]["viewports"], motor["layouts"]["viewports"]),
        "escalas": (gabarito["layouts"]["escalas"], motor["layouts"]["escalas"]),
        "estilos_de_cota": (gabarito["estilos"]["cota"], motor["estilos"]["cota"]),
        "hachuras": (gabarito["hachuras"]["total"], motor["hachuras"]["total"]),
        "cotas": (gabarito["modelo"]["tipos"].get("DIMENSION", 0),
                  motor["modelo"]["tipos"].get("DIMENSION", 0)),
        "entidades_no_model": (gabarito["modelo"]["entidades"], motor["modelo"]["entidades"]),
    }
    return {"lacunas": lacunas, "cobertos": cobre, "so_no_motor": extras,
            "cobertura": f"{len(cobre)}/{len(cobre) + len(lacunas)}",
            "lado_a_lado": {k: {"referencia": a, "motor": b} for k, (a, b) in lado.items()}}


def relatorio(cmp: dict[str, Any]) -> str:
    linhas = [f"Cobertura dos recursos do desenho de referência: {cmp['cobertura']}", ""]
    linhas.append("Lacunas (a referência tem, o motor ainda não produz):")
    linhas += [f"  - {x}" for x in cmp["lacunas"]] or ["  (nenhuma)"]
    linhas += ["", "Já cobertos: " + ", ".join(cmp["cobertos"])]
    linhas += ["", "Números (referência | motor):"]
    for k, v in cmp["lado_a_lado"].items():
        linhas.append(f"  {k}: {v['referencia']} | {v['motor']}")
    return "\n".join(linhas)


def construir_exemplo(destino: Path) -> Path:
    """Desenho de exemplo do motor com todos os recursos já implementados (D1 a D5, F)."""
    from coscip_mcp.autoria import Authoring

    ops: list[dict[str, Any]] = [
        {"tipo": "edificacao", "pe_direito_m": 3.6, "laje_m": 0.2, "platibanda_m": 0.6,
         "volumes": [{"nome": "Duto", "retangulo": [7.0, 5.0, 7.5, 5.5], "base_m": 2.7,
                      "topo_m": 5.4}]},
        {"tipo": "sala", "nome": "Salão", "retangulo": [0, 0, 10, 6]},
        {"tipo": "sala", "nome": "Cozinha", "retangulo": [10.2, 0, 16, 6]},
        {"tipo": "porta", "x": 5, "y": -0.075, "largura_m": 1.2},
        {"tipo": "janela", "x": 8, "y": -0.075, "largura_m": 1.5},
        {"tipo": "janela", "x": 13, "y": -0.075, "largura_m": 1.5},
        {"tipo": "janela", "x": -0.075, "y": 3, "largura_m": 1.5, "angulo_graus": 90},
        {"tipo": "mobiliario", "id": "FOGAO", "x": 13, "y": 5.2},
        *({"tipo": "mobiliario", "id": "MESA_4_LUGARES", "x": x, "y": 3}
          for x in (2.5, 5.5, 8.0)),
        {"tipo": "simbolo", "classe": "EXTINTOR", "agente": "PQS_ABC", "capacidade": "6 kg",
         "x": 2, "y": 5.5},
        *({"tipo": "simbolo", "classe": "ILUMINACAO_EMERGENCIA", "x": x, "y": 2}
          for x in (1, 4, 7, 11, 14)),
        {"tipo": "chamada", "codigo": "S-12", "x": 5, "y": 1.5, "dimensao": "600x300"},
        {"tipo": "chamada", "codigo": "E-5", "x": 2, "y": 4.6, "dimensao": "150x150"},
        {"tipo": "cota_cadeia", "pontos": [[0, 0], [10, 0], [16, 0]], "afastamento_m": -1.2},
        {"tipo": "marca_corte", "nome": "A", "a": [-1.5, 3], "b": [17.5, 3]},
        {"tipo": "legenda", "x": 20, "y": 10},
        {"tipo": "secao", "nome": "A", "a": [-1.5, 3], "b": [17.5, 3], "x": 30, "y": 0,
         "marca_na_planta": False},
        {"tipo": "fachada", "lado": "sul", "x": 30, "y": 12},
        {"tipo": "quadro_resumo", "x": 60, "y": 20},
        {"tipo": "situacao", "escala": 500, "titulo": "Planta de situação",
         "lote": [[100, 0], [120, 0], [120, 30], [100, 30]],
         "edificacoes": [{"poligono": [[102, 5], [118, 5], [118, 11], [102, 11]]}],
         "ruas": [{"nome": "Rua do exemplo", "eixo": [[90, -6], [130, -6]], "largura_m": 10}],
         "norte_graus": 0},
        {"tipo": "detalhe", "modelo": "extintor", "x": 100, "y": -20},
        {"tipo": "folha", "nome": "PRANCHA 01", "formato": "A1", "prancha": "1/1",
         "titulo": "PLANTA, CORTE E FACHADA",
         "selo": {"obra": "Exemplo", "proprietario": "Fictício", "autor_projeto": "Motor",
                  "data": "10/11/2026"},
         "notas": ["Exemplo gerado pelo motor."],
         "vistas": [{"titulo": "Planta baixa", "janela": [-3, -3, 18, 8], "escala": 50},
                    {"titulo": "Corte A-A", "janela": [28, -3, 50, 8], "escala": 100}]},
    ]
    auth = Authoring(Path(destino), title="exemplo D6", escala=100)
    auth.add(ops)
    auth.build()
    return Path(destino)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m1 = sub.add_parser("MEDIR", help="mede um desenho (DWG ou DXF) e grava só números")
    m1.add_argument("arquivo", type=Path)
    m1.add_argument("--saida", type=Path)
    m2 = sub.add_parser("COMPARAR", help="compara o DXF do motor com o gabarito")
    m2.add_argument("arquivo", type=Path)
    m2.add_argument("--gabarito", type=Path, required=True)
    m3 = sub.add_parser("EXEMPLO", help="gera o desenho de exemplo do motor")
    m3.add_argument("saida", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "EXEMPLO":
        print(construir_exemplo(a.saida))
        return 0
    medidas = medir(abrir(a.arquivo))
    if a.cmd == "MEDIR":
        texto = yaml.safe_dump(medidas, allow_unicode=True, sort_keys=False)
        if a.saida:
            a.saida.write_text("# só números e presença de recursos; nenhum texto do projeto\n"
                               + texto, encoding="utf-8")
            print(f"gravado: {a.saida}")
        else:
            print(texto)
        return 0
    gab = yaml.safe_load(a.gabarito.read_text(encoding="utf-8"))
    cmp = comparar(gab, medidas)
    print(relatorio(cmp))
    print(json.dumps(cmp["lacunas"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
