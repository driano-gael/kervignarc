"""Adapters de persistance SQLite (guide §7, ADR-0005).

Accès **synchrones** (SQLAlchemy sync), base en **mode WAL**, migrations Alembic.
Le domaine ignore tout de SQLAlchemy : ces adapters vivent dans l'infrastructure,
derrière les ports repository (`domain.ports`), dont `TournoiRepositorySQL` est la
première implémentation (E00US009).
"""

from infrastructure.db.base import Base
from infrastructure.db.config import DEFAULT_DATABASE_URL, default_database_url
from infrastructure.db.engine import Database, create_database_engine
from infrastructure.db.models import TournoiORM
from infrastructure.db.repositories import TournoiRepositorySQL
from infrastructure.db.write_queue import (
    PostCommitListener,
    WriteCommand,
    WriteQueue,
    WriteQueueClosedError,
)

__all__ = [
    "DEFAULT_DATABASE_URL",
    "Base",
    "Database",
    "PostCommitListener",
    "TournoiORM",
    "TournoiRepositorySQL",
    "WriteCommand",
    "WriteQueue",
    "WriteQueueClosedError",
    "create_database_engine",
    "default_database_url",
]
