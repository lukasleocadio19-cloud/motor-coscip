"""Fila persistente no SQLite e executor local (plano §7, LOC-07..LOC-09).

- A intenção de job é gravada na MESMA transação dos metadados (sem broker externo).
- O supervisor reclama o job com token de tentativa e lease.
- Só a tentativa vigente pode publicar resultado.
"""

from coscip_jobs.queue import SCHEMA, Claim, JobQueue, StaleAttemptError, ensure_schema

__all__ = ["SCHEMA", "Claim", "JobQueue", "StaleAttemptError", "ensure_schema"]
