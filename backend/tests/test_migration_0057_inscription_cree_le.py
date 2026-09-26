"""Migration 0057 — la date d'inscription, sans date inventée pour l'existant (E17US012).

La suite d'API migre une base **vide** (`base_migree.py`) : ce qui distingue cette migration de
`0027` — une inscription **déjà là** reçoit `NULL`, pas l'instant de la migration — n'y serait
exercé sur aucune ligne. Test de non-régression (règle 9) : l'oracle est la docstring de `0057`.

Clés étrangères désactivées côté Alembic (`env.py`) : identifiants parents fictifs, comme les
autres tests de migration.
"""

from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_AVANT = "0056_ancrage_par_identite"
_APRES = "0057_inscription_cree_le"


def _config(url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _preparer(tmp_path: Path) -> tuple[Config, sa.Engine]:
    """Base migrée jusqu'à `0056`, avec une inscription **payée** et une **non payée**."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    engine = sa.create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO inscription (id, archer_id, depart_id, paye) "
                "VALUES (1, 10, 20, 0), (2, 11, 20, 1)"
            )
        )
    return cfg, engine


def _inscriptions(engine: sa.Engine) -> list[tuple[int, int, int, bool]]:
    with engine.connect() as conn:
        lignes = conn.execute(
            sa.text("SELECT id, archer_id, depart_id, paye FROM inscription ORDER BY id")
        ).all()
    return [(int(i), int(a), int(d), bool(p)) for i, a, d, p in lignes]


def test_upgrade_laisse_les_inscriptions_existantes_sans_date(tmp_path: Path) -> None:
    """Aucune date inventée : un défaut `CURRENT_TIMESTAMP` aurait daté l'existant du jour J."""
    cfg, engine = _preparer(tmp_path)
    try:
        command.upgrade(cfg, _APRES)
        with engine.connect() as conn:
            dates = conn.execute(sa.text("SELECT cree_le FROM inscription ORDER BY id")).all()
        assert [ligne[0] for ligne in dates] == [None, None]
    finally:
        engine.dispose()


def test_l_aller_retour_restitue_les_inscriptions(tmp_path: Path) -> None:
    """`downgrade` retire la colonne et garde chaque inscription, `paye` compris."""
    cfg, engine = _preparer(tmp_path)
    try:
        avant = _inscriptions(engine)
        command.upgrade(cfg, _APRES)
        command.downgrade(cfg, _AVANT)
        assert _inscriptions(engine) == avant
        colonnes = {c["name"] for c in sa.inspect(engine).get_columns("inscription")}
        assert "cree_le" not in colonnes
    finally:
        engine.dispose()
