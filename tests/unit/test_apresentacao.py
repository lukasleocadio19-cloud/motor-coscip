"""Padrão de apresentação do desenho (frente D1): tabela de camadas, escalas e formatação."""
from __future__ import annotations

import ezdxf
import pytest

from coscip_mcp import apresentacao as ap

# espessuras de linha válidas no DXF (centésimos de mm)
LINEWEIGHTS_VALIDOS = {0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53, 60, 70, 80, 90, 100,
                       106, 120, 140, 158, 200, 211}


def test_tabela_de_camadas_so_usa_espessuras_e_cores_validas():
    for nome, p in ap.CAMADAS.items():
        assert p.espessura in LINEWEIGHTS_VALIDOS, nome
        assert 1 <= p.cor <= 255, nome
        assert p.descricao, f"{nome}: descreva a camada"


def test_paredes_sao_as_linhas_mais_grossas():
    paredes = [p.espessura for n, p in ap.CAMADAS.items() if n.startswith("PAREDE")]
    outras = [p.espessura for n, p in ap.CAMADAS.items() if not n.startswith("PAREDE")]
    assert min(paredes) >= max(outras)


def test_camadas_dos_simbolos_do_catalogo_estao_na_tabela():
    from coscip_mcp import simbologia

    faltam = {e.camada for e in simbologia.CATALOGO.values()} - set(ap.CAMADAS)
    assert not faltam, f"camadas do catálogo sem padrão de cor e espessura: {sorted(faltam)}"


def test_altura_do_texto_acompanha_a_escala():
    assert ap.altura_texto(100) == 0.25
    assert ap.altura_texto(50) == 0.125
    assert ap.altura_texto(200) == 0.5
    assert ap.altura_texto(100, ap.TEXTO_PEQUENO_MM) == 0.18
    assert ap.fator(100) == 1.0 and ap.fator(50) == 0.5


@pytest.mark.parametrize("ruim", [0, 5, 5000, 100.5, "100", True, None])
def test_escala_invalida_e_recusada(ruim):
    with pytest.raises(ValueError):
        ap.fator(ruim)


def test_formatacao_em_metros_e_em_centimetros():
    assert ap.medida(24) == "24,00"
    assert ap.medida(1.955) in ("1,95", "1,96")
    assert ap.rotulo_porta(0.8, 2.1) == "80x210"
    assert ap.rotulo_janela(1.5, 1.2, 0.9) == "150x120/90"
    assert ap.rotulo_janela(1.5, 1.2, 0.0) == "150x120/0"


def test_criar_camada_aplica_o_padrao_e_nao_duplica():
    doc = ezdxf.new("R2018", setup=True)
    ap.configurar(doc, 100)
    ap.criar_camada(doc, "PAREDE")
    ap.criar_camada(doc, "PAREDE")
    ap.criar_camada(doc, "INC_EXT")
    ap.criar_camada(doc, "CORTES")
    ap.criar_camada(doc, "MINHA_CAMADA")
    paredes = [layer for layer in doc.layers if layer.dxf.name == "PAREDE"]
    assert len(paredes) == 1
    assert (paredes[0].dxf.color, paredes[0].dxf.lineweight) == (7, 50)
    assert doc.layers.get("INC_EXT").dxf.color == 1
    assert doc.layers.get("CORTES").dxf.linetype == "DASHDOT"
    outra = doc.layers.get("MINHA_CAMADA")
    assert (outra.dxf.color, outra.dxf.lineweight) == (7, 25)


def test_configurar_define_unidade_estilos_e_dimstyle_da_escala():
    doc = ezdxf.new("R2018", setup=True)
    ap.configurar(doc, 50)
    assert doc.header["$INSUNITS"] == 6
    assert doc.header["$LWDISPLAY"] == 1
    assert ap.ESTILO_TEXTO in doc.styles and ap.ESTILO_AMBIENTE in doc.styles
    ds = doc.dimstyles.get("COSCIP-50")
    assert ds.dxf.dimtxt == 0.125 and ds.dxf.dimdec == 2 and ds.dxf.dimdsep == ord(",")
    assert ds.dxf.dimtsz > 0  # tique arquitetônico, não seta
    ap.configurar(doc, 50)  # repetir não duplica nem falha
    assert [d.dxf.name for d in doc.dimstyles].count("COSCIP-50") == 1
