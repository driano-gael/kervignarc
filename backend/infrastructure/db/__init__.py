"""Adapters de persistance SQLite (guide §7, ADR-0005).

Accès **synchrones** (SQLAlchemy sync), base en **mode WAL**, migrations Alembic.
Le domaine ignore tout de SQLAlchemy : ces adapters vivent dans l'infrastructure,
derrière les ports repository (à venir en E00US009).
"""

from infrastructure.db.base import Base
from infrastructure.db.config import DEFAULT_DATABASE_URL, default_database_url
from infrastructure.db.engine import Database, create_database_engine

__all__ = [
    "DEFAULT_DATABASE_URL",
    "Base",
    "Database",
    "create_database_engine",
    "default_database_url",
]
