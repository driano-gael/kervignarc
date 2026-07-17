"""Migration 0020 — backfill de `hauteur_cm` depuis `ages` (E03US001, ADR-0022).

La suite d'API migre toujours une base **vide** jusqu'à `head` : le **backfill** (110 pour les U11,
130 sinon) n'est exercé par aucun autre test. Ici, on insère des `categorie` à l'ancien schéma (sans
`hauteur_cm`) sur la révision `0019`, on applique `0020`, et on relit `hauteur_cm`.

Les clés étrangères sont désactivées côté Alembic (`env.py`), on peut donc insérer un `tournoi_id`
fictif sans matérialiser le tournoi parent — même geste que `test_migration_0018`.
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

# ages (JSON) → hauteur_cm attendue après upgrade.
_CAS = [
    (["U11"], 110),  # U11 seul → blason 80 cm, centre à 110 cm (§5)
    (["U11", "U13"], 110),  # U11 présent (jamais mêlé dans le référentiel, mais robuste)
    (["U15", "U18"], 130),  # regroupement arc nu adulte → 130
    ([], 130),  # aucune contrainte d'âge → défaut 130
]


def _config(url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_upgrade_backfille_la_hauteur(tmp_path: Path) -> None:
    """Après `0020`, `hauteur_cm` vaut 110 si `ages` contient U11, 130 sinon."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0019_blason_zones")

    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            for identifiant, (ages, _attendu) in enumerate(_CAS, start=1):
                conn.execute(
                    sa.text(
                        "INSERT INTO categorie (id, tournoi_id, libelle, arme, ages, sexe) "
                        "VALUES (:id, 1, :libelle, NULL, :ages, NULL)"
                    ),
                    {"id": identifiant, "libelle": f"Cat {identifiant}", "ages": json.dumps(ages)},
                )

        command.upgrade(cfg, "0020_categorie_hauteur_centre")

        with engine.connect() as conn:
            lignes = conn.execute(sa.text("SELECT id, hauteur_cm FROM categorie")).all()
        hauteur_par_id = {int(ligne[0]): int(ligne[1]) for ligne in lignes}
        for identifiant, (_ages, attendu) in enumerate(_CAS, start=1):
            assert hauteur_par_id[identifiant] == attendu
    finally:
        engine.dispose()


def test_upgrade_tolere_un_ages_non_liste(tmp_path: Path) -> None:
    """Un `ages` JSON **scalaire** (base corrompue / import hors repository) retombe sur 130 sans
    faire échouer la migration — `json.loads("null")` rend `None`, `"U11" in None` lèverait
    sinon."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0019_blason_zones")

    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            for identifiant, ages in enumerate(["null", "5", "true"], start=1):
                conn.execute(
                    sa.text(
                        "INSERT INTO categorie (id, tournoi_id, libelle, arme, ages, sexe) "
                        "VALUES (:id, 1, :libelle, NULL, :ages, NULL)"
                    ),
                    {"id": identifiant, "libelle": f"Cat {identifiant}", "ages": ages},
                )

        command.upgrade(cfg, "0020_categorie_hauteur_centre")  # ne doit pas lever

        with engine.connect() as conn:
            hauteurs = {
                int(r[0]) for r in conn.execute(sa.text("SELECT hauteur_cm FROM categorie"))
            }
        assert hauteurs == {130}
    finally:
        engine.dispose()


def test_downgrade_retire_la_colonne(tmp_path: Path) -> None:
    """Le downgrade retire `hauteur_cm` (rien ne la portait avant cette revision)."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0020_categorie_hauteur_centre")
    command.downgrade(cfg, "0019_blason_zones")

    engine = sa.create_engine(url)
    try:
        with engine.connect() as conn:
            colonnes = {ligne[1] for ligne in conn.execute(sa.text("PRAGMA table_info(categorie)"))}
        assert "hauteur_cm" not in colonnes
    finally:
        engine.dispose()
