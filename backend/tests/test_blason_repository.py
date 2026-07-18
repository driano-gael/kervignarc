"""Tests d'intégration du repository SQL des blasons (E01US005).

Exerce l'adapter sur une **vraie base** créée par les migrations (`alembic upgrade head`) :
persistance, relecture, absence (None), listing par tournoi, mise à jour et suppression.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from domain.blason import ZONES_DEFAUT, Blason
from domain.tournoi import Tournoi
from infrastructure.db import (
    BlasonRepositorySQL,
    Database,
    TournoiRepositorySQL,
)
from infrastructure.db.models import BlasonORM
from infrastructure.erreurs import InfrastructureError

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
        repository = BlasonRepositorySQL(db.session_factory)
        cree = repository.ajouter(Blason.creer(tournoi_id, "Trispot 40", 0.5, 3))
        assert cree.id is not None
        assert cree.tournoi_id == tournoi_id
        assert cree.taille == 0.5
        assert cree.capacite == 3
        assert repository.par_id(cree.id) == cree
    finally:
        db.engine.dispose()


def test_par_id_inexistant_renvoie_none(tmp_path: Path) -> None:
    """`par_id` renvoie None pour un identifiant absent (pas d'exception)."""
    db, _ = _base_avec_tournoi(tmp_path)
    try:
        assert BlasonRepositorySQL(db.session_factory).par_id(999) is None
    finally:
        db.engine.dispose()


def test_par_tournoi_liste_dans_l_ordre_de_creation(tmp_path: Path) -> None:
    """`par_tournoi` renvoie les blasons du tournoi, dans l'ordre de création."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = BlasonRepositorySQL(db.session_factory)
        assert repository.par_tournoi(tournoi_id) == []
        repository.ajouter(Blason.creer(tournoi_id, "A", 0.5, 1))
        repository.ajouter(Blason.creer(tournoi_id, "B", 1.0, 2))
        assert [b.nom for b in repository.par_tournoi(tournoi_id)] == ["A", "B"]
    finally:
        db.engine.dispose()


def test_enregistrer_met_a_jour(tmp_path: Path) -> None:
    """`enregistrer` persiste l'édition des attributs."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = BlasonRepositorySQL(db.session_factory)
        cree = repository.ajouter(Blason.creer(tournoi_id, "Ancien", 0.25, 4))
        assert cree.id is not None
        modifie = cree.modifier("Nouveau", 0.5, 2, cree.zones)
        enregistre = repository.enregistrer(modifie)
        assert enregistre.nom == "Nouveau"
        assert enregistre.taille == 0.5
        assert enregistre.capacite == 2
        assert repository.par_id(cree.id) == enregistre
    finally:
        db.engine.dispose()


def test_supprimer_retire_la_ligne(tmp_path: Path) -> None:
    """`supprimer` retire la ligne ; `par_id` renvoie ensuite None."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = BlasonRepositorySQL(db.session_factory)
        cree = repository.ajouter(Blason.creer(tournoi_id, "Monospot", 1.0, 1))
        assert cree.id is not None
        repository.supprimer(cree.id)
        assert repository.par_id(cree.id) is None
        assert repository.par_tournoi(tournoi_id) == []
    finally:
        db.engine.dispose()


def test_les_zones_font_l_aller_retour_json(tmp_path: Path) -> None:
    """Les zones (E01US014) survivent au tour ORM : stockées en JSON, relues en tuple."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = BlasonRepositorySQL(db.session_factory)
        cree = repository.ajouter(
            Blason.creer(tournoi_id, "Trispot 40", 0.5, 3, zones=["10", "9", "8", "7", "6", "M"])
        )
        assert cree.id is not None
        assert cree.zones == ("10", "9", "8", "7", "6", "M")
        assert repository.par_id(cree.id) == cree
    finally:
        db.engine.dispose()


def test_les_zones_par_defaut_sont_persistees(tmp_path: Path) -> None:
    """Un blason créé sans zones persiste le défaut du domaine, pas une valeur vide."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = BlasonRepositorySQL(db.session_factory)
        cree = repository.ajouter(Blason.creer(tournoi_id, "Monospot 60", 1.0, 1))
        assert cree.id is not None
        assert repository.par_id(cree.id) == cree
        assert cree.zones == ZONES_DEFAUT
    finally:
        db.engine.dispose()


def test_enregistrer_met_a_jour_les_zones(tmp_path: Path) -> None:
    """L'édition des zones est bien persistée (E01US014)."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = BlasonRepositorySQL(db.session_factory)
        cree = repository.ajouter(Blason.creer(tournoi_id, "Trispot 40", 0.5, 3))
        modifie = repository.enregistrer(
            cree.modifier("Trispot 40", 0.5, 3, zones=["10", "9", "8", "7", "6", "M"])
        )
        assert cree.id is not None
        assert modifie.zones == ("10", "9", "8", "7", "6", "M")
        assert repository.par_id(cree.id) == modifie
    finally:
        db.engine.dispose()


@pytest.mark.parametrize(
    "zones_en_base",
    [
        pytest.param("pas du json", id="JSON illisible"),
        pytest.param('["10", "X", "M"]', id="JSON valide mais zone hors vocabulaire"),
        pytest.param(
            '{"10": 1}', id="objet JSON : sans coercition, rehydratait ('10',) en silence"
        ),
        pytest.param("null", id="JSON valide mais non iterable"),
    ],
)
def test_zones_corrompues_levent_infrastructure_error(tmp_path: Path, zones_en_base: str) -> None:
    """Une colonne `zones` illisible est enveloppée en `InfrastructureError` (ADR-0007).

    Le repository en est le seul rédacteur : une valeur aberrante est une **incohérence
    technique**, jamais un cas métier. Sans la coercition `ZoneScore(...)`, les deux derniers cas
    réhydrataient un `Blason` **silencieusement invalide** qui aurait piloté le pavé d'EPIC-04.
    Même patron que `test_config_corrompue_leve_infrastructure_error` (gabarits).
    """
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        with db.session_factory() as session:
            session.add(
                BlasonORM(
                    tournoi_id=tournoi_id,
                    nom="Cassé",
                    taille=0.5,
                    capacite=1,
                    zones=zones_en_base,
                )
            )
            session.commit()
        with pytest.raises(InfrastructureError):
            BlasonRepositorySQL(db.session_factory).par_tournoi(tournoi_id)
    finally:
        db.engine.dispose()
