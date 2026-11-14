"""Biblioteca própria de blocos (D2) e pictogramas simplificados das placas."""
from __future__ import annotations

import ezdxf
import pytest

from coscip_mcp import apresentacao, biblioteca, simbologia


def test_todo_bloco_monta_no_tamanho_padrao_e_em_outros():
    for b in biblioteca.BIBLIOTECA.values():
        for largura, prof in ((None, None), (b.largura_m * 1.5, b.profundidade_m * 0.8)):
            w, d = biblioteca.tamanho(b, largura, None if b.so_diametro else prof)
            g = b.desenho(w, d)
            assert g.ops, b.id
            assert b.camada in apresentacao.CAMADAS, f"{b.id}: camada {b.camada} sem padrão"


def test_ids_acentos_e_parecidos():
    assert biblioteca.achar("fogão").id == "FOGAO"
    assert biblioteca.achar(" mesa 4 lugares ").id == "MESA_4_LUGARES"
    assert biblioteca.achar("nada") is None
    assert "FOGAO" in biblioteca.parecidos("fogao6")


def test_recipiente_de_gas_e_redondo_e_usa_so_o_diametro():
    b = biblioteca.BIBLIOTECA["BOTIJAO_P190"]
    assert biblioteca.tamanho(b, 0.7, 5.0) == (0.7, 0.7)
    assert biblioteca.tamanho(b, None, None) == (0.6, 0.6)


def test_bloco_e_definido_uma_vez_por_tamanho_e_na_camada_certa():
    doc = ezdxf.new("R2018", setup=True)
    msp = doc.modelspace()
    fogao = biblioteca.BIBLIOTECA["FOGAO"]
    n1 = biblioteca.inserir(doc, msp, fogao, 0, 0, 0, None, None, "MOBILIARIO")
    n2 = biblioteca.inserir(doc, msp, fogao, 5, 0, 90, None, None, "MOBILIARIO")
    n3 = biblioteca.inserir(doc, msp, fogao, 9, 0, 0, 2.0, 1.0, "MOBILIARIO")
    assert n1 == n2 == "MOB_FOGAO_160X90" and n3 == "MOB_FOGAO_200X100"
    assert len([b for b in doc.blocks if b.name.startswith("MOB_FOGAO")]) == 2
    assert all(i.dxf.xscale == 1.0 for i in msp.query("INSERT"))  # sem escala desigual


def test_nomes_dos_blocos_nao_sao_confundidos_com_equipamento_de_seguranca():
    """O dicionário do motor não pode reconhecer nenhum bloco da biblioteca como símbolo."""
    from coscip_mcp.workspace import dictionary

    d = dictionary()
    for b in biblioteca.BIBLIOTECA.values():
        nome = biblioteca.nome_do_bloco(b, *biblioteca.tamanho(b, None, None))
        reconhecido = [c.id for c in d.classes.values()
                       if any(p.search(nome) for p in c.block) and not c.excluded(nome)]
        assert not reconhecido, f"{nome} seria lido como {reconhecido}"


def _cores_dos_hatches(codigo: str) -> list[tuple[int, int, int]]:
    doc = ezdxf.new("R2018", setup=True)
    simbologia.emit(doc.blocks.new("T"), simbologia.achar(codigo).glyph())
    return [tuple(h.rgb) for h in doc.blocks.get("T").query("HATCH") if h.dxf.hasattr("true_color")]


def test_placas_e_simbolos_trazem_o_desenho_oficial_das_nts():
    """O desenho de cada placa (NT 2-05) e símbolo (NT 1-03) é o da tabela, vetorizado do PDF."""
    placas = [e for e in simbologia.CATALOGO.values() if e.esquematico]
    sem = {e.id for e in placas if not e.oficial}
    assert sem == {"PICTO_E-17"}  # sinalização de solo: segue as medidas da norma
    sem_simbolo = {e.id for e in simbologia.CATALOGO.values()
                   if not e.esquematico and not e.oficial}
    assert sem_simbolo <= {"PAREDE_CORTA_FOGO"}  # a parede sai da operação parede
    r = simbologia.achar("E-5").resumo()
    assert r["desenho"].startswith("oficial") and "pictograma" not in r
    assert simbologia.achar("E-17").resumo()["desenho"] == "esquemático"
    assert simbologia.achar("HIDRANTE_SIMPLES").resumo()["desenho"].startswith("oficial")


def test_reserva_a_mao_continua_disponivel_sem_o_arquivo_das_nts(monkeypatch):
    monkeypatch.setattr(simbologia, "_NT", {"placas": {}, "simbolos": {}, "fontes": {}})
    g = simbologia._placa_glyph("S-12")()  # desenho feito à mão, com o pictograma simplificado
    assert len(g.ops) >= 10 and "S-12" in simbologia.PICTOGRAMAS


def _verde(c):
    return c[1] > c[0] + 30 and c[1] > c[2] + 30


def _vermelho(c):
    return c[0] > c[1] + 100 and c[0] > c[2] + 100


@pytest.mark.parametrize("codigo,cor", [("S-12", _verde), ("S-1", _verde), ("E-5", _vermelho),
                                        ("E-2", _vermelho)])
def test_placa_oficial_leva_a_cor_do_grupo_em_cor_verdadeira(codigo, cor):
    """Placas de orientação em verde e de equipamentos em vermelho, como na tabela da NT 2-05."""
    cores = _cores_dos_hatches(codigo)
    assert cores and any(cor(c) for c in cores)


def test_placa_de_alerta_tem_fundo_transparente_e_preto():
    cores = _cores_dos_hatches("A-1")
    assert cores and not (min(cores[0]) >= 225)  # o fundo branco não vira retângulo
    assert any(max(c) < 60 for c in cores)  # a moldura e o pictograma pretos


def test_simbolo_da_nt_herda_a_cor_da_camada_da_insercao():
    doc = ezdxf.new("R2018", setup=True)
    simbologia.emit(doc.blocks.new("T"), simbologia.achar("HIDRANTE_SIMPLES").glyph())
    h = list(doc.blocks.get("T").query("HATCH"))
    assert h and all(x.dxf.color == 256 and not x.dxf.hasattr("true_color") for x in h)


def test_placa_oficial_cabe_na_caixa_unitaria_e_mantem_a_proporcao():
    for codigo, largura_maior in (("S-1", True), ("E-5", False)):
        item = simbologia._NT["placas"][codigo]
        px, py = item["proporcao"]
        assert max(px, py) == pytest.approx(1.0, abs=1e-3)
        assert (px > py) == largura_maior or px == py
