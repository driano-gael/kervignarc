"""Tests d'intégration du repository SQL des tournois (E00US009, E01US001).

Exerce l'adapter sur une **vraie base** créée par les migrations (`alembic upgrade head`) :
persistance des métadonnées (date, lieu, type), relecture, absence (None), et listing.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config

from domain.tournoi import Tournoi, TypeTournoi
from infrastructure.db import Database, TournoiRepositorySQL

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def test_ajouter_puis_relire(tmp_path: Path) -> None:
    """`ajouter` attribue un id ; `par_id` relit l'agrégat (métadonnées comprises)."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        cree = repository.ajouter(
            Tournoi.creer("Salle 18m", _DATE, "Quimper", TypeTournoi.OFFICIEL)
        )
        assert cree.id is not None
        assert cree.date == _DATE
        assert cree.lieu == "Quimper"
        assert cree.type_tournoi is TypeTournoi.OFFICIEL
        assert repository.par_id(cree.id) == cree
    finally:
        db.engine.dispose()


def test_par_id_inexistant_renvoie_none(tmp_path: Path) -> None:
    """`par_id` renvoie None pour un identifiant absent (pas d'exception)."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        assert repository.par_id(999) is None
    finally:
        db.engine.dispose()


def test_lister_renvoie_du_plus_recent_au_plus_ancien(tmp_path: Path) -> None:
    """`lister` renvoie tous les tournois, le dernier créé en premier."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        assert repository.lister() == []
        repository.ajouter(Tournoi.creer("Ancien", _DATE))
        repository.ajouter(Tournoi.creer("Récent", _DATE))
        assert [t.nom for t in repository.lister()] == ["Récent", "Ancien"]
    finally:
        db.engine.dispose()
