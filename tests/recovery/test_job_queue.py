"""LOC-07/LOC-09: um job ativo, tentativa vencida não publica, retomada após queda."""

from __future__ import annotations

import sqlite3
from datetime import timedelta

import pytest

from coscip_jobs import JobQueue, StaleAttemptError, ensure_schema


@pytest.fixture
def conn(tmp_path):
    c = sqlite3.connect(tmp_path / "q.db", isolation_level=None)
    ensure_schema(c)
    yield c
    c.close()


def test_idempotent_enqueue(conn):
    q = JobQueue(conn)
    a = q.enqueue("IMPORT_DXF", {"f": 1}, "k1")
    assert q.enqueue("IMPORT_DXF", {"f": 1}, "k1") == a
    with pytest.raises(ValueError):
        q.enqueue("IMPORT_DXF", {"f": 2}, "k1")


def test_single_heavy_job_active(conn):
    q = JobQueue(conn)
    q.enqueue("IMPORT_DXF", {}, "k1")
    q.enqueue("IMPORT_DXF", {}, "k2")
    assert q.claim(1) is not None
    assert q.claim(2) is None


def test_stale_attempt_cannot_publish(conn):
    q = JobQueue(conn, lease=timedelta(seconds=-1))  # lease já vencido
    q.enqueue("IMPORT_DXF", {}, "k1")
    old = q.claim(1)
    assert q.recover_interrupted() == [old.job_id]
    assert q.state(old.job_id) == "QUEUED"
    new = q.claim(2)
    assert new.attempt_token != old.attempt_token
    with pytest.raises(StaleAttemptError):
        q.complete(old.job_id, old.attempt_token, "SUCCEEDED")
    q.complete(new.job_id, new.attempt_token, "SUCCEEDED")
    assert q.state(new.job_id) == "SUCCEEDED"


def test_interruption_never_becomes_success(conn):
    q = JobQueue(conn, lease=timedelta(seconds=-1))
    q.enqueue("IMPORT_DXF", {}, "k1")
    c = q.claim(1)
    q.recover_interrupted()
    assert q.state(c.job_id) != "SUCCEEDED"


def test_cancel_queued_and_running(conn):
    q = JobQueue(conn)
    a = q.enqueue("IMPORT_DXF", {}, "k1")
    b = q.enqueue("IMPORT_DXF", {}, "k2")
    c = q.claim(1)
    assert c.job_id == a
    q.request_cancel(a)
    q.request_cancel(b)
    assert q.state(a) == "CANCEL_REQUESTED"
    assert q.state(b) == "CANCELLED"
    q.complete(a, c.attempt_token, "CANCELLED")
    assert q.state(a) == "CANCELLED"
