"""Aplicação FastAPI: API /v1 e interface estática na mesma origem."""

from __future__ import annotations

import getpass
import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from coscip_api import __version__
from coscip_api.config import Settings, get_settings
from coscip_api.db import make_engine, make_session_factory, migrate
from coscip_api.deps import AppState, ensure_local_identity
from coscip_api.errors import ApiError, api_error_handler
from coscip_api.routers import (
    analyses,
    backups,
    drawings,
    executions,
    geometry,
    local,
    normative,
    plant_analyses,
    preparation,
    preparation_reports,
    projects,
    unit_reviews,
)
from coscip_api.security import LocalBoundaryMiddleware, SessionStore, allowed_for
from coscip_storage import DataLayout, LocalFileStorage

STATIC_DIR = Path(__file__).parent / "static"


def _logging(layout: DataLayout) -> None:
    # Logs rotativos, sem conteúdo de projetos, tokens ou chaves.
    handler = RotatingFileHandler(layout.logs / "coscip.log", maxBytes=5_000_000,
                                  backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger("coscip")
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def create_app(settings: Settings | None = None, *, start_supervisor: bool = True) -> FastAPI:
    settings = settings or get_settings()
    layout = DataLayout(settings.data_dir)
    layout.ensure()
    _logging(layout)
    migrate(settings.database_url)

    engine = make_engine(settings.database_url)
    factory = make_session_factory(engine)
    tenant_id, operator_id = ensure_local_identity(factory, getpass.getuser())
    storage = LocalFileStorage(layout.root)
    app_state = AppState(settings, layout, storage, factory, tenant_id, operator_id)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        sup = None
        if start_supervisor:
            from coscip_api.supervisor import Supervisor

            sup = Supervisor(settings, layout, storage, factory, tenant_id)
            sup.start()
        yield
        if sup:
            sup.stop()
        engine.dispose()

    app = FastAPI(title="Motor CAD/COSCIP — API local", version=__version__,
                  lifespan=lifespan, docs_url="/v1/docs", openapi_url="/v1/openapi.json")
    app.state.coscip = app_state
    app.state.sessions = SessionStore(launch_token=settings.launch_token)

    hosts, origins = allowed_for(settings.port, settings.dev_origin)
    app.add_middleware(LocalBoundaryMiddleware, allowed_hosts=hosts, allowed_origins=origins,
                       sessions=app.state.sessions)
    app.add_exception_handler(ApiError, api_error_handler)

    for r in (local.router, projects.router, drawings.router, executions.router,
              analyses.router, backups.router, unit_reviews.router,
              preparation.router, geometry.router, preparation_reports.router,
              normative.router, plant_analyses.router):
        app.include_router(r, prefix="/v1")

    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="web")
    return app
