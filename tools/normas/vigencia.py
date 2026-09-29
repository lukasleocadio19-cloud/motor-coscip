"""Controle de vigência da base normativa (plano de correção, F1.3).

Baixa cada PDF oficial listado no manifesto e compara o SHA-256 com o ``sha256_pdf`` capturado
(23/07/2026). **Nunca** altera a base: só relata. O workflow mensal ``vigencia.yml`` abre uma
issue por documento que mudou ("NT x-yy mudou no portal"), com o hash antigo e o novo.

    python -m tools.normas.vigencia --saida vigencia.json

Estados por fonte: ``IGUAL`` (hash confere), ``MUDOU`` (hash diferente: conferir a edição e
atualizar por pull request), ``INDISPONIVEL`` (erro de rede/HTTP: não conclui nada).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

from tools.normas.manifesto import MANIFESTO

USER_AGENT = "motor-coscip-vigencia/1.0 (+controle de vigencia; sem alteracao automatica)"


def fetch(url: str, timeout: float = 60.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — URL do manifesto
        return resp.read()


def check(fontes: list[dict[str, Any]], fetcher=fetch) -> list[dict[str, Any]]:
    out = []
    for f in fontes:
        row = {"documento": f["documento"], "arquivo": f["arquivo"], "url": f["url"],
               "sha256_capturado": f["sha256_pdf"], "data_captura": f["data_captura"]}
        try:
            data = fetcher(f["url"])
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            out.append({**row, "estado": "INDISPONIVEL", "erro": str(exc)[:300]})
            continue
        digest = hashlib.sha256(data).hexdigest()
        out.append({**row, "sha256_atual": digest, "bytes": len(data),
                    "estado": "IGUAL" if digest == f["sha256_pdf"] else "MUDOU"})
    return out


def issue_body(row: dict[str, Any]) -> str:
    return (f"O PDF oficial de **{row['documento']}** mudou no portal do CBMERJ.\n\n"
            f"- URL: {row['url']}\n- Arquivo na base: `normative/fontes/{row['arquivo']}`\n"
            f"- SHA-256 capturado em {row['data_captura']}: `{row['sha256_capturado']}`\n"
            f"- SHA-256 atual: `{row['sha256_atual']}`\n\n"
            "Nada foi alterado automaticamente. Conferir a nova edição, converter, rodar os "
            "testes (citações podem cair), regenerar o manifesto e atualizar por pull request.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Controle de vigência (F1.3)")
    ap.add_argument("--saida", type=Path, default=Path("vigencia.json"))
    args = ap.parse_args(argv)
    data = yaml.safe_load(MANIFESTO.read_text(encoding="utf-8"))
    rows = check(data["fontes"])
    for r in rows:
        if r["estado"] == "MUDOU":
            r["issue"] = {"titulo": f"{r['documento']} mudou no portal", "corpo": issue_body(r)}
    args.saida.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["estado"]] = counts.get(r["estado"], 0) + 1
    print(json.dumps(counts, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
