"""Tests d'intégration du repository SQL des scoreurs (E10US003).

Exerce l'adapter sur une **vraie base** migrée (`alembic upgrade head`) : persistance (tournoi, nom,
code), relecture, listing par tournoi, mise à jour du nom (code figé), suppression, et — propre à
l'adapter, invisible via le service — la recherche `par_code` **globale et normalisée** et la
contrainte `UNIQUE(code)`. Un scoreur référence un tournoi (FK) : chaque test en crée un d'abord.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from domain.scoreur import Scoreur
from domain.tournoi import Tournoi
from infrastructure.db import Database, ScoreurRepositorySQL, TournoiRepositorySQL
from infrastructure.erreurs import InfrastructureError

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def _base_avec_tournoi(tmp_path: Path) -> tuple[Database, int]:
    """Migre une base jetable et y crée un tournoi ; renvoie la base et l'id du tournoi."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    tournoi = TournoiRepositorySQL(db.session_factory).ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None
    return db, tournoi.id


def test_ajouter_puis_relire(tmp_path: Path) -> None:
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = ScoreurRepositorySQL(db.session_factory)
        cree = repository.ajouter(Scoreur.creer(tournoi_id, "Camille", "AB12CD"))
        assert cree.id is not None
        assert repository.par_id(cree.id) == cree
        assert cree.tournoi_id == tournoi_id
        assert cree.nom == "Camille"
        assert cree.code == "AB12CD"
    finally:
        db.engine.dispose()


def test_par_tournoi_ne_renvoie_que_le_tournoi(tmp_path: Path) -> None:
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        tournois = TournoiRepositorySQL(db.session_factory)
        autre = tournois.ajouter(Tournoi.creer("Autre", _DATE))
        assert autre.id is not None
        repository = ScoreurRepositorySQL(db.session_factory)
        repository.ajouter(Scoreur.creer(tournoi_id, "Alice", "AB12CD"))
        repository.ajouter(Scoreur.creer(autre.id, "Bob", "EF34GH"))

        noms = [s.nom for s in repository.par_tournoi(tournoi_id)]

        assert noms == ["Alice"]
    finally:
        db.engine.dispose()


def test_par_code_est_global_et_normalise(tmp_path: Path) -> None:
    """`par_code` cherche dans **toute la base** et compare sur la forme canonique (majuscules)."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = ScoreurRepositorySQL(db.session_factory)
        cree = repository.ajouter(Scoreur.creer(tournoi_id, "Camille", "AB12CD"))

        assert repository.par_code("ab12cd") == cree
        assert repository.par_code("  AB12CD ") == cree
        assert repository.par_code("ZZ99ZZ") is None
    finally:
        db.engine.dispose()


def test_enregistrer_renomme_en_gardant_le_code(tmp_path: Path) -> None:
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = ScoreurRepositorySQL(db.session_factory)
        cree = repository.ajouter(Scoreur.creer(tournoi_id, "Camile", "AB12CD"))

        relu = repository.enregistrer(cree.modifier("Camille Dubois"))

        assert relu.nom == "Camille Dubois"
        assert relu.code == "AB12CD"
    finally:
        db.engine.dispose()


def test_supprimer_retire_la_ligne(tmp_path: Path) -> None:
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = ScoreurRepositorySQL(db.session_factory)
        cree = repository.ajouter(Scoreur.creer(tournoi_id, "Camille", "AB12CD"))
        assert cree.id is not None

        repository.supprimer(cree.id)

        assert repository.par_id(cree.id) is None
    finally:
        db.engine.dispose()


def test_code_unique_en_base(tmp_path: Path) -> None:
    """La contrainte `UNIQUE(code)` est le garde-fou d'intégrité (le service évite d'y arriver)."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = ScoreurRepositorySQL(db.session_factory)
        repository.ajouter(Scoreur.creer(tournoi_id, "Alice", "AB12CD"))

        with pytest.raises(InfrastructureError):
            repository.ajouter(Scoreur.creer(tournoi_id, "Bob", "AB12CD"))
    finally:
        db.engine.dispose()
