"""Tests d'intégration du repository SQL des clubs (E02US001).

Exerce l'adapter sur une **vraie base** créée par les migrations (`alembic upgrade head`) :
persistance, relecture, absence (None), recherche par nom insensible à la casse, listing,
mise à jour, suppression, et contrainte d'unicité.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from domain.club import Club
from infrastructure.db import ClubRepositorySQL, Database
from infrastructure.erreurs import InfrastructureError

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


@pytest.fixture
def clubs(tmp_path: Path) -> ClubRepositorySQL:
    """Renvoie un repository de clubs branché sur une base migrée jetable."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    return ClubRepositorySQL(Database(url).session_factory)


def test_ajouter_puis_relire(clubs: ClubRepositorySQL) -> None:
    """`ajouter` attribue un id ; `par_id` relit l'agrégat."""
    persiste = clubs.ajouter(Club.creer("Arc Club Rennes"))

    assert persiste.id is not None
    relu = clubs.par_id(persiste.id)
    assert relu == persiste
    assert relu is not None and relu.nom == "Arc Club Rennes"


def test_par_id_absent_renvoie_none(clubs: ClubRepositorySQL) -> None:
    assert clubs.par_id(404) is None


def test_par_nom_trouve_a_la_casse_pres(clubs: ClubRepositorySQL) -> None:
    persiste = clubs.ajouter(Club.creer("Arc Club Rennes"))

    assert clubs.par_nom("arc club RENNES") == persiste


def test_par_nom_ignore_les_espaces_de_bord(clubs: ClubRepositorySQL) -> None:
    persiste = clubs.ajouter(Club.creer("Arc Club Rennes"))

    assert clubs.par_nom("  Arc Club Rennes  ") == persiste


def test_par_nom_replie_les_accents(clubs: ClubRepositorySQL) -> None:
    """Contrat du port : `COLLATE NOCASE` ne suffirait pas (ASCII seul), d'où la comparaison
    côté Python."""
    persiste = clubs.ajouter(Club.creer("Élan de Fougères"))

    assert clubs.par_nom("élan de fougères") == persiste


def test_par_nom_absent_renvoie_none(clubs: ClubRepositorySQL) -> None:
    clubs.ajouter(Club.creer("Arc Club Rennes"))

    assert clubs.par_nom("Élan de Fougères") is None


def test_lister_renvoie_tout_le_referentiel(clubs: ClubRepositorySQL) -> None:
    clubs.ajouter(Club.creer("Arc Club Rennes"))
    clubs.ajouter(Club.creer("Élan de Fougères"))

    assert {club.nom for club in clubs.lister()} == {"Arc Club Rennes", "Élan de Fougères"}


def test_lister_un_referentiel_vide(clubs: ClubRepositorySQL) -> None:
    assert clubs.lister() == []


def test_enregistrer_met_a_jour_le_nom(clubs: ClubRepositorySQL) -> None:
    persiste = clubs.ajouter(Club.creer("Arc Club Rennes"))

    clubs.enregistrer(persiste.modifier("Arc Club de Rennes"))

    assert persiste.id is not None
    relu = clubs.par_id(persiste.id)
    assert relu is not None and relu.nom == "Arc Club de Rennes"


def test_enregistrer_une_ligne_absente_est_une_incoherence_technique(
    clubs: ClubRepositorySQL,
) -> None:
    """Contrat du port : l'appelant garantit l'existence — l'absence n'est pas un cas métier."""
    fantome = Club(nom="Jamais persisté", id=404)

    with pytest.raises(InfrastructureError):
        clubs.enregistrer(fantome)


def test_supprimer_retire_la_ligne(clubs: ClubRepositorySQL) -> None:
    persiste = clubs.ajouter(Club.creer("Arc Club Rennes"))
    assert persiste.id is not None

    clubs.supprimer(persiste.id)

    assert clubs.par_id(persiste.id) is None


def test_supprimer_une_ligne_absente_est_une_incoherence_technique(
    clubs: ClubRepositorySQL,
) -> None:
    with pytest.raises(InfrastructureError):
        clubs.supprimer(404)


def test_la_contrainte_unique_garde_le_referentiel(clubs: ClubRepositorySQL) -> None:
    """Garde-fou d'intégrité en base, sous le refus fonctionnel porté par `ServiceClubs`.

    La contrainte est **exacte** (elle n'attrape pas « arc club rennes ») : c'est le service
    qui compare sans tenir compte de la casse. Ici on vérifie seulement que le filet existe.
    """
    clubs.ajouter(Club.creer("Arc Club Rennes"))

    with pytest.raises(InfrastructureError):
        clubs.ajouter(Club.creer("Arc Club Rennes"))
