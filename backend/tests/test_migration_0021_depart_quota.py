"""Migration 0021 — ajout de `quota` aux départs (E02US006).

La suite d'API et celle du repository migrent toujours une base **vide** jusqu'à `head` : le chemin
d'un départ **déjà présent** au moment de l'`upgrade` n'est exercé par aucun autre test.
Contrairement à `0019`, il n'y a **pas de backfill** — un départ existant doit ressortir avec
`quota = NULL` (illimité), défaut sémantiquement correct. On le vérifie ici, avec la réversibilité.

On insère un départ à l'**ancien** schéma (sans `quota`) sur la révision `0019`, on applique `0021`
(qui inclut `0020`), et on relit. Mêmes conditions que les migrations voisines : les clés étrangères
sont désactivées côté Alembic, d'où le `tournoi_id` fictif sans tournoi parent matérialisé.
"""

from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _config(url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_upgrade_pose_quota_null_sur_les_departs_existants(tmp_path: Path) -> None:
    """Après `0021`, un départ préexistant porte `quota = NULL` (sans plafond) — pas de backfill."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0019_blason_zones")

    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO depart (id, tournoi_id, numero, tarif_centimes) "
                    "VALUES (1, 1, 1, 810)"
                )
            )

        command.upgrade(cfg, "0021_depart_quota")

        with engine.connect() as conn:
            quota = conn.execute(sa.text("SELECT quota FROM depart WHERE id = 1")).scalar_one()
        assert quota is None
    finally:
        engine.dispose()


def test_upgrade_sur_base_vide_pose_une_colonne_nullable(tmp_path: Path) -> None:
    """La colonne `quota` existe après `0021` et reste **nullable** (un plafond absent est ok)."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0021_depart_quota")

    engine = sa.create_engine(url)
    try:
        with engine.connect() as conn:
            colonnes = conn.execute(sa.text("PRAGMA table_info(depart)")).all()
        quota = [colonne for colonne in colonnes if colonne[1] == "quota"]
        assert len(quota) == 1, "la colonne `quota` doit exister après 0020"
        assert quota[0][3] == 0, "`quota` doit être nullable (NOT NULL = 0)"
    finally:
        engine.dispose()


def test_downgrade_retire_la_colonne(tmp_path: Path) -> None:
    """Le downgrade retire `quota` sans toucher au reste du départ."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0021_depart_quota")

    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO depart (id, tournoi_id, numero, tarif_centimes, quota) "
                    "VALUES (1, 1, 1, 810, 20)"
                )
            )

        command.downgrade(cfg, "0019_blason_zones")

        with engine.connect() as conn:
            colonnes = {
                str(colonne[1]) for colonne in conn.execute(sa.text("PRAGMA table_info(depart)"))
            }
            tarif = conn.execute(
                sa.text("SELECT tarif_centimes FROM depart WHERE id = 1")
            ).scalar_one()
        assert "quota" not in colonnes
        assert tarif == 810
    finally:
        engine.dispose()
