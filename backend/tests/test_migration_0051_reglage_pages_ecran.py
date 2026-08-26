"""Migration 0051 — le réglage des pages projetées d'un écran, **sans rien changer pour personne**.

Test **de non-régression** au sens de la règle 9 : l'oracle est le comportement décrit par la
docstring de la migration, et l'implémenteur est le mieux placé pour l'écrire.

Ce que ces tests gardent :

1. les deux colonnes naissent **nulles** partout — c'est la propriété qui rend la migration
   invisible au déploiement : nul veut dire « rien réglé », donc `ReglagePages.par_defaut()`, dont
   les valeurs sont **exactement** celles que le front tenait en dur (`DETTE-039`) ;
2. le réglage posé après la montée **survit à l'aller-retour** `downgrade → upgrade` ? Non — et
   c'est le point : la descente **perd** les réglages, la docstring le dit, le test l'épingle. Un
   aller-retour qui prétendrait les préserver serait une promesse que le schéma ne tient pas ;
3. un écran **déjà réglé sur son déroulé** traverse sans que `deroule_json` ne bouge : les deux
   réglages sont indépendants, y compris à travers une migration.

Les clés étrangères sont désactivées côté Alembic (`env.py`) : on insère un `tournoi_id` fictif sans
matérialiser toute la descendance, comme les tests de migration voisins.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

_AVANT = "0050_identite_visuelle_tournoi"
_PAGES = "0051_reglage_pages_ecran"

_DEROULE = [{"vue": "classement", "cadence_s": 30}, {"vue": "affectations", "cadence_s": 45}]


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
    """Un écran réglé sur son déroulé, un écran vierge, et une **cible** (qui ne projette rien)."""
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO poste (tournoi_id, cible_index, code, type, libelle, deroule_json) "
                "VALUES (1, NULL, 'ECR1', 'ecran', 'Hall', :deroule)"
            ),
            {"deroule": json.dumps(_DEROULE)},
        )
        conn.execute(
            sa.text(
                "INSERT INTO poste (tournoi_id, cible_index, code, type, libelle, deroule_json) "
                "VALUES (1, NULL, 'ECR2', 'ecran', 'Buvette', NULL)"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO poste (tournoi_id, cible_index, code, type, libelle, deroule_json) "
                "VALUES (1, 3, 'CIB3', 'cible', NULL, NULL)"
            )
        )


def _lire(engine: sa.Engine, code: str) -> dict[str, Any]:
    with engine.begin() as conn:
        ligne = conn.execute(
            sa.text(
                "SELECT noms_par_page, cadence_page_s, deroule_json FROM poste WHERE code = :code"
            ),
            {"code": code},
        ).one()
    return {
        "noms_par_page": ligne[0],
        "cadence_page_s": ligne[1],
        "deroule_json": ligne[2],
    }


def test_les_deux_colonnes_naissent_nulles_pour_tout_le_monde(tmp_path: Path) -> None:
    """La propriété qui rend le déploiement invisible : aucun écran ne change de comportement.

    Semer les valeurs par défaut aurait rendu indiscernable « l'organisateur a mesuré et choisi 40 »
    de « il n'a rien choisi » — même parti qu'en 0050 pour les accents hérités.
    """
    engine, cfg = _base(tmp_path, "nulles.db")
    _semer(engine)

    command.upgrade(cfg, _PAGES)

    for code in ("ECR1", "ECR2", "CIB3"):
        ligne = _lire(engine, code)
        assert ligne["noms_par_page"] is None, code
        assert ligne["cadence_page_s"] is None, code


def test_le_deroule_deja_regle_traverse_intact(tmp_path: Path) -> None:
    """Les deux réglages sont indépendants — y compris à travers une migration."""
    engine, cfg = _base(tmp_path, "deroule.db")
    _semer(engine)

    command.upgrade(cfg, _PAGES)

    assert json.loads(str(_lire(engine, "ECR1")["deroule_json"])) == _DEROULE


def test_la_descente_perd_les_reglages_poses(tmp_path: Path) -> None:
    """**La perte est assumée et documentée**, elle n'est pas un défaut à corriger.

    Le test l'épingle pour que personne ne croie à un aller-retour neutre : les deux colonnes
    disparaissent, et un écran redescendu reprend les 40 noms / 20 s d'avant l'US — c'est-à-dire le
    comportement que le dépôt a eu pendant tout le reste de son histoire.
    """
    engine, cfg = _base(tmp_path, "descente.db")
    _semer(engine)
    command.upgrade(cfg, _PAGES)
    with engine.begin() as conn:
        conn.execute(
            sa.text("UPDATE poste SET noms_par_page = 24, cadence_page_s = 12 WHERE code = 'ECR1'")
        )

    command.downgrade(cfg, _AVANT)
    command.upgrade(cfg, _PAGES)

    assert _lire(engine, "ECR1")["noms_par_page"] is None
    # Le déroulé, lui, n'a jamais été en jeu : la descente ne touche que les deux colonnes neuves.
    assert json.loads(str(_lire(engine, "ECR1")["deroule_json"])) == _DEROULE
