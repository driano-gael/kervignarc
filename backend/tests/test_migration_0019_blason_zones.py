"""Migration 0019 — backfill des `zones` des blasons existants (E01US014).

La suite d'API et celle du repository migrent toujours une base **vide** jusqu'à `head` : le
chemin de **backfill** — des lignes `blason` déjà présentes au moment de l'`upgrade` — n'est
exercé par aucun autre test. C'est pourtant un CA explicite (« migration des blasons existants »),
et la colonne passe `NOT NULL` juste après : un backfill défaillant casserait l'upgrade sur une
base réelle alors que toute la CI resterait verte.

On insère donc des blasons à l'**ancien** schéma (sans `zones`) sur la révision `0018`, on applique
`0019`, et on relit. Mêmes conditions que pour la migration 0018 : les clés étrangères sont
désactivées côté Alembic, d'où le `tournoi_id` fictif sans tournoi parent matérialisé.
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

_ZONES_DEFAUT = ["10", "9", "8", "7", "6", "5", "4", "3", "2", "1", "M"]


def _config(url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_upgrade_backfille_les_blasons_existants(tmp_path: Path) -> None:
    """Après `0019`, tout blason préexistant porte le jeu complet d'un blason simple.

    Y compris un « Trispot 40 » : rien en base ne permet de le reconnaître comme triple (`taille`
    est une fraction de place, pas un diamètre), et on refuse de le deviner depuis le `nom`. Le
    sur-ensemble est le choix assumé — l'admin restreint à la main (cf. CA d'E01US014).
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0018_categorie_ages")

    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            for identifiant, nom, taille, capacite in [
                (1, "Monospot 60", 1.0, 1),
                (2, "Trispot 40", 0.5, 3),
            ]:
                conn.execute(
                    sa.text(
                        "INSERT INTO blason (id, tournoi_id, nom, taille, capacite) "
                        "VALUES (:id, 1, :nom, :taille, :capacite)"
                    ),
                    {"id": identifiant, "nom": nom, "taille": taille, "capacite": capacite},
                )

        command.upgrade(cfg, "0019_blason_zones")

        with engine.connect() as conn:
            lignes = conn.execute(sa.text("SELECT id, zones FROM blason ORDER BY id")).all()
        assert [int(ligne[0]) for ligne in lignes] == [1, 2]
        for ligne in lignes:
            assert json.loads(str(ligne[1])) == _ZONES_DEFAUT
    finally:
        engine.dispose()


def test_upgrade_sur_base_vide_pose_la_colonne_not_null(tmp_path: Path) -> None:
    """Sans aucune ligne à backfiller, l'upgrade passe et `zones` est bien NOT NULL."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0019_blason_zones")

    engine = sa.create_engine(url)
    try:
        with engine.connect() as conn:
            colonnes = conn.execute(sa.text("PRAGMA table_info(blason)")).all()
        zones = [colonne for colonne in colonnes if colonne[1] == "zones"]
        assert len(zones) == 1, "la colonne `zones` doit exister après 0019"
        assert zones[0][3] == 1, "`zones` doit être NOT NULL"
    finally:
        engine.dispose()


def test_downgrade_retire_la_colonne(tmp_path: Path) -> None:
    """Le downgrade retire `zones` sans toucher au reste du blason."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0019_blason_zones")

    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO blason (id, tournoi_id, nom, taille, capacite, zones) "
                    "VALUES (1, 1, 'Trispot 40', 0.5, 3, :zones)"
                ),
                {"zones": json.dumps(["10", "9", "8", "7", "6", "M"])},
            )

        command.downgrade(cfg, "0018_categorie_ages")

        with engine.connect() as conn:
            colonnes = {
                str(colonne[1]) for colonne in conn.execute(sa.text("PRAGMA table_info(blason)"))
            }
            nom = conn.execute(sa.text("SELECT nom FROM blason WHERE id = 1")).scalar_one()
        assert "zones" not in colonnes
        assert nom == "Trispot 40"
    finally:
        engine.dispose()
