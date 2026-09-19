from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from coscip_api.config import Settings
from coscip_api.models import Organization, User
from coscip_storage import DataLayout, LocalFileStorage


@dataclass
class AppState:
    settings: Settings
    layout: DataLayout
    storage: LocalFileStorage
    session_factory: sessionmaker[Session]
    tenant_id: str
    operator_id: str


def state(request: Request) -> AppState:
    return request.app.state.coscip


def db(request: Request) -> Iterator[Session]:
    with state(request).session_factory() as s:
        yield s


def ensure_local_identity(factory: sessionmaker[Session], os_account: str) -> tuple[str, str]:
    """Organização e operador locais com IDs estáveis, criados na primeira execução.

    O servidor define o contexto; nenhum tenant_id enviado pelo cliente o altera.
    """
    with factory() as s, s.begin():
        org = s.scalars(select(Organization).limit(1)).first()
        if org is None:
            org = Organization(name="Organização local")
            s.add(org)
            s.flush()
        user = s.scalars(select(User).where(User.tenant_id == org.id).limit(1)).first()
        if user is None:
            user = User(tenant_id=org.id, name=os_account, os_account=os_account)
            s.add(user)
            s.flush()
        return org.id, user.id
