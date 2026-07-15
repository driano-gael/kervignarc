"""Tests d'intégration du repository SQL des tournois (E00US009, E01US001, E01US002, E01US010).

Exerce l'adapter sur une **vraie base** créée par les migrations (`alembic upgrade head`) :
persistance des métadonnées (date, lieu, type), du statut et du **tarif d'un départ** (E01US010),
relecture, absence (None), listing, mise à jour (`enregistrer`) et suppression (`supprimer`).
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

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


@pytest.mark.parametrize(
    "tarif", [None, 0, 810, 1250], ids=["non_defini", "gratuit", "8_10_euros", "12_50_euros"]
)
def test_le_tarif_fait_laller_retour_en_base(tmp_path: Path, tarif: int | None) -> None:
    """Le tarif est persisté et relu à l'identique — `None` (non défini) comme `0` (gratuit)."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        cree = repository.ajouter(Tournoi.creer("Salle 18m", _DATE, tarif_depart_centimes=tarif))
        assert cree.id is not None
        assert cree.tarif_depart_centimes == tarif

        relu = repository.par_id(cree.id)
        assert relu is not None
        assert relu.tarif_depart_centimes == tarif
    finally:
        db.engine.dispose()


def test_le_tarif_est_stocke_en_entier(tmp_path: Path) -> None:
    """**Le cœur du choix « centimes »** : la colonne contient un INTEGER, pas un flottant.

    8,10 € n'est pas représentable exactement en binaire ; stocké en REAL, il se relirait
    `8.0999999999999996`. En centimes, la base contient `810` — exact, et sommable sans dérive
    par EPIC-08/09 (montant dû par archer, par club — EF-8.1 / EF-9.6).
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        cree = repository.ajouter(Tournoi.creer("Salle 18m", _DATE, tarif_depart_centimes=810))

        with db.session_factory() as session:
            valeur, type_sqlite = session.execute(
                text(
                    "SELECT tarif_depart_centimes, typeof(tarif_depart_centimes)"
                    " FROM tournoi WHERE id = :id"
                ),
                {"id": cree.id},
            ).one()
        assert (valeur, type_sqlite) == (810, "integer")
    finally:
        db.engine.dispose()


def test_enregistrer_met_a_jour_le_tarif(tmp_path: Path) -> None:
    """`enregistrer` persiste l'édition du tarif, y compris le retour à « non défini »."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        cree = repository.ajouter(Tournoi.creer("Salle 18m", _DATE, tarif_depart_centimes=810))
        assert cree.id is not None

        hausse = repository.enregistrer(
            cree.modifier("Salle 18m", _DATE, tarif_depart_centimes=900)
        )
        assert hausse.tarif_depart_centimes == 900

        efface = repository.enregistrer(cree.modifier("Salle 18m", _DATE))
        assert efface.tarif_depart_centimes is None
        assert repository.par_id(cree.id) == efface
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
