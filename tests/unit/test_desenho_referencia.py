"""D6: medidor de desenho profissional e lista de lacunas do motor."""
from __future__ import annotations

from pathlib import Path

import ezdxf
import pytest
import yaml

from tools.validacao import desenho_referencia as dr

ROOT = Path(__file__).resolve().parents[2]
GABARITO = ROOT / "docs" / "validacao" / "desenho-referencia.yaml"

# Recursos do desenho profissional de referência que o motor AINDA não produz. Quando um deles
# passar a ser produzido, este teste falha: tire o item daqui e registre no §9 da arquitetura.
LACUNAS_CONHECIDAS = {"isometrico", "multileaders_ou_leaders"}


def folhas_e_numeros(x, caminho=""):
    """Todas as folhas do YAML (valores) com o caminho, para checar que só há números."""
    if isinstance(x, dict):
        for k, v in x.items():
            yield from folhas_e_numeros(v, f"{caminho}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from folhas_e_numeros(v, f"{caminho}[{i}]")
    else:
        yield caminho, x


def test_gabarito_so_leva_numeros_e_presencas_de_recursos():
    gab = yaml.safe_load(GABARITO.read_text(encoding="utf-8"))
    for caminho, v in folhas_e_numeros(gab):
        assert isinstance(v, (int, bool)), f"{caminho}={v!r}: o gabarito não pode ter texto"
    assert set(gab["recursos"]) == set(dr.recursos(gab))
    assert gab["layouts"]["viewports"] >= 1 and gab["recursos"]["folha_em_paper_space"]


@pytest.fixture(scope="module")
def motor(tmp_path_factory):
    destino = tmp_path_factory.mktemp("d6") / "exemplo.dxf"
    dr.construir_exemplo(destino)
    return dr.medir(ezdxf.readfile(destino)), destino


def test_exemplo_do_motor_cobre_os_recursos_que_ja_existem(motor):
    medidas, _ = motor
    r = medidas["recursos"]
    for k in ("folha_em_paper_space", "varias_escalas_na_folha", "camadas_com_espessura",
              "camadas_coloridas", "estilos_de_cota_por_escala", "cotas_nativas",
              "janelas_em_planta", "etiquetas_de_vao", "blocos_distintos_em_uso",
              "chamadas_de_placa", "hachuras", "marca_de_corte", "cortes", "fachadas",
              "quadro_resumo", "quadro_de_areas", "selo_na_folha", "notas_de_projeto", "legenda"):
        assert r[k], k
    assert medidas["layouts"]["escalas"] == [50, 100]


def test_lacunas_do_motor_sao_as_conhecidas(motor):
    medidas, _ = motor
    gab = yaml.safe_load(GABARITO.read_text(encoding="utf-8"))
    cmp = dr.comparar(gab, medidas)
    assert set(cmp["lacunas"]) == LACUNAS_CONHECIDAS, (
        "mudou o que o motor produz: atualize LACUNAS_CONHECIDAS e docs/arquitetura-projeto.md §9")
    assert cmp["lado_a_lado"]["escalas"]["motor"] == [50, 100]
    assert "Lacunas" in dr.relatorio(cmp)


def test_medidor_nao_vaza_texto_do_desenho(motor):
    medidas, _ = motor
    for caminho, v in folhas_e_numeros(medidas):
        assert isinstance(v, (int, bool)), f"{caminho}={v!r}"


def test_escala_da_viewport_vem_da_razao_vista_papel():
    assert dr._escala_padrao(99.2) == 100 and dr._escala_padrao(250) == 250
    assert dr._escala_padrao(333) == 333  # fora dos padrões: devolve o valor
