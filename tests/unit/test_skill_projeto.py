"""Skill ``projetar-pscip-cbmerj``: os arquivos existem e não divergem do motor."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "projetar-pscip-cbmerj"


def test_skill_tem_frontmatter_e_referencias():
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert texto.startswith("---\nname: projetar-pscip-cbmerj\ndescription: ")
    for ref in re.findall(r"`(references/[a-z\-]+\.md)`", texto):
        assert (SKILL / ref).exists(), ref
    assert {p.name for p in (SKILL / "references").glob("*.md")} == {
        "perguntas.md", "medidas.md", "modelo-projeto.md", "entregaveis.md"}


def test_ferramentas_citadas_na_skill_existem_no_servidor():
    from coscip_mcp.server import Server

    tools = set(Server().tools)
    texto = "".join(p.read_text(encoding="utf-8") for p in SKILL.rglob("*.md"))
    citadas = set(re.findall(r"`([a-z]+_[a-z_]+)`", texto)) - {"como_tratar", "building_floors",
                                                               "building_area_m2",
                                                               "building_height_m",
                                                               "single_occupancy",
                                                               "dados_da_edificacao",
                                                               "corta_fogo", "corta_fogo_min",
                                                               "excecoes_que_o_motor_nao_aplica"}
    assert citadas <= tools, citadas - tools


def test_referencia_de_medidas_esta_em_dia_com_o_yaml():
    spec = importlib.util.spec_from_file_location(
        "gerar", ROOT / "scripts" / "projeto" / "gerar_referencia_medidas.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    atual = (SKILL / "references" / "medidas.md").read_text(encoding="utf-8")
    assert atual == mod.render(), "rode scripts/projeto/gerar_referencia_medidas.py"
