"""Tests de l'application programmatique des migrations (E11US001, CA « base au 1er lancement »).

Tests **après implémentation** (câblage, pas d'oracle). On prouve le comportement attendu du
1er lancement : `appliquer_migrations` sur un fichier SQLite **absent** le crée et applique la
**suite complète** des révisions jusqu'à `head` — puis qu'un 2ᵉ appel est idempotent.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from infrastructure.db import create_database_engine
from infrastructure.db.migrate import appliquer_migrations

_MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


def _tables(url: str) -> set[str]:
    engine = create_database_engine(url)
    try:
        with engine.connect() as conn:
            lignes = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            return {str(nom) for (nom,) in lignes}
    finally:
        engine.dispose()


def test_cree_la_base_et_applique_tout_le_schema(tmp_path: Path) -> None:
    """Fichier absent → créé, schéma complet appliqué (tables réelles + estampille Alembic)."""
    fichier = tmp_path / "kervignarc.db"
    assert not fichier.exists()
    url = f"sqlite:///{fichier.as_posix()}"

    appliquer_migrations(_MIGRATIONS, url=url)

    assert fichier.exists()
    tables = _tables(url)
    # Un échantillon de tables réelles du schéma + la table de suivi Alembic.
    assert {"alembic_version", "tournoi", "club", "depart"} <= tables


def test_est_idempotent(tmp_path: Path) -> None:
    """Un 2ᵉ passage sur une base déjà à `head` ne lève pas et ne casse rien."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    appliquer_migrations(_MIGRATIONS, url=url)
    appliquer_migrations(_MIGRATIONS, url=url)  # ne doit pas lever
    assert "alembic_version" in _tables(url)
