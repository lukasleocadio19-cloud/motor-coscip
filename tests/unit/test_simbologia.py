"""Catálogo da simbologia do COSCIP (NT 1-03, Anexo A, e placas da NT 2-05).

O teste central confere que o MOTOR lê de volta cada símbolo desenhado: o nome do bloco de
cada entrada tem de bater com a classe declarada no catálogo pelo dicionário
(``normative/base/simbolos.yaml``). Se o dicionário mudar e um nome deixar de bater, acusa aqui.
"""
from __future__ import annotations

import pytest

from coscip_mcp import simbologia
from coscip_mcp.autoria import Authoring
from coscip_mcp.workspace import Workspace

BLOCOS = [e for e in simbologia.CATALOGO.values() if e.uso == "bloco"]


def test_catalogo_cobre_o_anexo_a_e_as_placas():
    nt103 = [e for e in simbologia.CATALOGO.values() if not e.esquematico]
    placas = [e for e in simbologia.CATALOGO.values() if e.esquematico]
    assert len(nt103) == 104 and len(placas) == 56
    assert {e.pagina for e in nt103} == set(range(4, 13))  # Anexo A: páginas 4 a 12
    assert all(e.fonte.startswith("NT 1-03") for e in nt103)
    assert {e.id.split("_")[0] for e in placas} == {"PICTO"}
    assert {e.id[6] for e in placas} == {"P", "A", "S", "E"}


def test_ids_unicos_nomes_oficiais_em_caixa_alta_e_busca_por_codigo():
    assert len({e.id for e in simbologia.CATALOGO.values()}) == len(simbologia.CATALOGO)
    for e in simbologia.CATALOGO.values():
        if not e.esquematico:
            assert e.nome == e.nome.upper(), e.id  # como na tabela da norma
        assert e.camada and e.glyph().ops, e.id  # todo símbolo tem desenho
    assert simbologia.achar("e-5").id == "PICTO_E-5"
    assert simbologia.achar("PICTO_S-13-D").id == "PICTO_S-13-D"
    assert simbologia.achar("EXTINTOR_PQS_ABC").classe == "EXTINTOR"
    assert simbologia.achar("nao-existe") is None


@pytest.mark.parametrize("entrada", BLOCOS, ids=lambda e: e.id)
def test_motor_le_de_volta_cada_simbolo(entrada, tmp_path, monkeypatch):
    monkeypatch.setenv("COSCIP_NORMAS_DIR", str(tmp_path))  # sem NTs: só o dicionário
    arq = tmp_path / "s.dxf"
    auth = Authoring(arq)
    auth.add([{"tipo": "simbolo", "id": entrada.id, "x": 0, "y": 0}])
    auth.build()
    ws = Workspace()
    d = ws.drawings[ws.open(str(arq))["planta_id"]]
    esperado = sorted(([entrada.classe] if entrada.classe else []) + list(entrada.extra_classes))
    assert sorted(s.cls for s in d.symbols) == esperado
