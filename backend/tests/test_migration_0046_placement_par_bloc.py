"""Migration 0046 — `placement_poule` devient `placement_par_bloc`, **sans perdre un plan**.

Test **de non-régression** au sens de la règle 9 : l'oracle est le comportement décrit par la
docstring de la migration, et l'implémenteur est le mieux placé pour l'écrire.

Ce que ces tests gardent, et c'est tout ce qui compte pour un renommage :

1. la table cible porte le **bon schéma** (colonne `groupe_numero`, contrainte renommée) ;
2. les blocs déjà posés sont **recopiés à l'identique** — c'est la promesse qui distingue cette
   migration d'un `drop` / `create`, et la seule qui puisse coûter quelque chose à un club ;
3. l'**aller-retour** `upgrade → downgrade → upgrade` rend la donnée intacte. C'est la propriété qui
   rend la migration sûre à jouer sur une base réelle, là où la `0045` détruisait sa table en
   descendant.

Les clés étrangères sont désactivées côté Alembic (`env.py`) : on insère des identifiants parents
fictifs sans matérialiser toute la descendance, comme les tests de migration voisins.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

_AVANT = "0045_placement_des_poules"
_PAR_BLOC = "0046_placement_par_bloc"

# Un plan de deux groupes : le premier déborde de la cible 1 sur la cible 2, ce qui est justement
# le cas que `rang` existe pour rendre relisible.
_PLAN = [
    (7, 1, "A", 1, 1),
    (7, 1, "B", 1, 2),
    (7, 2, "A", 1, 3),
    (7, 2, "B", 2, 1),
    (7, 2, "C", 2, 2),
]


def _config(url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _base(tmp_path: Path, nom: str) -> tuple[sa.Engine, Config]:
    url = f"sqlite:///{(tmp_path / nom).as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    return sa.create_engine(url), cfg


def _semer(engine: sa.Engine) -> None:
    """Pose un plan dans l'ancienne table, tel que la `0045` l'aurait écrit."""
    with engine.begin() as conn:
        for phase_id, cible, position, poule, rang in _PLAN:
            conn.execute(
                sa.text(
                    "INSERT INTO placement_poule "
                    "(phase_id, cible_index, position, poule_numero, rang) "
                    "VALUES (:phase_id, :cible, :position, :poule, :rang)"
                ),
                {
                    "phase_id": phase_id,
                    "cible": cible,
                    "position": position,
                    "poule": poule,
                    "rang": rang,
                },
            )


def _lire(engine: sa.Engine, table: str, colonne: str) -> list[tuple[int, int, str, int, int]]:
    with engine.begin() as conn:
        lignes = conn.execute(
            sa.text(
                f"SELECT phase_id, cible_index, position, {colonne}, rang "
                f"FROM {table} ORDER BY {colonne}, rang"
            )
        ).all()
    return [(a, b, c, d, e) for a, b, c, d, e in lignes]


def test_la_table_cible_porte_le_bon_schema(tmp_path: Path) -> None:
    """`groupe_numero` remplace `poule_numero`, et l'ancienne table disparaît.

    Le nom de la colonne est tout l'objet de la migration : une ronde de système suisse rangée sous
    `poule_numero` ferait chercher au prochain lecteur *ce qui a bien pu écrire ça*.
    """
    engine, cfg = _base(tmp_path, "schema.db")
    command.upgrade(cfg, _PAR_BLOC)

    inspecteur = sa.inspect(engine)
    tables = set(inspecteur.get_table_names())

    assert "placement_par_bloc" in tables
    assert "placement_poule" not in tables
    colonnes = {c["name"] for c in inspecteur.get_columns("placement_par_bloc")}
    assert "groupe_numero" in colonnes
    assert "poule_numero" not in colonnes


def test_les_blocs_deja_poses_survivent_au_renommage(tmp_path: Path) -> None:
    """**La promesse qui distingue ce renommage d'un `drop` / `create`.**

    Un club qui a déjà posé le plan de ses poules ne doit pas le reperdre parce que le mot a changé.
    Le contenu passe à l'identique : `groupe_numero` reçoit `poule_numero` sans transformation — un
    numéro de poule *était déjà* un numéro de groupe.
    """
    engine, cfg = _base(tmp_path, "donnees.db")
    _semer(engine)

    command.upgrade(cfg, _PAR_BLOC)

    assert _lire(engine, "placement_par_bloc", "groupe_numero") == _PLAN


def test_l_aller_retour_rend_la_donnee_intacte(tmp_path: Path) -> None:
    """`upgrade → downgrade → upgrade` sans perte — c'est ce qui rend la migration sûre.

    La `0045`, elle, détruisait sa table en descendant : sa docstring l'assumait (« la perte est
    totale et évidente »). Un renommage n'a pas cette excuse, puisqu'il ne change rien au contenu.
    """
    engine, cfg = _base(tmp_path, "aller_retour.db")
    _semer(engine)

    command.upgrade(cfg, _PAR_BLOC)
    command.downgrade(cfg, _AVANT)
    # Redescendu : l'ancienne table est de retour, avec ses lignes.
    assert _lire(engine, "placement_poule", "poule_numero") == _PLAN

    command.upgrade(cfg, _PAR_BLOC)
    assert _lire(engine, "placement_par_bloc", "groupe_numero") == _PLAN


def test_la_contrainte_dunicite_tient_toujours(tmp_path: Path) -> None:
    """Un bloc ne saute ni ne répète de rang — l'invariant de la `0045` traverse le renommage.

    C'est le contrôle qu'un renommage à la main perd le plus facilement : recréer la table sans sa
    contrainte laisse un schéma qui *semble* correct et n'empêche plus rien.
    """
    engine, cfg = _base(tmp_path, "unicite.db")
    _semer(engine)
    command.upgrade(cfg, _PAR_BLOC)

    with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO placement_par_bloc "
                "(phase_id, cible_index, position, groupe_numero, rang) "
                "VALUES (7, 3, 'A', 1, 1)"
            )
        )
