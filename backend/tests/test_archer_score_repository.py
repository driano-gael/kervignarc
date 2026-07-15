"""Tests d'intégration des repositories SQL Archer et Score (E00US011, club en E02US001).

Exerce les adapters sur une **vraie base** créée par les migrations (`alembic upgrade head`) :
persistance, relecture, mise à jour (placement), jointure score→archer→tournoi, et rattachement
au club (`archer.club_id`, `par_club`).
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from domain.archer import Archer
from domain.club import Club
from domain.score import Score
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    ClubRepositorySQL,
    Database,
    ScoreRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.erreurs import InfrastructureError

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def test_archers_et_scores_bout_en_bout(tmp_path: Path) -> None:
    """Persistance/relecture des archers et scores, placement, et agrégation par tournoi."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        tournois = TournoiRepositorySQL(db.session_factory)
        archers = ArcherRepositorySQL(db.session_factory)
        scores = ScoreRepositorySQL(db.session_factory)

        tournoi = tournois.ajouter(Tournoi.creer("Salle 18m", datetime.date(2026, 3, 14)))
        assert tournoi.id is not None

        alice = archers.ajouter(Archer.creer("Alice", tournoi.id))
        bob = archers.ajouter(Archer.creer("Bob", tournoi.id))
        assert alice.id is not None and bob.id is not None

        # Relecture à l'identique et liste par tournoi.
        assert archers.par_id(alice.id) == alice
        assert {a.id for a in archers.par_tournoi(tournoi.id)} == {alice.id, bob.id}

        # Placement (mise à jour) persisté.
        place = archers.enregistrer(alice.placer(5))
        assert place.cible == 5
        assert archers.par_id(alice.id) == place

        # Scores agrégés par tournoi (jointure archer→tournoi).
        scores.ajouter(Score.creer(alice.id, 10))
        scores.ajouter(Score.creer(alice.id, 9))
        scores.ajouter(Score.creer(bob.id, 8))
        du_tournoi = scores.par_tournoi(tournoi.id)
        assert sorted(s.points for s in du_tournoi) == [8, 9, 10]
    finally:
        db.engine.dispose()


def test_par_id_archer_inexistant_renvoie_none(tmp_path: Path) -> None:
    """`par_id` renvoie None pour un identifiant d'archer absent (pas d'exception)."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        assert ArcherRepositorySQL(db.session_factory).par_id(999) is None
    finally:
        db.engine.dispose()


def _base(tmp_path: Path) -> Database:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    return Database(url)


def test_archer_porte_son_club_en_base(tmp_path: Path) -> None:
    """`club_id` fait l'aller-retour agrégat ↔ ORM (migration 0014), placement compris."""
    db = _base(tmp_path)
    try:
        tournoi = TournoiRepositorySQL(db.session_factory).ajouter(
            Tournoi.creer("Salle 18m", datetime.date(2026, 3, 14))
        )
        assert tournoi.id is not None
        club = ClubRepositorySQL(db.session_factory).ajouter(Club.creer("Arc Club Rennes"))
        archers = ArcherRepositorySQL(db.session_factory)

        cree = archers.ajouter(Archer.creer("Robin", tournoi.id, club.id))
        assert cree.id is not None
        assert cree.club_id == club.id
        assert archers.par_id(cree.id) == cree

        # Le rattachement survit à une mise à jour portant sur un autre champ.
        place = archers.enregistrer(cree.placer(3))
        assert place.club_id == club.id
        assert archers.par_id(cree.id) == place
    finally:
        db.engine.dispose()


def test_par_club_renvoie_les_archers_tous_tournois_confondus(tmp_path: Path) -> None:
    """`par_club` ignore les frontières de tournoi : le référentiel des clubs est global."""
    db = _base(tmp_path)
    try:
        tournois = TournoiRepositorySQL(db.session_factory)
        premier = tournois.ajouter(Tournoi.creer("2025", datetime.date(2025, 3, 14)))
        second = tournois.ajouter(Tournoi.creer("2026", datetime.date(2026, 3, 14)))
        assert premier.id is not None and second.id is not None
        clubs = ClubRepositorySQL(db.session_factory)
        rennes = clubs.ajouter(Club.creer("Arc Club Rennes"))
        fougeres = clubs.ajouter(Club.creer("Élan de Fougères"))
        assert rennes.id is not None and fougeres.id is not None
        archers = ArcherRepositorySQL(db.session_factory)
        archers.ajouter(Archer.creer("Robin", premier.id, rennes.id))
        archers.ajouter(Archer.creer("Marion", second.id, rennes.id))
        archers.ajouter(Archer.creer("Alix", second.id, fougeres.id))
        archers.ajouter(Archer.creer("Sans club", second.id))

        assert [a.nom for a in archers.par_club(rennes.id)] == ["Robin", "Marion"]
        assert [a.nom for a in archers.par_club(fougeres.id)] == ["Alix"]
    finally:
        db.engine.dispose()


def test_par_club_sans_archer_renvoie_vide(tmp_path: Path) -> None:
    """Un club que personne ne référence renvoie une liste vide — donc supprimable."""
    db = _base(tmp_path)
    try:
        club = ClubRepositorySQL(db.session_factory).ajouter(Club.creer("Arc Club Rennes"))
        assert club.id is not None
        assert ArcherRepositorySQL(db.session_factory).par_club(club.id) == []
    finally:
        db.engine.dispose()


def test_supprimer_un_club_reference_est_bloque_par_la_fk(tmp_path: Path) -> None:
    """Filet **sous** le service : la FK refuse de laisser une référence pendante.

    Le service refuse déjà en amont (409, `ClubReference`) ; on vérifie ici que la base ne s'en
    remet pas à lui. `PRAGMA foreign_keys=ON` est posé à chaque connexion (`engine.py`), sans quoi
    SQLite ignorerait la contrainte.
    """
    db = _base(tmp_path)
    try:
        tournoi = TournoiRepositorySQL(db.session_factory).ajouter(
            Tournoi.creer("Salle 18m", datetime.date(2026, 3, 14))
        )
        assert tournoi.id is not None
        clubs = ClubRepositorySQL(db.session_factory)
        club = clubs.ajouter(Club.creer("Arc Club Rennes"))
        assert club.id is not None
        ArcherRepositorySQL(db.session_factory).ajouter(Archer.creer("Robin", tournoi.id, club.id))

        with pytest.raises(InfrastructureError):
            clubs.supprimer(club.id)
    finally:
        db.engine.dispose()
