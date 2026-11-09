"""Grava ``normative/projeto/anexo-iii.yaml`` com o resumo (digest) das tabelas lidas AGORA.

Rodar SOMENTE depois de conferir as tabelas no PDF oficial, célula a célula: o arquivo afirma
que a leitura atual foi conferida. Uso (no .venv):

    python scripts/projeto/registrar_conferencia_anexo_iii.py "nota da conferência" 5 6 7 ...

Sem números, registra todas as tabelas sem problema estrutural. Os cabeçalhos corrigidos das
tabelas do grupo M (células mescladas no PDF) ficam em ``COLUNAS`` abaixo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
for extra in ("apps/mcp", "packages/design", "packages/normative"):
    sys.path.insert(0, str(ROOT / extra))

from coscip_design import anexo_iii  # noqa: E402

from coscip_mcp import norms  # noqa: E402

# Cabeçalhos conferidos no PDF (p. 49, 50 e 52), onde há células mescladas.
COLUNAS: dict[int, list[dict]] = {
    25: [{"rotulo": "Extensão até 90 m"}, {"rotulo": "Extensão acima de 90 até 500 m"},
         {"rotulo": "Extensão acima de 500 até 1000 m"},
         {"rotulo": "Extensão acima de 1000 até 3000 m"},
         {"rotulo": "Extensão acima de 3000 m"}],
    26: [{"rotulo": "Tanques ou cilindros e processos — líquidos até 20 m³ ou gases até 10 m³ (b)"},
         {"rotulo": "Tanques ou cilindros e processos — líquidos acima de 20 m³ ou gases acima "
                    "de 10 m³ (b)"},
         {"rotulo": "Plataforma de carregamento e descarregamento"},
         {"rotulo": "Produtos acondicionados — líquidos até 20 m³ ou gases até 12.480 kg"},
         {"rotulo": "Produtos acondicionados — líquidos acima de 20 m³ ou gases acima de "
                    "12.480 kg"}],
    28: [{"rotulo": "M-4 (canteiro de obras) — ATC ≤ 900 m²"},
         {"rotulo": "M-4 (canteiro de obras) — 900 m² < ATC ≤ 1.500 m²"},
         {"rotulo": "M-4 (canteiro de obras) — ATC > 1.500 m²"},
         {"rotulo": "M-7 (pátio de armazenagem) — qualquer área (não coberta)",
          "observacoes": [5]}],
}


def main() -> None:
    nota = sys.argv[1]
    only = {int(a) for a in sys.argv[2:]}
    src = norms.load_base().sources[anexo_iii.DOCUMENT]
    tables = anexo_iii.parse_tables(src)
    conferidas = {}
    for num, t in sorted(tables.items()):
        if (only and num not in only) or not t.valida:
            continue
        entry: dict = {"nota": nota, "pagina": t.pagina, "digest": t.digest()}
        if num in COLUNAS:
            assert len(COLUNAS[num]) == len(t.colunas), num
            entry["colunas"] = COLUNAS[num]
        conferidas[num] = entry
    head = anexo_iii.REGISTRO.read_text(encoding="utf-8").split("schema_version:")[0]
    body = {"schema_version": "annex-iii-check/1.1", "pdf_sha256": src.pdf_sha256,
            "url": "https://www.cbmerj.rj.gov.br/wp-content/uploads/2024/05/"
                   "COSCIP_DEC_42-2018_COMPILADO.pdf",
            "conferidas": conferidas}
    anexo_iii.REGISTRO.write_text(
        head + yaml.safe_dump(body, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8", newline="\n")
    print(f"{len(conferidas)} tabelas registradas em {anexo_iii.REGISTRO}")


if __name__ == "__main__":
    main()
