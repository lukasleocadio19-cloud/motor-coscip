"""CLI de manutenção (modo launcher, sem a API escrevendo na base).

    python -m coscip_api.cli set-backup-destination <pasta> [--label NOME]
    python -m coscip_api.cli backup
    python -m coscip_api.cli verify-backup <pasta-do-backup>
    python -m coscip_api.cli restore <pasta-do-backup> <pasta-destino-vazia>
    python -m coscip_api.cli make-fixtures <pasta>
    python -m coscip_api.cli normative-import-sources <pasta-com-.md>
    python -m coscip_api.cli normative-import-package [<pasta-do-pacote>]
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from coscip_api.backup import create_backup, restore_backup, verify_backup
from coscip_api.config import get_settings
from coscip_api.db import make_engine, make_session_factory, migrate, write_tx
from coscip_api.models import BackupRecord, LocalSetting
from coscip_storage import DataLayout


def _factory(*, run_migrations: bool = True):
    s = get_settings()
    DataLayout(s.data_dir).ensure()
    if run_migrations:
        migrate(s.database_url)
    return make_session_factory(make_engine(s.database_url))


def cmd_set_dest(args: argparse.Namespace) -> int:
    dest = Path(args.path).resolve()
    data = get_settings().data_dir.resolve()
    if dest == data or data in dest.parents:
        print("Destino não pode ficar dentro da pasta de dados.", file=sys.stderr)
        return 1
    if dest.drive and dest.drive.lower() == data.drive.lower():
        print("[aviso] Mesmo disco da pasta de dados: não protege contra falha física.")
    dest.mkdir(parents=True, exist_ok=True)
    with write_tx(_factory()) as s:
        for key, value in (("backup_destination_path", str(dest)),
                           ("backup_destination_label", args.label or dest.name)):
            row = s.get(LocalSetting, key)
            if row:
                row.value = value
            else:
                s.add(LocalSetting(key=key, value=value))
    print(f"Destino de backup cadastrado: {dest}")
    return 0


def cmd_backup(_: argparse.Namespace) -> int:
    # Backup antes de atualizar: nunca migrar a base antes de copiá-la.
    factory = _factory(run_migrations=False)
    with factory() as s:
        row = s.get(LocalSetting, "backup_destination_path")
        label_row = s.get(LocalSetting, "backup_destination_label")
    if row is None:
        print("Cadastre o destino com set-backup-destination.", file=sys.stderr)
        return 1
    out = create_backup(DataLayout(get_settings().data_dir), Path(row.value))
    with write_tx(factory) as s:
        s.add(BackupRecord(manifest_path=str(out / "manifest.json"),
                           destination_label=label_row.value if label_row else "",
                           state="VERIFIED", verified_at=datetime.now(UTC)))
    print(f"Backup verificado: {out}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    problems = verify_backup(Path(args.path))
    for p in problems:
        print(f"- {p}")
    print("Íntegro." if not problems else "Backup com problemas.")
    return 1 if problems else 0


def cmd_restore(args: argparse.Namespace) -> int:
    layout = restore_backup(Path(args.backup), Path(args.target))
    print(f"Restaurado em {layout.root}. Abra com COSCIP_DATA_DIR={layout.root} para conferir "
          "projetos e relatórios antes de substituir a base ativa.")
    return 0


def cmd_fixtures(args: argparse.Namespace) -> int:
    from coscip_cad.synthetic import make_simple_floor

    out = Path(args.path)
    out.mkdir(parents=True, exist_ok=True)
    make_simple_floor(out / "sala_metros.dxf")
    make_simple_floor(out / "sala_milimetros.dxf", insunits=4, scale=1000)
    make_simple_floor(out / "sala_sem_unidade.dxf", insunits=0)
    print(f"DXFs sintéticos gerados em {out}")
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    import json

    from coscip_api.benchmark import run_corpus

    folder = Path(args.path)
    rows = run_corpus(folder)
    out = Path(args.out) if args.out else folder / "benchmark.json"
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    for r in rows:
        status = "ERRO" if "error" in r else ("ok" if r["within_profile"] else "fora do perfil")
        print(f"{r['file']}: {r['size_mb']} MB, {r['seconds']} s, pico {r['peak_rss_mb']} MB "
              f"— {status}")
    print(f"Relatório: {out}")
    return 0


def _normative_ctx():
    import getpass

    from coscip_api.deps import ensure_local_identity
    from coscip_storage import LocalFileStorage

    factory = _factory()
    _, operator_id = ensure_local_identity(factory, getpass.getuser())
    return factory, LocalFileStorage(DataLayout(get_settings().data_dir).root), operator_id


def cmd_normative_sources(args: argparse.Namespace) -> int:
    """Ingere todos os .md da pasta (NTs e decreto); o mesmo texto não é duplicado."""
    from coscip_api.normative_base import ingest_sources

    files = sorted(Path(args.path).glob("*.md"))
    if not files:
        print("Nenhum .md na pasta.", file=sys.stderr)
        return 1
    factory, storage, operator_id = _normative_ctx()
    out = ingest_sources(factory, storage, [(f.name, f.read_bytes()) for f in files],
                         operator_id)
    for r in out:
        print(f"{r['status']:<15} {r.get('document', '—'):<18} {r['file']}"
              + (f"  ({r['problem']})" if r.get("problem") else ""))
    rejected = sum(r["status"] == "REJECTED" for r in out)
    print(f"{len(out) - rejected} fonte(s) na base, {rejected} recusada(s).")
    return 1 if rejected else 0


def cmd_normative_package(args: argparse.Namespace) -> int:
    from coscip_api.normative_base import NormativeError, import_package

    factory, storage, operator_id = _normative_ctx()
    try:
        r = import_package(factory, storage, Path(args.path) if args.path else None,
                           actor_id=operator_id)
    except NormativeError as exc:
        print(f"Pacote recusado: {exc}", file=sys.stderr)
        for d in exc.details:
            print(f"- {d}", file=sys.stderr)
        return 1
    print(f"{r['status']}: {r['name']} ({r['rules']} regras) — {r['id']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="coscip")
    sub = ap.add_subparsers(required=True)
    p = sub.add_parser("set-backup-destination")
    p.add_argument("path")
    p.add_argument("--label")
    p.set_defaults(fn=cmd_set_dest)
    sub.add_parser("backup").set_defaults(fn=cmd_backup)
    p = sub.add_parser("verify-backup")
    p.add_argument("path")
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("restore")
    p.add_argument("backup")
    p.add_argument("target")
    p.set_defaults(fn=cmd_restore)
    p = sub.add_parser("make-fixtures")
    p.add_argument("path")
    p.set_defaults(fn=cmd_fixtures)
    p = sub.add_parser("benchmark", help="roda o worker em cada DXF da pasta e mede recursos")
    p.add_argument("path")
    p.add_argument("--out")
    p.set_defaults(fn=cmd_benchmark)
    p = sub.add_parser("normative-import-sources", help="ingere os textos .md das NTs")
    p.add_argument("path")
    p.set_defaults(fn=cmd_normative_sources)
    p = sub.add_parser("normative-import-package", help="importa o pacote de regras")
    p.add_argument("path", nargs="?")
    p.set_defaults(fn=cmd_normative_package)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
