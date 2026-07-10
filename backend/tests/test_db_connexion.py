"""Tests d'intégration de la connexion SQLite (E00US006).

Vérifie les critères d'acceptation :
- la base est ouverte en **mode WAL** (via l'adapter d'infrastructure) ;
- **Alembic** applique la **migration initiale** (baseline) sur une base neuve.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from infrastructure.db import Database, create_database_engine

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_connexion_active_le_mode_wal(tmp_path: Path) -> None:
    """Chaque connexion applique PRAGMA journal_mode=WAL et foreign_keys=ON."""
    engine = create_database_engine(_sqlite_url(tmp_path / "kervignarc.db"))
    try:
        with engine.connect() as conn:
            mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
            foreign_keys = conn.exec_driver_sql("PRAGMA foreign_keys").scalar()
    finally:
        engine.dispose()
    assert isinstance(mode, str) and mode.lower() == "wal"
    assert foreign_keys == 1


def test_database_expose_un_engine_wal(tmp_path: Path) -> None:
    """L'adapter `Database` fournit un Engine déjà configuré en WAL."""
    db = Database(_sqlite_url(tmp_path / "kervignarc.db"))
    try:
        with db.engine.connect() as conn:
            mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
    finally:
        db.engine.dispose()
    assert isinstance(mode, str) and mode.lower() == "wal"


def _alembic_config(database_url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def test_migration_initiale_s_applique(tmp_path: Path) -> None:
    """`alembic upgrade head` crée la base et l'estampille à la révision baseline."""
    url = _sqlite_url(tmp_path / "kervignarc.db")
    command.upgrade(_alembic_config(url), "head")

    engine = create_database_engine(url)
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    finally:
        engine.dispose()
    assert version == "0001_initiale"
