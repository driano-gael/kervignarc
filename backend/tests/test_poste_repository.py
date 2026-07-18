"""Tests d'intégration du repository SQL des postes (E04US001).

Exerce l'adapter sur une **vraie base** migrée (`alembic upgrade head`) : persistance (tournoi,
cible, code), relecture, listing par tournoi **ordonné par cible**, et — propre à l'adapter,
invisible via le service — la recherche `par_code` **globale et normalisée** et les deux contraintes
`UNIQUE` (code global ; couple `(tournoi_id, cible_index)`). Un poste référence un tournoi (FK) :
chaque test en crée un d'abord.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from domain.poste import Poste
from domain.tournoi import Tournoi
from infrastructure.db import Database, PosteRepositorySQL, TournoiRepositorySQL
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
        repository = PosteRepositorySQL(db.session_factory)
        cree = repository.ajouter(Poste.creer(tournoi_id, 12, "AB12CD"))
        assert cree.id is not None
        assert repository.par_id(cree.id) == cree
        assert cree.tournoi_id == tournoi_id
        assert cree.cible_index == 12
        assert cree.code == "AB12CD"
    finally:
        db.engine.dispose()


def test_par_tournoi_ordonne_par_cible(tmp_path: Path) -> None:
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        tournois = TournoiRepositorySQL(db.session_factory)
        autre = tournois.ajouter(Tournoi.creer("Autre", _DATE))
        assert autre.id is not None
        repository = PosteRepositorySQL(db.session_factory)
        repository.ajouter(Poste.creer(tournoi_id, 3, "C3"))
        repository.ajouter(Poste.creer(tournoi_id, 1, "C1"))
        repository.ajouter(Poste.creer(autre.id, 1, "AUTRE1"))

        cibles = [p.cible_index for p in repository.par_tournoi(tournoi_id)]

        assert cibles == [1, 3]
    finally:
        db.engine.dispose()


def test_par_code_est_global_et_normalise(tmp_path: Path) -> None:
    """`par_code` cherche dans **toute la base** et compare sur la forme canonique (majuscules)."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = PosteRepositorySQL(db.session_factory)
        cree = repository.ajouter(Poste.creer(tournoi_id, 1, "AB12CD"))

        assert repository.par_code("ab12cd") == cree
        assert repository.par_code("  AB12CD ") == cree
        assert repository.par_code("ZZ99ZZ") is None
    finally:
        db.engine.dispose()


def test_code_unique_en_base(tmp_path: Path) -> None:
    """La contrainte `UNIQUE(code)` (globale) est le garde-fou d'intégrité ultime."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = PosteRepositorySQL(db.session_factory)
        repository.ajouter(Poste.creer(tournoi_id, 1, "AB12CD"))

        with pytest.raises(InfrastructureError):
            repository.ajouter(Poste.creer(tournoi_id, 2, "AB12CD"))
    finally:
        db.engine.dispose()


def test_cible_unique_par_tournoi(tmp_path: Path) -> None:
    """La contrainte `UNIQUE(tournoi_id, cible_index)` : une seule cible N par tournoi."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = PosteRepositorySQL(db.session_factory)
        repository.ajouter(Poste.creer(tournoi_id, 1, "AB12CD"))

        with pytest.raises(InfrastructureError):
            repository.ajouter(Poste.creer(tournoi_id, 1, "EF34GH"))
    finally:
        db.engine.dispose()


def test_meme_cible_dans_deux_tournois(tmp_path: Path) -> None:
    """La cible 1 peut exister dans deux tournois différents (unicité **par** tournoi)."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        autre = TournoiRepositorySQL(db.session_factory).ajouter(Tournoi.creer("Extérieur", _DATE))
        assert autre.id is not None
        repository = PosteRepositorySQL(db.session_factory)
        repository.ajouter(Poste.creer(tournoi_id, 1, "INT1"))
        repository.ajouter(Poste.creer(autre.id, 1, "EXT1"))

        assert [p.cible_index for p in repository.par_tournoi(tournoi_id)] == [1]
        assert [p.cible_index for p in repository.par_tournoi(autre.id)] == [1]
    finally:
        db.engine.dispose()
