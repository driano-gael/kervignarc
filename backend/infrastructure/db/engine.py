"""Connexion SQLite synchrone en mode WAL (guide §7, ADR-0005).

`create_database_engine` fabrique un `Engine` SQLAlchemy **synchrone** et applique, à
**chaque connexion**, les PRAGMA SQLite requis :

- `journal_mode=WAL` : lectures concurrentes non bloquées par l'écriture en cours
  (indispensable au single-writer, cf. ADR-0005) ;
- `foreign_keys=ON` : SQLite désactive les clés étrangères par défaut ; on rétablit
  l'intégrité référentielle.

`Database` encapsule l'`Engine` et une fabrique de sessions courtes. Les repositories
(ports côté domaine, E00US009) consommeront ces sessions ; le domaine reste pur.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def _set_sqlite_pragmas(dbapi_connection: Any, connection_record: Any) -> None:
    """Applique les PRAGMA SQLite à l'ouverture d'une connexion (listener `connect`)."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def create_database_engine(database_url: str) -> Engine:
    """Crée un `Engine` SQLite synchrone, WAL activé sur chaque connexion.

    `check_same_thread=False` : les connexions traversent les threads (lectures en
    threadpool + writer unique, cf. ADR-0005) ; la sérialisation des écritures est
    assurée par la file d'écriture (E00US007), pas par le verrou de thread SQLite.
    """
    connect_args: dict[str, Any] = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    engine = create_engine(database_url, future=True, connect_args=connect_args)
    event.listen(engine, "connect", _set_sqlite_pragmas)
    return engine


class Database:
    """Adapter de connexion : `Engine` WAL + fabrique de sessions courtes."""

    def __init__(self, database_url: str) -> None:
        self._engine = create_database_engine(database_url)
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)

    @property
    def engine(self) -> Engine:
        """Moteur SQLAlchemy configuré (WAL)."""
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        """Fabrique de sessions SQLAlchemy (consommée par les repositories, E00US009)."""
        return self._session_factory
