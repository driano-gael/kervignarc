"""Migration 0052 — le réglage des podiums, **sans rien changer pour personne**.

Test **de non-régression** au sens de la règle 9 : l'oracle est le comportement décrit par la
docstring de la migration, et l'implémenteur est le mieux placé pour l'écrire.

⚠️ **C'est le seul test qui exerce la garantie de non-régression d'E16US014.** La migration l'écrit
en toutes lettres — « c'est la seule garantie de non-régression du réglage, et elle vit ici, pas
dans le code » — et rien ne la vérifiait : `test_le_reglage_par_defaut_reproduit_e06us004` teste les
défauts de la **dataclass**, chemin que les lignes déjà en base n'empruntent pas (elles passent par
les **colonnes**), et les tournois des tests d'API sont tous créés *après* la montée par un
repository qui écrit les deux colonnes explicitement — le `server_default` n'y sert jamais. Manque
relevé en revue.

Ce que ces tests gardent :

1. un tournoi **déjà en base** hérite de `["categorie"]` / `4`, c'est-à-dire du comportement exact
   d'E06US004 : podiums par catégorie, quatre places ;
2. le repository **refuse** une portée qu'il ne sait pas lire au lieu de l'ignorer — un podium
   qu'on croit réglé et qui ne rend rien est le pire des deux mondes ;
3. la descente **perd** les réglages posés, la docstring l'assume, le test l'épingle.

Les clés étrangères sont désactivées côté Alembic (`env.py`) : on insère un tournoi sans
matérialiser toute sa descendance, comme les tests de migration voisins.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import sessionmaker

from domain.podium import PROFONDEUR_PODIUM_PAR_DEFAUT, PorteePodium
from infrastructure.db.repositories.referentiel import TournoiRepositorySQL
from infrastructure.erreurs import InfrastructureError

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

_AVANT = "0051_reglage_pages_ecran"
_PODIUMS = "0052_reglage_podiums"


def _config(url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _base(tmp_path: Path, nom: str) -> tuple[sa.Engine, Config]:
    """Une base montée **jusqu'à la veille** de 0052, avec un tournoi déjà dedans."""
    url = f"sqlite:///{(tmp_path / nom).as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    engine = sa.create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO tournoi (nom, date, type_tournoi, statut, cloisonnement) "
                "VALUES ('Salle 18m', '2026-03-14', 'non_officiel', 'termine', 'aucun')"
            )
        )
    return engine, cfg


def _colonnes(engine: sa.Engine) -> tuple[str, int]:
    with engine.begin() as conn:
        ligne = conn.execute(sa.text("SELECT podium_portees, podium_profondeur FROM tournoi")).one()
    return str(ligne[0]), int(ligne[1])


def test_un_tournoi_deja_en_base_herite_du_comportement_d_e06us004(tmp_path: Path) -> None:
    """La propriété qui rend le déploiement invisible : aucun palmarès ne change d'affichage.

    Le `server_default` remplit les lignes existantes en une passe. `NULL` aurait ouvert un état de
    plus à traduire — « pas encore réglé » — alors que « podiums par catégorie » **est** une valeur.
    """
    engine, cfg = _base(tmp_path, "heritage.db")

    command.upgrade(cfg, _PODIUMS)

    assert _colonnes(engine) == ('["categorie"]', PROFONDEUR_PODIUM_PAR_DEFAUT)


def test_le_reglage_herite_se_relit_bien_en_value_object(tmp_path: Path) -> None:
    """La colonne ne suffit pas : c'est le **repository** qui la traduit, et c'est lui qu'on lit.

    Le chemin complet `server_default → colonne → _vers_reglage_podiums → ReglagePodiums` est ce que
    l'écran voit d'un tournoi antérieur à l'US.
    """
    engine, cfg = _base(tmp_path, "relecture.db")
    command.upgrade(cfg, _PODIUMS)

    tournoi = TournoiRepositorySQL(sessionmaker(bind=engine)).par_id(1)

    assert tournoi is not None
    assert tournoi.reglage_podiums.portees == frozenset({PorteePodium.CATEGORIE})
    assert tournoi.reglage_podiums.profondeur == PROFONDEUR_PODIUM_PAR_DEFAUT


@pytest.mark.parametrize("ecrit", ['["equipe"]', "4", '{"portee": "club"}', "pas du json"])
def test_une_valeur_illisible_en_base_est_refusee_et_non_ignoree(
    tmp_path: Path, ecrit: str
) -> None:
    """La docstring de la migration promet une `InfrastructureError` — voici la promesse tenue.

    Les quatre formes couvrent les quatre façons de casser la colonne : une portée **inconnue**
    (base plus récente, ou éditée), un JSON **qui n'est pas une liste**, un objet, et du non-JSON.
    Ignorer l'une d'elles rendrait silencieusement un palmarès amputé d'un podium que l'organisateur
    croit réglé — et le `TypeError` des deux formes du milieu échappait à l'enveloppe (relevé en
    revue).
    """
    # `tmp_path` est déjà unique par cas paramétré : un `hash()` ici n'ajoutait que de
    # l'aléa non maîtrisé (`PYTHONHASHSEED`), ce que la règle 9 proscrit.
    engine, cfg = _base(tmp_path, "illisible.db")
    command.upgrade(cfg, _PODIUMS)
    with engine.begin() as conn:
        conn.execute(sa.text("UPDATE tournoi SET podium_portees = :ecrit"), {"ecrit": ecrit})

    with pytest.raises(InfrastructureError):
        TournoiRepositorySQL(sessionmaker(bind=engine)).par_id(1)


@pytest.mark.parametrize("ecrit", ["0", "'abc'", "999"])
def test_une_profondeur_illisible_est_refusee_elle_aussi(tmp_path: Path, ecrit: str) -> None:
    """La colonne d'à côté relève du même modèle de menace, et n'avait aucune garde.

    SQLite est à typage **dynamique** : une affinité `INTEGER` ne rejette pas `'abc'`. Les trois
    formes couvrent le hors-borne bas (que le domaine refuse), le mauvais type (qui levait un
    `TypeError` hors enveloppe) et le hors-borne haut, atteignable depuis une base plus récente.
    """
    engine, cfg = _base(tmp_path, "profondeur.db")
    command.upgrade(cfg, _PODIUMS)
    with engine.begin() as conn:
        conn.execute(sa.text(f"UPDATE tournoi SET podium_profondeur = {ecrit}"))

    with pytest.raises(InfrastructureError):
        TournoiRepositorySQL(sessionmaker(bind=engine)).par_id(1)


def test_la_descente_perd_les_reglages_poses(tmp_path: Path) -> None:
    """**La perte est assumée et documentée**, elle n'est pas un défaut à corriger.

    Le test l'épingle pour que personne ne croie à un aller-retour neutre : un tournoi redescendu
    puis remonté reprend les podiums par catégorie à quatre places — le comportement que le dépôt a
    eu pendant tout le reste de son histoire.
    """
    engine, cfg = _base(tmp_path, "descente.db")
    command.upgrade(cfg, _PODIUMS)
    with engine.begin() as conn:
        conn.execute(
            sa.text("UPDATE tournoi SET podium_portees = :portees, podium_profondeur = 8"),
            {"portees": json.dumps(["scratch", "club"])},
        )

    command.downgrade(cfg, _AVANT)
    command.upgrade(cfg, _PODIUMS)

    assert _colonnes(engine) == ('["categorie"]', PROFONDEUR_PODIUM_PAR_DEFAUT)
