"""Tests d'intégration des repositories SQL Archer et Score (E00US011).

Exerce les adapters sur une **vraie base** créée par les migrations (`alembic upgrade head`) :
persistance, relecture, mise à jour (placement) et jointure score→archer→tournoi.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from domain.archer import Archer
from domain.score import Score
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    Database,
    ScoreRepositorySQL,
    TournoiRepositorySQL,
)

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

        tournoi = tournois.ajouter(Tournoi.creer("Salle 18m"))
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
