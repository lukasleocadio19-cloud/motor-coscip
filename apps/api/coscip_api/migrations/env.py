from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool

from coscip_api.models import Base

config = context.config
target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):  # noqa: ANN001
    # job_queue é gerida por coscip_jobs (SQL próprio), fora do ORM.
    return not (type_ == "table" and name == "job_queue") and not (
        type_ == "index" and name == "ix_job_queue_state")

if not config.get_main_option("sqlalchemy.url"):
    # Linha de comando: usa a pasta de dados local (COSCIP_DATA_DIR).
    from coscip_api.config import get_settings

    settings = get_settings()
    (settings.data_dir / "database").mkdir(parents=True, exist_ok=True)
    config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"),
                      target_metadata=target_metadata, literal_binds=True,
                      render_as_batch=True, include_object=include_object)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}),
                                     prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        # Sem este commit, o autobegin do PRAGMA faz o Alembic não gravar alembic_version.
        connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=True,  # SQLite exige batch para ALTER
                          include_object=include_object)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
