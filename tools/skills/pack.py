"""Empacota as skills CBMERJ a partir do repositório (plano de correção, F1.1).

O repositório é a fonte das skills: ``skills/<nome>/`` tem SKILL.md, referências próprias,
scripts e agents; os textos das NTs e do Decreto vêm de ``normative/fontes`` (cópia única) e
são copiados para ``references/`` na hora de gerar o zip, com as imagens de página que eles
citam. Referências geradas (``edicoes-vigentes.md``, ``banco-de-citacoes.md``, ``itens.jsonl``)
são criadas aqui a partir do manifesto e do índice de itens (F3.3).

    python -m tools.skills.pack                 # dist/skills/<nome>.zip (vigentes)
    python -m tools.skills.pack --transicao     # também as skills antigas corrigidas

O zip tem a pasta da skill na raiz (formato aceito em claude.ai → Configurações → Skills) e é
determinístico: mesma entrada, mesmos bytes (datas fixas, ordem fixa). O envio para a conta é
manual, feito pelo usuário.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
FONTES = ROOT / "normative" / "fontes"
DIST = ROOT / "dist" / "skills"
_EPOCH = (2026, 1, 1, 0, 0, 0)


def config() -> dict[str, Any]:
    return yaml.safe_load((SKILLS / "pacotes.yaml").read_text(encoding="utf-8"))


def skill_dir(name: str) -> Path:
    for base in (SKILLS, SKILLS / "transicao"):
        if (base / name / "SKILL.md").is_file():
            return base / name
    raise FileNotFoundError(f"skill {name} não encontrada em skills/")


def source_files(patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pat in patterns:
        found = sorted(FONTES.glob(pat))
        if not found:
            raise FileNotFoundError(f"nenhuma fonte para {pat!r} em normative/fontes")
        out += [f for f in found if f not in out]
    return out


def generated_references(name: str) -> dict[str, bytes]:
    """Referências derivadas da base (não versionadas dentro de skills/)."""
    if name != "emitir-bilhete-cbmerj":
        return {}
    from tools.normas import indice_itens

    return {"references/edicoes-vigentes.md": indice_itens.edicoes_md().encode("utf-8"),
            "references/banco-de-citacoes.md": indice_itens.banco_md().encode("utf-8"),
            "references/itens.jsonl": indice_itens.jsonl().encode("utf-8")}


def files_for(name: str, patterns: list[str]) -> dict[str, bytes]:
    """Conteúdo final da skill: caminho relativo → bytes (ordenado, determinístico)."""
    from tools.normas.manifesto import media_refs

    base = skill_dir(name)
    out: dict[str, bytes] = {}
    for path in sorted(base.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            out[path.relative_to(base).as_posix()] = path.read_bytes()
    for src in source_files(patterns):
        rel = f"references/{src.name}"
        if rel in out:
            raise ValueError(f"{name}: {rel} duplicado (o texto da NT só pode vir de "
                             "normative/fontes)")
        raw = src.read_bytes()
        out[rel] = raw
        for media, _page in media_refs(raw.decode("utf-8")):
            img = FONTES / media
            if img.is_file():  # ausente fica registrada no manifesto; o texto remete ao PDF
                out[f"references/{media}"] = img.read_bytes()
    for rel, data in generated_references(name).items():
        if rel in out:
            raise ValueError(f"{name}: {rel} é gerado; não versionar em skills/")
        out[rel] = data
    return dict(sorted(out.items()))


def write_zip(name: str, files: dict[str, bytes], dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    zpath = dest / f"{name}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel, data in files.items():
            info = zipfile.ZipInfo(f"{name}/{rel}", date_time=_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)
    return zpath


def pack(transicao: bool = False, dest: Path = DIST) -> list[Path]:
    cfg = config()
    out = [write_zip(n, files_for(n, spec.get("fontes") or []), dest)
           for n, spec in cfg["vigentes"].items()]
    if transicao:
        for n in cfg["aposentar"]:
            try:
                skill_dir(n)
            except FileNotFoundError:
                continue  # o legado do grupo 5 não é mantido: só removido da conta
            out.append(write_zip(n, files_for(n, []), dest / "transicao"))
    lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(dest).as_posix()}"
             for p in out]
    (dest / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Empacota as skills CBMERJ (F1.1)")
    ap.add_argument("--transicao", action="store_true")
    ap.add_argument("--saida", type=Path, default=DIST)
    args = ap.parse_args(argv)
    for p in pack(args.transicao, args.saida):
        print(f"ok: {p} ({p.stat().st_size / 1e6:.2f} MB)")
    print("Enviar em claude.ai → Configurações → Skills (manual). Remover da conta: "
          + ", ".join(config()["aposentar"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
