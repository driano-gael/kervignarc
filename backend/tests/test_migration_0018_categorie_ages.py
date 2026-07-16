"""Migration 0018 — reconstruction de `ages` depuis l'ancien `tranche_age` (E01US013, ADR-0019).

La suite d'API migre toujours une base **vide** jusqu'à `head` : le chemin de **reconstruction des
données** (regroupement arc nu, texte libre non mappable) n'est exercé par aucun autre test. Ici, on
insère des lignes à l'**ancien** schéma (`tranche_age` scalaire) sur la révision `0017`, on applique
`0018`, et on relit `ages`.

Les clés étrangères sont **désactivées** côté Alembic (`env.py` monte l'engine sans le listener
PRAGMA de `infrastructure.db.engine`) comme sur la connexion de test : on peut donc insérer des
`categorie` avec un `tournoi_id` fictif sans matérialiser le tournoi parent.
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

# (arme, tranche_age ancien) → ages attendu après upgrade.
_CAS = [
    ("Arc Nu", "U18", ["U15", "U18"]),  # regroupement arc nu : U18 couvre U15 + U18
    ("Arc Nu", "Scratch", ["U21", "S1", "S2", "S3"]),  # « Scratch » = libellé de regroupement
    ("Arc Classique", "U18", ["U18"]),  # même code, sens « U18 seul » hors arc nu
    ("classique", "senior", []),  # texte libre non mappable → aucune contrainte d'âge
    (None, None, []),  # âge non renseigné → []
]


def _config(url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_upgrade_reconstruit_les_ages(tmp_path: Path) -> None:
    """Après `0018`, `ages` est le tableau JSON reconstruit depuis l'ancien `(arme, tranche)`."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0017_inscription")

    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            for identifiant, (arme, tranche, _attendu) in enumerate(_CAS, start=1):
                conn.execute(
                    sa.text(
                        "INSERT INTO categorie (id, tournoi_id, libelle, arme, tranche_age, sexe) "
                        "VALUES (:id, 1, :libelle, :arme, :tranche, NULL)"
                    ),
                    {
                        "id": identifiant,
                        "libelle": f"Cat {identifiant}",
                        "arme": arme,
                        "tranche": tranche,
                    },
                )

        command.upgrade(cfg, "0018_categorie_ages")

        with engine.connect() as conn:
            lignes = conn.execute(sa.text("SELECT id, ages FROM categorie")).all()
        ages_par_id = {int(ligne[0]): str(ligne[1]) for ligne in lignes}
        for identifiant, (_arme, _tranche, attendu) in enumerate(_CAS, start=1):
            assert json.loads(ages_par_id[identifiant]) == attendu
    finally:
        engine.dispose()


def test_downgrade_restaure_tranche_age_au_mieux(tmp_path: Path) -> None:
    """Le downgrade recrée `tranche_age` en meilleur effort (première tranche de `ages`)."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0018_categorie_ages")

    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO categorie (id, tournoi_id, libelle, arme, ages, sexe) "
                    "VALUES (1, 1, 'Cat', 'Arc Nu', :ages, NULL)"
                ),
                {"ages": json.dumps(["U15", "U18"])},
            )

        command.downgrade(cfg, "0017_inscription")

        with engine.connect() as conn:
            tranche = conn.execute(
                sa.text("SELECT tranche_age FROM categorie WHERE id = 1")
            ).scalar_one()
        assert tranche == "U15"
    finally:
        engine.dispose()
