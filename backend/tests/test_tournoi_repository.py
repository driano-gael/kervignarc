"""Tests d'intégration du repository SQL des tournois (E00US009, E01US001, E01US002).

Exerce l'adapter sur une **vraie base** créée par les migrations (`alembic upgrade head`) :
persistance des métadonnées (date, lieu, type) et du statut, relecture, absence (None), listing,
mise à jour (`enregistrer`) et suppression (`supprimer`). Le tarif n'est plus au tournoi (E02US004,
ADR-0017) — voir `test_depart_repository.py`.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config

from domain.tournoi import StatutTournoi, Tournoi, TypeTournoi
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
        assert cree.statut is StatutTournoi.BROUILLON
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


def test_enregistrer_met_a_jour_metadonnees_et_statut(tmp_path: Path) -> None:
    """`enregistrer` persiste l'édition des métadonnées et la transition de statut."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        cree = repository.ajouter(Tournoi.creer("Ancien", _DATE))
        assert cree.id is not None
        modifie = cree.modifier("Nouveau", _DATE, "Quimper", TypeTournoi.OFFICIEL).demarrer()
        enregistre = repository.enregistrer(modifie)
        assert enregistre.nom == "Nouveau"
        assert enregistre.lieu == "Quimper"
        assert enregistre.type_tournoi is TypeTournoi.OFFICIEL
        assert enregistre.statut is StatutTournoi.EN_COURS
        assert repository.par_id(cree.id) == enregistre
    finally:
        db.engine.dispose()


def test_supprimer_retire_le_tournoi(tmp_path: Path) -> None:
    """`supprimer` retire la ligne ; `par_id` renvoie ensuite None."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        cree = repository.ajouter(Tournoi.creer("Trophée", _DATE))
        assert cree.id is not None
        repository.supprimer(cree.id)
        assert repository.par_id(cree.id) is None
        assert repository.lister() == []
    finally:
        db.engine.dispose()
