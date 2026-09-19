from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS job_queue (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload TEXT NOT NULL,
    state TEXT NOT NULL,
    attempt_token TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    lease_until TEXT,
    worker_pid INTEGER,
    error_code TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_job_queue_state ON job_queue(state, created_at);
"""


class StaleAttemptError(RuntimeError):
    """Tentativa vencida ou substituída tentou publicar."""


@dataclass(frozen=True)
class Claim:
    job_id: str
    kind: str
    payload: dict[str, Any]
    attempt_token: str
    lease_until: datetime


def _now() -> datetime:
    return datetime.now(UTC)


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Usado por testes; em produção a tabela vem da migração Alembic."""
    conn.executescript(SCHEMA)


class JobQueue:
    """Opera sobre uma conexão SQLite já configurada (FK, WAL, synchronous=FULL).

    ``enqueue`` não faz commit: chamado com a conexão da transação de metadados,
    a intenção de job é persistida atomicamente com eles.
    """

    def __init__(self, conn: sqlite3.Connection, lease: timedelta = timedelta(minutes=2)) -> None:
        self.conn = conn
        self.lease = lease

    def enqueue(self, kind: str, payload: dict[str, Any], idempotency_key: str) -> str:
        """Idempotente: mesma chave devolve o mesmo job."""
        row = self.conn.execute(
            "SELECT id, kind, payload FROM job_queue WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        body = json.dumps(payload, sort_keys=True)
        if row:
            if row[1] != kind or row[2] != body:
                raise ValueError("chave de idempotência reutilizada com outro corpo")
            return row[0]
        job_id = str(uuid.uuid4())
        ts = _now().isoformat()
        self.conn.execute(
            "INSERT INTO job_queue (id, kind, idempotency_key, payload, state, created_at, "
            "updated_at) VALUES (?, ?, ?, ?, 'QUEUED', ?, ?)",
            (job_id, kind, idempotency_key, body, ts, ts),
        )
        return job_id

    def claim(self, worker_pid: int) -> Claim | None:
        """Reclama o próximo job em transação curta. Só um job pesado ativo."""
        with self.conn:
            self.conn.execute("BEGIN IMMEDIATE")
            active = self.conn.execute(
                "SELECT 1 FROM job_queue WHERE state = 'RUNNING' LIMIT 1"
            ).fetchone()
            if active:
                return None
            row = self.conn.execute(
                "SELECT id, kind, payload FROM job_queue WHERE state = 'QUEUED' "
                "ORDER BY created_at LIMIT 1"
            ).fetchone()
            if not row:
                return None
            token = uuid.uuid4().hex
            lease_until = _now() + self.lease
            self.conn.execute(
                "UPDATE job_queue SET state='RUNNING', attempt_token=?, attempts=attempts+1, "
                "lease_until=?, worker_pid=?, updated_at=? WHERE id=?",
                (token, lease_until.isoformat(), worker_pid, _now().isoformat(), row[0]),
            )
        return Claim(row[0], row[1], json.loads(row[2]), token, lease_until)

    def heartbeat(self, job_id: str, token: str) -> None:
        cur = self.conn.execute(
            "UPDATE job_queue SET lease_until=?, updated_at=? "
            "WHERE id=? AND attempt_token=? AND state='RUNNING'",
            ((_now() + self.lease).isoformat(), _now().isoformat(), job_id, token),
        )
        if cur.rowcount != 1:
            raise StaleAttemptError(job_id)

    def complete(self, job_id: str, token: str, state: str, error_code: str | None = None) -> None:
        """Publicação aceita apenas da tentativa vigente."""
        if state not in {"SUCCEEDED", "PARTIAL", "WAITING_INPUT", "FAILED", "CANCELLED"}:
            raise ValueError(state)
        with self.conn:
            cur = self.conn.execute(
                "UPDATE job_queue SET state=?, error_code=?, lease_until=NULL, updated_at=? "
                "WHERE id=? AND attempt_token=? AND state IN ('RUNNING','CANCEL_REQUESTED')",
                (state, error_code, _now().isoformat(), job_id, token),
            )
            if cur.rowcount != 1:
                raise StaleAttemptError(job_id)

    def request_cancel(self, job_id: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE job_queue SET state = CASE state WHEN 'QUEUED' THEN 'CANCELLED' "
                "ELSE 'CANCEL_REQUESTED' END, updated_at=? "
                "WHERE id=? AND state IN ('QUEUED','RUNNING')",
                (_now().isoformat(), job_id),
            )

    def recover_interrupted(self) -> list[str]:
        """Na inicialização: tentativas com lease vencido voltam à fila com novo token.

        Interrupção nunca é marcada como sucesso. O worker antigo deve ser encerrado
        pelo supervisor antes desta chamada.
        """
        now = _now().isoformat()
        with self.conn:
            rows = self.conn.execute(
                "SELECT id FROM job_queue WHERE state IN ('RUNNING','CANCEL_REQUESTED') "
                "AND (lease_until IS NULL OR lease_until < ?)",
                (now,),
            ).fetchall()
            for (job_id,) in rows:
                self.conn.execute(
                    "UPDATE job_queue SET state = CASE state WHEN 'CANCEL_REQUESTED' "
                    "THEN 'CANCELLED' ELSE 'QUEUED' END, attempt_token=NULL, "
                    "lease_until=NULL, worker_pid=NULL, error_code='WORKER_INTERRUPTED', "
                    "updated_at=? WHERE id=?",
                    (now, job_id),
                )
        return [r[0] for r in rows]

    def state(self, job_id: str) -> str | None:
        row = self.conn.execute("SELECT state FROM job_queue WHERE id=?", (job_id,)).fetchone()
        return row[0] if row else None
