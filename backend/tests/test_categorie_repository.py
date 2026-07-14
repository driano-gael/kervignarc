"""Tests d'intégration du repository SQL des catégories (E01US003).

Exerce l'adapter sur une **vraie base** créée par les migrations (`alembic upgrade head`) :
persistance, relecture, absence (None), listing par tournoi, mise à jour et suppression.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config

from domain.blason import Blason
from domain.categorie import Categorie, SexeCategorie
from domain.tournoi import Tournoi
from infrastructure.db import (
    BlasonRepositorySQL,
    CategorieRepositorySQL,
    Database,
    TournoiRepositorySQL,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def _base_avec_tournoi(tmp_path: Path) -> tuple[Database, int]:
    """Crée une base migrée avec un tournoi persisté ; renvoie (db, tournoi_id)."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    tournoi = TournoiRepositorySQL(db.session_factory).ajouter(Tournoi.creer("Trophée", _DATE))
    assert tournoi.id is not None
    return db, tournoi.id


def test_ajouter_puis_relire(tmp_path: Path) -> None:
    """`ajouter` attribue un id ; `par_id` relit l'agrégat (attributs compris)."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = CategorieRepositorySQL(db.session_factory)
        cree = repository.ajouter(
            Categorie.creer(
                tournoi_id, "Senior H Classique", "classique", "senior", SexeCategorie.HOMME
            )
        )
        assert cree.id is not None
        assert cree.tournoi_id == tournoi_id
        assert cree.arme == "classique"
        assert cree.sexe is SexeCategorie.HOMME
        assert repository.par_id(cree.id) == cree
    finally:
        db.engine.dispose()


def test_par_id_inexistant_renvoie_none(tmp_path: Path) -> None:
    """`par_id` renvoie None pour un identifiant absent (pas d'exception)."""
    db, _ = _base_avec_tournoi(tmp_path)
    try:
        assert CategorieRepositorySQL(db.session_factory).par_id(999) is None
    finally:
        db.engine.dispose()


def test_par_tournoi_liste_dans_l_ordre_de_creation(tmp_path: Path) -> None:
    """`par_tournoi` renvoie les catégories du tournoi, dans l'ordre de création."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = CategorieRepositorySQL(db.session_factory)
        assert repository.par_tournoi(tournoi_id) == []
        repository.ajouter(Categorie.creer(tournoi_id, "A"))
        repository.ajouter(Categorie.creer(tournoi_id, "B"))
        assert [c.libelle for c in repository.par_tournoi(tournoi_id)] == ["A", "B"]
    finally:
        db.engine.dispose()


def test_enregistrer_met_a_jour(tmp_path: Path) -> None:
    """`enregistrer` persiste l'édition des attributs."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = CategorieRepositorySQL(db.session_factory)
        cree = repository.ajouter(Categorie.creer(tournoi_id, "Ancien"))
        assert cree.id is not None
        modifiee = cree.modifier("Nouveau", "nu", "cadet", SexeCategorie.FEMME)
        enregistree = repository.enregistrer(modifiee)
        assert enregistree.libelle == "Nouveau"
        assert enregistree.arme == "nu"
        assert enregistree.sexe is SexeCategorie.FEMME
        assert repository.par_id(cree.id) == enregistree
    finally:
        db.engine.dispose()


def test_supprimer_retire_la_ligne(tmp_path: Path) -> None:
    """`supprimer` retire la ligne ; `par_id` renvoie ensuite None."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = CategorieRepositorySQL(db.session_factory)
        cree = repository.ajouter(Categorie.creer(tournoi_id, "Libre"))
        assert cree.id is not None
        repository.supprimer(cree.id)
        assert repository.par_id(cree.id) is None
        assert repository.par_tournoi(tournoi_id) == []
    finally:
        db.engine.dispose()


def test_blason_par_defaut_persiste_et_par_blason(tmp_path: Path) -> None:
    """E01US006 : `blason_id` est persisté/relu ; `par_blason` liste les catégories liées."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        blason = BlasonRepositorySQL(db.session_factory).ajouter(
            Blason.creer(tournoi_id, "Trispot 40", 0.5, 3)
        )
        assert blason.id is not None
        repository = CategorieRepositorySQL(db.session_factory)
        liee = repository.ajouter(Categorie.creer(tournoi_id, "Senior H", blason_id=blason.id))
        repository.ajouter(Categorie.creer(tournoi_id, "Sans blason"))
        assert liee.id is not None
        assert repository.par_id(liee.id) == liee
        assert liee.blason_id == blason.id
        assert repository.par_blason(blason.id) == [liee]
    finally:
        db.engine.dispose()


def test_enregistrer_detache_le_blason(tmp_path: Path) -> None:
    """E01US006 : `enregistrer` peut retirer le blason par défaut (`blason_id` → None)."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        blason = BlasonRepositorySQL(db.session_factory).ajouter(
            Blason.creer(tournoi_id, "Monospot", 1.0, 1)
        )
        assert blason.id is not None
        repository = CategorieRepositorySQL(db.session_factory)
        cree = repository.ajouter(Categorie.creer(tournoi_id, "Libre", blason_id=blason.id))
        detachee = repository.enregistrer(cree.modifier("Libre", blason_id=None))
        assert detachee.blason_id is None
        assert repository.par_blason(blason.id) == []
    finally:
        db.engine.dispose()
