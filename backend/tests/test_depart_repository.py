"""Tests d'intégration du repository SQL des départs (E02US004, ADR-0017).

Exerce l'adapter sur une **vraie base** migrée (`alembic upgrade head`) : persistance d'un créneau
(tournoi, numéro, horaire, tarif), tarif stocké en **entier** (centimes, ADR-0012), relecture, tri
par numéro, mise à jour, suppression, et la contrainte `UNIQUE(tournoi_id, numero)`. Un départ
référence un tournoi (FK) : chaque test en crée un d'abord.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from domain.depart import Depart
from domain.tournoi import Tournoi
from infrastructure.db import Database, DepartRepositorySQL, TournoiRepositorySQL
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
    """`ajouter` attribue un id ; `par_id` relit l'agrégat (horaire compris)."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = DepartRepositorySQL(db.session_factory)
        cree = repository.ajouter(Depart.creer(tournoi_id, 1, 810, "9h00"))
        assert cree.id is not None
        assert cree.tournoi_id == tournoi_id
        assert cree.numero == 1
        assert cree.horaire == "9h00"
        assert cree.tarif_centimes == 810
        assert repository.par_id(cree.id) == cree
    finally:
        db.engine.dispose()


def test_horaire_absent_fait_laller_retour(tmp_path: Path) -> None:
    """Un créneau sans horaire se persiste et se relit avec `horaire` à None."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = DepartRepositorySQL(db.session_factory)
        cree = repository.ajouter(Depart.creer(tournoi_id, 1, 810))
        assert cree.id is not None
        relu = repository.par_id(cree.id)
        assert relu is not None
        assert relu.horaire is None
    finally:
        db.engine.dispose()


def test_le_tarif_est_stocke_en_entier(tmp_path: Path) -> None:
    """**Le cœur du choix « centimes »** : la colonne contient un INTEGER, pas un flottant.

    8,10 € n'est pas représentable exactement en binaire ; stocké en REAL, il se relirait
    `8.0999999999999996`. En centimes, la base contient `810` — exact, et sommable sans dérive par
    EPIC-08/09 (montant dû par archer = somme des tarifs de ses départs).
    """
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = DepartRepositorySQL(db.session_factory)
        cree = repository.ajouter(Depart.creer(tournoi_id, 1, 810))

        with db.session_factory() as session:
            valeur, type_sqlite = session.execute(
                text("SELECT tarif_centimes, typeof(tarif_centimes) FROM depart WHERE id = :id"),
                {"id": cree.id},
            ).one()
        assert (valeur, type_sqlite) == (810, "integer")
    finally:
        db.engine.dispose()


def test_par_tournoi_trie_par_numero(tmp_path: Path) -> None:
    """`par_tournoi` renvoie les départs du tournoi, triés par numéro croissant."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = DepartRepositorySQL(db.session_factory)
        repository.ajouter(Depart.creer(tournoi_id, 2, 810, "14h00"))
        repository.ajouter(Depart.creer(tournoi_id, 1, 900, "9h00"))
        assert [d.numero for d in repository.par_tournoi(tournoi_id)] == [1, 2]
    finally:
        db.engine.dispose()


def test_par_id_inexistant_renvoie_none(tmp_path: Path) -> None:
    """`par_id` renvoie None pour un identifiant absent (pas d'exception)."""
    db, _ = _base_avec_tournoi(tmp_path)
    try:
        assert DepartRepositorySQL(db.session_factory).par_id(999) is None
    finally:
        db.engine.dispose()


def test_enregistrer_met_a_jour_tarif_et_horaire(tmp_path: Path) -> None:
    """`enregistrer` persiste l'édition du tarif et de l'horaire ; le numéro ne change pas."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = DepartRepositorySQL(db.session_factory)
        cree = repository.ajouter(Depart.creer(tournoi_id, 1, 810, "9h00"))
        assert cree.id is not None

        modifie = repository.enregistrer(cree.modifier(1250, "14h00"))
        assert (modifie.numero, modifie.tarif_centimes, modifie.horaire) == (1, 1250, "14h00")
        assert repository.par_id(cree.id) == modifie
    finally:
        db.engine.dispose()


def test_supprimer_retire_le_depart(tmp_path: Path) -> None:
    """`supprimer` retire la ligne ; `par_id` renvoie ensuite None."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = DepartRepositorySQL(db.session_factory)
        cree = repository.ajouter(Depart.creer(tournoi_id, 1, 810))
        assert cree.id is not None
        repository.supprimer(cree.id)
        assert repository.par_id(cree.id) is None
        assert repository.par_tournoi(tournoi_id) == []
    finally:
        db.engine.dispose()


def test_numero_unique_par_tournoi(tmp_path: Path) -> None:
    """La contrainte `UNIQUE(tournoi_id, numero)` refuse deux créneaux de même numéro (garde-fou).

    Le service attribue les numéros et n'en produit pas de doublon ; cette contrainte est le
    filet ultime, et une violation remonte enveloppée en `InfrastructureError` (jamais brute).
    """
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = DepartRepositorySQL(db.session_factory)
        repository.ajouter(Depart.creer(tournoi_id, 1, 810))
        with pytest.raises(InfrastructureError):
            repository.ajouter(Depart.creer(tournoi_id, 1, 900))
    finally:
        db.engine.dispose()
